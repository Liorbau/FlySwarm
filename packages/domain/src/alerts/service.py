"""Alerts domain service — dedup + record of delivered notifications."""

from __future__ import annotations

from packages.domain.src import Alert

from .repository import AlertRepository


class AlertsService:
    def __init__(self, alerts: AlertRepository) -> None:
        self._alerts = alerts

    def already_sent(self, criterion_id: int, offer_key: str) -> bool:
        return self._alerts.was_alerted(criterion_id, offer_key)

    def record(self, alert: Alert) -> Alert:
        return self._alerts.record(alert)

    def for_criterion(self, criterion_id: int) -> list[Alert]:
        return self._alerts.for_criterion(criterion_id)

    def recent(self, *, limit: int = 50) -> list[Alert]:
        return self._alerts.recent(limit=limit)


__all__ = ["AlertsService"]
