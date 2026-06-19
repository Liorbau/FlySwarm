"""Minimal Telegram Bot API client (dependency-free, urllib).

Supports long-poll ``getUpdates`` (inbound) and ``sendMessage`` (outbound). The
bot token is read by the caller from ``TELEGRAM_BOT_TOKEN`` and passed in.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Optional


class TelegramClient:
    """Thin wrapper over the Telegram Bot HTTP API."""

    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://api.telegram.org",
        timeout_seconds: int = 35,
    ) -> None:
        self._base = f"{base_url}/bot{token}"
        self.timeout_seconds = timeout_seconds

    def _post(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base}/{method}", data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def send_message(self, chat_id: int | str, text: str) -> dict[str, Any]:
        return self._post("sendMessage", {"chat_id": chat_id, "text": text})

    def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> dict[str, Any]:
        payload: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        return self._post("getUpdates", payload)


def parse_updates(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract ``{update_id, chat_id, text}`` from a getUpdates response.

    Pure (no network) so it is unit-testable. Skips non-text and service updates.
    """
    parsed: list[dict[str, Any]] = []
    for update in response.get("result", []):
        message = update.get("message") or update.get("edited_message")
        if not message:
            continue
        text = message.get("text")
        chat_id = (message.get("chat") or {}).get("id")
        if text is None or chat_id is None:
            continue
        parsed.append({"update_id": update["update_id"], "chat_id": chat_id, "text": text})
    return parsed


__all__ = ["TelegramClient", "parse_updates"]
