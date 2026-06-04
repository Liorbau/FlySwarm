from __future__ import annotations

import json

from harness.loop import AgentHarness
from packages.contracts.src.llm_provider import (
    AssistantMessage,
    CompletionResult,
    ToolCall,
    Usage,
)


class StubClient:
    def __init__(self) -> None:
        self.model = "openai/gpt-4o-mini"
        self.calls = 0

    def complete(self, messages, tools=None, tool_choice="auto"):
        self.calls += 1
        if self.calls == 1:
            return CompletionResult(
                message=AssistantMessage(
                    content="Planning file write and command run.",
                    tool_calls=[
                        ToolCall(
                            id="tc-1",
                            name="write_file",
                            arguments=json.dumps(
                                {"path": "tmp/out.txt", "content": "hello from harness"}
                            ),
                        ),
                        ToolCall(
                            id="tc-2",
                            name="run_command",
                            arguments=json.dumps(
                                {"command": "pwd", "timeout_seconds": 5}
                            ),
                        ),
                    ],
                ),
                usage=Usage(prompt_tokens=20, completion_tokens=15, total_tokens=35),
                model=self.model,
                raw=None,
            )

        return CompletionResult(
            message=AssistantMessage(
                content=json.dumps(
                    {
                        "thought": "Tools succeeded",
                        "response": "Done.",
                        "satisfied": True,
                    }
                )
            ),
            usage=Usage(prompt_tokens=10, completion_tokens=8, total_tokens=18),
            model=self.model,
            raw=None,
        )


class StubClientNoProgress:
    def __init__(self) -> None:
        self.model = "openai/gpt-4o-mini"

    def complete(self, messages, tools=None, tool_choice="auto"):
        return CompletionResult(
            message=AssistantMessage(
                content=json.dumps(
                    {
                        "thought": "Need user reply",
                        "response": "Please clarify your request.",
                        "satisfied": False,
                    }
                )
            ),
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=self.model,
            raw=None,
        )


def test_loop_noninteractive_smoke(tmp_path, monkeypatch):
    from harness import loop as loop_module
    from harness.tools import run_command, write_file

    monkeypatch.setattr(write_file, "_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(run_command, "_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setattr(loop_module, "get_llm_client", lambda **_: StubClient())

    harness = AgentHarness(token_limit=2000, compact_at=1500, compact_words=60)
    harness.run("Create file and run command", max_steps=4, interactive=False)

    target = tmp_path / "tmp" / "out.txt"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "hello from harness"
    assert harness.metadata["status"] == "satisfied"
    assert harness.metadata["tool_call_count"] >= 2


def test_loop_stops_after_no_progress_threshold(monkeypatch):
    from harness import loop as loop_module

    monkeypatch.setattr(loop_module, "get_llm_client", lambda **_: StubClientNoProgress())

    harness = AgentHarness(
        token_limit=2000,
        compact_at=1500,
        compact_words=60,
        max_no_progress_steps=2,
    )
    harness.run("Do something", max_steps=8, interactive=False)

    assert harness.metadata["status"] == "stalled_no_progress"
    assert harness.metadata["step_count"] == 2
