"""
Top-Level DataRouter
====================
Single entry point for market data requests.

The modern API returns normalized OHLCV DataFrames for single tickers and a
``dict[ticker, DataFrame]`` for multi-ticker requests. A small compatibility
wrapper keeps older tests/tools that used ``"AAPL" in router.get("AAPL")`` and
``router.get("AAPL")["AAPL"]`` working without breaking DataFrame behavior.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Dict, Iterable, Optional

import pandas as pd

from atlas.data_layer.normalize import normalize_ohlcv
from atlas.providers.cache_provider import CacheProvider
from atlas.providers.yfinance_provider import NetworkUnavailableError, YFinanceProvider

logger = logging.getLogger("atlas.data_router")


class RoutedFrame(pd.DataFrame):
    """DataFrame with legacy mapping-style ticker access."""

    _metadata = ["_atlas_ticker", "_atlas_present"]

    @property
    def _constructor(self):
        return RoutedFrame

    def __init__(self, *args, ticker: Optional[str] = None, present: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self._atlas_ticker = ticker
        self._atlas_present = present

    def __contains__(self, key: object) -> bool:
        if (
            self._atlas_present
            and isinstance(key, str)
            and self._atlas_ticker
            and key.upper() == self._atlas_ticker.upper()
        ):
            return True
        return super().__contains__(key)

    def __getitem__(self, key):
        if (
            self._atlas_present
            and isinstance(key, str)
            and self._atlas_ticker
            and key.upper() == self._atlas_ticker.upper()
        ):
            return self
        return super().__getitem__(key)


def _default_end() -> str:
    return date.today().isoformat()


def _default_start(years: int = 1) -> str:
    return (date.today() - timedelta(days=365 * years)).isoformat()


class DataRouter:
    """Unified data access layer for Atlas."""

    def __init__(
        self,
        allow_network: bool = True,
        cache_dir: str = "data/cache/router",
        ttl_hours: int = 24,
    ) -> None:
        self.allow_network = allow_network
        self._yf = YFinanceProvider(allow_network=allow_network)
        self._cache = CacheProvider(cache_dir=cache_dir, ttl_hours=ttl_hours)

    def get(
        self,
        ticker: str | Iterable[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
    ) -> pd.DataFrame | Dict[str, pd.DataFrame]:
        """Fetch one ticker as a DataFrame, or many tickers as a dict."""
        if not isinstance(ticker, str):
            return self.get_many(ticker, start=start, end=end, interval=interval)

        start = start or _default_start()
        end = end or _default_end()

        cached = self._cache.get(ticker, start, end, interval, allow_stale=False)
        if cached is not None:
            logger.debug("DataRouter: fresh cache hit for %s", ticker)
            return _routed(_normalize(cached), ticker)

        if self.allow_network:
            try:
                df = self._yf.get_historical(ticker, start=start, end=end, interval=interval)
                if df is not None and not df.empty:
                    self._cache.set(ticker, start, end, interval, df)
                    logger.info("DataRouter: fetched %s from yfinance (%d rows)", ticker, len(df))
                    return _routed(_normalize(df), ticker)
                logger.warning("DataRouter: yfinance returned empty frame for %s", ticker)
            except NetworkUnavailableError:
                pass
            except Exception as exc:
                logger.warning("DataRouter: yfinance failed for %s: %s", ticker, exc)

        stale = self._cache.get(ticker, start, end, interval, allow_stale=True)
        if stale is not None:
            logger.info("DataRouter: using stale cache for %s", ticker)
            return _routed(_normalize(stale), ticker)

        logger.warning(
            "DataRouter: no data for %s (%s -> %s). Network available: %s.",
            ticker,
            start,
            end,
            self.allow_network,
        )
        return RoutedFrame(ticker=ticker, present=False)

    def get_many(
        self,
        tickers: Iterable[str],
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """Fetch multiple tickers, omitting misses."""
        start = start or _default_start()
        end = end or _default_end()

        results: Dict[str, pd.DataFrame] = {}
        for ticker in tickers:
            try:
                df = self.get(ticker, start=start, end=end, interval=interval)
                if isinstance(df, pd.DataFrame) and not df.empty:
                    results[ticker] = df
            except Exception as exc:
                logger.error("DataRouter.get_many: skipping %s: %s", ticker, exc)
        return results

    def get_quote(self, ticker: str) -> Dict:
        """Get latest delayed quote, returning a structured fallback on failure."""
        if not self.allow_network:
            logger.debug("DataRouter.get_quote: offline; no quote for %s", ticker)
            return {"symbol": ticker, "price": None, "error": "offline", "provider": "cache"}
        try:
            return self._yf.get_quote(ticker)
        except Exception as exc:
            logger.warning("DataRouter.get_quote: failed for %s: %s", ticker, exc)
            return {"symbol": ticker, "price": None, "error": str(exc), "provider": "error"}

    @staticmethod
    def _cache_key(provider: str, ticker: str, start: str, end: str, interval: str = "1d") -> str:
        """Legacy cache key helper. Provider is accepted for compatibility."""
        return CacheProvider.make_key(ticker, start, end, interval)

    def is_cached(self, ticker: str, start: str, end: str, interval: str = "1d") -> bool:
        """Return True when a cache entry exists, fresh or stale."""
        return self._cache.has(ticker, start, end, interval, allow_stale=True)

    def cache_stats(self) -> Dict:
        """Return cache storage statistics."""
        return self._cache.stats()

    def clear_cache(self, ticker: Optional[str] = None) -> int:
        """Clear cache for one ticker, or all entries."""
        return self._cache.clear(ticker=ticker)


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
    elif normalized.index.tz is None:
        normalized.index = normalized.index.tz_localize("UTC")

    normalized.index.name = "timestamp_utc"
    return normalized.sort_index()


def _routed(df: pd.DataFrame, ticker: str) -> RoutedFrame:
    return RoutedFrame(df, ticker=ticker, present=not df.empty)


_router: Optional[DataRouter] = None


def get_router(
    allow_network: bool = True,
    cache_dir: str = "data/cache/router",
    ttl_hours: int = 24,
) -> DataRouter:
    """Return or create the module-level shared DataRouter."""
    global _router
    if _router is None:
        _router = DataRouter(
            allow_network=allow_network,
            cache_dir=cache_dir,
            ttl_hours=ttl_hours,
        )
    return _router
