"""SearchQuery value object — a vendor-neutral flight search request.

Callers (orchestrator/agents) build a ``SearchQuery`` and hand it to any
``FlightSource``; each adapter translates it into vendor-specific params.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SearchQuery:
    """Inputs for a flight search.

    ``origin``/``destination`` are IATA codes; ``depart_date``/``return_date``
    accept ``YYYY-MM-DD`` or ``YYYY-MM``; ``currency`` is ISO 4217 (default USD).
    """

    origin: str
    destination: str
    depart_date: Optional[str] = None
    return_date: Optional[str] = None
    currency: str = "USD"
    one_way: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "origin", str(self.origin).strip().upper())
        object.__setattr__(self, "destination", str(self.destination).strip().upper())
        object.__setattr__(self, "currency", str(self.currency).strip().upper())
