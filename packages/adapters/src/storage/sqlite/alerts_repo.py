"""SQLite implementation of the alerts-domain repository port."""

from __future__ import annotations

import sqlite3

from packages.domain.src import Alert

from ._common import iso, now, row_to_alert


class SqliteAlertRepo:
    """``AlertRepository`` backed by a shared sqlite3 connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(self, alert: Alert) -> Alert:
        sent_at = alert.sent_at or now()
        cur = self._conn.execute(
            """
            INSERT INTO alerts
                (criterion_id, offer_key, amount, currency, deal_score,
                 booking_link, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert.criterion_id,
                alert.offer_key,
                alert.price.amount,
                alert.price.currency,
                alert.deal_score,
                alert.booking_link,
                iso(sent_at),
            ),
        )
        self._conn.commit()
        return Alert(
            criterion_id=alert.criterion_id, offer_key=alert.offer_key,
            price=alert.price, deal_score=alert.deal_score,
            booking_link=alert.booking_link, id=int(cur.lastrowid), sent_at=sent_at,
        )

    def was_alerted(self, criterion_id: int, offer_key: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM alerts WHERE criterion_id = ? AND offer_key = ? LIMIT 1",
            (criterion_id, offer_key),
        ).fetchone()
        return row is not None

    def for_criterion(self, criterion_id: int) -> list[Alert]:
        rows = self._conn.execute(
            "SELECT * FROM alerts WHERE criterion_id = ? ORDER BY sent_at DESC",
            (criterion_id,),
        ).fetchall()
        return [row_to_alert(r) for r in rows]

    def recent(self, *, limit: int = 50) -> list[Alert]:
        rows = self._conn.execute(
            "SELECT * FROM alerts ORDER BY sent_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [row_to_alert(r) for r in rows]


__all__ = ["SqliteAlertRepo"]
