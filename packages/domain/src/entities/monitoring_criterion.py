"""MonitoringCriterion entity — a user's saved request to watch a route.

The Telegram interface agent turns a natural-language request into a canonical
``SearchQuery`` and persists it as a ``MonitoringCriterion``. The scan workflow
later loads active criteria, fetches offers, and judges deal quality against
stored price history.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from packages.domain.src.value_objects.search_query import SearchQuery


@dataclass
class MonitoringCriterion:
    """A persisted request to monitor a route for good deals.

    ``user_id`` identifies the requesting user (e.g. a Telegram chat id).
    ``query`` is the canonical search to run. ``target_price`` is an optional
    hard threshold in ``query.currency``; when set, an offer at or below it is a
    deal regardless of history. ``id`` and ``created_at`` are assigned by the
    repository on save.
    """

    user_id: str
    query: SearchQuery
    target_price: Optional[float] = None
    label: Optional[str] = None  # original NL text / human-friendly label
    active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
