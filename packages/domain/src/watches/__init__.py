"""Watches domain — the routes users ask the swarm to monitor (criteria)."""

from .repository import CriteriaRepository
from .service import WatchesService

__all__ = ["CriteriaRepository", "WatchesService"]
