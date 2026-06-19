"""Alerts domain — delivered deal notifications and their dedup bookkeeping."""

from .repository import AlertRepository
from .service import AlertsService

__all__ = ["AlertRepository", "AlertsService"]
