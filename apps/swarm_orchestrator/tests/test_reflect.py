"""Offline tests for the reflection step (wins + lessons)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apps.swarm_orchestrator.judge import DealVerdict
from apps.swarm_orchestrator.reflect import reflect
from apps.swarm_orchestrator.scan import DealResult, ScanReport
from packages.adapters.src.storage.sqlite_repository import SqliteRepository
from packages.domain.src import (
    LESSON,
    WIN,
    Alert,
    FlightOffer,
    Money,
    MonitoringCriterion,
    PriceObservation,
    SearchQuery,
)

NOW = datetime(2026, 6, 11, tzinfo=timezone.utc)


@pytest.fixture()
def repo(tmp_path):
    r = SqliteRepository(tmp_path / "reflect.sqlite3")
    r.initialize()
    yield r
    r.close()


def test_reflect_records_win_for_a_deal(repo):
    crit = repo.save_criterion(MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "LON")))
    offer = FlightOffer(
        origin="TLV",
        destination="LON",
        departure_at=NOW,
        price=Money(290, "USD"),
        booking_link="x",
        source="s",
    )
    report = ScanReport(deals=[DealResult(crit, offer, DealVerdict(True, 0.9, "great"))])

    recorded = reflect(report, repo)
    wins = repo.learnings_for_route("TLV", "LON", kind=WIN)
    assert len(wins) == 1
    assert any(l.kind == WIN for l in recorded)


def test_reflect_records_lesson_for_expired_without_alert(repo):
    crit = repo.save_criterion(
        MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "NYC"), target_price=100)
    )
    repo.record_observation(
        PriceObservation("TLV", "NYC", Money(500, "USD"), observed_at=NOW)
    )
    repo.deactivate_criterion(crit.id)  # simulate expiry

    reflect(ScanReport(expired=[crit.id]), repo)
    lessons = repo.learnings_for_route("TLV", "NYC", kind=LESSON)
    assert len(lessons) == 1
    assert "never met" in lessons[0].text
    assert lessons[0].data["lowest_seen"] == 500.0


def test_no_lesson_when_expired_criterion_had_an_alert(repo):
    crit = repo.save_criterion(MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "PAR")))
    repo.record_alert(Alert(criterion_id=crit.id, offer_key="k", price=Money(200, "USD")))

    reflect(ScanReport(expired=[crit.id]), repo)
    assert repo.learnings_for_route("TLV", "PAR", kind=LESSON) == []
