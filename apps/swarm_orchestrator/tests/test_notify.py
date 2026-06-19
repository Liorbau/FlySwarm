"""Offline tests for notification composition + de-duplication."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from apps.swarm_orchestrator.judge import DealVerdict
from apps.swarm_orchestrator.notify import build_notifications, format_message, offer_key
from apps.swarm_orchestrator.evaluate import DealResult
from packages.adapters.src.storage.sqlite import SqliteStorage
from packages.domain.src import FlightOffer, Money, MonitoringCriterion, SearchQuery


@pytest.fixture()
def storage(tmp_path):
    s = SqliteStorage(tmp_path / "notify.sqlite3")
    s.initialize()
    yield s
    s.close()


def _deal(storage) -> DealResult:
    crit = storage.criteria.save(
        MonitoringCriterion(user_id="u1", query=SearchQuery("TLV", "LON"), target_price=400)
    )
    offer = FlightOffer(
        origin="TLV",
        destination="LON",
        departure_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        price=Money(314, "USD"),
        booking_link="https://www.aviasales.com/search/TLV0108LON1?marker=738534",
        source="travelpayouts",
        airline="W6",
    )
    verdict = DealVerdict(is_deal=True, score=0.9, reason="Well below your target.", target_met=True)
    return DealResult(criterion=crit, offer=offer, verdict=verdict)


def test_build_notifications_records_alert_and_composes(storage):
    deal = _deal(storage)
    notes = build_notifications([deal], storage)

    assert len(notes) == 1
    n = notes[0]
    assert n.user_id == "u1"
    assert "TLV → LON" in n.text
    assert "314 USD" in n.text
    assert "marker=738534" in n.booking_link
    assert "Well below your target." in n.text
    # the alert was recorded (so it won't repeat)
    assert storage.alerts.was_alerted(deal.criterion.id, n.offer_key) is True


def test_notifications_are_deduped_across_passes(storage):
    deal = _deal(storage)
    first = build_notifications([deal], storage)
    second = build_notifications([deal], storage)  # same offer again

    assert len(first) == 1
    assert second == []  # already alerted -> no repeat


def test_offer_key_is_stable_and_route_specific():
    offer = FlightOffer(
        origin="TLV",
        destination="LON",
        departure_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        price=Money(314.0, "USD"),
        booking_link="x",
        source="s",
        airline="W6",
    )
    assert offer_key(offer) == offer_key(offer)
    assert "TLV-LON" in offer_key(offer)
    assert "314USD" in offer_key(offer)
