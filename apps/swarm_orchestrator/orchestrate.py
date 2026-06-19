"""Orchestrator — one swarm cycle coordinating the agents.

A single pass fetches prices once per route (growing the corpus and feeding deal
detection). Per cycle:
  1. auto-stop expired criteria; collect the routes of all DUE criteria (watched).
  2. watched routes are ALWAYS fetched; remaining API budget goes to seed routes
     the LLM prioritizer picks (freshness-skipped, stalest-first).
  3. Fetching agent pulls + records prices for the chosen routes.
  4. Analytics judges due criteria against the fetched offers -> deals.
  5. Notification composes/dedupes alerts; Reflection records wins/lessons.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from apps.swarm_orchestrator.evaluate import CycleReport, evaluate_deals
from apps.swarm_orchestrator.fetch import collect_prices
from apps.swarm_orchestrator.notify import Notification, build_notifications
from apps.swarm_orchestrator.prioritize import prioritize_routes
from apps.swarm_orchestrator.reflect import reflect
from packages.adapters.src.flights import get_flight_source
from packages.adapters.src.storage import Storage, get_storage
from packages.domain.src import Route, SearchQuery
from packages.domain.src.watches import WatchesService
from packages.shared.src.config import ResolvedHarvestConfig, resolve_harvest_config


def run_cycle(
    *,
    storage: Optional[Storage] = None,
    source=None,
    now: Optional[datetime] = None,
    use_llm: bool = True,
    client=None,
    harvest_config: Optional[ResolvedHarvestConfig] = None,
) -> tuple[CycleReport, list[Notification]]:
    """Run one full swarm cycle; return the report and the alerts to deliver."""
    storage = storage or get_storage()
    source = source or get_flight_source()
    now = now or datetime.now(timezone.utc)
    cfg = harvest_config or resolve_harvest_config()
    watches = WatchesService(storage.criteria)

    expired = watches.deactivate_expired(now=now)
    due = watches.due(now=now)
    # Demand = how many users watch each route (highly-asked -> refresh more often).
    demand = Counter(Route(c.query.origin, c.query.destination) for c in due)
    watched_routes = list(demand)
    watched_set = set(watched_routes)
    # Representative query per watched route — carries the user's depart/return dates
    # through fetch + judging so deals match the dates requested. (If the same route
    # is watched with different dates, the first due criterion's dates are used.)
    query_by_route: dict[Route, SearchQuery] = {}
    for c in due:
        query_by_route.setdefault(Route(c.query.origin, c.query.destination), c.query)

    # max_routes_per_cycle is a HARD ceiling on API CALLS PER CYCLE (a provider
    # rate-limit throttle — NOT a data cap; nothing is ever deleted). Watched routes
    # get the budget first, ordered by demand then staleness, never freshness-skipped;
    # any overflow is simply refreshed on a later cycle.
    budget = cfg.max_routes_per_cycle
    watched_selected = prioritize_routes(
        watched_routes, storage=storage, budget=budget, now=now,
        freshness_hours=None, use_llm=False, demand=demand,
    )

    # Seed routes nobody is watching fill whatever budget remains (freshness-skipped,
    # LLM-prioritized).
    seed_routes = [
        Route(o, d) for (o, d) in cfg.seed_routes if Route(o, d) not in watched_set
    ]
    seed_selected = prioritize_routes(
        seed_routes,
        storage=storage,
        budget=budget - len(watched_selected),
        now=now,
        freshness_hours=cfg.freshness_hours,
        use_llm=use_llm and cfg.prioritize_with_llm,
        client=client,
    )

    # Watched routes search with the user's dates; seed routes are date-less.
    queries = [query_by_route[r] for r in watched_selected]
    queries += [SearchQuery(origin=r.origin, destination=r.destination) for r in seed_selected]
    fetch_report = collect_prices(queries, storage=storage, source=source, now=now)

    deals = evaluate_deals(due, fetch_report, use_llm=use_llm, client=client)
    notifications = build_notifications(deals, storage)

    report = CycleReport(
        deals=deals,
        expired=expired,
        routes_fetched=len(fetch_report.fetched),
        observations_recorded=fetch_report.observations_recorded,
        notifications_sent=len(notifications),
    )
    reflect(report, storage)
    return report, notifications


__all__ = ["run_cycle"]
