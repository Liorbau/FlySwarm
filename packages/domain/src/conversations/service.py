"""Conversations domain service — durable chat memory for the bot.

``window`` bounds how many recent turns are fed back to the LLM.
"""

from __future__ import annotations

from packages.domain.src import ASSISTANT, USER, Message

from .repository import ConversationRepository


class ConversationsService:
    def __init__(self, conversations: ConversationRepository, *, window: int = 8) -> None:
        self._conversations = conversations
        self._window = window

    def record_user(self, chat_id: str, content: str) -> Message:
        return self._conversations.append(chat_id, USER, content)

    def record_assistant(self, chat_id: str, content: str) -> Message:
        return self._conversations.append(chat_id, ASSISTANT, content)

    def recent(self, chat_id: str) -> list[Message]:
        """The last ``window`` turns, oldest first (LLM-ready ordering)."""
        return self._conversations.recent(chat_id, limit=self._window)

    def clear(self, chat_id: str) -> None:
        self._conversations.clear(chat_id)


__all__ = ["ConversationsService"]
