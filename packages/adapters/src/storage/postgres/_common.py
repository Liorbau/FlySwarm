"""Shared Postgres helpers + row->entity mappers for the per-domain repos.

The only place (besides ``schema``) that knows the psycopg driver. Native PG types
(datetime/bool/dict) come back directly; mappers normalize datetimes to UTC.
"""

from __future__ import annotations

import re
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


def utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def safe_schema(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid schema name: {name!r}")
    return name


def row_to_criterion(row: dict) -> MonitoringCriterion:
    return MonitoringCriterion(
        user_id=row["user_id"],
        query=SearchQuery(
            origin=row["origin"], destination=row["destination"],
            depart_date=row["depart_date"], return_date=row["return_date"],
            currency=row["currency"], one_way=bool(row["one_way"]),
        ),
        target_price=row["target_price"], label=row["label"],
        active=bool(row["active"]), id=row["id"],
        created_at=utc(row["created_at"]), expires_at=utc(row["expires_at"]),
    )


def row_to_observation(row: dict) -> PriceObservation:
    return PriceObservation(
        origin=row["origin"], destination=row["destination"],
        price=Money(amount=row["amount"], currency=row["currency"]),
        observed_at=utc(row["observed_at"]), depart_date=row["depart_date"],
        airline=row["airline"], source=row["source"], id=row["id"],
    )


def row_to_alert(row: dict) -> Alert:
    return Alert(
        criterion_id=row["criterion_id"], offer_key=row["offer_key"],
        price=Money(amount=row["amount"], currency=row["currency"]),
        deal_score=row["deal_score"], booking_link=row["booking_link"],
        id=row["id"], sent_at=utc(row["sent_at"]),
    )


def row_to_learning(row: dict) -> Learning:
    return Learning(
        kind=row["kind"], text=row["text"], origin=row["origin"],
        destination=row["destination"],
        data=row["data"],  # JSONB already decoded to a Python object by psycopg
        id=row["id"], created_at=utc(row["created_at"]),
    )


def row_to_message(row: dict) -> Message:
    return Message(
        chat_id=row["chat_id"], role=row["role"], content=row["content"],
        id=row["id"], created_at=utc(row["created_at"]),
    )
