"""Storage/repository contract for FlySwarm (CLAUDE.md section 5).

A single, engine-neutral persistence interface every agent/workflow calls
instead of a database driver. Concrete implementations live in
``packages/adapters/src/storage`` (e.g. a SQLite repository); callers depend
only on the ``Repository`` protocol below and the canonical domain objects.

Swapping engines (SQLite -> Postgres) is a config/credentials change only:
``config/storage.yaml`` + ``.env`` (``DATABASE_URL``). No business logic changes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from packages.domain.src import Alert, Learning, MonitoringCriterion, PriceObservation


@runtime_checkable
class Repository(Protocol):
    """Engine-neutral persistence for criteria, price history, and alerts.

    Implementations are responsible for assigning ids and timestamps on save and
    for round-tripping the canonical domain objects faithfully. No engine- or
    driver-specific types leak past this interface.
    """

    def initialize(self) -> None:
        """Create schema if absent. Safe to call repeatedly (idempotent)."""
        ...

    # ── monitoring criteria ──────────────────────────────────────────────────

    def save_criterion(self, criterion: MonitoringCriterion) -> MonitoringCriterion:
        """Persist a criterion, returning it with ``id``/``created_at`` set."""
        ...

    def get_criterion(self, criterion_id: int) -> Optional[MonitoringCriterion]:
        ...

    def list_active_criteria(
        self, *, user_id: Optional[str] = None
    ) -> list[MonitoringCriterion]:
        """Active criteria, optionally scoped to one user."""
        ...

    def deactivate_criterion(self, criterion_id: int) -> None:
        ...

    def due_criteria(self, now: Optional[datetime] = None) -> list[MonitoringCriterion]:
        """Active criteria whose deadline (``expires_at``) has not passed."""
        ...

    def deactivate_expired(self, now: Optional[datetime] = None) -> list[int]:
        """Auto-stop active criteria past their deadline; return the stopped ids."""
        ...

    # ── price history ────────────────────────────────────────────────────────

    def record_observation(self, observation: PriceObservation) -> PriceObservation:
        """Persist one observed price, returning it with ``id`` set."""
        ...

    def price_history(
        self,
        origin: str,
        destination: str,
        *,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[PriceObservation]:
        """Observations for a route, newest first, optionally since a cutoff."""
        ...

    # ── alerts ───────────────────────────────────────────────────────────────

    def record_alert(self, alert: Alert) -> Alert:
        """Persist a sent alert, returning it with ``id``/``sent_at`` set."""
        ...

    def was_alerted(self, criterion_id: int, offer_key: str) -> bool:
        """True if this criterion was already alerted for this offer key."""
        ...

    def alerts_for_criterion(self, criterion_id: int) -> list[Alert]:
        """All alerts sent for one criterion (used by reflection)."""
        ...

    def recent_alerts(self, *, limit: int = 50) -> list[Alert]:
        """Most recently sent alerts, newest first."""
        ...

    # ── learnings (self-improving memory) ────────────────────────────────────

    def record_learning(self, learning: Learning) -> Learning:
        """Persist a win/lesson, returning it with ``id``/``created_at`` set."""
        ...

    def learnings_for_route(
        self,
        origin: str,
        destination: str,
        *,
        kind: Optional[str] = None,
        limit: int = 20,
    ) -> list[Learning]:
        """Learnings for a route (optionally filtered by kind), newest first."""
        ...


__all__ = ["Repository", "Alert", "Learning", "MonitoringCriterion", "PriceObservation"]
