"""The ``Storage`` bundle protocol — one handle exposing every domain's repo
(``.criteria`` / ``.prices`` / ``.alerts`` / ``.learnings`` / ``.conversations``).
Concrete bundles live per engine in ``sqlite`` / ``postgres``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from packages.domain.src.alerts import AlertRepository
from packages.domain.src.conversations import ConversationRepository
from packages.domain.src.learnings import LearningRepository
from packages.domain.src.prices import PriceRepository
from packages.domain.src.watches import CriteriaRepository


@runtime_checkable
class Storage(Protocol):
    """Aggregate of every domain repository, sharing one engine connection."""

    criteria: CriteriaRepository
    prices: PriceRepository
    alerts: AlertRepository
    learnings: LearningRepository
    conversations: ConversationRepository

    def initialize(self) -> None:
        """Create schema if absent. Idempotent."""
        ...

    def close(self) -> None:
        ...


__all__ = ["Storage"]
