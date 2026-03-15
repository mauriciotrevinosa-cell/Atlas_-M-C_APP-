"""
SignalScheduler — asyncio-based background collection loop.

• Holds one instance of all services (singleton via module-level _instance).
• run_once() fetches all enabled sources sequentially (thread-pool for blocking I/O).
• start() / stop() manage the background asyncio task.
• get_scheduler() returns the singleton for use in the API router.
"""
from __future__ import annotations
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from .collectors import RSSCollector, RedditCollector
from .models import SourceType
from .services import AlertService, SignalService, WatchlistService, WhaleService
from .storage import SignalRepository
from . import config as cfg

logger = logging.getLogger(__name__)

_instance: Optional["SignalScheduler"] = None
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="signal_col")


def get_scheduler() -> Optional["SignalScheduler"]:
    return _instance


def init_scheduler(db_path=None) -> "SignalScheduler":
    """Create (or return existing) singleton scheduler. Call once at server startup."""
    global _instance
    if _instance is None:
        _instance = SignalScheduler(db_path=db_path)
    return _instance


class SignalScheduler:
    def __init__(self, db_path=None):
        self.repo       = SignalRepository(db_path)
        self.alert_svc  = AlertService(self.repo)
        self.whale_svc  = WhaleService(self.repo)
        self.signal_svc = SignalService(self.repo, self.alert_svc, self.whale_svc)
        self.watch_svc  = WatchlistService(self.repo)   # also seeds default sources

        self._task:    Optional[asyncio.Task] = None
        self._running: bool = False

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task    = asyncio.create_task(self._loop(), name="signal_terminal_loop")
        logger.info("[Scheduler] Signal Terminal background loop started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[Scheduler] Signal Terminal stopped")

    # ── Main loop ─────────────────────────────────────────────────────────

    async def _loop(self):
        while self._running:
            try:
                result = await self.run_once()
                logger.debug("[Scheduler] loop result: %s", result)
            except Exception as exc:
                logger.error("[Scheduler] loop error: %s", exc)
            await asyncio.sleep(cfg.DEFAULT_REFRESH_INTERVAL)

    # ── Single collection pass ────────────────────────────────────────────

    async def run_once(self) -> Dict[str, Any]:
        """Collect from all enabled sources, returns summary dict."""
        loop    = asyncio.get_event_loop()
        sources = self.watch_svc.get_sources(enabled_only=True)

        total_inserted = 0
        total_dupes    = 0
        source_results: List[Dict] = []

        for source in sources:
            try:
                # Build collector based on type
                collector = self._make_collector(source)
                if collector is None:
                    continue

                # Run blocking I/O in thread pool
                t0      = time.monotonic()
                items   = await loop.run_in_executor(_executor, collector.fetch)
                elapsed = round(time.monotonic() - t0, 2)

                inserted, dupes = self.signal_svc.ingest(items)
                total_inserted += inserted
                total_dupes    += dupes

                self.repo.update_source_fetch(source.id, count=inserted)
                source_results.append({
                    "source": source.name, "fetched": len(items),
                    "inserted": inserted, "dupes": dupes, "elapsed_s": elapsed,
                })
                logger.info("[Scheduler] %s → %d items, +%d new in %.1fs",
                            source.name, len(items), inserted, elapsed)

            except Exception as exc:
                logger.error("[Scheduler] error fetching %s: %s", source.name, exc)
                self.repo.update_source_fetch(source.id, error=str(exc))
                source_results.append({"source": source.name, "error": str(exc)})

        return {
            "sources_run":     len(source_results),
            "total_inserted":  total_inserted,
            "total_dupes":     total_dupes,
            "details":         source_results,
        }

    def _make_collector(self, source):
        if source.type == SourceType.RSS:
            return RSSCollector(source)
        if source.type == SourceType.REDDIT:
            return RedditCollector(source)
        logger.debug("[Scheduler] no collector for type=%s source=%s", source.type, source.id)
        return None
