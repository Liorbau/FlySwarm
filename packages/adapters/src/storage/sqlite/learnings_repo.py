"""SQLite implementation of the learnings-domain repository port."""

from __future__ import annotations

import json
import sqlite3
from typing import Optional

from packages.domain.src import Learning

from ._common import iso, now, row_to_learning


class SqliteLearningRepo:
    """``LearningRepository`` backed by a shared sqlite3 connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(self, learning: Learning) -> Learning:
        created_at = learning.created_at or now()
        cur = self._conn.execute(
            """
            INSERT INTO learnings (kind, origin, destination, text, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                learning.kind,
                learning.origin,
                learning.destination,
                learning.text,
                json.dumps(learning.data) if learning.data is not None else None,
                iso(created_at),
            ),
        )
        self._conn.commit()
        return Learning(
            kind=learning.kind, text=learning.text, origin=learning.origin,
            destination=learning.destination, data=learning.data,
            id=int(cur.lastrowid), created_at=created_at,
        )

    def for_route(
        self,
        origin: str,
        destination: str,
        *,
        kind: Optional[str] = None,
        limit: int = 20,
    ) -> list[Learning]:
        origin = origin.strip().upper()
        destination = destination.strip().upper()
        if kind is None:
            rows = self._conn.execute(
                """
                SELECT * FROM learnings
                WHERE origin = ? AND destination = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (origin, destination, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM learnings
                WHERE origin = ? AND destination = ? AND kind = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (origin, destination, kind, limit),
            ).fetchall()
        return [row_to_learning(r) for r in rows]


__all__ = ["SqliteLearningRepo"]
