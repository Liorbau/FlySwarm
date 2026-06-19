"""PriceObservation entity — one historical price point for a route.

Recorded each scan to build the history deal-judgment compares against.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from packages.domain.src.value_objects.money import Money


@dataclass
class PriceObservation:
    """A single observed price for a route at a point in time.

    All datetimes are timezone-aware UTC. ``id`` is assigned by the repository.
    """

    origin: str
    destination: str
    price: Money
    observed_at: datetime
    depart_date: Optional[str] = None  # YYYY-MM-DD or YYYY-MM, as searched
    airline: Optional[str] = None
    source: Optional[str] = None
    id: Optional[int] = None
