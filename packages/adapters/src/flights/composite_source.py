"""Composite flight source — combine several sources behind one FlightSource.

- ``merge``    queries every source and concatenates their offers (each offer
  keeps its own ``source`` tag, so observations record provenance and the
  analytics step judges the cheapest across all of them).
- ``failover`` tries sources in order and returns the first non-empty result.

A single source raising is isolated (logged + skipped) so one provider's outage
never blanks the whole cycle.
"""

from __future__ import annotations

from packages.contracts.src.flight_source import FlightSource
from packages.domain.src import FlightOffer, SearchQuery


class CompositeFlightSource:
    """Concrete ``FlightSource`` delegating to several sub-sources."""

    def __init__(self, sources: list[FlightSource], *, mode: str = "merge") -> None:
        if not sources:
            raise ValueError("CompositeFlightSource needs at least one source.")
        self._sources = list(sources)
        self.mode = mode

    def search(self, query: SearchQuery) -> list[FlightOffer]:
        if self.mode == "failover":
            for source in self._sources:
                try:
                    offers = source.search(query)
                except Exception as exc:  # isolate a flaky provider
                    print(f"[flights] {type(source).__name__} failed (failover): {exc}")
                    continue
                if offers:
                    return offers
            return []

        merged: list[FlightOffer] = []
        for source in self._sources:
            try:
                merged.extend(source.search(query))
            except Exception as exc:  # one source down -> still return the rest
                print(f"[flights] {type(source).__name__} failed (merge): {exc}")
        return merged


__all__ = ["CompositeFlightSource"]
