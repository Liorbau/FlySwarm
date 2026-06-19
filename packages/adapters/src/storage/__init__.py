"""Storage factory (mirrors ``get_flight_source``). Backend selection is config-only
(``config/storage.yaml`` + ``.env`` ``DATABASE_URL``); callers depend only on the
``Storage`` bundle and the per-domain repository ports.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from packages.shared.src.config import resolve_storage_config

from .base import Storage
from .sqlite import BACKEND_NAME as SQLITE, SqliteStorage

POSTGRES = "postgres"


def _repo_root() -> Path:
    # packages/adapters/src/storage/__init__.py -> repo root is 5 levels up.
    return Path(__file__).resolve().parents[4]


def get_storage(*, backend_override: Optional[str] = None) -> Storage:
    """Build and initialize a Storage bundle from resolved project config."""
    resolved = resolve_storage_config(backend_override=backend_override)

    if resolved.backend == SQLITE:
        raw_path = resolved.options.get("sqlite_path", "data/flyswarm.sqlite3")
        path = Path(raw_path)
        if not path.is_absolute():
            path = _repo_root() / path
        storage = SqliteStorage(path)
        storage.initialize()
        return storage

    if resolved.backend == POSTGRES:
        if not resolved.database_url:
            raise ValueError("Postgres backend selected but DATABASE_URL is not set in .env.")
        # Import here so SQLite-only runs don't require the psycopg dependency.
        from .postgres import PostgresStorage

        schema = resolved.options.get("schema", "public")
        storage = PostgresStorage(resolved.database_url, schema=schema)
        storage.initialize()
        return storage

    supported = ", ".join((SQLITE, POSTGRES))
    raise ValueError(f"Unknown storage backend '{resolved.backend}'. Supported: {supported}.")


__all__ = ["get_storage", "Storage", "SqliteStorage"]
