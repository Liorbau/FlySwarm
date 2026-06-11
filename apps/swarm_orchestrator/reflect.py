"""Reflection — turn scan outcomes into stored learnings (self-improving memory).

After a scan, record:
- **wins**  — good deals we surfaced this pass, and
- **lessons** — criteria that expired this pass without ever alerting (e.g. a target
  that was never met), with the lowest price actually seen.

Those learnings are read back by the interface agent (via the route-insight policy)
to give users data-informed guidance — closing the self-improving loop.
"""

from __future__ import annotations

from apps.swarm_orchestrator.scan import ScanReport
from packages.contracts.src.storage import Repository
from packages.domain.src import LESSON, WIN, Learning


def reflect(report: ScanReport, repo: Repository) -> list[Learning]:
    """Record wins (from this scan's deals) and lessons (from expired criteria)."""
    recorded: list[Learning] = []

    for deal in report.deals:
        o = deal.offer
        recorded.append(
            repo.record_learning(
                Learning(
                    kind=WIN,
                    origin=o.origin,
                    destination=o.destination,
                    text=(
                        f"Surfaced a deal {o.origin}->{o.destination} at "
                        f"{o.price.amount:.0f} {o.price.currency} (score {deal.verdict.score:.2f})."
                    ),
                    data={
                        "price": o.price.amount,
                        "currency": o.price.currency,
                        "score": deal.verdict.score,
                        "criterion_id": deal.criterion.id,
                    },
                )
            )
        )

    for criterion_id in report.expired:
        crit = repo.get_criterion(criterion_id)
        if crit is None or repo.alerts_for_criterion(criterion_id):
            continue  # never expired-without-alert -> not a lesson

        origin, destination = crit.query.origin, crit.query.destination
        history = repo.price_history(origin, destination, limit=500)
        lowest = min((h.price.amount for h in history), default=None)

        if crit.target_price is not None:
            text = (
                f"Watched {origin}->{destination} until the deadline; target "
                f"{crit.target_price:.0f} never met"
                + (f" (lowest seen {lowest:.0f})." if lowest is not None else " (no prices seen).")
            )
        else:
            text = (
                f"Watched {origin}->{destination} until the deadline with no deal"
                + (f"; lowest seen {lowest:.0f}." if lowest is not None else "; no prices seen.")
            )

        recorded.append(
            repo.record_learning(
                Learning(
                    kind=LESSON,
                    origin=origin,
                    destination=destination,
                    text=text,
                    data={
                        "target": crit.target_price,
                        "lowest_seen": lowest,
                        "criterion_id": criterion_id,
                    },
                )
            )
        )

    return recorded


__all__ = ["reflect"]
