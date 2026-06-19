"""Money value object — a price amount paired with an ISO 4217 currency."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    """A monetary amount (major units) in an ISO 4217 currency (upper-cased)."""

    amount: float
    currency: str

    def __post_init__(self) -> None:
        normalized = str(self.currency).strip().upper()
        if not normalized:
            raise ValueError("Money.currency must be a non-empty ISO 4217 code")
        # frozen dataclass: bypass immutability only to normalize on construction.
        object.__setattr__(self, "currency", normalized)
        object.__setattr__(self, "amount", float(self.amount))
