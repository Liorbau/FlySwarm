"""Repository port for the conversations domain (durable chat history).

Keyed by ``chat_id`` (one thread per chat); messages are the durable unit.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from packages.domain.src import Message


@runtime_checkable
class ConversationRepository(Protocol):
    """Persistence for per-chat message history."""

    def append(self, chat_id: str, role: str, content: str) -> Message:
        """Persist one turn, returning it with ``id``/``created_at`` set."""
        ...

    def recent(self, chat_id: str, *, limit: int = 8) -> list[Message]:
        """Most recent turns for a chat, oldest first (ready to feed an LLM)."""
        ...

    def clear(self, chat_id: str) -> None:
        """Forget a chat's history (e.g. a /reset command)."""
        ...


__all__ = ["ConversationRepository"]
