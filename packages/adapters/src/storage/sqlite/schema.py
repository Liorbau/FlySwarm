"""SQLite DDL for every domain's tables (idempotent CREATE ... IF NOT EXISTS).
Intended to port to Postgres (see ``postgres/schema.py``)."""

SCHEMA = """
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

CREATE TABLE IF NOT EXISTS learnings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL,
    origin      TEXT,
    destination TEXT,
    text        TEXT NOT NULL,
    data        TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id    TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_obs_route ON price_observations (origin, destination);
CREATE INDEX IF NOT EXISTS idx_alerts_dedup ON alerts (criterion_id, offer_key);
CREATE INDEX IF NOT EXISTS idx_learn_route ON learnings (origin, destination);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages (chat_id, id);
"""
