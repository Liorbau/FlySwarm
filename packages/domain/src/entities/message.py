"""Message entity — one durable turn of a Telegram conversation (keyed by chat_id)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

USER = "user"
ASSISTANT = "assistant"


@dataclass
class Message:
    """A single chat turn. ``id``/``created_at`` are assigned on save."""

    chat_id: str
    role: str  # USER or ASSISTANT
    content: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None
