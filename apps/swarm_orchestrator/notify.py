"""Notification composition — turn judged deals into deduped, ready-to-send alerts.

Each alert-worthy ``DealResult`` becomes a ``Notification`` with a concise message
and the affiliate booking link. The ``alerts`` table de-dups (``was_alerted``) so a
user is never pinged twice for the same offer. Actual delivery (Telegram) is a
separate layer; this module only composes + records.

``scan_and_notify`` is the full F2+F3 pipeline the scheduler calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from apps.swarm_orchestrator.reflect import reflect
from apps.swarm_orchestrator.scan import DealResult, run_scan
from packages.adapters.src.storage import get_repository
from packages.contracts.src.storage import Repository
from packages.domain.src import Alert, FlightOffer


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
    repo: Repository,
) -> list[Notification]:
    """De-dup deals against the alerts table, record new ones, return notifications."""
    notifications: list[Notification] = []
    for deal in deals:
        criterion_id = deal.criterion.id
        if criterion_id is None:
            continue
        key = offer_key(deal.offer)
        if repo.was_alerted(criterion_id, key):
            continue  # already told this user about this exact offer
        repo.record_alert(
            Alert(
                criterion_id=criterion_id,
                offer_key=key,
                price=deal.offer.price,
                deal_score=deal.verdict.score,
                booking_link=deal.offer.booking_link,
            )
        )
        notifications.append(
            Notification(
                user_id=deal.criterion.user_id,
                criterion_id=criterion_id,
                text=format_message(deal),
                booking_link=deal.offer.booking_link,
                offer_key=key,
            )
        )
    return notifications


def scan_and_notify(
    *,
    repo: Optional[Repository] = None,
    source=None,
    now: Optional[datetime] = None,
    use_llm: bool = True,
    client=None,
    learn: bool = True,
) -> list[Notification]:
    """Full pipeline: scan due criteria, judge, compose deduped notifications, then
    reflect (record wins/lessons) so the swarm improves on the next run."""
    repo = repo or get_repository()
    report = run_scan(repo=repo, source=source, now=now, use_llm=use_llm, client=client)
    notifications = build_notifications(report.deals, repo)
    if learn:
        reflect(report, repo)
    return notifications


__all__ = ["Notification", "offer_key", "format_message", "build_notifications", "scan_and_notify"]
