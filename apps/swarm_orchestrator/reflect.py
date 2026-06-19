"""Reflection — turn scan outcomes into stored learnings (self-improving memory).

After a scan, record **wins** (good deals surfaced this pass) and **lessons**
(criteria that expired without ever alerting, with the lowest price seen). The
interface agent reads these back (via the route-insight policy) to give users
data-informed guidance — closing the self-improving loop.
"""

from __future__ import annotations

from apps.swarm_orchestrator.evaluate import CycleReport
from packages.adapters.src.storage import Storage
from packages.domain.src import LESSON, WIN, Learning
from packages.domain.src.alerts import AlertsService
from packages.domain.src.learnings import LearningsService
from packages.domain.src.prices import PricesService
from packages.domain.src.watches import WatchesService


def reflect(report: CycleReport, storage: Storage) -> list[Learning]:
    """Record wins (from this scan's deals) and lessons (from expired criteria)."""
    watches = WatchesService(storage.criteria)
    prices = PricesService(storage.prices)
    alerts = AlertsService(storage.alerts)
    learnings = LearningsService(storage.learnings)
    recorded: list[Learning] = []

    for deal in report.deals:
        o = deal.offer
        recorded.append(
            learnings.record(
                Learning(
                    kind=WIN,
                    origin=o.origin,
                    destination=o.destination,
                    text=(
                        f"Surfaced a deal {o.origin}->{o.destination} at "
                        f"{o.price.amount:.0f} {o.price.currency} (score {deal.verdict.score:.2f})."
                    ),
                    data={
                        "price": o.price.amount, "currency": o.price.currency,
                        "score": deal.verdict.score, "criterion_id": deal.criterion.id,
                    },
                )
            )
        )

    for criterion_id in report.expired:
        crit = watches.get(criterion_id)
        if crit is None or alerts.for_criterion(criterion_id):
            continue  # never expired-without-alert -> not a lesson

        origin, destination = crit.query.origin, crit.query.destination
        history = prices.history(origin, destination, limit=500)
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
            learnings.record(
                Learning(
                    kind=LESSON,
                    origin=origin,
                    destination=destination,
                    text=text,
                    data={
                        "target": crit.target_price, "lowest_seen": lowest,
                        "criterion_id": criterion_id,
                    },
                )
            )
        )

    return recorded


__all__ = ["reflect"]
