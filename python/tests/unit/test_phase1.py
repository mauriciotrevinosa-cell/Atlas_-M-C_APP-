"""
Phase 1 Data Architecture — Unit Tests
=======================================
Tests for DataRouter, CacheProvider, YFinanceProvider, and AssetRegistry.

Run with:
    pytest python/tests/unit/test_phase1.py -v

Copyright (c) 2026 M&C. All rights reserved.
"""
from __future__ import annotations

import time
import types
from typing import Optional
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv(n: int = 30) -> pd.DataFrame:
    """Build a minimal OHLCV DataFrame for mocking."""
    idx = pd.date_range("2024-01-02", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(
        {
            "open":   [100.0 + i for i in range(n)],
            "high":   [101.0 + i for i in range(n)],
            "low":    [ 99.0 + i for i in range(n)],
            "close":  [100.5 + i for i in range(n)],
            "volume": [1_000_000.0] * n,
        },
        index=idx,
    )


# ===========================================================================
# TEST 1 — Local / offline mode: DataRouter must use cache only
# ===========================================================================

class TestLocalOffline:
    """DataRouter(allow_network=False) must never call yfinance."""

    def test_local_offline(self, tmp_path):
        """Offline router returns cached DataFrame without hitting the network."""
        from atlas.providers.cache_provider import CacheProvider

        cache_dir = str(tmp_path / "cache")
        cache = CacheProvider(cache_dir=cache_dir)

        df_original = _make_ohlcv(20)
        cache.set("AAPL", "2024-01-02", "2024-02-09", "1d", df_original)

        # Now build an offline DataRouter pointing at the same cache
        from atlas.data_router import DataRouter
        router = DataRouter(allow_network=False, cache_dir=cache_dir)

        # Patch YFinanceProvider._guard to detect any accidental network call
        with patch(
            "atlas.providers.yfinance_provider.YFinanceProvider.get_historical",
            side_effect=AssertionError("Network must NOT be called in offline mode"),
        ):
            result = router.get("AAPL", "2024-01-02", "2024-02-09", interval="1d")

        assert result is not None
        assert not result.empty
        assert "close" in result.columns


# ===========================================================================
# TEST 2 — yfinance fetch: DataRouter pulls live data and writes cache
# ===========================================================================

class TestYFinanceFetch:
    """DataRouter(allow_network=True) fetches from yfinance and caches."""

    def test_yfinance_fetch(self, tmp_path):
        """Online router calls yfinance and stores the result in cache."""
        from atlas.data_router import DataRouter

        cache_dir = str(tmp_path / "cache")
        mock_df = _make_ohlcv(10)

        with patch(
            "atlas.providers.yfinance_provider.YFinanceProvider.get_historical",
            return_value=mock_df,
        ) as mock_get:
            router = DataRouter(allow_network=True, cache_dir=cache_dir)
            result = router.get("TSLA", "2024-01-02", "2024-01-16", interval="1d")

        mock_get.assert_called_once()
        assert result is not None
        assert len(result) > 0

        # Verify cache was written
        from atlas.providers.cache_provider import CacheProvider
        cache = CacheProvider(cache_dir=cache_dir)
        cached = cache.get("TSLA", "2024-01-02", "2024-01-16", "1d", allow_stale=True)
        assert cached is not None, "DataRouter must write to cache after a successful fetch"


# ===========================================================================
# TEST 3 — Fallback: yfinance failure → stale cache used
# ===========================================================================

class TestFallback:
    """When yfinance fails, DataRouter must fall back to stale cache."""

    def test_fallback_to_stale_cache(self, tmp_path):
        """Network failure triggers stale cache fallback transparently."""
        from atlas.providers.cache_provider import CacheProvider
        from atlas.data_router import DataRouter

        cache_dir = str(tmp_path / "cache")

        # Pre-populate stale cache
        cache = CacheProvider(cache_dir=cache_dir, ttl_hours=0)  # TTL=0 → always stale
        df_stale = _make_ohlcv(15)
        cache.set("SPY", "2024-01-02", "2024-01-26", "1d", df_stale)

        # Router that tries network but yfinance will fail
        with patch(
            "atlas.providers.yfinance_provider.YFinanceProvider.get_historical",
            side_effect=RuntimeError("yfinance down"),
        ):
            router = DataRouter(allow_network=True, cache_dir=cache_dir, ttl_hours=0)
            result = router.get("SPY", "2024-01-02", "2024-01-26", interval="1d")

        assert result is not None
        assert not result.empty, "Stale cache fallback must return data"


# ===========================================================================
# TEST 4 — Multi-asset correlation: fetch multiple asset classes + correlate
# ===========================================================================

class TestMultiAssetCorrelation:
    """get_many returns DataFrames for multiple asset classes; they correlate."""

    def test_multi_asset_correlation(self, tmp_path):
        """Equity + ETF + crypto fetches produce a non-trivial correlation matrix."""
        from atlas.data_router import DataRouter

        tickers = ["AAPL", "SPY", "BTC-USD"]
        cache_dir = str(tmp_path / "cache")

        def _side_effect(ticker, start, end, interval="1d"):
            return _make_ohlcv(30)

        with patch(
            "atlas.providers.yfinance_provider.YFinanceProvider.get_historical",
            side_effect=_side_effect,
        ):
            router = DataRouter(allow_network=True, cache_dir=cache_dir)
            frames = router.get_many(tickers, start="2024-01-02", end="2024-02-16")

        assert set(frames.keys()) == set(tickers), "All tickers must be returned"

        # Compute pairwise correlation on close prices
        close_panel = pd.DataFrame({t: f["close"] for t, f in frames.items()})
        corr = close_panel.corr()

        assert corr.shape == (3, 3), "Correlation matrix must be 3×3"
        assert (corr.values >= -1).all() and (corr.values <= 1).all()


# ===========================================================================
# TEST 5 — Cache write → read round-trip
# ===========================================================================

class TestCacheWriteRead:
    """CacheProvider round-trip: write then read back the same DataFrame."""

    def test_cache_write_read(self, tmp_path):
        """Written DataFrame must survive a cache round-trip intact."""
        from atlas.providers.cache_provider import CacheProvider

        cache_dir = str(tmp_path / "cache")
        cache = CacheProvider(cache_dir=cache_dir, ttl_hours=24)

        df_in = _make_ohlcv(25)
        cache.set("GLD", "2024-01-02", "2024-02-07", "1d", df_in)

        df_out = cache.get("GLD", "2024-01-02", "2024-02-07", "1d", allow_stale=False)

        assert df_out is not None, "Cache must return DataFrame on fresh hit"
        assert len(df_out) == len(df_in), "Row count must match after round-trip"
        assert list(df_out.columns) == list(df_in.columns), "Columns must match"
        pd.testing.assert_series_equal(
            df_out["close"].reset_index(drop=True),
            df_in["close"].reset_index(drop=True),
            check_names=False,
        )

    def test_cache_miss_returns_none(self, tmp_path):
        """Cache must return None for a key that was never written."""
        from atlas.providers.cache_provider import CacheProvider

        cache = CacheProvider(cache_dir=str(tmp_path / "cache"))
        result = cache.get("NVDA", "2024-01-01", "2024-12-31", "1d", allow_stale=True)
        assert result is None

    def test_cache_stale_respects_flag(self, tmp_path):
        """allow_stale=False must return None for an expired entry."""
        from atlas.providers.cache_provider import CacheProvider

        cache = CacheProvider(cache_dir=str(tmp_path / "cache"), ttl_hours=0)
        df_in = _make_ohlcv(5)
        cache.set("MSFT", "2024-01-02", "2024-01-09", "1d", df_in)

        # TTL=0 means it's immediately expired
        result_strict = cache.get("MSFT", "2024-01-02", "2024-01-09", "1d", allow_stale=False)
        assert result_strict is None, "Expired entry must not be returned when allow_stale=False"

        result_stale = cache.get("MSFT", "2024-01-02", "2024-01-09", "1d", allow_stale=True)
        assert result_stale is not None, "Expired entry must be returned when allow_stale=True"
