"""Offline tests for the SQLite repository adapter and storage config resolver.

No network, no shared state: each test uses a fresh temp DB file.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from packages.domain.src import (
    Alert,
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


def test_resolve_storage_config_defaults_to_sqlite():
    cfg = resolve_storage_config()
    assert cfg.backend == "sqlite"
    assert "sqlite_path" in cfg.options
