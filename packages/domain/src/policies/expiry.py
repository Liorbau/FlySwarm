"""Criterion expiry policy — when to stop monitoring a route.

A monitoring criterion is watched until its travel deadline passes (or the user
stops it manually). The deadline is derived from the search date:

- full date ``YYYY-MM-DD`` -> end of that day (UTC),
- month only ``YYYY-MM``   -> end of that month (UTC),
- no date                  -> ``created_at`` + a default horizon (90 days).

Pure and vendor-neutral: callers compute the expiry and persist it; the scan
loop and scheduler use it to skip/auto-stop overdue criteria.
"""

from __future__ import annotations

import calendar
from datetime import datetime, time, timedelta, timezone

from packages.domain.src.value_objects.search_query import SearchQuery

DEFAULT_HORIZON_DAYS = 90


def _end_of_day(year: int, month: int, day: int) -> datetime:
    return datetime.combine(
        datetime(year, month, day).date(), time.max, tzinfo=timezone.utc
    )


def compute_expiry(
    query: SearchQuery,
    created_at: datetime,
    *,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
) -> datetime:
    """Return the UTC datetime after which ``query`` should no longer be monitored."""
    date_text = (query.depart_date or "").strip()

    # YYYY-MM-DD
    try:
        parsed = datetime.strptime(date_text, "%Y-%m-%d")
        return _end_of_day(parsed.year, parsed.month, parsed.day)
    except ValueError:
        pass

    # YYYY-MM -> last day of that month
    try:
        parsed = datetime.strptime(date_text, "%Y-%m")
        last_day = calendar.monthrange(parsed.year, parsed.month)[1]
        return _end_of_day(parsed.year, parsed.month, last_day)
    except ValueError:
        pass

    # no usable date -> horizon from creation
    base = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    return base.astimezone(timezone.utc) + timedelta(days=horizon_days)


__all__ = ["compute_expiry", "DEFAULT_HORIZON_DAYS"]
