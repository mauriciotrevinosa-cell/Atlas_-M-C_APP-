"""
Signal Terminal — SQLite repository (raw sqlite3, consistent with Atlas server.py).
All public methods are synchronous; call from a thread-pool if needed in async context.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from ..models import (
    Signal, Source, Match, AlertRule, WhaleEvent, WatchlistItem,
)
from .schema import SCHEMA_SQL
from .. import config as cfg


# ── helpers ──────────────────────────────────────────────────────────────

def _dt(v: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(v) if v else None


def _str(v: Optional[datetime]) -> Optional[str]:
    return v.isoformat() if v else None


class SignalRepository:
    """All DB access for the Signal Terminal."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or cfg.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_schema()

    # ── Internal ─────────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        with self._lock, self._conn() as conn:
            conn.executescript(SCHEMA_SQL)

    # ── Sources ──────────────────────────────────────────────────────────

    def upsert_source(self, src: Source) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO st_sources
                  (id, name, type, url, enabled, refresh_interval, config_json,
                   last_fetched_at, last_error, error_count, total_fetched)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                  name=excluded.name, type=excluded.type, url=excluded.url,
                  enabled=excluded.enabled, refresh_interval=excluded.refresh_interval,
                  config_json=excluded.config_json,
                  last_fetched_at=excluded.last_fetched_at, last_error=excluded.last_error,
                  error_count=excluded.error_count, total_fetched=excluded.total_fetched
            """, (
                src.id, src.name, src.type, src.url, int(src.enabled),
                src.refresh_interval, json.dumps(src.config),
                _str(src.last_fetched_at), src.last_error,
                src.error_count, src.total_fetched,
            ))

    def get_sources(self, enabled_only: bool = True) -> List[Source]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM st_sources" + (" WHERE enabled=1" if enabled_only else "")
            ).fetchall()
        return [self._row_to_source(r) for r in rows]

    def get_source(self, source_id: str) -> Optional[Source]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM st_sources WHERE id=?", (source_id,)).fetchone()
        return self._row_to_source(row) if row else None

    def update_source_fetch(self, source_id: str, error: Optional[str] = None, count: int = 0):
        with self._lock, self._conn() as conn:
            if error:
                conn.execute("""
                    UPDATE st_sources
                    SET last_fetched_at=?, last_error=?, error_count=error_count+1
                    WHERE id=?
                """, (datetime.utcnow().isoformat(), error, source_id))
            else:
                conn.execute("""
                    UPDATE st_sources
                    SET last_fetched_at=?, last_error=NULL, error_count=0,
                        total_fetched=total_fetched+?
                    WHERE id=?
                """, (datetime.utcnow().isoformat(), count, source_id))

    @staticmethod
    def _row_to_source(row) -> Source:
        return Source(
            id=row["id"], name=row["name"], type=row["type"], url=row["url"],
            enabled=bool(row["enabled"]), refresh_interval=row["refresh_interval"],
            config=json.loads(row["config_json"] or "{}"),
            last_fetched_at=_dt(row["last_fetched_at"]),
            last_error=row["last_error"], error_count=row["error_count"],
            total_fetched=row["total_fetched"],
        )

    # ── Signals ──────────────────────────────────────────────────────────

    def insert_signal(self, sig: Signal) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO st_signals
                  (id, source_id, raw_id, url, title, body, author,
                   published_at, collected_at, category, sentiment, sentiment_score,
                   tickers_json, keywords_json, tags_json, content_hash,
                   relevance_score, urgency)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                sig.id, sig.source_id, sig.raw_id, sig.url, sig.title, sig.body,
                sig.author, sig.published_at.isoformat(), sig.collected_at.isoformat(),
                sig.category, sig.sentiment, sig.sentiment_score,
                json.dumps(sig.tickers), json.dumps(sig.keywords), json.dumps(sig.tags),
                sig.content_hash, sig.relevance_score, sig.urgency,
            ))

    def hash_exists(self, content_hash: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM st_signals WHERE content_hash=? LIMIT 1", (content_hash,)
            ).fetchone()
        return row is not None

    def get_signals(
        self,
        limit: int = 50,
        offset: int = 0,
        ticker: Optional[str] = None,
        category: Optional[str] = None,
        sentiment: Optional[str] = None,
        source_id: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> List[Signal]:
        filters, params = [], []
        if ticker:
            filters.append("tickers_json LIKE ?")
            params.append(f'%"{ticker.upper()}"%')
        if category:
            filters.append("category=?"); params.append(category)
        if sentiment:
            filters.append("sentiment=?"); params.append(sentiment)
        if source_id:
            filters.append("source_id=?"); params.append(source_id)
        if since:
            filters.append("published_at>=?"); params.append(since.isoformat())

        where = ("WHERE " + " AND ".join(filters)) if filters else ""
        params += [limit, offset]

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM st_signals {where} ORDER BY published_at DESC LIMIT ? OFFSET ?",
                params,
            ).fetchall()
        return [self._row_to_signal(r) for r in rows]

    def get_signal(self, signal_id: str) -> Optional[Signal]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM st_signals WHERE id=?", (signal_id,)).fetchone()
        return self._row_to_signal(row) if row else None

    @staticmethod
    def _row_to_signal(row) -> Signal:
        return Signal(
            id=row["id"], source_id=row["source_id"], raw_id=row["raw_id"],
            url=row["url"], title=row["title"], body=row["body"], author=row["author"],
            published_at=datetime.fromisoformat(row["published_at"]),
            collected_at=datetime.fromisoformat(row["collected_at"]),
            category=row["category"], sentiment=row["sentiment"],
            sentiment_score=row["sentiment_score"],
            tickers=json.loads(row["tickers_json"] or "[]"),
            keywords=json.loads(row["keywords_json"] or "[]"),
            tags=json.loads(row["tags_json"] or "[]"),
            content_hash=row["content_hash"],
            relevance_score=row["relevance_score"], urgency=row["urgency"],
        )

    # ── Matches ──────────────────────────────────────────────────────────

    def insert_match(self, m: Match) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO st_matches
                  (id, signal_id, watchlist_item_id, ticker, match_type, match_score, created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (
                m.id, m.signal_id, m.watchlist_item_id, m.ticker,
                m.match_type, m.match_score, m.created_at.isoformat(),
            ))

    def get_matches_for_signal(self, signal_id: str) -> List[Match]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM st_matches WHERE signal_id=?", (signal_id,)
            ).fetchall()
        return [self._row_to_match(r) for r in rows]

    @staticmethod
    def _row_to_match(row) -> Match:
        return Match(
            id=row["id"], signal_id=row["signal_id"],
            watchlist_item_id=row["watchlist_item_id"], ticker=row["ticker"],
            match_type=row["match_type"], match_score=row["match_score"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # ── Alert Rules ──────────────────────────────────────────────────────

    def upsert_alert_rule(self, rule: AlertRule) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO st_alert_rules
                  (id, name, enabled, conditions_json, action, action_config_json,
                   created_at, last_triggered_at, trigger_count)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                  name=excluded.name, enabled=excluded.enabled,
                  conditions_json=excluded.conditions_json, action=excluded.action,
                  action_config_json=excluded.action_config_json,
                  last_triggered_at=excluded.last_triggered_at,
                  trigger_count=excluded.trigger_count
            """, (
                rule.id, rule.name, int(rule.enabled),
                json.dumps(rule.conditions), rule.action,
                json.dumps(rule.action_config), rule.created_at.isoformat(),
                _str(rule.last_triggered_at), rule.trigger_count,
            ))

    def get_alert_rules(self, enabled_only: bool = True) -> List[AlertRule]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM st_alert_rules" + (" WHERE enabled=1" if enabled_only else "")
            ).fetchall()
        return [self._row_to_rule(r) for r in rows]

    def record_alert_trigger(self, rule_id: str, signal_id: str, details: Dict[str, Any] = None):
        import uuid as _uuid
        now = datetime.utcnow().isoformat()
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO st_alert_triggers (id, rule_id, signal_id, fired_at, details_json)
                VALUES (?,?,?,?,?)
            """, (str(_uuid.uuid4()), rule_id, signal_id, now, json.dumps(details or {})))
            conn.execute("""
                UPDATE st_alert_rules
                SET last_triggered_at=?, trigger_count=trigger_count+1
                WHERE id=?
            """, (now, rule_id))

    def delete_alert_rule(self, rule_id: str) -> bool:
        with self._lock, self._conn() as conn:
            cur = conn.execute("DELETE FROM st_alert_rules WHERE id=?", (rule_id,))
            return cur.rowcount > 0

    @staticmethod
    def _row_to_rule(row) -> AlertRule:
        return AlertRule(
            id=row["id"], name=row["name"], enabled=bool(row["enabled"]),
            conditions=json.loads(row["conditions_json"] or "{}"),
            action=row["action"],
            action_config=json.loads(row["action_config_json"] or "{}"),
            created_at=datetime.fromisoformat(row["created_at"]),
            last_triggered_at=_dt(row["last_triggered_at"]),
            trigger_count=row["trigger_count"],
        )

    # ── Whale Events ─────────────────────────────────────────────────────

    def insert_whale_event(self, event: WhaleEvent) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO st_whale_events
                  (id, signal_id, ticker, event_type, size, size_label,
                   description, source, confidence, detected_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
                event.id, event.signal_id, event.ticker, event.event_type,
                event.size, event.size_label, event.description,
                event.source, event.confidence, event.detected_at.isoformat(),
            ))

    def get_whale_events(
        self, ticker: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[WhaleEvent]:
        if ticker:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM st_whale_events WHERE ticker=? ORDER BY detected_at DESC LIMIT ? OFFSET ?",
                    (ticker, limit, offset),
                ).fetchall()
        else:
            with self._conn() as conn:
                rows = conn.execute(
                    "SELECT * FROM st_whale_events ORDER BY detected_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
        return [self._row_to_whale(r) for r in rows]

    @staticmethod
    def _row_to_whale(row) -> WhaleEvent:
        return WhaleEvent(
            id=row["id"], signal_id=row["signal_id"], ticker=row["ticker"],
            event_type=row["event_type"], size=row["size"], size_label=row["size_label"],
            description=row["description"], source=row["source"],
            confidence=row["confidence"],
            detected_at=datetime.fromisoformat(row["detected_at"]),
        )

    # ── Watchlist ────────────────────────────────────────────────────────

    def upsert_watchlist_item(self, item: WatchlistItem) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO st_watchlist
                  (id, ticker, name, asset_type, priority, tags_json, aliases_json,
                   notes, alert_enabled, added_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(ticker) DO UPDATE SET
                  name=excluded.name, asset_type=excluded.asset_type,
                  priority=excluded.priority, tags_json=excluded.tags_json,
                  aliases_json=excluded.aliases_json, notes=excluded.notes,
                  alert_enabled=excluded.alert_enabled
            """, (
                item.id, item.ticker.upper(), item.name, item.asset_type,
                item.priority, json.dumps(item.tags), json.dumps(item.aliases),
                item.notes, int(item.alert_enabled), item.added_at.isoformat(),
            ))

    def get_watchlist(self) -> List[WatchlistItem]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM st_watchlist ORDER BY priority DESC, ticker ASC").fetchall()
        return [self._row_to_watch(r) for r in rows]

    def delete_watchlist_item(self, ticker: str) -> bool:
        with self._lock, self._conn() as conn:
            cur = conn.execute("DELETE FROM st_watchlist WHERE ticker=?", (ticker.upper(),))
        return cur.rowcount > 0

    @staticmethod
    def _row_to_watch(row) -> WatchlistItem:
        return WatchlistItem(
            id=row["id"], ticker=row["ticker"], name=row["name"],
            asset_type=row["asset_type"], priority=row["priority"],
            tags=json.loads(row["tags_json"] or "[]"),
            aliases=json.loads(row["aliases_json"] or "[]"),
            notes=row["notes"], alert_enabled=bool(row["alert_enabled"]),
            added_at=datetime.fromisoformat(row["added_at"]),
        )

    # ── Stats ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            total_signals  = conn.execute("SELECT COUNT(*) FROM st_signals").fetchone()[0]
            total_sources  = conn.execute("SELECT COUNT(*) FROM st_sources WHERE enabled=1").fetchone()[0]
            total_watch    = conn.execute("SELECT COUNT(*) FROM st_watchlist").fetchone()[0]
            total_whales   = conn.execute("SELECT COUNT(*) FROM st_whale_events").fetchone()[0]
            total_alerts   = conn.execute("SELECT COUNT(*) FROM st_alert_triggers").fetchone()[0]
            recent_signals = conn.execute(
                "SELECT COUNT(*) FROM st_signals WHERE collected_at >= datetime('now','-24 hours')"
            ).fetchone()[0]
        return {
            "total_signals":   total_signals,
            "recent_24h":      recent_signals,
            "active_sources":  total_sources,
            "watchlist_items": total_watch,
            "whale_events":    total_whales,
            "alert_triggers":  total_alerts,
        }
