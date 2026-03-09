"""
Data Router Tests
=================
Tests for DataRouter, providers, cache, and multi-asset analytics.

Required tests:
  - test_local_offline           : Router works offline (cache-only)
  - test_yfinance_fetch          : Network fetch + cache write (mocked)
  - test_fallback                : Falls back to cache when network fails
  - test_multi_asset_correlation : Cross-asset correlation pipeline
  - test_cache_write_read        : CacheStore write/read cycle

Run with: pytest python/tests/unit/test_data_router.py -v

Copyright (c) 2026 M&C. All rights reserved.
"""

import time
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

def make_ohlcv(
    ticker: str = "AAPL",
    n: int = 30,
    start: str = "2024-01-02",
) -> pd.DataFrame:
    """Create a realistic OHLCV DataFrame for testing."""
    idx = pd.bdate_range(start=start, periods=n)  # business days only
    rng = np.random.default_rng(abs(hash(ticker)) % (2 ** 32))
    close = 100.0 * np.cumprod(1 + rng.normal(0.0005, 0.015, n))
    df = pd.DataFrame({
        "open":   close * rng.uniform(0.99, 1.01, n),
        "high":   close * rng.uniform(1.00, 1.02, n),
        "low":    close * rng.uniform(0.98, 1.00, n),
        "close":  close,
        "volume": rng.integers(1_000_000, 10_000_000, n),
    }, index=idx)
    df.index.name = "date"
    return df


@pytest.fixture
def tmp_cache_dir(tmp_path: Path) -> str:
    """Isolated cache directory per test."""
    d = tmp_path / "cache"
    d.mkdir()
    return str(d)


# ---------------------------------------------------------------------------
# Test 1: test_cache_write_read
# ---------------------------------------------------------------------------

class TestCacheWriteRead:
    """CacheStore write/read cycle."""

    def test_cache_write_read(self, tmp_cache_dir: str):
        """Write a DataFrame and read it back — must be identical."""
        from atlas.data_layer.cache_store import CacheStore

        store = CacheStore(cache_dir=tmp_cache_dir, ttl_hours=24)
        df_original = make_ohlcv("AAPL", n=20)

        key = "test_AAPL_2024-01-02_2024-02-09_1d"
        store.set(key, df_original)

        df_loaded = store.get(key)

        assert df_loaded is not None, "Cache should return data for valid key"
        assert len(df_loaded) == len(df_original)
        assert list(df_loaded.columns) == list(df_original.columns)
        pd.testing.assert_frame_equal(df_original, df_loaded, check_freq=False)

    def test_cache_miss_returns_none(self, tmp_cache_dir: str):
        """Non-existent key returns None."""
        from atlas.data_layer.cache_store import CacheStore

        store = CacheStore(cache_dir=tmp_cache_dir, ttl_hours=24)
        assert store.get("nonexistent_key_xyz") is None

    def test_cache_ttl_expiry(self, tmp_cache_dir: str):
        """Expired entries return None."""
        from atlas.data_layer.cache_store import CacheStore

        # TTL of 0 hours → expires immediately
        store = CacheStore(cache_dir=tmp_cache_dir, ttl_hours=0)
        df = make_ohlcv("MSFT", n=10)
        key = "test_ttl_key"
        store.set(key, df)

        # Overwrite meta with old timestamp
        import json
        meta_path = Path(tmp_cache_dir) / f"{key}.meta"
        old_meta = json.loads(meta_path.read_text())
        old_meta["cached_at"] = time.time() - 3601  # 1 hour ago
        meta_path.write_text(json.dumps(old_meta))

        result = store.get(key)
        assert result is None, "Expired cache entry should return None"

    def test_cache_metadata_fields(self, tmp_cache_dir: str):
        """Cache metadata JSON contains expected fields."""
        import json
        from atlas.data_layer.cache_store import CacheStore

        store = CacheStore(cache_dir=tmp_cache_dir, ttl_hours=24)
        df = make_ohlcv("GLD", n=15)
        key = "test_meta_key"
        store.set(key, df)

        meta_file = Path(tmp_cache_dir) / f"{key}.meta"
        assert meta_file.exists()
        meta = json.loads(meta_file.read_text())
        assert "cached_at" in meta
        assert "rows" in meta
        assert meta["rows"] == 15


# ---------------------------------------------------------------------------
# Test 2: test_yfinance_fetch  (mocked — no real network required)
# ---------------------------------------------------------------------------

class TestYFinanceFetch:
    """YFinanceProvider fetch + DataRouter caching (network mocked)."""

    def _make_mock_yf_ticker(self, df: pd.DataFrame):
        """Create a mock yfinance Ticker that returns df on .history()."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = df
        return mock_ticker

    def test_yfinance_fetch_returns_normalized_df(self, tmp_cache_dir: str):
        """YFinanceProvider.fetch returns normalized OHLCV DataFrame."""
        from atlas.providers.yfinance_provider import YFinanceProvider

        raw = make_ohlcv("AAPL", n=20)
        # Simulate yfinance column casing (Title Case)
        raw_yf = raw.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })

        with patch("yfinance.Ticker") as mock_class:
            mock_class.return_value = self._make_mock_yf_ticker(raw_yf)
            provider = YFinanceProvider()
            result = provider.fetch("AAPL", "2024-01-02", "2024-02-09")

        assert not result.empty
        assert "close" in result.columns
        assert "open" in result.columns
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_data_router_network_writes_cache(self, tmp_cache_dir: str):
        """DataRouter saves to cache after successful network fetch."""
        from atlas.data_router import DataRouter

        sample = make_ohlcv("SPY", n=20)
        sample_yf = sample.rename(columns={
            "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })

        with patch("yfinance.Ticker") as mock_class:
            mock_class.return_value.history.return_value = sample_yf
            # Also mock download for batch path
            with patch("yfinance.download", return_value=pd.DataFrame()):
                router = DataRouter(allow_network=True, cache_dir=tmp_cache_dir)
                result = router.get("SPY", "2024-01-02", "2024-02-09")

        assert "SPY" in result
        assert len(result["SPY"]) > 0
        # Verify it was cached
        assert router.is_cached("SPY", "2024-01-02", "2024-02-09")


# ---------------------------------------------------------------------------
# Test 3: test_local_offline
# ---------------------------------------------------------------------------

class TestLocalOffline:
    """DataRouter works without network (allow_network=False)."""

    def test_local_offline_reads_cache(self, tmp_cache_dir: str):
        """Offline router reads from cache correctly."""
        from atlas.data_router import DataRouter
        from atlas.providers.cache_provider import CacheProvider

        # Pre-seed cache
        sample = make_ohlcv("AAPL", n=25)
        cache = CacheProvider(cache_dir=tmp_cache_dir)
        key = DataRouter._cache_key("yfinance", "AAPL", "2024-01-02", "2024-02-09", "1d")
        cache.store(key, sample)

        # Router in offline mode
        router = DataRouter(allow_network=False, cache_dir=tmp_cache_dir)
        result = router.get("AAPL", "2024-01-02", "2024-02-09")

        assert "AAPL" in result
        assert len(result["AAPL"]) == 25

    def test_local_offline_missing_ticker_returns_empty(self, tmp_cache_dir: str):
        """Offline router returns empty dict for uncached ticker."""
        from atlas.data_router import DataRouter

        router = DataRouter(allow_network=False, cache_dir=tmp_cache_dir)
        result = router.get("NONCACHED_TICKER", "2024-01-02", "2024-02-09")

        assert "NONCACHED_TICKER" not in result

    def test_local_offline_multi_asset(self, tmp_cache_dir: str):
        """Offline router returns all cached tickers in a multi-asset request."""
        from atlas.data_router import DataRouter
        from atlas.providers.cache_provider import CacheProvider

        tickers = ["AAPL", "SPY", "GLD"]
        cache = CacheProvider(cache_dir=tmp_cache_dir)

        for t in tickers:
            df = make_ohlcv(t, n=20)
            key = DataRouter._cache_key("yfinance", t, "2024-01-02", "2024-02-09", "1d")
            cache.store(key, df)

        router = DataRouter(allow_network=False, cache_dir=tmp_cache_dir)
        result = router.get(tickers, "2024-01-02", "2024-02-09")

        assert set(result.keys()) == set(tickers)
        for t in tickers:
            assert len(result[t]) == 20


# ---------------------------------------------------------------------------
# Test 4: test_fallback
# ---------------------------------------------------------------------------

class TestFallback:
    """DataRouter falls back to cache when network provider fails."""

    def test_fallback_on_network_error(self, tmp_cache_dir: str):
        """When yfinance raises, router uses cached data."""
        from atlas.data_router import DataRouter
        from atlas.providers.cache_provider import CacheProvider

        # Pre-seed cache
        sample = make_ohlcv("MSFT", n=20)
        cache = CacheProvider(cache_dir=tmp_cache_dir)
        key = DataRouter._cache_key("yfinance", "MSFT", "2024-01-02", "2024-02-09", "1d")
        cache.store(key, sample)

        # Mock yfinance to always fail
        with patch("yfinance.Ticker") as mock_class:
            mock_class.return_value.history.side_effect = RuntimeError("network error")
            with patch("yfinance.download", side_effect=RuntimeError("batch error")):
                router = DataRouter(allow_network=True, cache_dir=tmp_cache_dir)
                result = router.get("MSFT", "2024-01-02", "2024-02-09")

        assert "MSFT" in result, "Should fallback to cached data on network failure"
        assert len(result["MSFT"]) == 20

    def test_fallback_no_cache_returns_empty(self, tmp_cache_dir: str):
        """No cache + network failure → ticker absent from results."""
        from atlas.data_router import DataRouter

        with patch("yfinance.Ticker") as mock_class:
            mock_class.return_value.history.side_effect = RuntimeError("offline")
            with patch("yfinance.download", side_effect=RuntimeError("offline")):
                router = DataRouter(allow_network=True, cache_dir=tmp_cache_dir)
                result = router.get("NONCACHED", "2024-01-02", "2024-02-09")

        assert "NONCACHED" not in result

    def test_fallback_rate_limit(self, tmp_cache_dir: str):
        """Rate-limit errors trigger fallback to cache."""
        from atlas.data_router import DataRouter
        from atlas.providers.cache_provider import CacheProvider

        sample = make_ohlcv("NVDA", n=15)
        cache = CacheProvider(cache_dir=tmp_cache_dir)
        key = DataRouter._cache_key("yfinance", "NVDA", "2024-01-02", "2024-02-09", "1d")
        cache.store(key, sample)

        with patch("yfinance.Ticker") as mock_class:
            mock_class.return_value.history.side_effect = Exception("Too Many Requests 429")
            with patch("yfinance.download", side_effect=Exception("rate limit")):
                router = DataRouter(allow_network=True, cache_dir=tmp_cache_dir)
                result = router.get("NVDA", "2024-01-02", "2024-02-09")

        assert "NVDA" in result
        assert len(result["NVDA"]) == 15


# ---------------------------------------------------------------------------
# Test 5: test_multi_asset_correlation
# ---------------------------------------------------------------------------

class TestMultiAssetCorrelation:
    """End-to-end multi-asset correlation pipeline."""

    def test_returns_matrix_shape(self):
        """returns_matrix produces correct shape from multi-asset dfs."""
        from atlas.analytics.returns import returns_matrix

        tickers = ["AAPL", "SPY", "GLD", "TLT"]
        dfs = {t: make_ohlcv(t, n=60) for t in tickers}
        mat = returns_matrix(dfs, method="log")

        assert not mat.empty
        assert set(mat.columns) == set(tickers)
        assert len(mat) <= 60  # dropna removes first row per asset

    def test_static_correlation_symmetry(self):
        """Correlation matrix is symmetric with 1.0 on diagonal."""
        from atlas.analytics.returns import returns_matrix
        from atlas.analytics.correlation import static_correlation

        tickers = ["AAPL", "SPY", "GLD"]
        dfs = {t: make_ohlcv(t, n=80) for t in tickers}
        ret_mat = returns_matrix(dfs)
        corr = static_correlation(ret_mat)

        assert corr.shape == (3, 3)
        # Diagonal must be 1.0
        for t in tickers:
            assert abs(corr.loc[t, t] - 1.0) < 1e-10
        # Must be symmetric
        for a in tickers:
            for b in tickers:
                assert abs(corr.loc[a, b] - corr.loc[b, a]) < 1e-10

    def test_correlation_values_in_range(self):
        """All correlation values are in [-1, 1]."""
        from atlas.analytics.returns import returns_matrix
        from atlas.analytics.correlation import static_correlation

        tickers = ["AAPL", "MSFT", "SPY", "GLD", "TLT", "BTC-USD"]
        dfs = {t: make_ohlcv(t, n=100) for t in tickers}
        ret_mat = returns_matrix(dfs)
        corr = static_correlation(ret_mat)

        vals = corr.values.flatten()
        vals = vals[~np.isnan(vals)]
        assert np.all(vals >= -1.0 - 1e-10)
        assert np.all(vals <= 1.0 + 1e-10)

    def test_rolling_correlation_shape(self):
        """Rolling correlation produces correct time-series shape."""
        from atlas.analytics.returns import returns_matrix
        from atlas.analytics.correlation import rolling_correlation

        dfs = {
            "AAPL": make_ohlcv("AAPL", n=120),
            "SPY":  make_ohlcv("SPY",  n=120),
        }
        ret_mat = returns_matrix(dfs)
        rolling = rolling_correlation(ret_mat, window=30)

        assert "AAPL_vs_SPY" in rolling.columns
        # Should have values for most of the period
        assert rolling.dropna().shape[0] > 0

    def test_heatmap_data_structure(self):
        """heatmap_data returns list of dicts with expected keys."""
        from atlas.analytics.returns import returns_matrix
        from atlas.analytics.correlation import static_correlation, heatmap_data

        tickers = ["SPY", "GLD"]
        dfs = {t: make_ohlcv(t, n=50) for t in tickers}
        corr = static_correlation(returns_matrix(dfs))
        hm = heatmap_data(corr)

        assert isinstance(hm, list)
        assert len(hm) == 4  # 2x2 matrix → 4 cells
        for record in hm:
            assert "row" in record
            assert "col" in record
            assert "value" in record
            assert -1.0 <= record["value"] <= 1.0

    def test_cross_asset_from_router(self, tmp_cache_dir: str):
        """Full pipeline: DataRouter → returns_matrix → static_correlation."""
        from atlas.data_router import DataRouter
        from atlas.providers.cache_provider import CacheProvider
        from atlas.analytics.returns import returns_matrix
        from atlas.analytics.correlation import static_correlation

        # Pre-seed cache (offline test)
        tickers = ["AAPL", "SPY", "GLD", "TLT"]
        cache = CacheProvider(cache_dir=tmp_cache_dir)
        for t in tickers:
            df = make_ohlcv(t, n=90)
            key = DataRouter._cache_key("yfinance", t, "2024-01-02", "2024-04-30", "1d")
            cache.store(key, df)

        router = DataRouter(allow_network=False, cache_dir=tmp_cache_dir)
        dfs = router.get(tickers, "2024-01-02", "2024-04-30")

        assert len(dfs) == 4

        ret_mat = returns_matrix(dfs)
        corr = static_correlation(ret_mat)

        assert corr.shape == (4, 4)
        for t in tickers:
            assert abs(corr.loc[t, t] - 1.0) < 1e-10


# ---------------------------------------------------------------------------
# Asset Registry Tests
# ---------------------------------------------------------------------------

class TestAssetRegistry:
    """Asset Registry classification and validation."""

    def test_known_tickers_validate(self):
        from atlas.shared.asset_registry import REGISTRY, AssetClass

        assert REGISTRY.validate("AAPL")
        assert REGISTRY.validate("SPY")
        assert REGISTRY.validate("GLD")
        assert REGISTRY.validate("^GSPC")
        assert REGISTRY.validate("AGG")
        assert REGISTRY.validate("BTC-USD")

    def test_unknown_ticker_returns_unknown(self):
        from atlas.shared.asset_registry import REGISTRY, AssetClass

        ac = REGISTRY.classify("FAKEXYZ")
        assert ac == AssetClass.UNKNOWN

    def test_asset_classes_correct(self):
        from atlas.shared.asset_registry import REGISTRY, AssetClass

        assert REGISTRY.classify("AAPL")  == AssetClass.EQUITY
        assert REGISTRY.classify("SPY")   == AssetClass.ETF
        assert REGISTRY.classify("AGG")   == AssetClass.BOND
        assert REGISTRY.classify("GLD")   == AssetClass.COMMODITY
        assert REGISTRY.classify("^GSPC") == AssetClass.INDEX
        assert REGISTRY.classify("BTC-USD") == AssetClass.CRYPTO

    def test_filter_by_class(self):
        from atlas.shared.asset_registry import REGISTRY, AssetClass

        equities = REGISTRY.equities()
        assert "AAPL" in equities
        assert "SPY" not in equities  # SPY is ETF

        bonds = REGISTRY.bonds()
        assert "AGG" in bonds
        assert "AAPL" not in bonds

    def test_index_not_tradeable(self):
        from atlas.shared.asset_registry import REGISTRY

        info = REGISTRY.get("^GSPC")
        assert info is not None
        assert info.tradeable is False

    def test_runtime_extension(self):
        from atlas.shared.asset_registry import REGISTRY, AssetInfo, AssetClass

        # Add a hypothetical new ticker
        new = AssetInfo("CUSTOM", "Custom Asset", AssetClass.EQUITY, sector="Test")
        REGISTRY.add(new)
        assert REGISTRY.validate("CUSTOM")
        assert REGISTRY.classify("CUSTOM") == AssetClass.EQUITY

        # Clean up
        del REGISTRY._store["CUSTOM"]

    def test_group_by_class(self):
        from atlas.shared.asset_registry import REGISTRY

        tickers = ["AAPL", "SPY", "GLD", "^GSPC"]
        groups = REGISTRY.group_by_class(tickers)

        assert "equity" in groups
        assert "etf" in groups
        assert "commodity" in groups
        assert "index" in groups
        assert "AAPL" in groups["equity"]


# ---------------------------------------------------------------------------
# Analytics Tests
# ---------------------------------------------------------------------------

class TestAnalytics:
    """Unit tests for analytics functions."""

    def test_log_returns_length(self):
        from atlas.analytics.returns import log_returns

        df = make_ohlcv("AAPL", n=30)
        r = log_returns(df)
        assert len(r) == 29  # first row dropped

    def test_simple_returns_no_nan(self):
        from atlas.analytics.returns import simple_returns

        df = make_ohlcv("SPY", n=50)
        r = simple_returns(df)
        assert not r.isna().any()

    def test_rolling_volatility_annualized(self):
        from atlas.analytics.volatility import rolling_volatility

        df = make_ohlcv("AAPL", n=100)
        vol = rolling_volatility(df, window=21, annualize=True)
        # Typical equity annualized vol is 10-100%
        last_vol = vol.dropna().iloc[-1]
        assert 0.05 < last_vol < 2.0

    def test_max_drawdown_negative_or_zero(self):
        from atlas.analytics.risk_metrics import max_drawdown
        from atlas.analytics.returns import simple_returns

        df = make_ohlcv("AAPL", n=100)
        r = simple_returns(df)
        mdd = max_drawdown(r)
        assert mdd <= 0.0  # Must be ≤ 0

    def test_sharpe_ratio_positive_trend(self):
        from atlas.analytics.risk_metrics import sharpe_ratio

        # Pure uptrend → positive Sharpe
        returns = pd.Series([0.001] * 252)
        sr = sharpe_ratio(returns)
        assert sr > 0

    def test_drawdown_series_shape(self):
        from atlas.analytics.risk_metrics import drawdown_series
        from atlas.analytics.returns import simple_returns

        df = make_ohlcv("SPY", n=60)
        r = simple_returns(df)
        dd = drawdown_series(r)
        assert len(dd) == len(r)
        assert (dd <= 0).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
