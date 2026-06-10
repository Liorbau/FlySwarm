"""Skill input/output verifier — the "no wasted skill calls" gate.

Precedence (agreed design):

1. If the skill declares a valid schema -> validate **mechanically** (fast/free).
2. Mechanical pass -> proceed.
3. Schema missing/malformed, OR mechanical validation raises unexpectedly ->
   fall back to a lightweight **LLM judge** against the skill's purpose.
4. A clean mechanical *failure* (e.g. required field absent) is FINAL — the LLM
   does not get to override it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from orchestrator import schema as schema_mod
from orchestrator.discovery import SkillSpec
from orchestrator.llm_util import TokenLedger, extract_json, single_completion


@dataclass
class Verdict:
    ok: bool
    reason: str
    method: str  # "mechanical" | "llm" | "error"


class Verifier:
    def __init__(self, client, ledger: TokenLedger):
        self.client = client
        self.ledger = ledger

    # ── public gates ────────────────────────────────────────────────────────

    def verify_input(self, skill: SkillSpec, data: Any) -> Verdict:
        return self._verify(
            specs=skill.input_specs,
            schema_error=skill.schema_error,
            data=data,
            gate="input",
            skill=skill,
        )

    def verify_output(self, skill: SkillSpec, data: Any) -> Verdict:
        return self._verify(
            specs=skill.output_specs,
            schema_error=skill.schema_error,
            data=data,
            gate="output",
            skill=skill,
        )

    # ── core precedence ──────────────────────────────────────────────────────

    def _verify(
        self,
        specs,
        schema_error: Optional[str],
        data: Any,
        gate: str,
        skill: SkillSpec,
    ) -> Verdict:
        if specs is not None and schema_error is None:
            try:
                result = schema_mod.validate(data, specs)
            except Exception as exc:  # mechanical errored unexpectedly -> fallback
                return self._llm_judge(skill, data, gate, note=f"mechanical error: {exc}")
            if result.ok:
                return Verdict(True, "schema valid", "mechanical")
            # Clean mechanical failure is final.
            return Verdict(False, "; ".join(result.errors), "mechanical")

        # No (usable) schema -> LLM fallback.
        reason = schema_error or "no declared schema"
        return self._llm_judge(skill, data, gate, note=reason)

    # ── LLM fallback judge ───────────────────────────────────────────────────

    def _llm_judge(self, skill: SkillSpec, data: Any, gate: str, note: str) -> Verdict:
        try:
            payload = json.dumps(data, default=str)[:2000]
        except (TypeError, ValueError):
            payload = str(data)[:2000]

        if gate == "input":
            question = (
                "Is this INPUT appropriate for the skill AND sufficient for it to "
                "do useful work? Reject if the skill is irrelevant to the input or "
                "the input is too vague/empty to act on."
            )
        else:
            question = (
                "Does this OUTPUT fulfill the skill's stated purpose and look "
                "complete (not an error, refusal, or empty stub)?"
            )

        system = (
            "You are a strict verifier in an agent orchestrator. Judge only what is "
            "asked. Respond with ONLY JSON: {\"valid\": true|false, \"reason\": \"...\"}."
        )
        user = (
            f"Skill name: {skill.name}\n"
            f"Skill purpose: {skill.description}\n\n"
            f"{question}\n\n"
            f"{gate.upper()} under review:\n{payload}"
        )

        stats = single_completion(self.client, system, user)
        self.ledger.add(f"verifier:{gate}", stats.total_tokens, stats.cost_usd)

        parsed = extract_json(stats.content)
        if not isinstance(parsed, dict) or "valid" not in parsed:
            # Be permissive when the judge itself is unparseable: don't block on
            # a flaky judge, but say so.
            return Verdict(True, f"llm judge unparseable, allowing ({note})", "error")

        ok = bool(parsed.get("valid"))
        reason = str(parsed.get("reason") or "").strip() or note
        return Verdict(ok, f"{reason} [fallback: {note}]", "llm")
