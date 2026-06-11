"""Alert entity — a record that we notified a user about a deal.

Recording alerts lets the notification step de-duplicate (don't ping twice for
the same offer) and gives the self-improving layer a log of "earned wins".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from packages.domain.src.value_objects.money import Money


@dataclass
class Alert:
    """A sent (or about-to-be-sent) deal notification.

    ``offer_key`` is a stable de-dup key for the underlying offer (e.g.
    route+depart_date+price). ``deal_score`` is the judged quality (0..1 or a
    project-defined scale). ``id`` and ``sent_at`` are assigned on save.
    """

    criterion_id: int
    offer_key: str
    price: Money
    deal_score: Optional[float] = None
    booking_link: Optional[str] = None
    id: Optional[int] = None
    sent_at: Optional[datetime] = None
