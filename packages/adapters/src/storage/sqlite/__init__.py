"""SQLite storage engine — per-domain repositories composed into a bundle."""

from .storage import BACKEND_NAME, SqliteStorage

__all__ = ["SqliteStorage", "BACKEND_NAME"]
