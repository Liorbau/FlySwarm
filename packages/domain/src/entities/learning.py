"""Learning entity — a stored win or hard lesson the swarm accumulates.

Reflection writes these after each scan; the interface agent reads them back —
the self-improving feedback loop.
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

    ``kind`` is ``"win"``/``"lesson"``; ``data`` holds optional structured extras;
    ``id``/``created_at`` are assigned on save.
    """

    kind: str
    text: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
