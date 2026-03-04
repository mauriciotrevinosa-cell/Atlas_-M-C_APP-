"""
Top-Level DataRouter
====================
Single entry-point for all market data requests.

Flow:
  allow_network=True  → check fresh cache → try YFinance → write cache
                        → on failure: stale cache (offline fallback)
  allow_network=False → cache-only (stale allowed, never calls network)

This is the preferred way to fetch data throughout Atlas.
`market_finance.data_layer.DataRouter` is a more advanced phase-1
workflow router; this module is the lightweight, reusable core.

Copyright (c) 2026 M&C. All rights reserved.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional

import pandas as pd

from atlas.data_layer.normalize import normalize_ohlcv
from atlas.providers.cache_provider import CacheProvider
from atlas.providers.yfinance_provider import NetworkUnavailableError, YFinanceProvider

logger = logging.getLogger("atlas.data_router")


def _default_end() -> str:
    return date.today().isoformat()


def _default_start(years: int = 1) -> str:
    return (date.today() - timedelta(days=365 * years)).isoformat()


class DataRouter:
    """
    Unified data access layer for Atlas.

    Args:
        allow_network: True  → live yfinance fetches with cache write-back.
                       False → offline mode; cache only.
        cache_dir:     Directory for Parquet cache files.
        ttl_hours:     Cache TTL for fresh-cache check (default 24 h).

    Example::

        # Online (default)
        router = DataRouter(allow_network=True)
        df = router.get("AAPL", "2024-01-01", "2024-12-31")

        # Offline — only reads from disk cache
        router = DataRouter(allow_network=False)
        df = router.get("AAPL", "2024-01-01", "2024-12-31")
    """

    def __init__(
        self,
        allow_network: bool = True,
        cache_dir: str = "data/cache/router",
        ttl_hours: int = 24,
    ) -> None:
        self.allow_network = allow_network
        self._yf = YFinanceProvider(allow_network=allow_network)
        self._cache = CacheProvider(cache_dir=cache_dir, ttl_hours=ttl_hours)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(
        self,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a single ticker.

        Resolution order:
        1. Fresh cache hit (always checked first)
        2. Live yfinance fetch + cache write (if allow_network=True)
        3. Stale cache fallback (offline mode or network failure)

        Args:
            ticker:   Ticker symbol (e.g. "AAPL", "BTC-USD", "^GSPC")
            start:    Start date "YYYY-MM-DD" (default: 1 year ago)
            end:      End date "YYYY-MM-DD" (default: today)
            interval: Candle interval — "1d", "1h", "1wk" (default: "1d")

        Returns:
            Normalized OHLCV DataFrame (lowercase columns, UTC-indexed).

        Raises:
            RuntimeError: if no data found anywhere (no cache, no network).
        """
        start = start or _default_start()
        end = end or _default_end()

        # 1. Fresh cache
        cached = self._cache.get(ticker, start, end, interval, allow_stale=False)
        if cached is not None:
            logger.debug("DataRouter: fresh cache hit for %s", ticker)
            return _normalize(cached)

        # 2. Live fetch (only when network is permitted)
        if self.allow_network:
            try:
                df = self._yf.get_historical(ticker, start=start, end=end, interval=interval)
                if df is not None and not df.empty:
                    self._cache.set(ticker, start, end, interval, df)
                    logger.info("DataRouter: fetched %s from yfinance (%d rows)", ticker, len(df))
                    return _normalize(df)
                logger.warning("DataRouter: yfinance returned empty frame for %s", ticker)
            except NetworkUnavailableError:
                pass  # shouldn't happen since allow_network=True, but be safe
            except Exception as exc:
                logger.warning("DataRouter: yfinance failed for %s — %s", ticker, exc)

        # 3. Stale cache fallback
        stale = self._cache.get(ticker, start, end, interval, allow_stale=True)
        if stale is not None:
            logger.info("DataRouter: using stale cache for %s", ticker)
            return _normalize(stale)

        raise RuntimeError(
            f"DataRouter: no data for {ticker} ({start} → {end}). "
            "Network available: " + str(self.allow_network) + "."
        )

    def get_many(
        self,
        tickers: Iterable[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch OHLCV data for multiple tickers.

        Returns a dict mapping ticker → DataFrame.  Tickers that fail
        are logged and omitted from the result (no exception raised).
        """
        start = start or _default_start()
        end = end or _default_end()

        results: Dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            try:
                results[ticker] = self.get(ticker, start=start, end=end, interval=interval)
            except Exception as exc:
                logger.error("DataRouter.get_many: skipping %s — %s", ticker, exc)
        return results

    def get_quote(self, ticker: str) -> Dict:
        """
        Get latest delayed quote (~15 min) for a ticker.

        Falls back to ``{"symbol": ticker, "price": None, "error": "offline"}``
        when allow_network=False.
        """
        if not self.allow_network:
            logger.debug("DataRouter.get_quote: offline — no quote for %s", ticker)
            return {"symbol": ticker, "price": None, "error": "offline", "provider": "cache"}
        try:
            return self._yf.get_quote(ticker)
        except Exception as exc:
            logger.warning("DataRouter.get_quote: failed for %s — %s", ticker, exc)
            return {"symbol": ticker, "price": None, "error": str(exc), "provider": "error"}

    # ------------------------------------------------------------------
    # Cache management helpers
    # ------------------------------------------------------------------

    def cache_stats(self) -> Dict:
        """Return cache storage statistics."""
        return self._cache.stats()

    def clear_cache(self, ticker: Optional[str] = None) -> int:
        """Clear cache for one ticker (or all if ticker is None)."""
        return self._cache.clear(ticker=ticker)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize and sort OHLCV DataFrame."""
    try:
        normalized = normalize_ohlcv(df)
    except Exception:
        normalized = df.copy()

    if normalized.empty:
        return normalized

    if not isinstance(normalized.index, pd.DatetimeIndex):
        try:
            normalized.index = pd.to_datetime(normalized.index, utc=True)
        except Exception:
            pass
    else:
        if normalized.index.tz is None:
            normalized.index = normalized.index.tz_localize("UTC")

    normalized.index.name = "timestamp_utc"
    return normalized.sort_index()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_router: Optional[DataRouter] = None


def get_router(
    allow_network: bool = True,
    cache_dir: str = "data/cache/router",
    ttl_hours: int = 24,
) -> DataRouter:
    """
    Return (or create) the module-level shared DataRouter.

    On the first call the router is instantiated with the given arguments.
    Subsequent calls return the same instance regardless of arguments.
    """
    global _router
    if _router is None:
        _router = DataRouter(
            allow_network=allow_network,
            cache_dir=cache_dir,
            ttl_hours=ttl_hours,
        )
    return _router
