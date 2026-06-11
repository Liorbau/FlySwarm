"""Offline tests for the Telegram delivery layer (no network, no LLM)."""

from __future__ import annotations

from apps.telegram_bot.delivery.bot import (
    ConversationStore,
    RateLimiter,
    handle_update,
    parse_allowlist,
)
from apps.telegram_bot.delivery.telegram_client import parse_updates


class FakeClient:
    def __init__(self):
        self.sent: list[tuple] = []

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))
        return {"ok": True}


def test_parse_updates_extracts_text_messages():
    response = {
        "result": [
            {"update_id": 1, "message": {"chat": {"id": 42}, "text": "hi"}},
            {"update_id": 2, "edited_message": {"chat": {"id": 7}, "text": "edited"}},
            {"update_id": 3, "message": {"chat": {"id": 9}}},  # no text -> skipped
            {"update_id": 4, "channel_post": {"chat": {"id": 1}, "text": "x"}},  # not handled
        ]
    }
    parsed = parse_updates(response)
    assert [p["update_id"] for p in parsed] == [1, 2]
    assert parsed[0] == {"update_id": 1, "chat_id": 42, "text": "hi"}


def test_parse_updates_empty():
    assert parse_updates({"result": []}) == []
    assert parse_updates({}) == []


def test_conversation_store_keeps_rolling_window():
    store = ConversationStore(max_turns=4)
    for i in range(6):
        store.append(7, "user", f"m{i}")
    history = store.history(7)
    assert len(history) == 4
    assert history[0]["content"] == "m2"  # oldest two dropped
    assert history[-1]["content"] == "m5"
    assert store.history(999) == []  # unknown chat


def test_start_command_sends_welcome_without_llm():
    client = FakeClient()
    store = ConversationStore()
    reply = handle_update(client, repo=None, store=store, chat_id=42, text="/start")
    assert len(client.sent) == 1
    assert "FlySwarm" in client.sent[0][1]
    assert reply.startswith("✈️")
    assert store.history(42) == []  # commands aren't added to conversation history


# ── abuse protection (blocked paths must NOT reach the LLM) ──────────────────


def test_allowlist_blocks_stranger_without_calling_llm():
    client = FakeClient()
    # repo=None would crash handle_message; reaching it = test failure by exception.
    reply = handle_update(
        client, repo=None, store=ConversationStore(), chat_id=999, text="watch TLV to LON",
        allowlist={5632276491},
    )
    assert "private" in reply.lower()
    assert client.sent == [(999, reply)]  # one canned reply, nothing else


def test_allowlisted_user_passes_allowlist_gate():
    # Allowed + rate-limited-out so we still avoid the LLM but prove the gate passed.
    limiter = RateLimiter(max_events=1, window_seconds=60)
    limiter.allow(7, now=0.0)  # consume the only slot
    reply = handle_update(
        FakeClient(), repo=None, store=ConversationStore(), chat_id=7, text="hi",
        allowlist={7}, limiter=limiter, now=0.0,
    )
    assert "fast" in reply.lower()  # passed allowlist, then hit the rate limit


def test_rate_limiter_window():
    rl = RateLimiter(max_events=2, window_seconds=10)
    assert rl.allow("u", now=0.0) is True
    assert rl.allow("u", now=1.0) is True
    assert rl.allow("u", now=2.0) is False        # 3rd within window -> blocked
    assert rl.allow("u", now=11.0) is True         # window elapsed -> allowed again
    assert rl.allow("other", now=2.0) is True      # per-key isolation


def test_rate_limited_message_does_not_reach_llm():
    client = FakeClient()
    limiter = RateLimiter(max_events=1, window_seconds=60)
    limiter.allow(42, now=0.0)  # exhaust
    reply = handle_update(
        client, repo=None, store=ConversationStore(), chat_id=42, text="watch TLV to LON",
        limiter=limiter, now=0.0,
    )
    assert "fast" in reply.lower()
    assert client.sent == [(42, reply)]


def test_parse_allowlist():
    assert parse_allowlist("1, 2 ,3") == {1, 2, 3}
    assert parse_allowlist("x, 5") == {5}       # bad entries skipped
    assert parse_allowlist("") is None           # empty -> open bot
    assert parse_allowlist(None) is None
    assert parse_allowlist("   ") is None
