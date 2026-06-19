"""Prices domain service — recording and reading the observed-price corpus.

Harvesting calls ``record``; analytics reads ``history``/``lowest_seen``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from packages.domain.src import PriceObservation

from .repository import PriceRepository


class PricesService:
    def __init__(self, prices: PriceRepository) -> None:
        self._prices = prices

    def record(self, observation: PriceObservation) -> PriceObservation:
        return self._prices.record(observation)

    def history(
        self, origin: str, destination: str, *,
        since: Optional[datetime] = None, limit: int = 100,
    ) -> list[PriceObservation]:
        return self._prices.history(origin, destination, since=since, limit=limit)

    def lowest_seen(
        self, origin: str, destination: str, *, since: Optional[datetime] = None,
    ) -> Optional[PriceObservation]:
        """Cheapest observation on record for a route (analytics helper)."""
        observations = self._prices.history(origin, destination, since=since, limit=1000)
        if not observations:
            return None
        return min(observations, key=lambda o: o.price.amount)


__all__ = ["PricesService"]
