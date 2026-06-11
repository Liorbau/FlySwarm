"""SQLite-backed :class:`Repository` implementation.

This is the only place that knows SQL / the sqlite3 driver. It maps canonical
domain objects (``MonitoringCriterion``, ``PriceObservation``, ``Alert``) to and
from rows; no driver types leak past this file. The same schema is intended to
port to Postgres later (SQLite -> Postgres is a config + ``DATABASE_URL`` swap).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from packages.domain.src import (
    Alert,
    Money,
    MonitoringCriterion,
    PriceObservation,
    SearchQuery,
)

BACKEND_NAME = "sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS criteria (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      TEXT    NOT NULL,
    origin       TEXT    NOT NULL,
    destination  TEXT    NOT NULL,
    depart_date  TEXT,
    return_date  TEXT,
    currency     TEXT    NOT NULL DEFAULT 'USD',
    one_way      INTEGER NOT NULL DEFAULT 0,
    target_price REAL,
    label        TEXT,
    active       INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL,
    expires_at   TEXT
);

CREATE TABLE IF NOT EXISTS price_observations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    origin      TEXT NOT NULL,
    destination TEXT NOT NULL,
    amount      REAL NOT NULL,
    currency    TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    depart_date TEXT,
    airline     TEXT,
    source      TEXT
);

CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    criterion_id INTEGER NOT NULL,
    offer_key    TEXT    NOT NULL,
    amount       REAL    NOT NULL,
    currency     TEXT    NOT NULL,
    deal_score   REAL,
    booking_link TEXT,
    sent_at      TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_obs_route ON price_observations (origin, destination);
CREATE INDEX IF NOT EXISTS idx_alerts_dedup ON alerts (criterion_id, offer_key);
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.astimezone(timezone.utc).isoformat() if value else None


def _parse(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class SqliteRepository:
    """Concrete ``Repository`` backed by a local SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def initialize(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ── monitoring criteria ──────────────────────────────────────────────────

    def save_criterion(self, criterion: MonitoringCriterion) -> MonitoringCriterion:
        created_at = criterion.created_at or _now()
        q = criterion.query
        cur = self._conn.execute(
            """
            INSERT INTO criteria
                (user_id, origin, destination, depart_date, return_date,
                 currency, one_way, target_price, label, active, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                criterion.user_id,
                q.origin,
                q.destination,
                q.depart_date,
                q.return_date,
                q.currency,
                int(q.one_way),
                criterion.target_price,
                criterion.label,
                int(criterion.active),
                _iso(created_at),
                _iso(criterion.expires_at),
            ),
        )
        self._conn.commit()
        return MonitoringCriterion(
            user_id=criterion.user_id,
            query=q,
            target_price=criterion.target_price,
            label=criterion.label,
            active=criterion.active,
            id=int(cur.lastrowid),
            created_at=created_at,
            expires_at=criterion.expires_at,
        )

    def get_criterion(self, criterion_id: int) -> Optional[MonitoringCriterion]:
        row = self._conn.execute(
            "SELECT * FROM criteria WHERE id = ?", (criterion_id,)
        ).fetchone()
        return _row_to_criterion(row) if row else None

    def list_active_criteria(
        self, *, user_id: Optional[str] = None
    ) -> list[MonitoringCriterion]:
        if user_id is None:
            rows = self._conn.execute(
                "SELECT * FROM criteria WHERE active = 1 ORDER BY id"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM criteria WHERE active = 1 AND user_id = ? ORDER BY id",
                (user_id,),
            ).fetchall()
        return [_row_to_criterion(r) for r in rows]

    def deactivate_criterion(self, criterion_id: int) -> None:
        self._conn.execute(
            "UPDATE criteria SET active = 0 WHERE id = ?", (criterion_id,)
        )
        self._conn.commit()

    def due_criteria(self, now: Optional[datetime] = None) -> list[MonitoringCriterion]:
        """Active criteria whose deadline has not passed — what the scan processes."""
        now = now or _now()
        rows = self._conn.execute(
            """
            SELECT * FROM criteria
            WHERE active = 1 AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY id
            """,
            (_iso(now),),
        ).fetchall()
        return [_row_to_criterion(r) for r in rows]

    def deactivate_expired(self, now: Optional[datetime] = None) -> list[int]:
        """Auto-stop active criteria past their deadline; returns the ids stopped."""
        now = now or _now()
        rows = self._conn.execute(
            "SELECT id FROM criteria WHERE active = 1 AND expires_at IS NOT NULL AND expires_at <= ?",
            (_iso(now),),
        ).fetchall()
        ids = [int(r["id"]) for r in rows]
        if ids:
            self._conn.execute(
                "UPDATE criteria SET active = 0 WHERE id IN (%s)"
                % ",".join("?" for _ in ids),
                ids,
            )
            self._conn.commit()
        return ids

    # ── price history ────────────────────────────────────────────────────────

    def record_observation(self, observation: PriceObservation) -> PriceObservation:
        observed_at = observation.observed_at or _now()
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
                _iso(observed_at),
                observation.depart_date,
                observation.airline,
                observation.source,
            ),
        )
        self._conn.commit()
        return PriceObservation(
            origin=observation.origin,
            destination=observation.destination,
            price=observation.price,
            observed_at=observed_at,
            depart_date=observation.depart_date,
            airline=observation.airline,
            source=observation.source,
            id=int(cur.lastrowid),
        )

    def price_history(
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
                (origin, destination, _iso(since), limit),
            ).fetchall()
        return [_row_to_observation(r) for r in rows]

    # ── alerts ───────────────────────────────────────────────────────────────

    def record_alert(self, alert: Alert) -> Alert:
        sent_at = alert.sent_at or _now()
        cur = self._conn.execute(
            """
            INSERT INTO alerts
                (criterion_id, offer_key, amount, currency, deal_score,
                 booking_link, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert.criterion_id,
                alert.offer_key,
                alert.price.amount,
                alert.price.currency,
                alert.deal_score,
                alert.booking_link,
                _iso(sent_at),
            ),
        )
        self._conn.commit()
        return Alert(
            criterion_id=alert.criterion_id,
            offer_key=alert.offer_key,
            price=alert.price,
            deal_score=alert.deal_score,
            booking_link=alert.booking_link,
            id=int(cur.lastrowid),
            sent_at=sent_at,
        )

    def was_alerted(self, criterion_id: int, offer_key: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM alerts WHERE criterion_id = ? AND offer_key = ? LIMIT 1",
            (criterion_id, offer_key),
        ).fetchone()
        return row is not None

    def recent_alerts(self, *, limit: int = 50) -> list[Alert]:
        rows = self._conn.execute(
            "SELECT * FROM alerts ORDER BY sent_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_alert(r) for r in rows]


# ── row -> entity mappers ────────────────────────────────────────────────────


def _row_to_criterion(row: sqlite3.Row) -> MonitoringCriterion:
    return MonitoringCriterion(
        user_id=row["user_id"],
        query=SearchQuery(
            origin=row["origin"],
            destination=row["destination"],
            depart_date=row["depart_date"],
            return_date=row["return_date"],
            currency=row["currency"],
            one_way=bool(row["one_way"]),
        ),
        target_price=row["target_price"],
        label=row["label"],
        active=bool(row["active"]),
        id=row["id"],
        created_at=_parse(row["created_at"]),
        expires_at=_parse(row["expires_at"]),
    )


def _row_to_observation(row: sqlite3.Row) -> PriceObservation:
    return PriceObservation(
        origin=row["origin"],
        destination=row["destination"],
        price=Money(amount=row["amount"], currency=row["currency"]),
        observed_at=_parse(row["observed_at"]),
        depart_date=row["depart_date"],
        airline=row["airline"],
        source=row["source"],
        id=row["id"],
    )


def _row_to_alert(row: sqlite3.Row) -> Alert:
    return Alert(
        criterion_id=row["criterion_id"],
        offer_key=row["offer_key"],
        price=Money(amount=row["amount"], currency=row["currency"]),
        deal_score=row["deal_score"],
        booking_link=row["booking_link"],
        id=row["id"],
        sent_at=_parse(row["sent_at"]),
    )


__all__ = ["SqliteRepository", "BACKEND_NAME"]
