"""Postgres implementation of the prices-domain repository port (corpus)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from psycopg_pool import ConnectionPool

from packages.domain.src import PriceObservation

from ._common import now, row_to_observation


class PostgresPriceRepo:
    """``PriceRepository`` backed by a shared connection pool."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def record(self, observation: PriceObservation) -> PriceObservation:
        observed_at = observation.observed_at or now()
        with self._pool.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO price_observations
                    (origin, destination, amount, currency, observed_at,
                     depart_date, airline, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    observation.origin,
                    observation.destination,
                    observation.price.amount,
                    observation.price.currency,
                    observed_at,
                    observation.depart_date,
                    observation.airline,
                    observation.source,
                ),
            ).fetchone()
        return PriceObservation(
            origin=observation.origin, destination=observation.destination,
            price=observation.price, observed_at=observed_at,
            depart_date=observation.depart_date, airline=observation.airline,
            source=observation.source, id=int(row["id"]),
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
        with self._pool.connection() as conn:
            if since is None:
                rows = conn.execute(
                    """
                    SELECT * FROM price_observations
                    WHERE origin = %s AND destination = %s
                    ORDER BY observed_at DESC LIMIT %s
                    """,
                    (origin, destination, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM price_observations
                    WHERE origin = %s AND destination = %s AND observed_at >= %s
                    ORDER BY observed_at DESC LIMIT %s
                    """,
                    (origin, destination, since, limit),
                ).fetchall()
        return [row_to_observation(r) for r in rows]


__all__ = ["PostgresPriceRepo"]
