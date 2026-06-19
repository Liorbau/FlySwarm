"""Postgres implementation of the conversations-domain repository port."""

from __future__ import annotations

from psycopg_pool import ConnectionPool

from packages.domain.src import Message

from ._common import now, row_to_message


class PostgresConversationRepo:
    """``ConversationRepository`` backed by a shared connection pool."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def append(self, chat_id: str, role: str, content: str) -> Message:
        created_at = now()
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO messages (chat_id, role, content, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (chat_id, role, content, created_at),
            ).fetchone()
        return Message(
            chat_id=chat_id, role=role, content=content,
            id=int(row["id"]), created_at=created_at,
        )

    def recent(self, chat_id: str, *, limit: int = 8) -> list[Message]:
        # Newest-first then reversed -> oldest-first (LLM-ready ordering).
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE chat_id = %s ORDER BY id DESC LIMIT %s",
                (chat_id, limit),
            ).fetchall()
        return [row_to_message(r) for r in reversed(rows)]

    def clear(self, chat_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM messages WHERE chat_id = %s", (chat_id,))


__all__ = ["PostgresConversationRepo"]
