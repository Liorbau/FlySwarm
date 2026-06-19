"""Postgres implementation of the alerts-domain repository port."""

from __future__ import annotations

from psycopg_pool import ConnectionPool

from packages.domain.src import Alert

from ._common import now, row_to_alert


class PostgresAlertRepo:
    """``AlertRepository`` backed by a shared connection pool."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def record(self, alert: Alert) -> Alert:
        sent_at = alert.sent_at or now()
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO alerts
                    (criterion_id, offer_key, amount, currency, deal_score,
                     booking_link, sent_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    alert.criterion_id,
                    alert.offer_key,
                    alert.price.amount,
                    alert.price.currency,
                    alert.deal_score,
                    alert.booking_link,
                    sent_at,
                ),
            ).fetchone()
        return Alert(
            criterion_id=alert.criterion_id, offer_key=alert.offer_key,
            price=alert.price, deal_score=alert.deal_score,
            booking_link=alert.booking_link, id=int(row["id"]), sent_at=sent_at,
        )

    def was_alerted(self, criterion_id: int, offer_key: str) -> bool:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM alerts WHERE criterion_id = %s AND offer_key = %s LIMIT 1",
                (criterion_id, offer_key),
            ).fetchone()
        return row is not None

    def for_criterion(self, criterion_id: int) -> list[Alert]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE criterion_id = %s ORDER BY sent_at DESC",
                (criterion_id,),
            ).fetchall()
        return [row_to_alert(r) for r in rows]

    def recent(self, *, limit: int = 50) -> list[Alert]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY sent_at DESC LIMIT %s", (limit,)
            ).fetchall()
        return [row_to_alert(r) for r in rows]


__all__ = ["PostgresAlertRepo"]
