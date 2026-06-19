"""Shared test helpers for the orchestrator swarm tests."""

from __future__ import annotations

from datetime import datetime, timezone

from packages.domain.src import FlightOffer, Money, SearchQuery

NOW = datetime(2026, 6, 11, tzinfo=timezone.utc)


class FakeSource:
    """A FlightSource stub returning canned offers per (origin, destination)."""

    def __init__(self, by_route: dict[tuple[str, str], list[float]]):
        self.by_route = by_route
        self.calls: list[tuple[str, str]] = []
        self.queries: list[SearchQuery] = []  # full queries seen (to assert dates)

    def search(self, query: SearchQuery) -> list[FlightOffer]:
        self.calls.append((query.origin, query.destination))
        self.queries.append(query)
        prices = self.by_route.get((query.origin, query.destination), [])
        return [
            FlightOffer(
                origin=query.origin,
                destination=query.destination,
                departure_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                price=Money(p, "USD"),
                booking_link="https://example.com",
                source="fake",
            )
            for p in prices
        ]
