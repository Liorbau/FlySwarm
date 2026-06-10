"""Flight source contract for FlySwarm (mirrors ``llm_provider.py``).

A single, vendor-neutral interface every agent/orchestrator calls instead of a
provider SDK or raw HTTP. Concrete implementations live in
``packages/adapters/src/flights`` (e.g. a Travelpayouts client); callers depend
only on the ``FlightSource`` protocol below and the canonical domain objects.

The canonical shapes (``FlightOffer``, ``Money``, ``SearchQuery``) live in
``packages/domain`` and are re-exported here for convenience.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from packages.domain.src import FlightOffer, Money, SearchQuery


@runtime_checkable
class FlightSource(Protocol):
    """Vendor-neutral flight search.

    Implementations accept a :class:`SearchQuery` and return canonical
    :class:`FlightOffer` objects only. All vendor parsing stays inside the
    adapter in ``packages/adapters/src/flights``.
    """

    def search(self, query: SearchQuery) -> list[FlightOffer]:
        ...


__all__ = ["FlightSource", "FlightOffer", "Money", "SearchQuery"]
