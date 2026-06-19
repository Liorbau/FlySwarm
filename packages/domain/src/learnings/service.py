"""Learnings domain service — record and recall the swarm's wins/lessons."""

from __future__ import annotations

from typing import Optional

from packages.domain.src import Learning

from .repository import LearningRepository


class LearningsService:
    def __init__(self, learnings: LearningRepository) -> None:
        self._learnings = learnings

    def record(self, learning: Learning) -> Learning:
        return self._learnings.record(learning)

    def for_route(
        self, origin: str, destination: str, *,
        kind: Optional[str] = None, limit: int = 20,
    ) -> list[Learning]:
        return self._learnings.for_route(origin, destination, kind=kind, limit=limit)


__all__ = ["LearningsService"]
