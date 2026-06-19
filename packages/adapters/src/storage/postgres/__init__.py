"""Postgres storage engine — per-domain repositories composed into a bundle."""

from .storage import BACKEND_NAME, PostgresStorage

__all__ = ["PostgresStorage", "BACKEND_NAME"]
