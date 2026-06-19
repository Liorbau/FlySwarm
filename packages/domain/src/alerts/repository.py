"""Repository port for the alerts domain (sent deal notifications)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from packages.domain.src import Alert


@runtime_checkable
class AlertRepository(Protocol):
    """Persistence + dedup bookkeeping for alerts already delivered."""

    def record(self, alert: Alert) -> Alert:
        """Persist a sent alert, returning it with ``id``/``sent_at`` set."""
        ...

    def was_alerted(self, criterion_id: int, offer_key: str) -> bool:
        """True if this criterion was already alerted for this offer key."""
        ...

    def for_criterion(self, criterion_id: int) -> list[Alert]:
        """All alerts sent for one criterion (used by reflection)."""
        ...

    def recent(self, *, limit: int = 50) -> list[Alert]:
        """Most recently sent alerts, newest first."""
        ...


__all__ = ["AlertRepository"]
