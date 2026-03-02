"""
Tests for Atlas Data Layer (FASE 1)
====================================
Run with: pytest tests/test_data_layer.py -v

Copyright (c) 2026 M&C. All rights reserved.
"""

import numpy as np
import pandas as pd
import pytest
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_sample_ohlcv(rows: int = 100, start: str = "2024-01-01") -> pd.DataFrame:
    """Create a realistic sample OHLCV DataFrame for testing."""
    dates = pd.date_range(start=start, periods=rows, freq="D")
    np.random.seed(42)

    base_price = 150.0
    prices = base_price + np.cumsum(np.random.randn(rows) * 2)

    df = pd.DataFrame(
        {
            "open": prices + np.random.uniform(-1, 1, rows),
            "high": prices + np.abs(np.random.randn(rows) * 2),
            "low": prices - np.abs(np.random.randn(rows) * 2),
            "close": prices,
            "volume": np.random.randint(1_000_000, 50_000_000, rows),
        },
        index=dates,
    )
    df.index.name = "date"

    # Ensure high >= open, close, low and low <= open, close
    df["high"] = df[["open", "high", "low", "close"]].max(axis=1)
    df["low"] = df[["open", "high", "low", "close"]].min(axis=1)

    return df


# ===========================================================================
# Test normalize.py
# ===========================================================================

class TestNormalize:
    def test_basic_normalization(self):
        from atlas.data_layer.normalize import normalize_ohlcv

        df = make_sample_ohlcv()
        result = normalize_ohlcv(df)

        assert list(result.columns) == ["open", "high", "low", "close", "volume"]
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == 100

    def test_uppercase_columns(self):
        from atlas.data_layer.normalize import normalize_ohlcv

        df = make_sample_ohlcv()
        df.columns = [c.upper() for c in df.columns]
        result = normalize_ohlcv(df)

        assert "close" in result.columns
        assert "CLOSE" not in result.columns

    def test_alias_adj_close(self):
        from atlas.data_layer.normalize import normalize_ohlcv

        df = make_sample_ohlcv()
        df = df.rename(columns={"close": "adj close"})
        result = normalize_ohlcv(df)

        assert "close" in result.columns

    def test_missing_column_raises(self):
        from atlas.data_layer.normalize import normalize_ohlcv

        df = make_sample_ohlcv().drop(columns=["volume"])

        with pytest.raises(ValueError, match="Missing required columns"):
            normalize_ohlcv(df)

    def test_empty_dataframe(self):
        from atlas.data_layer.normalize import normalize_ohlcv

        result = normalize_ohlcv(pd.DataFrame())
        assert result.empty

    def test_timezone_removed(self):
        from atlas.data_layer.normalize import normalize_ohlcv

        df = make_sample_ohlcv()
        df.index = df.index.tz_localize("US/Eastern")

        result = normalize_ohlcv(df)
        assert result.index.tz is None

    def test_add_returns(self):
        from atlas.data_layer.normalize import add_returns

        df = make_sample_ohlcv()

        result_log = add_returns(df, method="log")
        assert "returns" in result_log.columns
        assert result_log["returns"].iloc[0] != result_log["returns"].iloc[0]  # first is NaN

        result_simple = add_returns(df, method="simple")
        assert "returns" in result_simple.columns

    def test_align_timeframe(self):
        from atlas.data_layer.normalize import align_timeframe

        df = make_sample_ohlcv(rows=365)
        weekly = align_timeframe(df, target="1W")

        assert len(weekly) < len(df)
        assert len(weekly) > 0


# ===========================================================================
# Test cache_store.py
# ===========================================================================

class TestCacheStore:
    def test_set_and_get(self, tmp_path):
        from atlas.data_layer.cache_store import CacheStore

        cache = CacheStore(cache_dir=str(tmp_path), ttl_hours=1)
        df = make_sample_ohlcv(rows=50)

        cache.set("test_key", df)
        result = cache.get("test_key")

        assert result is not None
        assert len(result) == 50
        assert list(result.columns) == list(df.columns)

    def test_cache_miss(self, tmp_path):
        from atlas.data_layer.cache_store import CacheStore

        cache = CacheStore(cache_dir=str(tmp_path))
        result = cache.get("nonexistent")

        assert result is None

    def test_cache_clear(self, tmp_path):
        from atlas.data_layer.cache_store import CacheStore

        cache = CacheStore(cache_dir=str(tmp_path))
        df = make_sample_ohlcv(rows=10)

        cache.set("aapl_data", df)
        cache.set("msft_data", df)

        # Clear only AAPL
        cache.clear(pattern="aapl")
        assert cache.get("aapl_data") is None
        assert cache.get("msft_data") is not None

        # Clear all
        cache.clear()
        assert cache.get("msft_data") is None

    def test_cache_stats(self, tmp_path):
        from atlas.data_layer.cache_store import CacheStore

        cache = CacheStore(cache_dir=str(tmp_path))
        df = make_sample_ohlcv(rows=10)

        cache.set("key1", df)
        cache.set("key2", df)

        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["total_size_mb"] > 0

    def test_list_keys(self, tmp_path):
        from atlas.data_layer.cache_store import CacheStore

        cache = CacheStore(cache_dir=str(tmp_path))
        df = make_sample_ohlcv(rows=5)

        cache.set("key_a", df)
        cache.set("key_b", df)

        keys = cache.list_keys()
        assert "key_a" in keys
        assert "key_b" in keys

    def test_safe_key_sanitization(self, tmp_path):
        from atlas.data_layer.cache_store import CacheStore

        cache = CacheStore(cache_dir=str(tmp_path))
        df = make_sample_ohlcv(rows=5)

        # Keys with special characters
        cache.set("BTC/USDT:2024", df)
        result = cache.get("BTC/USDT:2024")
        assert result is not None


# ===========================================================================
# Test validator.py
# ===========================================================================

class TestDataValidator:
    def test_clean_data_passes(self):
        from atlas.data_layer.quality.validator import DataValidator

        validator = DataValidator()
        df = make_sample_ohlcv()
        report = validator.validate(df)

        assert report["is_valid"] is True
        assert report["total_rows"] == 100
        assert len(report["issues"]) == 0

    def test_empty_data_fails(self):
        from atlas.data_layer.quality.validator import DataValidator

        validator = DataValidator()
        report = validator.validate(pd.DataFrame())

        assert report["is_valid"] is False

    def test_high_nan_ratio_fails(self):
        from atlas.data_layer.quality.validator import DataValidator

        validator = DataValidator(max_nan_ratio=0.01)
        df = make_sample_ohlcv()
        # Inject 10% NaNs
        mask = np.random.random(len(df)) < 0.10
        df.loc[mask, "close"] = np.nan

        report = validator.validate(df)
        assert report["is_valid"] is False
        assert any("NaN" in issue for issue in report["issues"])

    def test_ohlc_inconsistency_detected(self):
        from atlas.data_layer.quality.validator import DataValidator

        validator = DataValidator()
        df = make_sample_ohlcv()
        # Make high < low (bad data)
        df.iloc[5, df.columns.get_loc("high")] = 10.0
        df.iloc[5, df.columns.get_loc("low")] = 200.0

        report = validator.validate(df)
        assert report["checks"]["ohlc_inconsistencies"] > 0

    def test_duplicate_timestamps_detected(self):
        from atlas.data_layer.quality.validator import DataValidator

        validator = DataValidator()
        df = make_sample_ohlcv()
        # Add duplicate row
        dup = df.iloc[[0]]
        df = pd.concat([df, dup])

        report = validator.validate(df)
        assert report["checks"]["duplicate_timestamps"] > 0

    def test_spike_detection(self):
        from atlas.data_layer.quality.validator import DataValidator

        validator = DataValidator(max_spike_pct=0.10)
        df = make_sample_ohlcv()
        # Inject a massive spike
        df.iloc[50, df.columns.get_loc("close")] = df.iloc[49]["close"] * 3

        report = validator.validate(df)
        assert report["checks"]["spike_count"] > 0


# ===========================================================================
# Test DataManager (integration)
# ===========================================================================

class TestDataManager:
    def test_initialization(self):
        from atlas.data_layer.manager import DataManager

        dm = DataManager(enable_cache=False, enable_validation=False)
        assert dm.default_provider == "yahoo"

    def test_list_providers(self):
        from atlas.data_layer.manager import DataManager

        dm = DataManager()
        providers = dm.list_providers()
        assert "yahoo" in providers
        assert "polygon" in providers
        assert "ccxt" in providers

    def test_validate_shortcut(self):
        from atlas.data_layer.manager import DataManager

        dm = DataManager()
        df = make_sample_ohlcv()
        report = dm.validate(df)

        assert "is_valid" in report
        assert report["is_valid"] is True

    # NOTE: The tests below require internet and are marked for manual/CI runs
    @pytest.mark.skip(reason="Requires internet - run manually with --run-network")
    def test_get_historical_yahoo(self):
        from atlas.data_layer.manager import DataManager

        dm = DataManager(enable_cache=False)
        df = dm.get_historical("AAPL", "2024-01-01", "2024-03-31")

        assert not df.empty
        assert "close" in df.columns
        assert len(df) > 50  # ~60 trading days in Q1

    @pytest.mark.skip(reason="Requires internet - run manually with --run-network")
    def test_get_quote_yahoo(self):
        from atlas.data_layer.manager import DataManager

        dm = DataManager(enable_cache=False)
        quote = dm.get_quote("AAPL")

        assert "price" in quote
        assert quote["price"] > 0

    @pytest.mark.skip(reason="Requires internet + ccxt installed")
    def test_get_historical_ccxt(self):
        from atlas.data_layer.manager import DataManager

        dm = DataManager(default_provider="ccxt", enable_cache=False)
        df = dm.get_historical("BTC/USDT", "2024-01-01", "2024-01-31")

        assert not df.empty
        assert "close" in df.columns
