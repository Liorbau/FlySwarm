"""Offline integration test for the unified swarm cycle (run_cycle, LLM off).

Proves the single fetch pass serves both purposes: watched routes get judged +
alerted, and seed routes get harvested into the corpus — with the per-cycle
budget bounding seed fetches.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from apps.swarm_orchestrator.orchestrate import run_cycle
from apps.swarm_orchestrator.tests.helpers import NOW, FakeSource
from packages.adapters.src.storage.sqlite import SqliteStorage
from packages.domain.src import MonitoringCriterion, SearchQuery
from packages.shared.src.config import ResolvedHarvestConfig

SOURCE = {("TLV", "LON"): [290.0], ("TLV", "PAR"): [400.0], ("TLV", "ROM"): [350.0]}
SEED = ResolvedHarvestConfig(
    seed_routes=(("TLV", "PAR"), ("TLV", "ROM")),
    max_routes_per_cycle=20,
    freshness_hours=6,
    prioritize_with_llm=False,
)


@pytest.fixture()
def storage():
    s = SqliteStorage(":memory:")
    s.initialize()
    yield s
    s.close()


def test_cycle_alerts_watched_and_harvests_seed(storage):
    storage.criteria.save(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "LON"),
            target_price=300,
            expires_at=NOW + timedelta(days=30),
        )
    )
    report, notifications = run_cycle(
        storage=storage, source=FakeSource(SOURCE), now=NOW, use_llm=False, harvest_config=SEED,
    )

    # watched route -> deal alerted
    assert len(notifications) == 1
    assert notifications[0].user_id == "u1"
    assert "TLV → LON" in notifications[0].text

    # seed routes harvested into the corpus (nobody is watching them)
    assert len(storage.prices.history("TLV", "PAR")) == 1
    assert len(storage.prices.history("TLV", "ROM")) == 1
    # one fetch per route: 1 watched + 2 seed
    assert report.routes_fetched == 3
    assert report.observations_recorded == 3
    assert report.notifications_sent == 1


def test_watched_fetch_uses_criterion_dates(storage):
    # The user's depart_date must reach the flight source AND the recorded observation
    # (regression guard: route-level fetch must not drop per-criterion dates).
    storage.criteria.save(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "LON", depart_date="2026-08"),
            target_price=300,
            expires_at=NOW + timedelta(days=30),
        )
    )
    src = FakeSource({("TLV", "LON"): [290.0]})
    run_cycle(storage=storage, source=src, now=NOW, use_llm=False, harvest_config=SEED)

    watched_q = next(q for q in src.queries if q.destination == "LON")
    assert watched_q.depart_date == "2026-08"
    assert storage.prices.history("TLV", "LON")[0].depart_date == "2026-08"


def test_budget_bounds_seed_fetches(storage):
    storage.criteria.save(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "LON"),
            target_price=300,
            expires_at=NOW + timedelta(days=30),
        )
    )
    tight = ResolvedHarvestConfig(
        seed_routes=SEED.seed_routes, max_routes_per_cycle=1, freshness_hours=6,
        prioritize_with_llm=False,
    )
    report, notifications = run_cycle(
        storage=storage, source=FakeSource(SOURCE), now=NOW, use_llm=False, harvest_config=tight,
    )

    # budget=1 fully consumed by the watched route -> no seed harvested
    assert report.routes_fetched == 1
    assert storage.prices.history("TLV", "PAR") == []
    assert storage.prices.history("TLV", "ROM") == []
    assert len(notifications) == 1  # watched deal still alerted


def test_watched_routes_respect_hard_cap(storage):
    # 3 watched routes but cap=2 -> only 2 fetched, overflow + seed deferred.
    for dest in ("LON", "PAR", "ROM"):
        storage.criteria.save(
            MonitoringCriterion(
                user_id="u1",
                query=SearchQuery("TLV", dest),
                expires_at=NOW + timedelta(days=30),
            )
        )
    cfg = ResolvedHarvestConfig(
        seed_routes=(("TLV", "BCN"),), max_routes_per_cycle=2, freshness_hours=6,
        prioritize_with_llm=False,
    )
    src = FakeSource(
        {("TLV", "LON"): [300.0], ("TLV", "PAR"): [300.0], ("TLV", "ROM"): [300.0], ("TLV", "BCN"): [300.0]}
    )
    report, _ = run_cycle(storage=storage, source=src, now=NOW, use_llm=False, harvest_config=cfg)

    assert report.routes_fetched == 2          # hard ceiling honored
    assert storage.prices.history("TLV", "BCN") == []  # no budget left for seed


def test_expired_criterion_is_autostopped(storage):
    crit = storage.criteria.save(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "NYC"),
            target_price=100,
            expires_at=NOW - timedelta(days=1),  # overdue
        )
    )
    report, notifications = run_cycle(
        storage=storage, source=FakeSource(SOURCE), now=NOW, use_llm=False, harvest_config=SEED,
    )
    assert crit.id in report.expired
    assert storage.criteria.get(crit.id).active is False
    assert notifications == []  # expired route not fetched/judged
