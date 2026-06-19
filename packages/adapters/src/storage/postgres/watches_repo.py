"""Postgres implementation of the watches-domain repository port (criteria)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from psycopg_pool import ConnectionPool

from packages.domain.src import MonitoringCriterion

from ._common import row_to_criterion
from ._common import now as utcnow


class PostgresCriteriaRepo:
    """``CriteriaRepository`` backed by a shared connection pool."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def save(self, criterion: MonitoringCriterion) -> MonitoringCriterion:
        created_at = criterion.created_at or utcnow()
        q = criterion.query
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO criteria
                    (user_id, origin, destination, depart_date, return_date,
                     currency, one_way, target_price, label, active, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    criterion.user_id,
                    q.origin,
                    q.destination,
                    q.depart_date,
                    q.return_date,
                    q.currency,
                    bool(q.one_way),
                    criterion.target_price,
                    criterion.label,
                    bool(criterion.active),
                    created_at,
                    criterion.expires_at,
                ),
            ).fetchone()
        return MonitoringCriterion(
            user_id=criterion.user_id, query=q, target_price=criterion.target_price,
            label=criterion.label, active=criterion.active, id=int(row["id"]),
            created_at=created_at, expires_at=criterion.expires_at,
        )

    def get(self, criterion_id: int) -> Optional[MonitoringCriterion]:
        with self._pool.connection() as conn:
            row = conn.execute(
                "SELECT * FROM criteria WHERE id = %s", (criterion_id,)
            ).fetchone()
        return row_to_criterion(row) if row else None

    def list_active(self, *, user_id: Optional[str] = None) -> list[MonitoringCriterion]:
        with self._pool.connection() as conn:
            if user_id is None:
                rows = conn.execute(
                    "SELECT * FROM criteria WHERE active = TRUE ORDER BY id"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM criteria WHERE active = TRUE AND user_id = %s ORDER BY id",
                    (user_id,),
                ).fetchall()
        return [row_to_criterion(r) for r in rows]

    def deactivate(self, criterion_id: int) -> None:
        with self._pool.connection() as conn:
            conn.execute(
                "UPDATE criteria SET active = FALSE WHERE id = %s", (criterion_id,)
            )

    def due(self, now: Optional[datetime] = None) -> list[MonitoringCriterion]:
        now = now or utcnow()
        with self._pool.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM criteria
                WHERE active = TRUE AND (expires_at IS NULL OR expires_at > %s)
                ORDER BY id
                """,
                (now,),
            ).fetchall()
        return [row_to_criterion(r) for r in rows]

    def deactivate_expired(self, now: Optional[datetime] = None) -> list[int]:
        now = now or utcnow()
        with self._pool.connection() as conn:
            rows = conn.execute(
                """
                UPDATE criteria SET active = FALSE
                WHERE active = TRUE AND expires_at IS NOT NULL AND expires_at <= %s
                RETURNING id
                """,
                (now,),
            ).fetchall()
        return [int(r["id"]) for r in rows]


__all__ = ["PostgresCriteriaRepo"]
