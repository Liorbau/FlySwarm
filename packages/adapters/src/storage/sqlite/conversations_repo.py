"""SQLite implementation of the conversations-domain repository port."""

from __future__ import annotations

import sqlite3

from packages.domain.src import Message

from ._common import iso, now, row_to_message


class SqliteConversationRepo:
    """``ConversationRepository`` backed by a shared sqlite3 connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def append(self, chat_id: str, role: str, content: str) -> Message:
        created_at = now()
        cur = self._conn.execute(
            "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, iso(created_at)),
        )
        self._conn.commit()
        return Message(
            chat_id=chat_id, role=role, content=content,
            id=int(cur.lastrowid), created_at=created_at,
        )

    def recent(self, chat_id: str, *, limit: int = 8) -> list[Message]:
        # Fetch newest-first then reverse so callers get oldest-first (LLM order).
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
        return [row_to_message(r) for r in reversed(rows)]

    def clear(self, chat_id: str) -> None:
        self._conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        self._conn.commit()


__all__ = ["SqliteConversationRepo"]
