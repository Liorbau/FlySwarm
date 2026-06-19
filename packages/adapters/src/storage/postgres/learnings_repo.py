"""Postgres implementation of the learnings-domain repository port."""

from __future__ import annotations

from typing import Optional

from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from packages.domain.src import Learning

from ._common import now, row_to_learning


class PostgresLearningRepo:
    """``LearningRepository`` backed by a shared connection pool."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def record(self, learning: Learning) -> Learning:
        created_at = learning.created_at or now()
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO learnings (kind, origin, destination, text, data, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    learning.kind,
                    learning.origin,
                    learning.destination,
                    learning.text,
                    Jsonb(learning.data) if learning.data is not None else None,
                    created_at,
                ),
            ).fetchone()
        return Learning(
            kind=learning.kind, text=learning.text, origin=learning.origin,
            destination=learning.destination, data=learning.data,
            id=int(row["id"]), created_at=created_at,
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
        with self._pool.connection() as conn:
            if kind is None:
                rows = conn.execute(
                    """
                    SELECT * FROM learnings
                    WHERE origin = %s AND destination = %s
                    ORDER BY created_at DESC LIMIT %s
                    """,
                    (origin, destination, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM learnings
                    WHERE origin = %s AND destination = %s AND kind = %s
                    ORDER BY created_at DESC LIMIT %s
                    """,
                    (origin, destination, kind, limit),
                ).fetchall()
        return [row_to_learning(r) for r in rows]


__all__ = ["PostgresLearningRepo"]
