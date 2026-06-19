"""Offline tests for CompositeFlightSource (merge / failover + error isolation)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from packages.adapters.src.flights.composite_source import CompositeFlightSource
from packages.domain.src import FlightOffer, Money, SearchQuery

QUERY = SearchQuery("TLV", "LON")


def _offer(price: float, source: str) -> FlightOffer:
    return FlightOffer(
        origin="TLV",
        destination="LON",
        departure_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        price=Money(price, "USD"),
        booking_link="x",
        source=source,
    )


class Fixed:
    def __init__(self, offers):
        self._offers = offers

    def search(self, query):
        return list(self._offers)


class Broken:
    def search(self, query):
        raise RuntimeError("provider down")


def test_merge_concatenates_all_sources_tagged():
    comp = CompositeFlightSource(
        [Fixed([_offer(300, "travelpayouts")]), Fixed([_offer(280, "duffel")])],
        mode="merge",
    )
    offers = comp.search(QUERY)
    assert {o.source for o in offers} == {"travelpayouts", "duffel"}
    assert min(o.price.amount for o in offers) == 280


def test_merge_isolates_a_failing_source():
    comp = CompositeFlightSource([Broken(), Fixed([_offer(300, "duffel")])], mode="merge")
    offers = comp.search(QUERY)
    assert [o.source for o in offers] == ["duffel"]  # broken one skipped, rest kept


def test_failover_returns_first_non_empty():
    comp = CompositeFlightSource(
        [Fixed([]), Fixed([_offer(300, "duffel")]), Fixed([_offer(1, "never")])],
        mode="failover",
    )
    offers = comp.search(QUERY)
    assert [o.source for o in offers] == ["duffel"]  # stops at first non-empty


def test_failover_skips_a_failing_source():
    comp = CompositeFlightSource([Broken(), Fixed([_offer(300, "duffel")])], mode="failover")
    assert [o.source for o in comp.search(QUERY)] == ["duffel"]


def test_empty_sources_rejected():
    with pytest.raises(ValueError):
        CompositeFlightSource([], mode="merge")
