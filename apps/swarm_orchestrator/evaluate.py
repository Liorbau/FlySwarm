"""Analytics evaluation — judge watched criteria against freshly fetched offers.

The deal-detection half of the cycle. For each due criterion, judges that route's
best offer against its prior baseline + the user's target via ``judge_deal``. No
fetching or recording happens here — the Fetching agent owns that.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from apps.swarm_orchestrator.fetch import FetchReport
from apps.swarm_orchestrator.judge import DealVerdict, judge_deal
from packages.domain.src import FlightOffer, MonitoringCriterion, Route


@dataclass
class DealResult:
    """An alert-worthy offer for a specific criterion."""

    criterion: MonitoringCriterion
    offer: FlightOffer
    verdict: DealVerdict


@dataclass
class CycleReport:
    """Outcome of one full swarm cycle (consumed by reflection + logging)."""

    deals: list[DealResult] = field(default_factory=list)
    expired: list[int] = field(default_factory=list)
    routes_fetched: int = 0
    observations_recorded: int = 0
    notifications_sent: int = 0


def evaluate_deals(
    criteria: list[MonitoringCriterion],
    fetch_report: FetchReport,
    *,
    use_llm: bool = True,
    client=None,
) -> list[DealResult]:
    """Judge each due criterion against the offers the fetcher pulled this cycle."""
    deals: list[DealResult] = []
    for crit in criteria:
        route = Route(crit.query.origin, crit.query.destination)
        offers = fetch_report.offers_by_route.get(route)
        if not offers:
            continue  # route wasn't fetched this cycle (e.g. source returned nothing)
        best = min(offers, key=lambda o: o.price.amount)
        prior = fetch_report.prior_by_route.get(route, [])
        verdict = judge_deal(best, prior, crit.target_price, use_llm=use_llm, client=client)
        if verdict.is_deal:
            deals.append(DealResult(criterion=crit, offer=best, verdict=verdict))
    return deals


__all__ = ["DealResult", "CycleReport", "evaluate_deals"]
