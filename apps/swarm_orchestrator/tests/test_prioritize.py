"""Offline tests for the orchestrator route-prioritizer."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest

from apps.swarm_orchestrator.prioritize import prioritize_routes
from apps.swarm_orchestrator.tests.helpers import NOW
from packages.adapters.src.storage.sqlite import SqliteStorage
from packages.domain.src import Money, PriceObservation, Route

R_FRESH = Route("TLV", "LON")   # observed recently -> should be skipped
R_STALE = Route("TLV", "PAR")   # observed long ago -> stale
R_NEVER = Route("TLV", "ROM")   # never observed -> stalest
CANDIDATES = [R_FRESH, R_STALE, R_NEVER]


class FakeLLM:
    def __init__(self, content: str):
        self._content = content

    def complete(self, messages=None):
        return SimpleNamespace(message=SimpleNamespace(content=self._content))


@pytest.fixture()
def storage():
    s = SqliteStorage(":memory:")
    s.initialize()
    s.prices.record(PriceObservation("TLV", "LON", Money(300, "USD"), observed_at=NOW - timedelta(hours=1)))
    s.prices.record(PriceObservation("TLV", "PAR", Money(200, "USD"), observed_at=NOW - timedelta(hours=48)))
    yield s
    s.close()


def test_deterministic_skips_fresh_and_orders_stalest_first(storage):
    out = prioritize_routes(
        CANDIDATES, storage=storage, budget=5, now=NOW, freshness_hours=6, use_llm=False
    )
    assert R_FRESH not in out                 # freshness-skip
    assert out == [R_NEVER, R_STALE]          # never-seen first, then stalest


def test_budget_caps_result(storage):
    out = prioritize_routes(
        CANDIDATES, storage=storage, budget=1, now=NOW, freshness_hours=6, use_llm=False
    )
    assert out == [R_NEVER]


def test_zero_budget_returns_nothing(storage):
    assert prioritize_routes(CANDIDATES, storage=storage, budget=0, now=NOW, use_llm=False) == []


def test_llm_ranking_is_honored(storage):
    client = FakeLLM('{"routes": ["TLV-PAR", "TLV-ROM"]}')
    out = prioritize_routes(
        CANDIDATES, storage=storage, budget=5, now=NOW, freshness_hours=6,
        use_llm=True, client=client,
    )
    assert out == [R_STALE, R_NEVER]          # order from the LLM, fresh still excluded


def test_demand_refreshes_popular_routes_first(storage):
    # R_FRESH was seen recently but is highly watched -> demand outranks staleness.
    out = prioritize_routes(
        CANDIDATES, storage=storage, budget=2, now=NOW, freshness_hours=None,
        use_llm=False, demand={R_FRESH: 5},
    )
    assert out[0] == R_FRESH      # most-watched refreshed first
    assert len(out) == 2


def test_no_freshness_skip_when_none(storage):
    # freshness_hours=None -> even the freshly-seen route is a candidate (watched tier)
    out = prioritize_routes(
        CANDIDATES, storage=storage, budget=5, now=NOW, freshness_hours=None, use_llm=False
    )
    assert set(out) == set(CANDIDATES)        # nothing skipped
    assert out[0] == R_NEVER                  # still stalest-first


def test_llm_garbage_falls_back_to_deterministic(storage):
    client = FakeLLM("not json at all")
    out = prioritize_routes(
        CANDIDATES, storage=storage, budget=5, now=NOW, freshness_hours=6,
        use_llm=True, client=client,
    )
    assert out == [R_NEVER, R_STALE]
