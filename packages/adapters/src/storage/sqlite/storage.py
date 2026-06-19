"""``SqliteStorage`` — the SQLite storage bundle. Owns a single shared sqlite3
connection (``check_same_thread=False``) and exposes one repository per domain.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .alerts_repo import SqliteAlertRepo
from .conversations_repo import SqliteConversationRepo
from .learnings_repo import SqliteLearningRepo
from .prices_repo import SqlitePriceRepo
from .schema import SCHEMA
from .watches_repo import SqliteCriteriaRepo

BACKEND_NAME = "sqlite"


class SqliteStorage:
    """Concrete storage bundle backed by a local SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        self.criteria = SqliteCriteriaRepo(self._conn)
        self.prices = SqlitePriceRepo(self._conn)
        self.alerts = SqliteAlertRepo(self._conn)
        self.learnings = SqliteLearningRepo(self._conn)
        self.conversations = SqliteConversationRepo(self._conn)

    def initialize(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


__all__ = ["SqliteStorage", "BACKEND_NAME"]
