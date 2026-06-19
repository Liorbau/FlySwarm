"""MonitoringCriterion entity — a user's saved request to watch a route.

A persisted ``SearchQuery`` the scan workflow loads to fetch and judge offers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from packages.domain.src.value_objects.search_query import SearchQuery


@dataclass
class MonitoringCriterion:
    """A persisted request to monitor a route for good deals.

    ``target_price`` is an optional hard threshold in ``query.currency``; ``id``
    and ``created_at`` are assigned by the repository on save.
    """

    user_id: str
    query: SearchQuery
    target_price: Optional[float] = None
    label: Optional[str] = None  # original NL text / human-friendly label
    active: bool = True
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # stop monitoring after this (see policies.expiry)
