"""Vendor-neutral business policies (price-drop rules, expiry, etc.)."""

from .expiry import DEFAULT_HORIZON_DAYS, compute_expiry

__all__ = ["compute_expiry", "DEFAULT_HORIZON_DAYS"]
