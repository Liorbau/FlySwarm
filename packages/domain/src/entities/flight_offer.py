"""FlightOffer entity — the canonical shape every flight source maps into.

This is the only flight representation the rest of the swarm (price-drop
analytics, notifications) is allowed to see. Raw vendor JSON and field names
never leave the source adapter; they are mapped into this object.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from packages.domain.src.value_objects.money import Money


@dataclass
class FlightOffer:
    """A single priced flight offer, normalized across providers.

    Required facts are always present; optional facts are ``None`` when a source
    cannot supply them (flagged per-source in the mapping table). All datetimes
    are timezone-aware UTC.
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
