"""SQLite implementation of the prices-domain repository port (corpus)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from packages.domain.src import PriceObservation

from ._common import iso, now, row_to_observation


class SqlitePriceRepo:
    """``PriceRepository`` backed by a shared sqlite3 connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def record(self, observation: PriceObservation) -> PriceObservation:
        observed_at = observation.observed_at or now()
        cur = self._conn.execute(
            """
            INSERT INTO price_observations
                (origin, destination, amount, currency, observed_at,
                 depart_date, airline, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.origin,
                observation.destination,
                observation.price.amount,
                observation.price.currency,
                iso(observed_at),
                observation.depart_date,
                observation.airline,
                observation.source,
            ),
        )
        self._conn.commit()
        return PriceObservation(
            origin=observation.origin, destination=observation.destination,
            price=observation.price, observed_at=observed_at,
            depart_date=observation.depart_date, airline=observation.airline,
            source=observation.source, id=int(cur.lastrowid),
        )

    def history(
        self,
        origin: str,
        destination: str,
        *,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[PriceObservation]:
        origin = origin.strip().upper()
        destination = destination.strip().upper()
        if since is None:
            rows = self._conn.execute(
                """
                SELECT * FROM price_observations
                WHERE origin = ? AND destination = ?
                ORDER BY observed_at DESC LIMIT ?
                """,
                (origin, destination, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT * FROM price_observations
                WHERE origin = ? AND destination = ? AND observed_at >= ?
                ORDER BY observed_at DESC LIMIT ?
                """,
                (origin, destination, iso(since), limit),
            ).fetchall()
        return [row_to_observation(r) for r in rows]


__all__ = ["SqlitePriceRepo"]
