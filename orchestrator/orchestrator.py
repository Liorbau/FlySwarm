"""The orchestrator core: plan -> verify input -> run -> verify output -> report.

Ties together discovery, the planner brain, the isolated skill runner, the
input/output verifier, and a shared token ledger. Honors a total ``token_budget``
across the whole run, supports ``dry_run`` (plan + input-validate only), and a
single capped re-plan when a skill fails mid-run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from packages.adapters.src.llm import get_llm_client

from orchestrator import schema as schema_mod
from orchestrator.discovery import SkillSpec, discover_skills, select_skills
from orchestrator.llm_util import TokenLedger, extract_json, single_completion
from orchestrator.planner import Plan, PlanStep, make_plan
from orchestrator.skill_runner import run_skill
from orchestrator.verifier import Verdict, Verifier

EST_TOKENS_PER_SKILL = 4000
MAX_PRIOR_CONTEXT_CHARS = 4000


@dataclass
class RunConfig:
    goal: str
    token_budget: int
    dry_run: bool = False
    provider: Optional[str] = None
    model: Optional[str] = None
    only: Optional[list[str]] = None
    skip: Optional[list[str]] = None


@dataclass
class SkillRecord:
    name: str
    status: str = "pending"  # planned|ran|skipped|failed|error|budget-stopped
    rationale: str = ""
    input_verdict: Optional[Verdict] = None
    output_verdict: Optional[Verdict] = None
    repair_used: bool = False
    retry_used: bool = False
    tokens: int = 0
    cost_usd: float = 0.0
    note: str = ""
    output: Any = None


@dataclass
class RunResult:
    config: RunConfig
    all_skills: list[SkillSpec]
    invocable: list[SkillSpec]
    selection_notes: list[str]
    plan: Plan
    records: list[SkillRecord] = field(default_factory=list)
    direct_answer: Optional[str] = None
    ledger: Optional[TokenLedger] = None
    final_status: str = "unknown"
    estimated_tokens: int = 0


class Orchestrator:
    def __init__(self, config: RunConfig):
        self.config = config
        self.client = get_llm_client(
            provider_override=config.provider,
            model_override=config.model,
        )
        self.ledger = TokenLedger(budget=config.token_budget)
        self.verifier = Verifier(self.client, self.ledger)

    # ── entry point ──────────────────────────────────────────────────────────

    def run(self) -> RunResult:
        cfg = self.config
        all_skills = discover_skills()
        invocable, notes = select_skills(all_skills, only=cfg.only, skip=cfg.skip)

        plan = make_plan(self.client, self.ledger, cfg.goal, invocable)
        spec_by_name = {s.name: s for s in invocable}

        result = RunResult(
            config=cfg,
            all_skills=all_skills,
            invocable=invocable,
            selection_notes=notes,
            plan=plan,
            ledger=self.ledger,
        )

        if not plan.steps:
            result.direct_answer = plan.direct_answer or "(no skills selected and no direct answer)"
            result.final_status = "answered_directly"
            return result

        if cfg.dry_run:
            self._dry_run(plan, spec_by_name, result)
            return result

        self._execute(plan, spec_by_name, invocable, result)
        return result

    # ── dry run ──────────────────────────────────────────────────────────────

    def _dry_run(self, plan: Plan, spec_by_name, result: RunResult) -> None:
        est = 0
        for step in plan.steps:
            skill = spec_by_name.get(step.skill)
            if skill is None:
                continue
            rec = SkillRecord(name=step.skill, status="planned", rationale=step.rationale)
            rec.input_verdict = self.verifier.verify_input(skill, step.input)
            rec.note = "would skip (input invalid)" if not rec.input_verdict.ok else "would run"
            est += EST_TOKENS_PER_SKILL
            result.records.append(rec)
        result.estimated_tokens = est
        result.final_status = "dry_run"

    # ── real execution ───────────────────────────────────────────────────────

    def _execute(self, plan: Plan, spec_by_name, invocable, result: RunResult) -> None:
        steps: list[PlanStep] = list(plan.steps)
        prior_outputs: dict[str, Any] = {}
        replanned = False
        i = 0

        while i < len(steps):
            step = steps[i]
            i += 1
            skill = spec_by_name.get(step.skill)
            if skill is None:
                continue

            if self.ledger.over_budget:
                result.records.append(
                    SkillRecord(name=step.skill, status="budget-stopped",
                                rationale=step.rationale, note="token budget reached")
                )
                result.final_status = "stopped_token_budget"
                return

            rec = SkillRecord(name=step.skill, rationale=step.rationale)
            result.records.append(rec)

            # ── input gate (repair once, else skip) ──
            current_input = step.input
            verdict = self.verifier.verify_input(skill, current_input)
            if not verdict.ok:
                repaired = self._repair_input(skill, current_input, verdict.reason, prior_outputs)
                rec.repair_used = True
                if repaired is not None:
                    current_input = repaired
                    verdict = self.verifier.verify_input(skill, current_input)
            rec.input_verdict = verdict
            if not verdict.ok:
                rec.status = "skipped"
                rec.note = "input invalid after repair attempt"
                continue

            # ── run (retry once on bad output) ──
            prior_context = self._prior_context(prior_outputs)
            sr = run_skill(
                skill, current_input,
                token_cap=self.ledger.remaining,
                prior_context=prior_context,
                provider_override=self.config.provider,
                model=self.config.model,
            )
            self.ledger.add(f"skill:{skill.name}", sr.total_tokens, sr.cost_usd)
            rec.tokens += sr.total_tokens
            rec.cost_usd += sr.cost_usd

            out_verdict = self.verifier.verify_output(skill, sr.output)
            if not out_verdict.ok and not self.ledger.over_budget:
                rec.retry_used = True
                feedback = (
                    f"{prior_context}\n\nYOUR PREVIOUS OUTPUT WAS REJECTED: "
                    f"{out_verdict.reason}. Fix it and return a valid result."
                ).strip()
                sr = run_skill(
                    skill, current_input,
                    token_cap=self.ledger.remaining,
                    prior_context=feedback,
                    provider_override=self.config.provider,
                    model=self.config.model,
                )
                self.ledger.add(f"skill:{skill.name}:retry", sr.total_tokens, sr.cost_usd)
                rec.tokens += sr.total_tokens
                rec.cost_usd += sr.cost_usd
                out_verdict = self.verifier.verify_output(skill, sr.output)

            rec.output_verdict = out_verdict
            rec.output = sr.output

            if out_verdict.ok:
                rec.status = "ran"
                prior_outputs[skill.name] = sr.output
            else:
                rec.status = "failed"
                rec.note = sr.error or "output rejected after retry"
                # One capped re-plan of the remaining steps after a failure.
                if not replanned and i < len(steps) and not self.ledger.over_budget:
                    replanned = True
                    new_plan = make_plan(
                        self.client, self.ledger, self.config.goal, invocable,
                        prior_context=self._prior_context(prior_outputs, failures=[skill.name]),
                    )
                    if new_plan.steps:
                        steps = steps[:i] + new_plan.steps

        result.final_status = self._summary_status(result.records)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _repair_input(self, skill, bad_input, reason, prior_outputs) -> Optional[dict]:
        system = (
            "You repair a skill's input so it satisfies the required schema. "
            "Respond with ONLY a JSON object for the corrected input."
        )
        user = (
            f"GOAL:\n{self.config.goal}\n\n"
            f"SKILL: {skill.name} — {skill.description}\n\n"
            f"REQUIRED INPUT SCHEMA:\n{schema_mod.describe(skill.input_specs)}\n\n"
            f"CURRENT (INVALID) INPUT:\n{json.dumps(bad_input, default=str)}\n\n"
            f"WHY IT WAS REJECTED: {reason}\n\n"
            f"CONTEXT FROM PRIOR SKILLS:\n{self._prior_context(prior_outputs)}"
        )
        stats = single_completion(self.client, system, user)
        self.ledger.add("repair", stats.total_tokens, stats.cost_usd)
        parsed = extract_json(stats.content)
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _prior_context(prior_outputs: dict, failures: Optional[list[str]] = None) -> str:
        if not prior_outputs and not failures:
            return ""
        payload = {"completed": prior_outputs}
        if failures:
            payload["failed"] = failures
        try:
            text = json.dumps(payload, indent=2, default=str)
        except (TypeError, ValueError):
            text = str(payload)
        if len(text) > MAX_PRIOR_CONTEXT_CHARS:
            text = text[:MAX_PRIOR_CONTEXT_CHARS] + "\n... (truncated)"
        return text

    @staticmethod
    def _summary_status(records: list[SkillRecord]) -> str:
        statuses = {r.status for r in records}
        if statuses == {"ran"}:
            return "completed"
        if "failed" in statuses or "error" in statuses or "skipped" in statuses:
            return "completed_with_issues"
        return "completed"
