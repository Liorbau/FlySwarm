"""Interface agent — turns natural-language travel requests into saved criteria.

The harness loop (``AgentHarness``) wearing a *product* tool pack: same reasoning
/ token budgeting, different capabilities. Parses fuzzy requests, resolves cities
to IATA codes and relative dates, then persists a ``MonitoringCriterion``. Built
per user so its tools are bound to that user's id.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from apps.telegram_bot.tools.criteria_tools import build_criteria_toolset
from harness.loop import AgentHarness
from packages.adapters.src.storage import Storage, get_storage

INTERFACE_SYSTEM_PROMPT = """You are FlySwarm's flight-monitoring assistant. Users \
send natural-language travel requests; your job is to turn each into a saved \
monitoring criterion (or to list/stop their existing ones).

Today's date is {today} (UTC). Resolve relative dates ("in August", "next month", \
"this weekend") against it. Never produce a date in the past.

Extract from the user's message:
- origin and destination as IATA city/airport codes (Tel Aviv -> TLV, London -> \
LON, New York -> NYC, Paris -> PAR, Rome -> ROM). Pick the main metropolitan code.
- optional depart_date / return_date as YYYY-MM-DD, or YYYY-MM for a flexible month.
- optional target_price (budget) and currency (default USD).

Rules:
- You MUST have BOTH origin and destination before saving. If either is missing or \
genuinely ambiguous, ask ONE brief clarifying question and do NOT call \
save_criterion yet.
- Before saving, you MAY call route_insight(origin, destination, target_price) to \
see what the swarm has learned about the route (typical prices, past lessons). If \
the user's target looks unrealistic (e.g. below the lowest price ever seen), briefly \
say so and suggest a more realistic number — but still save what they asked for \
unless they change it. If nothing is known yet, just save.
- Once you have origin + destination, call save_criterion with whatever optional \
fields you parsed; pass the user's original phrasing as `label`.
- Use list_criteria / deactivate_criterion when the user asks what they're tracking \
or to stop one.
- After a tool succeeds, confirm in plain, friendly language what you set up.

Always reply with VALID JSON ONLY, in this exact shape:
{{
  "thought": "your private reasoning",
  "response": "the message shown to the user",
  "satisfied": true or false
}}
Set "satisfied" to true only once the request is fully handled (criterion saved, \
question answered, or list/stop done). Set it to false when you still need \
information from the user."""


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def build_interface_agent(
    user_id: str,
    *,
    storage: Optional[Storage] = None,
    today: Optional[str] = None,
    **harness_kwargs: Any,
) -> AgentHarness:
    """Build a per-user interface agent (harness loop + product tools)."""
    storage = storage or get_storage()
    toolset = build_criteria_toolset(storage, user_id)
    system_prompt = INTERFACE_SYSTEM_PROMPT.format(today=today or _today_iso())
    return AgentHarness(tools=toolset, system_prompt=system_prompt, **harness_kwargs)


def handle_message(
    user_id: str,
    text: str,
    *,
    storage: Optional[Storage] = None,
    today: Optional[str] = None,
    history: Optional[list[dict]] = None,
    max_steps: int = 6,
) -> dict:
    """Run one user message through the interface agent and return the result.

    Pass ``history`` (a list of ``{"role", "content"}`` turns) to carry prior
    conversation context across messages so clarifying questions work. Returns the
    response, whether the agent considered itself done, status, and tool breakdown.
    """
    agent = build_interface_agent(user_id, storage=storage, today=today)
    if history:
        agent.messages = list(history)
    agent.run(text, max_steps=max_steps, interactive=False)

    last = next((e for e in reversed(agent.trajectory) if e["type"] == "response"), None)
    return {
        "response": last["response"] if last else "",
        "satisfied": bool(last["satisfied"]) if last else False,
        "status": agent.metadata["status"],
        "tool_calls": dict(agent.metadata["tool_call_counts"]),
        "cost_usd": agent.metadata["total_cost_usd"],
    }


__all__ = ["build_interface_agent", "handle_message", "INTERFACE_SYSTEM_PROMPT"]
