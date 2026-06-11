"""Telegram polling bot — routes user messages to the interface agent.

Long-polls ``getUpdates``, runs each message through ``handle_message`` (with
per-chat conversation memory so clarifying questions carry context), and replies.
Outbound deal alerts are sent separately by the scheduler (see scripts/run_flyswarm).
"""

from __future__ import annotations

import time
from typing import Optional

from apps.telegram_bot.agent.interface_agent import handle_message
from apps.telegram_bot.delivery.telegram_client import TelegramClient, parse_updates
from packages.adapters.src.storage import get_repository
from packages.contracts.src.storage import Repository

_MAX_TURNS = 8  # rolling window of messages kept per chat
_WELCOME = (
    "✈️ Hi! I'm FlySwarm. Tell me a trip to watch in plain language — e.g. "
    "\"cheap flight from Tel Aviv to London in August under $300\". "
    "Ask \"what am I watching?\" to list, or to stop one."
)


class ConversationStore:
    """In-memory rolling conversation history per chat (resets on restart)."""

    def __init__(self, max_turns: int = _MAX_TURNS) -> None:
        self._by_chat: dict[int, list[dict]] = {}
        self._max = max_turns

    def history(self, chat_id: int) -> list[dict]:
        return list(self._by_chat.get(chat_id, []))

    def append(self, chat_id: int, role: str, content: str) -> None:
        msgs = self._by_chat.setdefault(chat_id, [])
        msgs.append({"role": role, "content": content})
        if len(msgs) > self._max:
            del msgs[: len(msgs) - self._max]


def handle_update(
    client: TelegramClient,
    repo: Repository,
    store: ConversationStore,
    chat_id: int,
    text: str,
) -> str:
    """Process one inbound message and send a reply. Returns the reply text."""
    if text.strip().lower() in ("/start", "/help"):
        client.send_message(chat_id, _WELCOME)
        return _WELCOME

    result = handle_message(
        str(chat_id), text, repo=repo, history=store.history(chat_id)
    )
    reply = result["response"] or "Sorry, I didn't catch that — try rephrasing."
    client.send_message(chat_id, reply)
    store.append(chat_id, "user", text)
    store.append(chat_id, "assistant", reply)
    return reply


def run_polling(
    client: TelegramClient,
    *,
    repo: Optional[Repository] = None,
    store: Optional[ConversationStore] = None,
    poll_timeout: int = 30,
) -> None:
    """Long-poll for updates and handle them until interrupted."""
    repo = repo or get_repository()
    store = store or ConversationStore()
    offset: Optional[int] = None
    print("[bot] polling for messages…")
    while True:
        try:
            response = client.get_updates(offset=offset, timeout=poll_timeout)
        except Exception as exc:  # network blip — back off and retry
            print(f"[bot] getUpdates error: {exc}; retrying in 3s")
            time.sleep(3)
            continue
        for update in parse_updates(response):
            offset = update["update_id"] + 1
            try:
                handle_update(client, repo, store, update["chat_id"], update["text"])
            except Exception as exc:  # never let one bad message kill the loop
                print(f"[bot] handler error for chat {update['chat_id']}: {exc}")


__all__ = ["run_polling", "handle_update", "ConversationStore"]
