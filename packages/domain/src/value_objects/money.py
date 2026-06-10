"""Money value object — a price amount paired with an ISO 4217 currency.

Vendor-neutral: every flight source maps its raw price into this shape so that
downstream analytics/notification logic never deals with provider quirks (minor
units, implied currencies, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Money:
    """A monetary amount in a specific currency.

    ``amount`` is in major units (e.g. dollars, not cents). ``currency`` is an
    ISO 4217 code, normalized to uppercase.
    """

    amount: float
    currency: str

    def __post_init__(self) -> None:
        normalized = str(self.currency).strip().upper()
        if not normalized:
            raise ValueError("Money.currency must be a non-empty ISO 4217 code")
        # frozen dataclass: bypass immutability only to normalize on construction.
        object.__setattr__(self, "currency", normalized)
        object.__setattr__(self, "amount", float(self.amount))
