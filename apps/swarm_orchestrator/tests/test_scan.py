"""Offline tests for the scan workflow (fake flight source, LLM disabled)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from apps.swarm_orchestrator.scan import run_scan
from packages.adapters.src.storage.sqlite_repository import SqliteRepository
from packages.domain.src import FlightOffer, Money, MonitoringCriterion, SearchQuery

NOW = datetime(2026, 6, 11, tzinfo=timezone.utc)


class FakeSource:
    """A FlightSource stub returning canned offers per route."""

    def __init__(self, by_route: dict[tuple[str, str], list[float]]):
        self.by_route = by_route

    def search(self, query: SearchQuery) -> list[FlightOffer]:
        prices = self.by_route.get((query.origin, query.destination), [])
        return [
            FlightOffer(
                origin=query.origin,
                destination=query.destination,
                departure_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                price=Money(p, "USD"),
                booking_link="https://example.com",
                source="fake",
            )
            for p in prices
        ]


@pytest.fixture()
def repo(tmp_path):
    r = SqliteRepository(tmp_path / "scan.sqlite3")
    r.initialize()
    yield r
    r.close()


def test_scan_flags_target_met_and_records_history(repo):
    repo.save_criterion(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "LON", depart_date="2026-08"),
            target_price=300,
            expires_at=NOW + timedelta(days=30),
        )
    )
    source = FakeSource({("TLV", "LON"): [290.0, 450.0]})

    report = run_scan(repo=repo, source=source, now=NOW, use_llm=False)

    assert report.scanned == 1
    assert report.offers_seen == 2
    assert len(report.deals) == 1
    assert report.deals[0].offer.price.amount == 290.0  # cheapest chosen
    # both offers recorded into history
    assert len(repo.price_history("TLV", "LON")) == 2


def test_scan_skips_and_autostops_expired(repo):
    repo.save_criterion(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "NYC"),
            target_price=100,
            expires_at=NOW - timedelta(days=1),  # overdue
        )
    )
    source = FakeSource({("TLV", "NYC"): [50.0]})

    report = run_scan(repo=repo, source=source, now=NOW, use_llm=False)

    assert report.scanned == 0  # not due
    assert len(report.expired) == 1  # auto-stopped
    assert report.deals == []


def test_scan_no_deal_when_not_improved(repo):
    repo.save_criterion(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "PAR"),
            target_price=None,
            expires_at=NOW + timedelta(days=30),
        )
    )
    # seed prior history with a cheaper price than what the source now returns
    from packages.domain.src import PriceObservation

    repo.record_observation(
        PriceObservation("TLV", "PAR", Money(200, "USD"), observed_at=NOW - timedelta(days=1))
    )
    source = FakeSource({("TLV", "PAR"): [260.0]})  # not a new low, no target

    report = run_scan(repo=repo, source=source, now=NOW, use_llm=False)
    assert report.deals == []
