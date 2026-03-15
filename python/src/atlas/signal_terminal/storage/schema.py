"""
Signal Terminal — SQLite schema DDL.
All tables are prefixed st_ to avoid collision with other Atlas tables.
"""

SCHEMA_SQL = """

-- ── Sources ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS st_sources (
    id               TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    type             TEXT NOT NULL,          -- rss | reddit | webhook | manual
    url              TEXT NOT NULL DEFAULT '',
    enabled          INTEGER NOT NULL DEFAULT 1,
    refresh_interval INTEGER NOT NULL DEFAULT 300,
    config_json      TEXT NOT NULL DEFAULT '{}',
    last_fetched_at  TEXT,
    last_error       TEXT,
    error_count      INTEGER NOT NULL DEFAULT 0,
    total_fetched    INTEGER NOT NULL DEFAULT 0
);

-- ── Signals ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS st_signals (
    id               TEXT PRIMARY KEY,
    source_id        TEXT NOT NULL REFERENCES st_sources(id),
    raw_id           TEXT NOT NULL DEFAULT '',
    url              TEXT,
    title            TEXT NOT NULL,
    body             TEXT,
    author           TEXT,
    published_at     TEXT NOT NULL,
    collected_at     TEXT NOT NULL,

    -- Classification
    category         TEXT NOT NULL DEFAULT 'unknown',
    sentiment        TEXT NOT NULL DEFAULT 'neutral',
    sentiment_score  REAL NOT NULL DEFAULT 0.0,

    -- Extraction
    tickers_json     TEXT NOT NULL DEFAULT '[]',
    keywords_json    TEXT NOT NULL DEFAULT '[]',
    tags_json        TEXT NOT NULL DEFAULT '[]',

    -- Dedup
    content_hash     TEXT NOT NULL DEFAULT '',

    -- Scoring
    relevance_score  REAL NOT NULL DEFAULT 0.0,
    urgency          TEXT NOT NULL DEFAULT 'low'
);

CREATE INDEX IF NOT EXISTS idx_signals_source     ON st_signals(source_id);
CREATE INDEX IF NOT EXISTS idx_signals_published  ON st_signals(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_hash       ON st_signals(content_hash);
CREATE INDEX IF NOT EXISTS idx_signals_category   ON st_signals(category);
CREATE INDEX IF NOT EXISTS idx_signals_sentiment  ON st_signals(sentiment);

-- ── Matches ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS st_matches (
    id                  TEXT PRIMARY KEY,
    signal_id           TEXT NOT NULL REFERENCES st_signals(id),
    watchlist_item_id   TEXT NOT NULL REFERENCES st_watchlist(id),
    ticker              TEXT NOT NULL,
    match_type          TEXT NOT NULL DEFAULT 'exact',
    match_score         REAL NOT NULL DEFAULT 1.0,
    created_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_matches_signal    ON st_matches(signal_id);
CREATE INDEX IF NOT EXISTS idx_matches_watchlist ON st_matches(watchlist_item_id);
CREATE INDEX IF NOT EXISTS idx_matches_ticker    ON st_matches(ticker);

-- ── Alert Rules ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS st_alert_rules (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    enabled             INTEGER NOT NULL DEFAULT 1,
    conditions_json     TEXT NOT NULL DEFAULT '{}',
    action              TEXT NOT NULL DEFAULT 'log',
    action_config_json  TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL,
    last_triggered_at   TEXT,
    trigger_count       INTEGER NOT NULL DEFAULT 0
);

-- ── Alert Triggers (log of fired alerts) ────────────────────────────────
CREATE TABLE IF NOT EXISTS st_alert_triggers (
    id           TEXT PRIMARY KEY,
    rule_id      TEXT NOT NULL REFERENCES st_alert_rules(id),
    signal_id    TEXT NOT NULL REFERENCES st_signals(id),
    fired_at     TEXT NOT NULL,
    details_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_triggers_rule   ON st_alert_triggers(rule_id);
CREATE INDEX IF NOT EXISTS idx_triggers_signal ON st_alert_triggers(signal_id);
CREATE INDEX IF NOT EXISTS idx_triggers_fired  ON st_alert_triggers(fired_at DESC);

-- ── Whale Events ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS st_whale_events (
    id           TEXT PRIMARY KEY,
    signal_id    TEXT REFERENCES st_signals(id),
    ticker       TEXT NOT NULL,
    event_type   TEXT NOT NULL DEFAULT 'unknown',
    size         REAL,
    size_label   TEXT NOT NULL DEFAULT '',
    description  TEXT NOT NULL DEFAULT '',
    source       TEXT NOT NULL DEFAULT '',
    confidence   REAL NOT NULL DEFAULT 0.5,
    detected_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_whale_ticker ON st_whale_events(ticker);
CREATE INDEX IF NOT EXISTS idx_whale_date   ON st_whale_events(detected_at DESC);

-- ── Watchlist ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS st_watchlist (
    id            TEXT PRIMARY KEY,
    ticker        TEXT NOT NULL UNIQUE,
    name          TEXT,
    asset_type    TEXT NOT NULL DEFAULT 'stock',
    priority      TEXT NOT NULL DEFAULT 'medium',
    tags_json     TEXT NOT NULL DEFAULT '[]',
    aliases_json  TEXT NOT NULL DEFAULT '[]',
    notes         TEXT,
    alert_enabled INTEGER NOT NULL DEFAULT 1,
    added_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_watchlist_ticker ON st_watchlist(ticker);
"""
