"""Conversations domain — durable per-chat message history for the bot."""

from .repository import ConversationRepository
from .service import ConversationsService

__all__ = ["ConversationRepository", "ConversationsService"]
