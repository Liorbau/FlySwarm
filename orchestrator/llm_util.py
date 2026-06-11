"""LLM helpers for the orchestrator's own reasoning (planner + verifier).

Skill execution goes through the existing :class:`AgentHarness`. The orchestrator
itself only needs cheap single-shot JSON completions plus a shared token/cost
ledger so the whole run can respect one ``--token-budget``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class CompletionStats:
    content: str
    total_tokens: int
    cost_usd: float


@dataclass
class TokenLedger:
    """Aggregates token + cost usage across planner, verifier and all skills."""

    budget: int
    total_tokens: int = 0
    cost_usd: float = 0.0
    by_phase: dict[str, int] = field(default_factory=dict)

    def add(self, phase: str, tokens: int, cost: float) -> None:
        self.total_tokens += int(tokens)
        self.cost_usd += float(cost)
        self.by_phase[phase] = self.by_phase.get(phase, 0) + int(tokens)

    @property
    def remaining(self) -> int:
        return self.budget - self.total_tokens

    @property
    def over_budget(self) -> bool:
        return self.total_tokens >= self.budget


def single_completion(client, system: str, user: str) -> CompletionStats:
    """One system+user completion; returns content and usage."""
    result = client.complete(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = (result.message.content or "").strip()
    usage = result.usage
    cost = 0.0
    getter = getattr(client, "get_completion_cost", None)
    if callable(getter):
        try:
            cost = float(getter(result))
        except Exception:
            cost = 0.0
    return CompletionStats(content=content, total_tokens=int(usage.total_tokens), cost_usd=cost)


def extract_json(text: str) -> Optional[Any]:
    """Best-effort parse of a JSON object/array from an LLM reply.

    Handles raw JSON, ```json fenced blocks, and leading/trailing prose.
    """
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    return None
