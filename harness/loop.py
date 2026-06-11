import json
import os
import warnings
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
from typing import Optional

from dotenv import load_dotenv
from litellm import completion_cost, token_counter

from harness.tools import CODING_TOOLS, ToolSet
from packages.adapters.src.llm import get_llm_client

load_dotenv()

SYSTEM_PROMPT = """You are a helpful AI agent working to satisfy a user's request.
You have access to tools — use them when needed.

When giving a final response (not a tool call), respond with valid JSON:
{
  "thought": "your internal reasoning about what to do next",
  "response": "your message to the user",
  "satisfied": true or false
}

Set "satisfied" to true only when you have fully addressed the user's request.
"""

DEFAULT_TOKEN_LIMIT = int(os.getenv("HARNESS_TOKEN_LIMIT", "24000"))
DEFAULT_COMPACT_AT = int(os.getenv("HARNESS_COMPACT_AT", "18000"))
DEFAULT_COMPACT_WORDS = int(os.getenv("HARNESS_COMPACT_WORDS", "120"))
DEFAULT_MAX_NO_PROGRESS_STEPS = int(os.getenv("HARNESS_MAX_NO_PROGRESS_STEPS", "2"))


class AgentHarness:
    def __init__(
        self,
        model: Optional[str] = None,
        provider_override: Optional[str] = None,
        token_limit: Optional[int] = None,
        compact_at: Optional[int] = None,
        compact_words: Optional[int] = None,
        max_no_progress_steps: Optional[int] = None,
        tools: Optional[ToolSet] = None,
        system_prompt: Optional[str] = None,
    ):
        self.client = get_llm_client(
            provider_override=provider_override,
            model_override=model,
        )
        self.model = getattr(self.client, "model", model or "unknown")

        # Pluggable tool pack + system prompt. Defaults preserve the original
        # coding-agent behavior; the product agent injects its own ToolSet.
        self.tools = tools or CODING_TOOLS
        self.system_prompt = system_prompt or SYSTEM_PROMPT
        self.token_limit = token_limit or DEFAULT_TOKEN_LIMIT
        self.compact_at = compact_at or DEFAULT_COMPACT_AT
        self.compact_words = compact_words or DEFAULT_COMPACT_WORDS
        self.max_no_progress_steps = max_no_progress_steps or DEFAULT_MAX_NO_PROGRESS_STEPS

        if self.compact_at >= self.token_limit:
            self.compact_at = int(self.token_limit * 0.8)
        self.compact_at = max(1, self.compact_at)
        self.token_limit = max(self.compact_at + 1, self.token_limit)

        self.messages:   list[dict] = []
        self.trajectory: list[dict] = []

        self.metadata = {
            "step_count":               0,
            "tool_call_count":          0,
            "tool_call_counts":         {},   # per-tool breakdown
            "compaction_count":         0,
            "context_tokens_current":   0,
            "total_prompt_tokens":      0,
            "total_completion_tokens":  0,
            "total_tokens_used":        0,
            "total_cost_usd":           0.0,
            "status":                   "running",
        }

    # ── token counting ─────────────────────────────────────────────────────────

    def _estimate_context_tokens(self) -> int:
        prompt_messages = [{"role": "system", "content": self.system_prompt}] + self.messages
        try:
            return int(
                token_counter(
                    model=self.model,
                    messages=prompt_messages,
                    tools=self.tools.schemas,
                )
            )
        except TypeError:
            return int(token_counter(model=self.model, messages=prompt_messages))
        except Exception:
            # Fallback estimate when model-specific tokenizers are unavailable.
            rough_chars = len(json.dumps(prompt_messages)) + len(json.dumps(self.tools.schemas))
            return max(1, rough_chars // 4)

    # ── compaction ─────────────────────────────────────────────────────────────

    def _compact(self) -> None:
        before = self._estimate_context_tokens()
        print(
            f"\n[Compaction] Context at ~{before} tokens "
            f"(limit {self.token_limit}) — summarizing..."
        )

        history = "\n".join(
            f"{m['role'].upper()}: {m.get('content', '')}"
            for m in self.messages if m.get("content")
        )

        result = self.client.complete(
            messages=[{
                "role": "user",
                "content": (
                    f"Summarize the conversation below in {self.compact_words} words or fewer. "
                    "Keep all key facts, decisions, and results. Be concise.\n\n"
                    f"{history}"
                ),
            }],
        )
        summary = (result.message.content or "").strip()
        self._track_usage(result)

        self.messages = [{
            "role": "user",
            "content": f"[Compacted context — summary of prior conversation]: {summary}",
        }]

        self.metadata["compaction_count"] += 1
        after = self._estimate_context_tokens()

        self.trajectory.append({
            "type":             "compaction",
            "step":             self.metadata["step_count"],
            "tokens_before":    before,
            "tokens_after":     after,
            "compaction_index": self.metadata["compaction_count"],
            "summary":          summary,
        })

        print(f"[Compaction #{self.metadata['compaction_count']}] "
              f"{before} → {after} tokens. Summary: {summary[:80]}...")

    # ── LLM call ───────────────────────────────────────────────────────────────

    def _track_usage(self, result) -> None:
        usage = result.usage
        self.metadata["total_prompt_tokens"] += usage.prompt_tokens
        self.metadata["total_completion_tokens"] += usage.completion_tokens
        self.metadata["total_tokens_used"] += usage.total_tokens
        self.metadata["total_cost_usd"] += self._completion_cost(result)

    def _completion_cost(self, result) -> float:
        getter = getattr(self.client, "get_completion_cost", None)
        if callable(getter):
            try:
                return float(getter(result))
            except Exception:
                pass

        if getattr(result, "raw", None) is None:
            return 0.0
        try:
            return float(completion_cost(completion_response=result.raw))
        except Exception:
            return 0.0

    def _call_llm(self):
        ctx = self._estimate_context_tokens()
        self.metadata["context_tokens_current"] = ctx
        print(f"[Tokens] context={ctx}  used={self.metadata['total_tokens_used']}  "
              f"compactions={self.metadata['compaction_count']}")

        if ctx >= self.compact_at:
            self._compact()
            self.metadata["context_tokens_current"] = self._estimate_context_tokens()

        if self.metadata["context_tokens_current"] >= self.token_limit:
            print(
                f"[Warning] Context is above token limit "
                f"({self.metadata['context_tokens_current']} >= {self.token_limit})."
            )

        result = self.client.complete(
            messages=[{"role": "system", "content": self.system_prompt}] + self.messages,
            tools=self.tools.schemas,
            tool_choice="auto",
        )
        self._track_usage(result)
        self.metadata["context_tokens_current"] = result.usage.prompt_tokens
        return result.message

    # ── main loop ──────────────────────────────────────────────────────────────

    def run(self, user_request: str, max_steps: int = 10, interactive: bool = True) -> None:
        self.messages.append({"role": "user", "content": user_request})
        satisfied = False
        no_progress_steps = 0

        while not satisfied and self.metadata["step_count"] < max_steps:
            self.metadata["step_count"] += 1
            step = self.metadata["step_count"]
            print(f"\n--- Step {step}/{max_steps} ---")

            message = self._call_llm()

            if message.tool_calls:
                no_progress_steps = 0
                self.messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": tc.arguments},
                        }
                        for tc in message.tool_calls
                    ],
                })

                for tc in message.tool_calls:
                    name = tc.name
                    self.metadata["tool_call_count"] += 1
                    self.metadata["tool_call_counts"][name] = (
                        self.metadata["tool_call_counts"].get(name, 0) + 1
                    )
                    args   = json.loads(tc.arguments)
                    result = self._execute_tool(tc)

                    print(f"[Tool]    {name}({args})")
                    print(f"[Result]  {result}")

                    self.trajectory.append({
                        "type": "tool_call", "step": step,
                        "tool": name, "args": args, "result": result,
                        "meta": dict(self.metadata),
                    })

                    self.messages.append({
                        "role": "tool", "tool_call_id": tc.id, "content": result,
                    })

            else:
                try:
                    parsed = json.loads(message.content or "")
                except json.JSONDecodeError:
                    parsed = {"thought": "", "response": message.content, "satisfied": False}

                thought        = parsed.get("thought", "")
                agent_response = parsed.get("response", "")
                satisfied      = parsed.get("satisfied", False)

                self.trajectory.append({
                    "type": "response", "step": step,
                    "thought": thought, "response": agent_response, "satisfied": satisfied,
                    "meta": dict(self.metadata),
                })

                self.messages.append({"role": "assistant", "content": agent_response})

                print(f"[Thought]    {thought}")
                print(f"[Agent]      {agent_response}")
                print(f"[Satisfied]  {satisfied}")

                if not satisfied and interactive:
                    follow_up = input("\nYour reply (or Enter to let agent continue): ").strip()
                    if follow_up:
                        self.messages.append({"role": "user", "content": follow_up})
                        no_progress_steps = 0
                    else:
                        no_progress_steps += 1
                elif not satisfied and not interactive:
                    no_progress_steps += 1

                if (
                    not satisfied
                    and no_progress_steps >= self.max_no_progress_steps
                ):
                    print(
                        "[Warning] Stopping early: no tool progress in "
                        f"{no_progress_steps} consecutive assistant responses."
                    )
                    self.metadata["status"] = "stalled_no_progress"
                    break

        if self.metadata["status"] == "running":
            self.metadata["status"] = "satisfied" if satisfied else "max_steps_reached"

        if satisfied:
            print(f"\n=== Agent satisfied — completed in {self.metadata['step_count']} step(s) ===")
        else:
            print(f"\n=== Max steps ({max_steps}) reached — not fully satisfied ===")
            last = next((e for e in reversed(self.trajectory) if e["type"] == "response"), None)
            if last:
                print(f"Last response: {last['response']}")

    def _execute_tool(self, tool_call) -> str:
        name = tool_call.name
        args = json.loads(tool_call.arguments)
        fn   = self.tools.registry.get(name)
        if fn is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        return fn(args)

    # ── reporting ──────────────────────────────────────────────────────────────

    def get_run_log(self) -> str:
        m = self.metadata

        tool_breakdown = "\n".join(
            f"    {name}: {count}"
            for name, count in m["tool_call_counts"].items()
        ) or "    (none)"

        compaction_lines = ""
        for entry in self.trajectory:
            if entry["type"] == "compaction":
                compaction_lines += (
                    f"\n    #{entry['compaction_index']} at step {entry['step']}: "
                    f"{entry['tokens_before']} → {entry['tokens_after']} tokens"
                )

        return (
            "\n╔══════════════════════════════════════╗"
            "\n║           E2E TEST RUN LOG           ║"
            "\n╚══════════════════════════════════════╝"
            f"\n  Status:              {m['status'].upper()}"
            f"\n  Steps completed:     {m['step_count']}"
            f"\n  Tool calls total:    {m['tool_call_count']}"
            f"\n  Per-tool breakdown:\n{tool_breakdown}"
            f"\n  Compactions:         {m['compaction_count']}"
            + (compaction_lines if compaction_lines else "")
            + f"\n\n  Token Usage:"
            f"\n    Prompt tokens:     {m['total_prompt_tokens']:,}"
            f"\n    Completion tokens: {m['total_completion_tokens']:,}"
            f"\n    Total tokens:      {m['total_tokens_used']:,}"
            f"\n\n  Estimated Cost (LiteLLM):"
            f"\n    Total:   ${m['total_cost_usd']:.6f}"
            f"\n\n  Limits:"
            f"\n    Token limit:       {self.token_limit:,}"
            f"\n    Compact at:        {self.compact_at:,}"
            f"\n    Compact words:     {self.compact_words:,}"
        )

    def print_trajectory(self) -> None:
        print("\n=== Trajectory Log ===")
        for entry in self.trajectory:
            if entry["type"] == "compaction":
                print(f"\nStep {entry['step']} [Compaction #{entry['compaction_index']}]")
                print(f"  Tokens:  {entry['tokens_before']} → {entry['tokens_after']}")
                print(f"  Summary: {entry['summary']}")
            elif entry["type"] == "tool_call":
                print(f"\nStep {entry['step']} [Tool Call]")
                print(f"  Tool:    {entry['tool']}")
                print(f"  Args:    {entry['args']}")
                print(f"  Result:  {entry['result']}")
            else:
                print(f"\nStep {entry['step']} [Response]")
                print(f"  Thought:   {entry['thought']}")
                print(f"  Response:  {entry['response']}")
                print(f"  Satisfied: {entry['satisfied']}")


if __name__ == "__main__":
    harness = AgentHarness()
    user_request = input("Insert request: ").strip()
    harness.run(user_request, interactive=True)
    harness.print_trajectory()
    print(harness.get_run_log())
