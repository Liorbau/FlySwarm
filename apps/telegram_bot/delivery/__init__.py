"""Telegram delivery layer — inbound polling and outbound sending."""

from .telegram_client import TelegramClient, parse_updates

__all__ = ["TelegramClient", "parse_updates"]
