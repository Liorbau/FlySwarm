"""Pure, vendor-neutral domain model shared across apps and adapters."""

from .entities import FlightOffer
from .value_objects import Money, SearchQuery

__all__ = ["FlightOffer", "Money", "SearchQuery"]
