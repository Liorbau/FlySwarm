"""Scan workflow — the recurring heart of the swarm.

For each active, not-yet-expired criterion: fetch live offers, record them into
price history, and judge the best one against that history + the user's target.
Offers judged alert-worthy come back as ``DealResult``s for the notification step
(F3). Overdue criteria are auto-stopped first.

This is deterministic orchestration (a workflow) that *consumes* the judge-deal
skill via ``judge.py``. The scheduler runs it on a cadence to make notifications
"active".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from apps.swarm_orchestrator.judge import DealVerdict, judge_deal
from packages.adapters.src.flights import get_flight_source
from packages.adapters.src.storage import get_repository
from packages.contracts.src.flight_source import FlightSource
from packages.contracts.src.storage import Repository
from packages.domain.src import FlightOffer, MonitoringCriterion, PriceObservation


@dataclass
class DealResult:
    """An alert-worthy offer for a specific criterion."""

    criterion: MonitoringCriterion
    offer: FlightOffer
    verdict: DealVerdict


@dataclass
class ScanReport:
    """Outcome of one scan pass."""

    scanned: int = 0
    offers_seen: int = 0
    expired: list[int] = field(default_factory=list)
    deals: list[DealResult] = field(default_factory=list)


def run_scan(
    *,
    repo: Optional[Repository] = None,
    source: Optional[FlightSource] = None,
    now: Optional[datetime] = None,
    use_llm: bool = True,
    client=None,
) -> ScanReport:
    """Run one scan pass over all due criteria and return the alert-worthy deals."""
    repo = repo or get_repository()
    source = source or get_flight_source()
    now = now or datetime.now(timezone.utc)

    report = ScanReport(expired=repo.deactivate_expired(now=now))

    criteria = repo.due_criteria(now=now)
    report.scanned = len(criteria)

    for crit in criteria:
        offers = source.search(crit.query)
        if not offers:
            continue
        report.offers_seen += len(offers)

        # Read history BEFORE recording the new prices, so the offer is judged
        # against its true baseline (see judge-deal gotchas).
        prior = repo.price_history(crit.query.origin, crit.query.destination)
        best = min(offers, key=lambda o: o.price.amount)

        for o in offers:
            repo.record_observation(
                PriceObservation(
                    origin=o.origin,
                    destination=o.destination,
                    price=o.price,
                    observed_at=now,
                    depart_date=crit.query.depart_date,
                    airline=o.airline,
                    source=o.source,
                )
            )

        verdict = judge_deal(
            best, prior, crit.target_price, use_llm=use_llm, client=client
        )
        if verdict.is_deal:
            report.deals.append(DealResult(criterion=crit, offer=best, verdict=verdict))

    return report


__all__ = ["run_scan", "ScanReport", "DealResult"]
