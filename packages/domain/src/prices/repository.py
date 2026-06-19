"""Repository port for the prices domain (the observed-price corpus).

Append-only, route-keyed market data; engine-neutral.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from packages.domain.src import PriceObservation


@runtime_checkable
class PriceRepository(Protocol):
    """Persistence for observed prices (the historical corpus)."""

    def record(self, observation: PriceObservation) -> PriceObservation:
        """Persist one observed price, returning it with ``id`` set."""
        ...

    def history(
        self, origin: str, destination: str, *,
        since: Optional[datetime] = None, limit: int = 100,
    ) -> list[PriceObservation]:
        """Observations for a route, newest first, optionally since a cutoff."""
        ...


__all__ = ["PriceRepository"]
