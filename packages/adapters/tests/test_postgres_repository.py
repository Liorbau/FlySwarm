"""Integration tests for the Postgres storage bundle.

These prove the per-domain repos round-trip canonical domain objects against a
real Postgres (e.g. Supabase) — the contract semantics themselves are covered
offline by ``test_sqlite_repository``.

Auto-skipped unless ``DATABASE_URL`` is set, and isolated in a throwaway schema
(``flyswarm_test_<pid>``, dropped on teardown) so they never touch real tables.

Run locally::

    SWARM_STORAGE_BACKEND=postgres pytest packages/adapters/tests/test_postgres_repository.py
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from dotenv import load_dotenv

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

load_dotenv()  # mirror the app: read DATABASE_URL from .env (git-ignored)
DATABASE_URL = os.getenv("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="DATABASE_URL not set; skipping Postgres integration tests"
)


@pytest.fixture()
def repo():
    # Late import so the psycopg dependency is only required when these run.
    from packages.adapters.src.storage.postgres import PostgresStorage

    schema = f"flyswarm_test_{os.getpid()}"
    r = PostgresStorage(DATABASE_URL, schema=schema)
    # Start from a clean schema even if a prior run died before teardown.
    with r._pool.connection() as conn:
        conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    r.initialize()
    yield r
    with r._pool.connection() as conn:
        conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
    r.close()


def test_save_and_get_criterion_roundtrips(repo):
    saved = repo.criteria.save(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery(origin="tlv", destination="lon", depart_date="2026-07-15"),
            target_price=300.0,
            label="cheap London in July",
        )
    )
    assert saved.id is not None
    assert saved.created_at is not None

    fetched = repo.criteria.get(saved.id)
    assert fetched is not None
    assert fetched.user_id == "u1"
    assert fetched.query.origin == "TLV"  # normalized by SearchQuery
    assert fetched.query.destination == "LON"
    assert fetched.target_price == 300.0
    assert fetched.label == "cheap London in July"
    assert fetched.active is True


def test_list_active_and_deactivate(repo):
    a = repo.criteria.save(MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "LON")))
    b = repo.criteria.save(MonitoringCriterion(user_id="u2", query=SearchQuery("TLV", "NYC")))

    assert {c.id for c in repo.criteria.list_active()} == {a.id, b.id}
    assert [c.id for c in repo.criteria.list_active(user_id="u1")] == [a.id]

    repo.criteria.deactivate(a.id)
    assert [c.id for c in repo.criteria.list_active()] == [b.id]
    assert repo.criteria.get(a.id).active is False


def test_due_criteria_excludes_expired_and_inactive(repo):
    now = datetime(2026, 6, 11, tzinfo=timezone.utc)
    future = repo.criteria.save(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "LON"),
            expires_at=now + timedelta(days=10),
        )
    )
    repo.criteria.save(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "NYC"),
            expires_at=now - timedelta(days=1),
        )
    )
    no_expiry = repo.criteria.save(
        MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "PAR"))
    )

    due_ids = {c.id for c in repo.criteria.due(now=now)}
    assert due_ids == {future.id, no_expiry.id}


def test_deactivate_expired_stops_overdue_only(repo):
    now = datetime(2026, 6, 11, tzinfo=timezone.utc)
    overdue = repo.criteria.save(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "LON"),
            expires_at=now - timedelta(hours=1),
        )
    )
    alive = repo.criteria.save(
        MonitoringCriterion(
            user_id="u1",
            query=SearchQuery("TLV", "NYC"),
            expires_at=now + timedelta(days=5),
        )
    )

    stopped = repo.criteria.deactivate_expired(now=now)
    assert stopped == [overdue.id]
    assert repo.criteria.get(overdue.id).active is False
    assert repo.criteria.get(alive.id).active is True


def test_price_history_orders_newest_first_and_filters_since(repo):
    base = datetime(2026, 6, 1, tzinfo=timezone.utc)
    for i in range(3):
        repo.prices.record(
            PriceObservation(
                origin="TLV",
                destination="LON",
                price=Money(amount=300 + i, currency="USD"),
                observed_at=base + timedelta(days=i),
            )
        )
    repo.prices.record(
        PriceObservation("TLV", "NYC", Money(900, "USD"), observed_at=base)
    )

    history = repo.prices.history("tlv", "lon")
    assert [o.price.amount for o in history] == [302.0, 301.0, 300.0]  # newest first
    assert all(o.destination == "LON" for o in history)

    since = base + timedelta(days=1)
    recent = repo.prices.history("TLV", "LON", since=since)
    assert [o.price.amount for o in recent] == [302.0, 301.0]


def test_alert_dedup_and_recent(repo):
    crit = repo.criteria.save(MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "LON")))
    assert repo.alerts.was_alerted(crit.id, "offer-abc") is False

    repo.alerts.record(
        Alert(
            criterion_id=crit.id,
            offer_key="offer-abc",
            price=Money(250, "USD"),
            deal_score=0.9,
            booking_link="https://example.com/book",
        )
    )
    assert repo.alerts.was_alerted(crit.id, "offer-abc") is True
    assert repo.alerts.was_alerted(crit.id + 999, "offer-abc") is False

    recent = repo.alerts.recent()
    assert len(recent) == 1
    assert recent[0].offer_key == "offer-abc"
    assert recent[0].sent_at is not None


def test_alerts_for_criterion(repo):
    crit = repo.criteria.save(MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "LON")))
    repo.alerts.record(Alert(criterion_id=crit.id, offer_key="k1", price=Money(250, "USD")))
    repo.alerts.record(Alert(criterion_id=crit.id, offer_key="k2", price=Money(240, "USD")))
    repo.alerts.record(Alert(criterion_id=999, offer_key="k3", price=Money(100, "USD")))

    got = repo.alerts.for_criterion(crit.id)
    assert {a.offer_key for a in got} == {"k1", "k2"}


def test_conversation_history_roundtrips_oldest_first(repo):
    repo.conversations.append("chat-1", "user", "hi")
    repo.conversations.append("chat-1", "assistant", "hello!")
    repo.conversations.append("chat-2", "user", "other chat")

    history = repo.conversations.recent("chat-1", limit=8)
    assert [(m.role, m.content) for m in history] == [("user", "hi"), ("assistant", "hello!")]
    assert [m.content for m in repo.conversations.recent("chat-1", limit=1)] == ["hello!"]

    repo.conversations.clear("chat-1")
    assert repo.conversations.recent("chat-1") == []
    assert len(repo.conversations.recent("chat-2")) == 1


def test_record_and_query_learnings_by_kind(repo):
    repo.learnings.record(Learning(kind=WIN, origin="TLV", destination="LON", text="deal at 300", data={"price": 300}))
    repo.learnings.record(Learning(kind=LESSON, origin="TLV", destination="LON", text="target never met"))
    repo.learnings.record(Learning(kind=WIN, origin="TLV", destination="NYC", text="other route"))

    all_route = repo.learnings.for_route("tlv", "lon")
    assert len(all_route) == 2

    lessons = repo.learnings.for_route("TLV", "LON", kind=LESSON)
    assert len(lessons) == 1 and lessons[0].text == "target never met"

    wins = repo.learnings.for_route("TLV", "LON", kind=WIN)
    assert len(wins) == 1 and wins[0].data == {"price": 300}  # JSONB round-trips
