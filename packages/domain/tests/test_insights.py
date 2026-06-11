"""Tests for the route-insight policy (pure)."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.domain.src import LESSON, Learning, Money, PriceObservation
from packages.domain.src.policies import route_insight_text

NOW = datetime(2026, 6, 11, tzinfo=timezone.utc)


def _hist(*prices):
    return [PriceObservation("TLV", "LON", Money(p, "USD"), observed_at=NOW) for p in prices]


def test_none_when_no_data():
    assert route_insight_text([], []) is None


def test_summarizes_history():
    text = route_insight_text(_hist(400, 350, 360))
    assert "3 prices seen" in text
    assert "low 350" in text and "high 400" in text


def test_warns_when_target_below_lowest():
    text = route_insight_text(_hist(350, 400), target_price=200)
    assert "below the lowest price ever seen" in text


def test_includes_lessons():
    lessons = [Learning(kind=LESSON, text="target 250 never met", origin="TLV", destination="LON")]
    text = route_insight_text(_hist(350), lessons)
    assert "Past lesson: target 250 never met" in text
