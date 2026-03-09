"""
Cache Store
===========
Disk-based cache using Parquet files with TTL (time-to-live) support.
Prevents redundant downloads and speeds up repeated queries.

Copyright (c) 2026 M&C. All rights reserved.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger("atlas.data_layer")


class CacheStore:
    """
    Parquet-based cache with TTL and metadata tracking.

    Each cached item gets two files:
      - {key}.parquet  -> the actual data
      - {key}.meta     -> JSON metadata (timestamp, rows, etc.)
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

    def _read_meta(self, key: str) -> Dict[str, Any]:
        """Read sidecar metadata safely."""
        meta_path = self._meta_path(key)
        if not meta_path.exists():
            return {}
        try:
            parsed = json.loads(meta_path.read_text())
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, OSError):
            pass
        return {}

    def get(
        self,
        key: str,
        allow_stale: bool = False,
        with_metadata: bool = False,
    ) -> Optional[pd.DataFrame | Tuple[pd.DataFrame, Dict[str, Any]]]:
        """
        Retrieve cached DataFrame if it exists and is not expired.

        Args:
            key: Cache key (e.g. "yahoo_AAPL_2024-01-01_2024-12-31_1d")
            allow_stale: If True, return expired entries instead of deleting them
            with_metadata: If True, return tuple (df, metadata)

        Returns:
            DataFrame (or tuple) on hit, None on miss
        """
        data_path = self._data_path(key)

        if not data_path.exists():
            return None

        # TTL check
        stale = False
        meta = self._read_meta(key)

        if meta:
            cached_at = float(meta.get("cached_at", 0) or 0)
            if cached_at > 0 and (time.time() - cached_at > self.ttl_seconds):
                if not allow_stale:
                    logger.debug("Cache EXPIRED for %s", key)
                    self._remove(key)
                    return None
                stale = True
        else:
            # No metadata file, fallback to file mtime
            file_age = time.time() - data_path.stat().st_mtime
            if file_age > self.ttl_seconds:
                if not allow_stale:
                    self._remove(key)
                    return None
                stale = True

        try:
            df = pd.read_parquet(data_path)
            logger.debug("Cache HIT: %s (%d rows%s)", key, len(df), ", stale" if stale else "")
            if with_metadata:
                meta_out = dict(meta)
                meta_out["stale"] = stale
                return df, meta_out
            return df
        except Exception as e:
            logger.warning("Cache read error for %s: %s", key, e)
            self._remove(key)
            return None

    def get_with_meta(
        self,
        key: str,
        allow_stale: bool = False,
    ) -> Optional[Tuple[pd.DataFrame, Dict[str, Any]]]:
        """Return (DataFrame, metadata) if available."""
        cached = self.get(key, allow_stale=allow_stale, with_metadata=True)
        if cached is None:
            return None
        return cached

    def set(self, key: str, df: pd.DataFrame, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Store DataFrame in cache.

        Args:
            key: Cache key
            df: DataFrame to cache
            metadata: Optional extra metadata for this cache entry
        """
        data_path = self._data_path(key)
        meta_path = self._meta_path(key)

        try:
            df.to_parquet(data_path, index=True)

            meta: Dict[str, Any] = {
                "cached_at": time.time(),
                "rows": len(df),
                "columns": list(df.columns),
                "date_range": {
                    "start": str(df.index.min()) if len(df) > 0 else None,
                    "end": str(df.index.max()) if len(df) > 0 else None,
                },
            }
            if metadata:
                meta["custom"] = metadata

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

    def list_keys(self) -> list[str]:
        """Return all cached keys."""
        return [f.stem for f in self.cache_dir.glob("*.parquet")]
