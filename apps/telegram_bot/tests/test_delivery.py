"""Offline tests for the Telegram delivery layer (no network, no LLM)."""

from __future__ import annotations

from apps.telegram_bot.delivery.bot import ConversationStore, handle_update
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
