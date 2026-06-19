"""Repository port for the watches domain (per-user monitoring criteria).

A user's intent to monitor a route until it expires; engine-neutral.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from packages.domain.src import MonitoringCriterion


@runtime_checkable
class CriteriaRepository(Protocol):
    """Persistence for monitoring criteria (the routes a user watches)."""

    def save(self, criterion: MonitoringCriterion) -> MonitoringCriterion:
        """Persist a criterion, returning it with ``id``/``created_at`` set."""
        ...

    def get(self, criterion_id: int) -> Optional[MonitoringCriterion]:
        ...

    def list_active(self, *, user_id: Optional[str] = None) -> list[MonitoringCriterion]:
        """Active criteria, optionally scoped to one user."""
        ...

    def deactivate(self, criterion_id: int) -> None:
        ...

    def due(self, now: Optional[datetime] = None) -> list[MonitoringCriterion]:
        """Active criteria whose deadline (``expires_at``) has not passed."""
        ...

    def deactivate_expired(self, now: Optional[datetime] = None) -> list[int]:
        """Auto-stop active criteria past their deadline; return the stopped ids."""
        ...


__all__ = ["CriteriaRepository"]
