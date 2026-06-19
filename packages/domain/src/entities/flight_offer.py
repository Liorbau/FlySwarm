"""FlightOffer entity — the canonical shape every flight source maps into.

The only flight representation the rest of the swarm sees; vendor JSON never escapes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from packages.domain.src.value_objects.money import Money


@dataclass
class FlightOffer:
    """A single priced flight offer, normalized across providers.

    Optional facts are ``None`` when a source can't supply them; datetimes are UTC.
    """

    origin: str
    destination: str
    departure_at: datetime
    price: Money
    booking_link: str
    source: str

    return_at: Optional[datetime] = None
    airline: Optional[str] = None
    flight_number: Optional[str] = None
    stops: Optional[int] = None
    observed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
