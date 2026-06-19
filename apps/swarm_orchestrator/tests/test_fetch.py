"""Offline tests for the Fetching agent (collect_prices)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from apps.swarm_orchestrator.fetch import collect_prices
from apps.swarm_orchestrator.tests.helpers import NOW, FakeSource
from packages.adapters.src.storage.sqlite import SqliteStorage
from packages.domain.src import Money, PriceObservation, Route, SearchQuery


@pytest.fixture()
def storage():
    s = SqliteStorage(":memory:")
    s.initialize()
    yield s
    s.close()


def test_collect_records_observations_and_returns_offers(storage):
    route = Route("TLV", "LON")
    source = FakeSource({("TLV", "LON"): [290.0, 450.0]})

    report = collect_prices([SearchQuery("TLV", "LON")], storage=storage, source=source, now=NOW)

    assert report.fetched == [route]
    assert report.observations_recorded == 2
    assert [o.price.amount for o in report.offers_by_route[route]] == [290.0, 450.0]
    # both offers landed in the corpus
    assert len(storage.prices.history("TLV", "LON")) == 2


def test_query_dates_reach_source_and_observation(storage):
    source = FakeSource({("TLV", "LON"): [290.0]})

    collect_prices(
        [SearchQuery("TLV", "LON", depart_date="2026-08")],
        storage=storage, source=source, now=NOW,
    )

    assert source.queries[0].depart_date == "2026-08"  # date passed to the source
    assert storage.prices.history("TLV", "LON")[0].depart_date == "2026-08"  # and recorded


def test_prior_snapshot_excludes_this_cycle(storage):
    route = Route("TLV", "LON")
    storage.prices.record(
        PriceObservation("TLV", "LON", Money(500, "USD"), observed_at=NOW - timedelta(days=1))
    )
    source = FakeSource({("TLV", "LON"): [290.0]})

    report = collect_prices([SearchQuery("TLV", "LON")], storage=storage, source=source, now=NOW)

    # prior_by_route is the baseline BEFORE this cycle's price was recorded
    assert [o.price.amount for o in report.prior_by_route[route]] == [500.0]
    # corpus now has both the old and the new
    assert len(storage.prices.history("TLV", "LON")) == 2


def test_empty_source_records_nothing_but_is_reported(storage):
    route = Route("TLV", "XXX")
    report = collect_prices([SearchQuery("TLV", "XXX")], storage=storage, source=FakeSource({}), now=NOW)

    assert report.fetched == []
    assert report.observations_recorded == 0
    assert report.offers_by_route[route] == []
