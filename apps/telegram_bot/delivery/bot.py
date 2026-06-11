"""Telegram polling bot — routes user messages to the interface agent.

Long-polls ``getUpdates``, runs each message through ``handle_message`` (with
per-chat conversation memory so clarifying questions carry context), and replies.
Outbound deal alerts are sent separately by the scheduler (see scripts/run_flyswarm).

Abuse protection (checked BEFORE any LLM/flight-API call, so spam can't burn the
operator's quota):
- an optional **allowlist** of chat ids (``TELEGRAM_ALLOWED_CHAT_IDS``) — when set,
  only those chats are served; everyone else is politely declined for free;
- per-chat **rate limiting** (``RATE_LIMIT_MAX`` per ``RATE_LIMIT_WINDOW`` seconds).
"""

from __future__ import annotations

import os
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
_PRIVATE_MSG = "Sorry — this bot is private and not open to new users right now."
_RATELIMIT_MSG = "You're sending messages a bit fast — please wait a moment and try again."


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


class RateLimiter:
    """Sliding-window per-key rate limiter (in-memory)."""

    def __init__(self, max_events: int = 5, window_seconds: int = 60) -> None:
        self.max_events = max_events
        self.window = window_seconds
        self._hits: dict[object, list[float]] = {}

    def allow(self, key: object, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        recent = [t for t in self._hits.get(key, []) if now - t < self.window]
        if len(recent) >= self.max_events:
            self._hits[key] = recent  # keep window pruned
            return False
        recent.append(now)
        self._hits[key] = recent
        return True


def parse_allowlist(raw: Optional[str]) -> Optional[set[int]]:
    """Parse ``TELEGRAM_ALLOWED_CHAT_IDS`` (comma-separated). None/empty -> open bot."""
    if not raw or not raw.strip():
        return None
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                ids.add(int(part))
            except ValueError:
                continue
    return ids or None


def handle_update(
    client: TelegramClient,
    repo: Repository,
    store: ConversationStore,
    chat_id: int,
    text: str,
    *,
    allowlist: Optional[set[int]] = None,
    limiter: Optional[RateLimiter] = None,
    now: Optional[float] = None,
) -> str:
    """Process one inbound message and send a reply. Returns the reply text.

    Gating (allowlist, then rate limit) happens before any LLM/flight-API call,
    so declined messages cost nothing beyond a free Telegram reply.
    """
    if text.strip().lower() in ("/start", "/help"):
        client.send_message(chat_id, _WELCOME)
        return _WELCOME

    if allowlist is not None and chat_id not in allowlist:
        client.send_message(chat_id, _PRIVATE_MSG)
        return _PRIVATE_MSG

    if limiter is not None and not limiter.allow(chat_id, now=now):
        client.send_message(chat_id, _RATELIMIT_MSG)
        return _RATELIMIT_MSG

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

    allowlist = parse_allowlist(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS"))
    limiter = RateLimiter(
        max_events=int(os.getenv("RATE_LIMIT_MAX", "5")),
        window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
    )
    mode = f"allowlist={sorted(allowlist)}" if allowlist else "open"
    print(f"[bot] polling for messages… ({mode}, rate {limiter.max_events}/{limiter.window}s)")

    offset: Optional[int] = None
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
                handle_update(
                    client, repo, store, update["chat_id"], update["text"],
                    allowlist=allowlist, limiter=limiter,
                )
            except Exception as exc:  # never let one bad message kill the loop
                print(f"[bot] handler error for chat {update['chat_id']}: {exc}")


__all__ = ["run_polling", "handle_update", "ConversationStore", "RateLimiter", "parse_allowlist"]
