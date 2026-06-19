"""Repository port for the learnings domain (self-improving memory)."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from packages.domain.src import Learning


@runtime_checkable
class LearningRepository(Protocol):
    """Persistence for accumulated wins/lessons, queryable per route."""

    def record(self, learning: Learning) -> Learning:
        """Persist a win/lesson, returning it with ``id``/``created_at`` set."""
        ...

    def for_route(
        self, origin: str, destination: str, *,
        kind: Optional[str] = None, limit: int = 20,
    ) -> list[Learning]:
        """Learnings for a route (optionally filtered by kind), newest first."""
        ...


__all__ = ["LearningRepository"]
