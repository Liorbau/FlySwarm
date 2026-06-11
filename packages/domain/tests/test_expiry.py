"""Tests for the criterion expiry policy."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.domain.src import SearchQuery
from packages.domain.src.policies import compute_expiry

CREATED = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)


def test_full_date_expires_end_of_that_day():
    q = SearchQuery("TLV", "LON", depart_date="2026-07-15")
    exp = compute_expiry(q, CREATED)
    assert exp.year == 2026 and exp.month == 7 and exp.day == 15
    assert exp.hour == 23 and exp.minute == 59  # end of day
    assert exp.tzinfo is not None


def test_month_only_expires_end_of_month():
    q = SearchQuery("TLV", "LON", depart_date="2026-08")
    exp = compute_expiry(q, CREATED)
    assert (exp.year, exp.month, exp.day) == (2026, 8, 31)  # August has 31 days


def test_no_date_uses_horizon_from_creation():
    q = SearchQuery("TLV", "LON")
    exp = compute_expiry(q, CREATED, horizon_days=90)
    assert (exp - CREATED).days == 90


def test_february_leap_year_end_of_month():
    q = SearchQuery("TLV", "LON", depart_date="2028-02")  # 2028 is a leap year
    exp = compute_expiry(q, CREATED)
    assert (exp.year, exp.month, exp.day) == (2028, 2, 29)
