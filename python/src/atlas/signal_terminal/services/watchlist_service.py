"""
WatchlistService — CRUD for watchlist items + source management.
"""
from __future__ import annotations
import logging
from typing import List, Optional

from ..models import Source, SourceType, WatchlistItem
from ..storage import SignalRepository
from .. import config as cfg

logger = logging.getLogger(__name__)


class WatchlistService:
    def __init__(self, repo: SignalRepository):
        self._repo = repo
        self._ensure_default_sources()

    def _ensure_default_sources(self):
        """Seed default RSS and Reddit sources if the DB is empty."""
        existing = {s.id for s in self._repo.get_sources(enabled_only=False)}

        for src_cfg in cfg.DEFAULT_RSS_SOURCES:
            if src_cfg["id"] not in existing:
                self._repo.upsert_source(Source(
                    id=src_cfg["id"],
                    name=src_cfg["name"],
                    type=SourceType.RSS,
                    url=src_cfg["url"],
                    refresh_interval=src_cfg.get("refresh_interval", 300),
                ))

        for src_cfg in cfg.DEFAULT_REDDIT_SOURCES:
            if src_cfg["id"] not in existing:
                self._repo.upsert_source(Source(
                    id=src_cfg["id"],
                    name=src_cfg["name"],
                    type=SourceType.REDDIT,
                    url="",
                    refresh_interval=src_cfg.get("refresh_interval", 600),
                    config={
                        "subreddit": src_cfg["subreddit"],
                        "sort": src_cfg.get("sort", "new"),
                        "limit": src_cfg.get("limit", 25),
                    },
                ))

    # ── Watchlist ─────────────────────────────────────────────────────────

    def add(self, item: WatchlistItem) -> WatchlistItem:
        item.ticker = item.ticker.upper()
        self._repo.upsert_watchlist_item(item)
        logger.info("[Watchlist] added %s", item.ticker)
        return item

    def remove(self, ticker: str) -> bool:
        ok = self._repo.delete_watchlist_item(ticker.upper())
        if ok:
            logger.info("[Watchlist] removed %s", ticker.upper())
        return ok

    def get_all(self) -> List[WatchlistItem]:
        return self._repo.get_watchlist()

    # ── Sources ───────────────────────────────────────────────────────────

    def get_sources(self, enabled_only: bool = True) -> List[Source]:
        return self._repo.get_sources(enabled_only=enabled_only)

    def add_source(self, source: Source) -> Source:
        self._repo.upsert_source(source)
        return source

    def toggle_source(self, source_id: str, enabled: bool) -> Optional[Source]:
        src = self._repo.get_source(source_id)
        if src:
            src.enabled = enabled
            self._repo.upsert_source(src)
        return src
