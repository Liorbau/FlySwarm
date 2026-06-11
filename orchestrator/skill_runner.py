"""Run a single skill as an isolated sub-agent.

Each skill executes in its OWN fresh :class:`AgentHarness` (clean context, full
tool registry), seeded with the skill's SKILL.md body, the validated input, and a
compact summary of relevant prior skill outputs. The sub-agent is told to finish
by returning a JSON object matching the skill's declared output schema so the
verifier can check it mechanically.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from harness.loop import AgentHarness

from orchestrator import schema as schema_mod
from orchestrator.discovery import SkillSpec
from orchestrator.llm_util import extract_json

MIN_SKILL_TOKENS = 3000
SKILL_MAX_STEPS = 8


@dataclass
class SkillResult:
    output: Any                      # parsed JSON output (dict) or raw string
    raw_response: str
    total_tokens: int = 0
    cost_usd: float = 0.0
    steps: int = 0
    status: str = "unknown"
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)


def _output_instruction(skill: SkillSpec) -> str:
    if skill.output_specs:
        return (
            "When finished, set \"satisfied\": true and make the \"response\" field a "
            "JSON OBJECT (as a JSON string) that matches EXACTLY this output schema:\n"
            f"{schema_mod.describe(skill.output_specs)}\n"
            "The \"response\" must be ONLY that JSON object — no prose around it."
        )
    return (
        "When finished, set \"satisfied\": true and put your complete result in the "
        "\"response\" field."
    )


def _build_request(skill: SkillSpec, skill_input: dict, prior_context: str) -> str:
    parts = [
        f"You are executing the '{skill.name}' skill. Follow these skill "
        f"instructions exactly:\n\n{skill.body}",
        "----\nVALIDATED INPUT (already matches the skill's input schema):\n"
        + json.dumps(skill_input, indent=2, default=str),
    ]
    if prior_context:
        parts.append("----\nRELEVANT PRIOR SKILL OUTPUTS (context):\n" + prior_context)
    parts.append("----\n" + _output_instruction(skill))
    return "\n\n".join(parts)


def run_skill(
    skill: SkillSpec,
    skill_input: dict,
    *,
    token_cap: int,
    prior_context: str = "",
    provider_override: Optional[str] = None,
    model: Optional[str] = None,
) -> SkillResult:
    token_limit = max(MIN_SKILL_TOKENS, int(token_cap))
    harness = AgentHarness(
        model=model,
        provider_override=provider_override,
        token_limit=token_limit,
    )

    request = _build_request(skill, skill_input, prior_context)

    try:
        harness.run(request, max_steps=SKILL_MAX_STEPS, interactive=False)
    except Exception as exc:  # never let one skill crash the whole orchestrator
        meta = harness.metadata
        return SkillResult(
            output=None,
            raw_response="",
            total_tokens=meta.get("total_tokens_used", 0),
            cost_usd=meta.get("total_cost_usd", 0.0),
            steps=meta.get("step_count", 0),
            status="error",
            error=str(exc),
            metadata=dict(meta),
        )

    raw_response = ""
    for entry in reversed(harness.trajectory):
        if entry.get("type") == "response":
            raw_response = entry.get("response") or ""
            break

    output: Any = extract_json(raw_response)
    if output is None:
        output = raw_response  # leave as raw; verifier/output-gate will judge

    meta = harness.metadata
    return SkillResult(
        output=output,
        raw_response=raw_response,
        total_tokens=meta.get("total_tokens_used", 0),
        cost_usd=meta.get("total_cost_usd", 0.0),
        steps=meta.get("step_count", 0),
        status=meta.get("status", "unknown"),
        metadata=dict(meta),
    )
