"""Route value object — a normalized, hashable origin→destination IATA pair."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    origin: str
    destination: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "origin", self.origin.strip().upper())
        object.__setattr__(self, "destination", self.destination.strip().upper())

    @property
    def key(self) -> str:
        return f"{self.origin}-{self.destination}"
