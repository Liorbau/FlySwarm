"""Learning entity — a stored win or hard lesson the swarm accumulates.

The reflection step writes Learnings after each scan (wins: good deals surfaced;
lessons: e.g. a criterion that expired without ever hitting its target). The
interface agent reads route learnings back to give data-informed guidance — the
self-improving feedback loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

WIN = "win"
LESSON = "lesson"


@dataclass
class Learning:
    """A vendor-neutral piece of accumulated knowledge.

    ``kind`` is ``"win"`` or ``"lesson"``. ``text`` is a short human-readable
    summary. ``data`` holds optional structured extras (e.g. lowest_seen, target).
    ``id`` and ``created_at`` are assigned on save.
    """

    kind: str
    text: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
