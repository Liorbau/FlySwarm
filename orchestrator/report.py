"""Render a single, readable run report to stdout (mirrors the harness style)."""

from __future__ import annotations

from orchestrator.orchestrator import RunResult
from orchestrator.verifier import Verdict


def _verdict(v: Verdict | None) -> str:
    if v is None:
        return "—"
    mark = "OK" if v.ok else "REJECT"
    reason = (v.reason or "").strip().replace("\n", " ")
    if len(reason) > 80:
        reason = reason[:77] + "..."
    return f"{mark} ({v.method}): {reason}"


def format_report(result: RunResult) -> str:
    cfg = result.config
    ledger = result.ledger
    lines: list[str] = []

    lines.append("\n╔══════════════════════════════════════════╗")
    lines.append("║         ORCHESTRATOR RUN REPORT          ║")
    lines.append("╚══════════════════════════════════════════╝")
    lines.append(f"  Goal:          {cfg.goal}")
    lines.append(f"  Mode:          {'DRY RUN' if cfg.dry_run else 'EXECUTE'}")
    lines.append(f"  Token budget:  {cfg.token_budget:,}")

    # Catalog
    lines.append("\n  Discovered skills:")
    invocable_names = {s.name for s in result.invocable}
    for s in result.all_skills:
        flags = []
        if s.disable_model_invocation:
            flags.append("disable-model-invocation")
        if not s.has_full_schema:
            flags.append("no/partial schema → LLM fallback")
        if s.schema_error:
            flags.append(f"schema error: {s.schema_error}")
        tag = "selectable" if s.name in invocable_names else "excluded"
        suffix = f" [{', '.join(flags)}]" if flags else ""
        lines.append(f"    - {s.name} ({tag}){suffix}")
    for note in result.selection_notes:
        lines.append(f"      · {note}")

    # Plan
    lines.append("\n  Plan:")
    if result.plan.rationale:
        lines.append(f"    rationale: {result.plan.rationale}")
    if not result.plan.steps:
        lines.append("    (no skills — answering directly)")
    for idx, step in enumerate(result.plan.steps, 1):
        lines.append(f"    {idx}. {step.skill} — {step.rationale}")

    # Direct answer
    if result.direct_answer is not None:
        lines.append("\n  Direct answer (no skills run):")
        lines.append(f"    {result.direct_answer}")

    # Per-skill execution
    if result.records:
        lines.append("\n  Skill execution:")
        for idx, rec in enumerate(result.records, 1):
            lines.append(f"    {idx}. {rec.name}  [{rec.status.upper()}]")
            lines.append(f"        input-gate:  {_verdict(rec.input_verdict)}")
            if not cfg.dry_run:
                lines.append(f"        output-gate: {_verdict(rec.output_verdict)}")
                lines.append(
                    f"        tokens: {rec.tokens:,}  cost: ${rec.cost_usd:.6f}  "
                    f"repair: {rec.repair_used}  retry: {rec.retry_used}"
                )
            if rec.note:
                lines.append(f"        note: {rec.note}")

    # Totals
    lines.append("\n  Totals:")
    if cfg.dry_run:
        lines.append(f"    Estimated skill tokens: ~{result.estimated_tokens:,} (rough)")
        if ledger:
            lines.append(f"    Planning/verify tokens spent: {ledger.total_tokens:,}")
    if ledger:
        lines.append(f"    Total tokens used:  {ledger.total_tokens:,} / {cfg.token_budget:,}")
        lines.append(f"    Total cost (USD):   ${ledger.cost_usd:.6f}")
        if ledger.by_phase:
            lines.append("    By phase:")
            for phase, toks in ledger.by_phase.items():
                lines.append(f"      {phase}: {toks:,}")
    lines.append(f"    Final status:       {result.final_status.upper()}")

    return "\n".join(lines)
