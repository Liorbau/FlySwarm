"""Shared SQLite helpers + row->entity mappers for the per-domain repos.

The only place (besides ``schema``) that knows the sqlite3 driver: datetimes stored
as ISO strings, booleans as ints, JSON as text — mapped back to domain objects here.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from packages.domain.src import (
    Alert,
    Learning,
    Message,
    Money,
    MonitoringCriterion,
    PriceObservation,
    SearchQuery,
)


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: Optional[datetime]) -> Optional[str]:
    return value.astimezone(timezone.utc).isoformat() if value else None


def parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def row_to_criterion(row: sqlite3.Row) -> MonitoringCriterion:
    return MonitoringCriterion(
        user_id=row["user_id"],
        query=SearchQuery(
            origin=row["origin"], destination=row["destination"],
            depart_date=row["depart_date"], return_date=row["return_date"],
            currency=row["currency"], one_way=bool(row["one_way"]),
        ),
        target_price=row["target_price"], label=row["label"],
        active=bool(row["active"]), id=row["id"],
        created_at=parse(row["created_at"]), expires_at=parse(row["expires_at"]),
    )


def row_to_observation(row: sqlite3.Row) -> PriceObservation:
    return PriceObservation(
        origin=row["origin"], destination=row["destination"],
        price=Money(amount=row["amount"], currency=row["currency"]),
        observed_at=parse(row["observed_at"]), depart_date=row["depart_date"],
        airline=row["airline"], source=row["source"], id=row["id"],
    )


def row_to_alert(row: sqlite3.Row) -> Alert:
    return Alert(
        criterion_id=row["criterion_id"], offer_key=row["offer_key"],
        price=Money(amount=row["amount"], currency=row["currency"]),
        deal_score=row["deal_score"], booking_link=row["booking_link"],
        id=row["id"], sent_at=parse(row["sent_at"]),
    )


def row_to_learning(row: sqlite3.Row) -> Learning:
    return Learning(
        kind=row["kind"], text=row["text"], origin=row["origin"],
        destination=row["destination"],
        data=json.loads(row["data"]) if row["data"] else None,
        id=row["id"], created_at=parse(row["created_at"]),
    )


def row_to_message(row: sqlite3.Row) -> Message:
    return Message(
        chat_id=row["chat_id"], role=row["role"], content=row["content"],
        id=row["id"], created_at=parse(row["created_at"]),
    )
