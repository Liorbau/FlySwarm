"""``PostgresStorage`` — the Postgres storage bundle (e.g. Supabase).

Owns a thread-safe ``psycopg_pool.ConnectionPool`` (one storage object shared across
threads) and exposes one repository per domain. ``schema`` confines all tables to a
Postgres schema (a throwaway one in tests); production uses the default ``public``.
"""

from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from ._common import safe_schema
from .alerts_repo import PostgresAlertRepo
from .conversations_repo import PostgresConversationRepo
from .learnings_repo import PostgresLearningRepo
from .prices_repo import PostgresPriceRepo
from .schema import SCHEMA_STATEMENTS
from .watches_repo import PostgresCriteriaRepo

BACKEND_NAME = "postgres"


class PostgresStorage:
    """Concrete storage bundle backed by Postgres."""

    def __init__(self, dsn: str, *, schema: str = "public", max_size: int = 4) -> None:
        self._schema = safe_schema(schema)

        def _configure(conn) -> None:
            if self._schema != "public":
                conn.execute(f'SET search_path TO "{self._schema}"')

        self._pool = ConnectionPool(
            conninfo=dsn,
            min_size=1,
            max_size=max_size,
            open=True,
            configure=_configure,
            kwargs={"autocommit": True, "row_factory": dict_row},
        )

        self.criteria = PostgresCriteriaRepo(self._pool)
        self.prices = PostgresPriceRepo(self._pool)
        self.alerts = PostgresAlertRepo(self._pool)
        self.learnings = PostgresLearningRepo(self._pool)
        self.conversations = PostgresConversationRepo(self._pool)

    def initialize(self) -> None:
        with self._pool.connection() as conn:
            if self._schema != "public":
                conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{self._schema}"')
                conn.execute(f'SET search_path TO "{self._schema}"')
            for stmt in SCHEMA_STATEMENTS:
                conn.execute(stmt)

    def close(self) -> None:
        self._pool.close()


__all__ = ["PostgresStorage", "BACKEND_NAME"]
