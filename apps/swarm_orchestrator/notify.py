"""Notification composition — turn judged deals into deduped, ready-to-send alerts.

Each alert-worthy ``DealResult`` becomes a ``Notification`` with a message and the
affiliate booking link. The ``alerts`` table de-dups so a user is never pinged twice
for the same offer. Delivery (Telegram) is a separate layer; this only composes +
records.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.swarm_orchestrator.evaluate import DealResult
from packages.adapters.src.storage import Storage
from packages.domain.src import Alert, FlightOffer
from packages.domain.src.alerts import AlertsService


@dataclass
class Notification:
    """A composed, deduped alert ready for the delivery layer to send."""

    user_id: str
    criterion_id: int
    text: str
    booking_link: str
    offer_key: str


def offer_key(offer: FlightOffer) -> str:
    """Stable de-dup key for an offer (route + date + rounded price + airline)."""
    depart = offer.departure_at.date().isoformat() if offer.departure_at else "?"
    price = int(round(offer.price.amount))
    airline = offer.airline or "?"
    return f"{offer.origin}-{offer.destination}-{depart}-{price}{offer.price.currency}-{airline}"


def format_message(deal: DealResult) -> str:
    """Compose the user-facing alert text (deterministic; uses the judge's reason)."""
    o = deal.offer
    depart = o.departure_at.date().isoformat() if o.departure_at else "flexible dates"
    airline = f" on {o.airline}" if o.airline else ""
    return (
        f"✈️ Deal: {o.origin} → {o.destination} ({depart}){airline}\n"
        f"Price: {o.price.amount:.0f} {o.price.currency}\n"
        f"{deal.verdict.reason}\n"
        f"Book: {o.booking_link}"
    )


def build_notifications(
    deals: list[DealResult],
    storage: Storage,
) -> list[Notification]:
    """De-dup deals against the alerts table, record new ones, return notifications."""
    alerts = AlertsService(storage.alerts)
    notifications: list[Notification] = []
    for deal in deals:
        criterion_id = deal.criterion.id
        if criterion_id is None:
            continue
        key = offer_key(deal.offer)
        if alerts.already_sent(criterion_id, key):
            continue  # already told this user about this exact offer
        alerts.record(Alert(
            criterion_id=criterion_id, offer_key=key, price=deal.offer.price,
            deal_score=deal.verdict.score, booking_link=deal.offer.booking_link,
        ))
        notifications.append(Notification(
            user_id=deal.criterion.user_id, criterion_id=criterion_id,
            text=format_message(deal), booking_link=deal.offer.booking_link,
            offer_key=key,
        ))
    return notifications


__all__ = ["Notification", "offer_key", "format_message", "build_notifications"]
