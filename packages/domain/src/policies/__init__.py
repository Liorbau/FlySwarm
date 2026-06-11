"""Vendor-neutral business policies (price-drop rules, expiry, insights, etc.)."""

from .expiry import DEFAULT_HORIZON_DAYS, compute_expiry
from .insights import route_insight_text

__all__ = ["compute_expiry", "DEFAULT_HORIZON_DAYS", "route_insight_text"]
