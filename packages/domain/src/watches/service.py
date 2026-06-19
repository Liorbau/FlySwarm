"""Watches domain service — managing the routes users monitor (criteria)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from packages.domain.src import MonitoringCriterion

from .repository import CriteriaRepository


class WatchesService:
    def __init__(self, criteria: CriteriaRepository) -> None:
        self._criteria = criteria

    def add(self, criterion: MonitoringCriterion) -> MonitoringCriterion:
        return self._criteria.save(criterion)

    def get(self, criterion_id: int) -> Optional[MonitoringCriterion]:
        return self._criteria.get(criterion_id)

    def list_for_user(self, user_id: str) -> list[MonitoringCriterion]:
        return self._criteria.list_active(user_id=user_id)

    def stop(self, criterion_id: int) -> None:
        self._criteria.deactivate(criterion_id)

    def due(self, now: Optional[datetime] = None) -> list[MonitoringCriterion]:
        return self._criteria.due(now)

    def deactivate_expired(self, now: Optional[datetime] = None) -> list[int]:
        return self._criteria.deactivate_expired(now)


__all__ = ["WatchesService"]
