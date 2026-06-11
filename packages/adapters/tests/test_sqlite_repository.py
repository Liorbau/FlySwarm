"""Offline tests for the SQLite repository adapter and storage config resolver.

No network, no shared state: each test uses a fresh temp DB file.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from packages.domain.src import (
    LESSON,
    WIN,
    Alert,
    Learning,
    Money,
    MonitoringCriterion,
    PriceObservation,
    SearchQuery,
)
from packages.adapters.src.storage.sqlite_repository import SqliteRepository
from packages.shared.src.config import resolve_storage_config


@pytest.fixture()
def repo(tmp_path):
    r = SqliteRepository(tmp_path / "sub" / "test.sqlite3")  # nested -> tests mkdir
    r.initialize()
    yield r
    r.close()


def test_save_and_get_criterion_roundtrips(repo):
    saved = repo.save_criterion(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery(origin="tlv", destination="lon", depart_date="2026-07-15"),
            target_price=300.0,
            label="cheap London in July",
        )
    )
    assert saved.id is not None
    assert saved.created_at is not None

    fetched = repo.get_criterion(saved.id)
    assert fetched is not None
    assert fetched.user_id == "u1"
    assert fetched.query.origin == "TLV"  # normalized by SearchQuery
    assert fetched.query.destination == "LON"
    assert fetched.target_price == 300.0
    assert fetched.label == "cheap London in July"
    assert fetched.active is True


def test_list_active_and_deactivate(repo):
    a = repo.save_criterion(MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "LON")))
    b = repo.save_criterion(MonitoringCriterion(user_id="u2", query=SearchQuery("TLV", "NYC")))

    assert {c.id for c in repo.list_active_criteria()} == {a.id, b.id}
    assert [c.id for c in repo.list_active_criteria(user_id="u1")] == [a.id]

    repo.deactivate_criterion(a.id)
    assert [c.id for c in repo.list_active_criteria()] == [b.id]
    # get still returns it, just inactive
    assert repo.get_criterion(a.id).active is False


def test_due_criteria_excludes_expired_and_inactive(repo):
    now = datetime(2026, 6, 11, tzinfo=timezone.utc)
    future = repo.save_criterion(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "LON"),
            expires_at=now + timedelta(days=10),
        )
    )
    repo.save_criterion(  # already expired -> not due
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "NYC"),
            expires_at=now - timedelta(days=1),
        )
    )
    no_expiry = repo.save_criterion(
        MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "PAR"))
    )  # NULL expiry -> always due

    due_ids = {c.id for c in repo.due_criteria(now=now)}
    assert due_ids == {future.id, no_expiry.id}


def test_deactivate_expired_stops_overdue_only(repo):
    now = datetime(2026, 6, 11, tzinfo=timezone.utc)
    overdue = repo.save_criterion(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "LON"),
            expires_at=now - timedelta(hours=1),
        )
    )
    alive = repo.save_criterion(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "NYC"),
            expires_at=now + timedelta(days=5),
        )
    )

    stopped = repo.deactivate_expired(now=now)
    assert stopped == [overdue.id]
    assert repo.get_criterion(overdue.id).active is False
    assert repo.get_criterion(alive.id).active is True


def test_price_history_orders_newest_first_and_filters_since(repo):
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    for i in range(3):
        repo.record_observation(
            PriceObservation(
                origin="TLV",
                destination="LON",
                price=Money(amount=300 + i, currency="USD"),
                observed_at=base + timedelta(days=i),
            )
        )
    # different route should not bleed in
    repo.record_observation(
        PriceObservation("TLV", "NYC", Money(900, "USD"), observed_at=base)
    )

    history = repo.price_history("tlv", "lon")
    assert [o.price.amount for o in history] == [302.0, 301.0, 300.0]  # newest first
    assert all(o.destination == "LON" for o in history)

    since = base + timedelta(days=1)
    recent = repo.price_history("TLV", "LON", since=since)
    assert [o.price.amount for o in recent] == [302.0, 301.0]


def test_alert_dedup_and_recent(repo):
    crit = repo.save_criterion(MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "LON")))
    assert repo.was_alerted(crit.id, "offer-abc") is False

    repo.record_alert(
        Alert(
            criterion_id=crit.id,
            offer_key="offer-abc",
            price=Money(250, "USD"),
            deal_score=0.9,
            booking_link="https://example.com/book",
        )
    )
    assert repo.was_alerted(crit.id, "offer-abc") is True
    # same offer key for a different criterion is not deduped
    assert repo.was_alerted(crit.id + 999, "offer-abc") is False

    recent = repo.recent_alerts()
    assert len(recent) == 1
    assert recent[0].offer_key == "offer-abc"
    assert recent[0].sent_at is not None


def test_alerts_for_criterion(repo):
    crit = repo.save_criterion(MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "LON")))
    repo.record_alert(Alert(criterion_id=crit.id, offer_key="k1", price=Money(250, "USD")))
    repo.record_alert(Alert(criterion_id=crit.id, offer_key="k2", price=Money(240, "USD")))
    repo.record_alert(Alert(criterion_id=999, offer_key="k3", price=Money(100, "USD")))

    got = repo.alerts_for_criterion(crit.id)
    assert {a.offer_key for a in got} == {"k1", "k2"}


def test_record_and_query_learnings_by_kind(repo):
    repo.record_learning(Learning(kind=WIN, origin="TLV", destination="LON", text="deal at 300", data={"price": 300}))
    repo.record_learning(Learning(kind=LESSON, origin="TLV", destination="LON", text="target never met"))
    repo.record_learning(Learning(kind=WIN, origin="TLV", destination="NYC", text="other route"))

    all_route = repo.learnings_for_route("tlv", "lon")
    assert len(all_route) == 2  # both kinds, route-scoped

    lessons = repo.learnings_for_route("TLV", "LON", kind=LESSON)
    assert len(lessons) == 1 and lessons[0].text == "target never met"

    wins = repo.learnings_for_route("TLV", "LON", kind=WIN)
    assert len(wins) == 1 and wins[0].data == {"price": 300}  # JSON round-trips


def test_resolve_storage_config_defaults_to_sqlite():
    cfg = resolve_storage_config()
    assert cfg.backend == "sqlite"
    assert "sqlite_path" in cfg.options
