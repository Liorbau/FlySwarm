"""Pure, vendor-neutral domain model shared across apps and adapters."""

from .entities import Alert, FlightOffer, MonitoringCriterion, PriceObservation
from .value_objects import Money, SearchQuery

__all__ = [
    "Alert",
    "FlightOffer",
    "MonitoringCriterion",
    "Money",
    "PriceObservation",
    "SearchQuery",
]
