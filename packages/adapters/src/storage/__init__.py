"""Storage/repository factory (mirrors ``get_flight_source``).

Selecting/swapping a backend is config-only: ``config/storage.yaml`` + ``.env``
(``DATABASE_URL`` for server engines). Adding a backend = one adapter file + one
``storage.yaml`` entry + a branch here. Callers depend only on the ``Repository``
contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from packages.contracts.src.storage import Repository
from packages.shared.src.config import resolve_storage_config

from .sqlite_repository import BACKEND_NAME as SQLITE, SqliteRepository


def _repo_root() -> Path:
    # packages/adapters/src/storage/__init__.py -> repo root is 5 levels up.
    return Path(__file__).resolve().parents[4]


def get_repository(*, backend_override: Optional[str] = None) -> Repository:
    """Build and initialize a Repository from resolved project config."""
    resolved = resolve_storage_config(backend_override=backend_override)

    if resolved.backend == SQLITE:
        raw_path = resolved.options.get("sqlite_path", "data/flyswarm.sqlite3")
        path = Path(raw_path)
        if not path.is_absolute():
            path = _repo_root() / path
        repo = SqliteRepository(path)
        repo.initialize()
        return repo

    raise ValueError(
        f"Unknown storage backend '{resolved.backend}'. Supported: {SQLITE}. "
        "(Postgres adapter not yet implemented — config-swap target.)"
    )


__all__ = ["get_repository", "SqliteRepository"]
