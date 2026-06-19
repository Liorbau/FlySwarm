"""SQLite implementation of the watches-domain repository port (criteria)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from packages.domain.src import MonitoringCriterion

from ._common import iso, row_to_criterion
from ._common import now as utcnow


class SqliteCriteriaRepo:
    """``CriteriaRepository`` backed by a shared sqlite3 connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def save(self, criterion: MonitoringCriterion) -> MonitoringCriterion:
        created_at = criterion.created_at or utcnow()
        q = criterion.query
        cur = self._conn.execute(
            """
            INSERT INTO criteria
                (user_id, origin, destination, depart_date, return_date,
                 currency, one_way, target_price, label, active, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                criterion.user_id,
                q.origin,
                q.destination,
                q.depart_date,
                q.return_date,
                q.currency,
                int(q.one_way),
                criterion.target_price,
                criterion.label,
                int(criterion.active),
                iso(created_at),
                iso(criterion.expires_at),
            ),
        )
        self._conn.commit()
        return MonitoringCriterion(
            user_id=criterion.user_id, query=q, target_price=criterion.target_price,
            label=criterion.label, active=criterion.active, id=int(cur.lastrowid),
            created_at=created_at, expires_at=criterion.expires_at,
        )

    def get(self, criterion_id: int) -> Optional[MonitoringCriterion]:
        row = self._conn.execute("SELECT * FROM criteria WHERE id = ?", (criterion_id,)).fetchone()
        return row_to_criterion(row) if row else None

    def list_active(self, *, user_id: Optional[str] = None) -> list[MonitoringCriterion]:
        if user_id is None:
            rows = self._conn.execute(
                "SELECT * FROM criteria WHERE active = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM criteria WHERE active = 1 AND user_id = ? ORDER BY id",
                (user_id,),
            ).fetchall()
        return [row_to_criterion(r) for r in rows]

    def deactivate(self, criterion_id: int) -> None:
        self._conn.execute("UPDATE criteria SET active = 0 WHERE id = ?", (criterion_id,))
        self._conn.commit()

    def due(self, now: Optional[datetime] = None) -> list[MonitoringCriterion]:
        now = now or utcnow()
        rows = self._conn.execute(
            """
            SELECT * FROM criteria
            WHERE active = 1 AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY id
            """,
            (iso(now),),
        ).fetchall()
        return [row_to_criterion(r) for r in rows]

    def deactivate_expired(self, now: Optional[datetime] = None) -> list[int]:
        now = now or utcnow()
        rows = self._conn.execute(
            "SELECT id FROM criteria WHERE active = 1 AND expires_at IS NOT NULL AND expires_at <= ?",
            (iso(now),),
        ).fetchall()
        ids = [int(r["id"]) for r in rows]
        if ids:
            self._conn.execute(
                "UPDATE criteria SET active = 0 WHERE id IN (%s)"
                % ",".join("?" for _ in ids),
                ids,
            )
            self._conn.commit()
        return ids


__all__ = ["SqliteCriteriaRepo"]
