"""Postgres DDL for every domain's tables (idempotent CREATE ... IF NOT EXISTS).
Native PG types (BIGSERIAL/TIMESTAMPTZ/BOOLEAN/JSONB). Mirrors ``sqlite/schema.py``."""

SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS criteria (
        id           BIGSERIAL PRIMARY KEY,
        user_id      TEXT NOT NULL,
        origin       TEXT NOT NULL,
        destination  TEXT NOT NULL,
        depart_date  TEXT,
        return_date  TEXT,
        currency     TEXT NOT NULL DEFAULT 'USD',
        one_way      BOOLEAN NOT NULL DEFAULT FALSE,
        target_price DOUBLE PRECISION,
        label        TEXT,
        active       BOOLEAN NOT NULL DEFAULT TRUE,
        created_at   TIMESTAMPTZ NOT NULL,
        expires_at   TIMESTAMPTZ
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS price_observations (
        id          BIGSERIAL PRIMARY KEY,
        origin      TEXT NOT NULL,
        destination TEXT NOT NULL,
        amount      DOUBLE PRECISION NOT NULL,
        currency    TEXT NOT NULL,
        observed_at TIMESTAMPTZ NOT NULL,
        depart_date TEXT,
        airline     TEXT,
        source      TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alerts (
        id           BIGSERIAL PRIMARY KEY,
        criterion_id BIGINT NOT NULL,
        offer_key    TEXT NOT NULL,
        amount       DOUBLE PRECISION NOT NULL,
        currency     TEXT NOT NULL,
        deal_score   DOUBLE PRECISION,
        booking_link TEXT,
        sent_at      TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS learnings (
        id          BIGSERIAL PRIMARY KEY,
        kind        TEXT NOT NULL,
        origin      TEXT,
        destination TEXT,
        text        TEXT NOT NULL,
        data        JSONB,
        created_at  TIMESTAMPTZ NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id         BIGSERIAL PRIMARY KEY,
        chat_id    TEXT NOT NULL,
        role       TEXT NOT NULL,
        content    TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_obs_route ON price_observations (origin, destination)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_dedup ON alerts (criterion_id, offer_key)",
    "CREATE INDEX IF NOT EXISTS idx_learn_route ON learnings (origin, destination)",
    "CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages (chat_id, id)",
)
