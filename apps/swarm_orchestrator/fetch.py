"""Fetching agent — pulls live prices for a set of queries into the corpus.

Each query carries its route AND the dates to search for (watched criteria keep
the user's depart/return dates; seed routes are date-less). Per query: snapshots
prior history BEFORE recording (so analytics judges against a true baseline),
pulls live offers, and records each as a ``PriceObservation`` tagged with the
query's depart_date. Returns live offers + prior snapshots keyed by route so
analytics can judge without re-fetching. Deterministic API worker (no LLM);
*which* queries to run is decided upstream by the orchestrator/prioritizer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from packages.adapters.src.flights import get_flight_source
from packages.adapters.src.storage import Storage, get_storage
from packages.contracts.src.flight_source import FlightSource
from packages.domain.src import FlightOffer, PriceObservation, Route, SearchQuery
from packages.domain.src.prices import PricesService


@dataclass
class FetchReport:
    """Outcome of one fetch pass, plus the data the analytics step reuses."""

    offers_by_route: dict[Route, list[FlightOffer]] = field(default_factory=dict)
    prior_by_route: dict[Route, list[PriceObservation]] = field(default_factory=dict)
    fetched: list[Route] = field(default_factory=list)
    observations_recorded: int = 0


def collect_prices(
    queries: list[SearchQuery],
    *,
    storage: Optional[Storage] = None,
    source: Optional[FlightSource] = None,
    now: Optional[datetime] = None,
) -> FetchReport:
    """Fetch + record prices for each query; return live offers and prior snapshots.

    Callers should pass at most one query per route (the orchestrator builds one
    representative query per watched route); a duplicate route overwrites its entry.
    """
    storage = storage or get_storage()
    source = source or get_flight_source()
    now = now or datetime.now(timezone.utc)
    prices = PricesService(storage.prices)

    report = FetchReport()
    for query in queries:
        route = Route(query.origin, query.destination)
        # Snapshot history BEFORE recording so the analytics baseline excludes
        # this cycle's prices (see judge_deal's prior_history contract).
        report.prior_by_route[route] = prices.history(route.origin, route.destination)

        offers = source.search(query)
        report.offers_by_route[route] = offers
        if not offers:
            continue

        report.fetched.append(route)
        for o in offers:
            prices.record(PriceObservation(
                origin=o.origin, destination=o.destination, price=o.price,
                observed_at=now, depart_date=query.depart_date, airline=o.airline,
                source=o.source,
            ))
            report.observations_recorded += 1

    return report


__all__ = ["collect_prices", "FetchReport"]
