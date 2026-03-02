"""
Cache Store
===========
Disk-based cache using Parquet files with TTL (time-to-live) support.
Prevents redundant downloads and speeds up repeated queries.

Copyright (c) 2026 M&C. All rights reserved.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger("atlas.data_layer")


class CacheStore:
    """
    Parquet-based cache with TTL and metadata tracking.

    Each cached item gets two files:
      - {key}.parquet  → the actual data
      - {key}.meta     → JSON metadata (timestamp, rows, etc.)
    """

    def __init__(self, cache_dir: str = "data/cache", ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_hours * 3600

        logger.debug("CacheStore ready | dir=%s ttl=%dh", self.cache_dir, ttl_hours)

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def _safe_key(self, key: str) -> str:
        """Sanitize key for use as filename."""
        return key.replace("/", "_").replace(":", "_").replace(" ", "_")

    def _data_path(self, key: str) -> Path:
        return self.cache_dir / f"{self._safe_key(key)}.parquet"

    def _meta_path(self, key: str) -> Path:
        return self.cache_dir / f"{self._safe_key(key)}.meta"

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """
        Retrieve cached DataFrame if it exists and is not expired.

        Args:
            key: Cache key (e.g. "yahoo_AAPL_2024-01-01_2024-12-31_1d")

        Returns:
            DataFrame if cache hit, None if miss or expired
        """
        data_path = self._data_path(key)
        meta_path = self._meta_path(key)

        if not data_path.exists():
            return None

        # Check TTL
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                cached_at = meta.get("cached_at", 0)
                if time.time() - cached_at > self.ttl_seconds:
                    logger.debug("Cache EXPIRED for %s", key)
                    self._remove(key)
                    return None
            except (json.JSONDecodeError, KeyError):
                pass  # Corrupted meta — treat as miss
        else:
            # No meta file — check file modification time as fallback
            file_age = time.time() - data_path.stat().st_mtime
            if file_age > self.ttl_seconds:
                self._remove(key)
                return None

        try:
            df = pd.read_parquet(data_path)
            logger.debug("Cache HIT: %s (%d rows)", key, len(df))
            return df
        except Exception as e:
            logger.warning("Cache read error for %s: %s", key, e)
            self._remove(key)
            return None

    def set(self, key: str, df: pd.DataFrame) -> None:
        """
        Store DataFrame in cache.

        Args:
            key: Cache key
            df:  DataFrame to cache
        """
        data_path = self._data_path(key)
        meta_path = self._meta_path(key)

        try:
            df.to_parquet(data_path, index=True)

            meta = {
                "cached_at": time.time(),
                "rows": len(df),
                "columns": list(df.columns),
                "date_range": {
                    "start": str(df.index.min()) if len(df) > 0 else None,
                    "end": str(df.index.max()) if len(df) > 0 else None,
                },
            }
            meta_path.write_text(json.dumps(meta, indent=2))

            logger.debug("Cache SET: %s (%d rows)", key, len(df))
        except Exception as e:
            logger.error("Cache write error for %s: %s", key, e)

    # ------------------------------------------------------------------
    # Management
    # ------------------------------------------------------------------

    def _remove(self, key: str) -> None:
        """Remove a single cached entry."""
        for path in [self._data_path(key), self._meta_path(key)]:
            if path.exists():
                path.unlink()

    def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cached entries.

        Args:
            pattern: If given, only delete keys containing this string.
                     e.g. pattern="AAPL" deletes all AAPL caches.

        Returns:
            Number of entries removed
        """
        removed = 0
        for f in self.cache_dir.glob("*.parquet"):
            key = f.stem
            if pattern is None or pattern in key:
                self._remove(key)
                removed += 1

        logger.info("Cache cleared: %d entries (pattern=%s)", removed, pattern)
        return removed

    def stats(self) -> Dict[str, Any]:
        """
        Return cache usage statistics.

        Returns:
            Dict with total_entries, total_size_mb, oldest, newest
        """
        parquet_files = list(self.cache_dir.glob("*.parquet"))

        if not parquet_files:
            return {
                "total_entries": 0,
                "total_size_mb": 0.0,
                "oldest": None,
                "newest": None,
            }

        total_size = sum(f.stat().st_size for f in parquet_files)
        mod_times = [f.stat().st_mtime for f in parquet_files]

        return {
            "total_entries": len(parquet_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest": time.ctime(min(mod_times)),
            "newest": time.ctime(max(mod_times)),
        }

    def list_keys(self) -> list:
        """Return all cached keys."""
        return [f.stem for f in self.cache_dir.glob("*.parquet")]
