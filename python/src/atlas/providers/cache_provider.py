"""
Cache Provider
==============
Read/write provider backed by the disk Parquet cache.

Used by DataRouter as the offline fallback — fully functional
without any network access.

Copyright (c) 2026 M&C. All rights reserved.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import pandas as pd

from atlas.data_layer.cache_store import CacheStore

logger = logging.getLogger("atlas.providers.cache")


class CacheProvider:
    """
    Parquet-based cache provider for offline / fallback reads.

    Wraps CacheStore with a provider-style interface so it can be
    used interchangeably with live providers in the DataRouter.

    Cache key format:  "router_{ticker}_{start}_{end}_{interval}"

    Args:
        cache_dir:  Directory for .parquet + .meta files
        ttl_hours:  TTL for fresh-cache checks (24h default)
    """

    def __init__(
        self,
        cache_dir: str = "data/cache",
        ttl_hours: int = 24,
    ) -> None:
        self._store = CacheStore(cache_dir=cache_dir, ttl_hours=ttl_hours)

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    @staticmethod
    def make_key(ticker: str, start: str, end: str, interval: str) -> str:
        """Build a deterministic cache key."""
        safe = ticker.replace("/", "_").replace("^", "idx_").replace("=", "_eq_")
        return f"router_{safe}_{start}_{end}_{interval}"

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(
        self,
        ticker: str,
        start: str,
        end: str,
        interval: str = "1d",
        allow_stale: bool = True,
    ) -> Optional[pd.DataFrame]:
        """
        Retrieve data from cache.

        Args:
            ticker:      Ticker symbol
            start:       Start date
            end:         End date
            interval:    Candle interval
            allow_stale: If True, return expired entries (offline fallback).
                         If False, return None for expired entries.

        Returns:
            DataFrame on hit, None on miss.
        """
        key = self.make_key(ticker, start, end, interval)
        df = self._store.get(key, allow_stale=allow_stale)
        if df is not None:
            logger.debug("CacheProvider HIT: %s (stale_ok=%s)", key, allow_stale)
        else:
            logger.debug("CacheProvider MISS: %s", key)
        return df

    def get_with_metadata(
        self,
        ticker: str,
        start: str,
        end: str,
        interval: str = "1d",
        allow_stale: bool = True,
    ) -> Optional[tuple[pd.DataFrame, Dict[str, Any]]]:
        """
        Return (DataFrame, metadata) tuple, or None on miss.
        """
        key = self.make_key(ticker, start, end, interval)
        result = self._store.get(key, allow_stale=allow_stale, with_metadata=True)
        return result  # None | (df, meta)

    def has(
        self,
        ticker: str,
        start: str,
        end: str,
        interval: str = "1d",
        allow_stale: bool = True,
    ) -> bool:
        """Return True if cache has data for this request."""
        return self.get(ticker, start, end, interval, allow_stale=allow_stale) is not None

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def set(
        self,
        ticker: str,
        start: str,
        end: str,
        interval: str,
        df: pd.DataFrame,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Write DataFrame into cache with metadata.

        Args:
            ticker:     Ticker symbol
            start:      Start date
            end:        End date
            interval:   Candle interval
            df:         DataFrame to cache
            extra_meta: Optional dict merged into cache metadata
        """
        if df is None or df.empty:
            logger.debug("CacheProvider: skipping empty frame for %s", ticker)
            return

        key = self.make_key(ticker, start, end, interval)

        meta: Dict[str, Any] = {
            "ticker": ticker,
            "start":  start,
            "end":    end,
            "interval": interval,
            "provider": "yfinance",
            "network_used": True,
            "cached_at": time.time(),
        }
        if extra_meta:
            meta.update(extra_meta)

        self._store.set(key, df, metadata=meta)
        logger.debug("CacheProvider SET: %s (%d rows)", key, len(df))

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def clear(self, ticker: Optional[str] = None) -> int:
        """
        Clear cache entries.

        Args:
            ticker: If given, only clear entries matching this ticker.
                    If None, clear everything.

        Returns:
            Number of entries removed.
        """
        pattern = ticker.replace("/", "_").replace("^", "idx_") if ticker else None
        return self._store.clear(pattern=pattern)

    def stats(self) -> Dict[str, Any]:
        """Return cache storage statistics."""
        return self._store.stats()
