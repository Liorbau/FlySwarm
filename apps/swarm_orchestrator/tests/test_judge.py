"""Offline tests for the deterministic deal-judgment gate (LLM disabled)."""

from __future__ import annotations

from datetime import datetime, timezone

from apps.swarm_orchestrator.judge import judge_deal
from packages.domain.src import FlightOffer, Money, PriceObservation

NOW = datetime(2026, 6, 11, tzinfo=timezone.utc)


def _offer(price: float) -> FlightOffer:
    return FlightOffer(
        origin="TLV",
        destination="LON",
        departure_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        price=Money(price, "USD"),
        booking_link="https://example.com",
        source="travelpayouts",
    )


def _hist(*prices: float) -> list[PriceObservation]:
    return [
        PriceObservation("TLV", "LON", Money(p, "USD"), observed_at=NOW) for p in prices
    ]


def test_target_met_is_a_deal():
    v = judge_deal(_offer(250), _hist(400, 380), target_price=300, use_llm=False)
    assert v.is_deal is True and v.target_met is True


def test_new_low_is_a_deal_without_target():
    v = judge_deal(_offer(310), _hist(400, 350, 360), target_price=None, use_llm=False)
    assert v.is_deal is True and v.is_new_best is True


def test_above_target_and_not_a_new_low_is_not_a_deal():
    v = judge_deal(_offer(370), _hist(350, 360), target_price=300, use_llm=False)
    assert v.is_deal is False


def test_first_sighting_no_target_is_not_a_deal():
    v = judge_deal(_offer(500), _hist(), target_price=None, use_llm=False)
    assert v.is_deal is False
    assert v.is_new_best is False  # no baseline -> not a "new" low
