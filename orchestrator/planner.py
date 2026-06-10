"""The orchestration brain: plan which skills (if any) to use for a goal.

A single planner LLM call produces an ordered plan over the *invocable* skill
catalog. Choosing zero skills (answering directly) is a valid plan. The same
function is reused for the capped re-plan when a skill fails mid-run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from orchestrator import schema as schema_mod
from orchestrator.discovery import SkillSpec
from orchestrator.llm_util import TokenLedger, extract_json, single_completion


@dataclass
class PlanStep:
    skill: str
    input: dict[str, Any]
    rationale: str = ""


@dataclass
class Plan:
    direct_answer: Optional[str] = None
    steps: list[PlanStep] = field(default_factory=list)
    rationale: str = ""
    raw: str = ""


_SYSTEM = (
    "You are the planning brain of a skill orchestrator. Given a user GOAL and a "
    "catalog of available skills, decide which skills (if any) to run, in what "
    "order, and what input to give each. Using NO skills (answering directly) is a "
    "valid and often correct choice — do not invent work. Only choose skills from "
    "the catalog by their exact name. Each step's input must match that skill's "
    "input schema.\n\n"
    "Respond with ONLY JSON of this exact shape:\n"
    "{\n"
    '  "rationale": "one or two sentences on the overall approach",\n'
    '  "direct_answer": "answer text if no skills are needed, else null",\n'
    '  "plan": [\n'
    '    {"skill": "<exact-name>", "input": { ... }, "rationale": "why this skill"}\n'
    "  ]\n"
    "}"
)


def _catalog_text(skills: list[SkillSpec]) -> str:
    if not skills:
        return "(no invocable skills available)"
    blocks = []
    for s in skills:
        blocks.append(
            f"### {s.name}\n"
            f"{s.description}\n"
            f"input schema:\n{schema_mod.describe(s.input_specs)}\n"
            f"output schema:\n{schema_mod.describe(s.output_specs)}"
        )
    return "\n\n".join(blocks)


def make_plan(
    client,
    ledger: TokenLedger,
    goal: str,
    skills: list[SkillSpec],
    prior_context: str = "",
) -> Plan:
    user = f"GOAL:\n{goal}\n\nAVAILABLE SKILLS:\n{_catalog_text(skills)}"
    if prior_context:
        user += (
            "\n\nWORK ALREADY DONE (revise the remaining plan accordingly; do not "
            f"repeat completed work):\n{prior_context}"
        )

    stats = single_completion(client, _SYSTEM, user)
    ledger.add("planner", stats.total_tokens, stats.cost_usd)

    parsed = extract_json(stats.content)
    if not isinstance(parsed, dict):
        return Plan(direct_answer=stats.content or "(planner returned no plan)", raw=stats.content)

    valid_names = {s.name for s in skills}
    steps: list[PlanStep] = []
    for item in parsed.get("plan") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("skill", "")).strip()
        if name not in valid_names:
            continue  # ignore hallucinated/non-invocable skills
        raw_input = item.get("input")
        step_input = raw_input if isinstance(raw_input, dict) else {}
        steps.append(
            PlanStep(skill=name, input=step_input, rationale=str(item.get("rationale", "")))
        )

    direct = parsed.get("direct_answer")
    direct_answer = str(direct).strip() if direct not in (None, "", "null") else None

    return Plan(
        direct_answer=direct_answer if not steps else None,
        steps=steps,
        rationale=str(parsed.get("rationale", "")),
        raw=stats.content,
    )
