"""
Compatibility tests for Atlas data_layer public API and legacy providers.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

import atlas.data_layer as data_layer
from atlas.data_layer.sources.alpaca import AlpacaProvider
from atlas.data_layer.sources.polygon import PolygonProvider
from atlas.data_layer.sources.yahoo import YahooProvider


def _sample_uppercase_ohlcv(rows: int = 3) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0][:rows],
            "High": [101.0, 102.0, 103.0][:rows],
            "Low": [99.0, 100.0, 101.0][:rows],
            "Close": [100.5, 101.5, 102.5][:rows],
            "Volume": [1_000_000, 1_100_000, 1_200_000][:rows],
        },
        index=idx,
    )


def _sample_lowercase_ohlcv(rows: int = 3) -> pd.DataFrame:
    return _sample_uppercase_ohlcv(rows=rows).rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )


def test_get_data_keeps_legacy_ohlcv_shape(monkeypatch):
    sample = _sample_lowercase_ohlcv()

    def fake_get_historical(self, **kwargs):  # noqa: ARG001
        return sample

    monkeypatch.setattr(data_layer.DataManager, "get_historical", fake_get_historical)

    out = data_layer.get_data("AAPL", "2024-01-01", "2024-01-31")
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(out) == len(sample)


def test_get_data_future_range_returns_empty():
    start = (date.today() + timedelta(days=15)).isoformat()
    end = (date.today() + timedelta(days=20)).isoformat()

    out = data_layer.get_data("AAPL", start, end)
    assert out.empty
    assert list(out.columns) == ["Open", "High", "Low", "Close", "Volume"]


def test_get_data_non_future_empty_raises(monkeypatch):
    def fake_get_historical(self, **kwargs):  # noqa: ARG001
        return pd.DataFrame()

    monkeypatch.setattr(data_layer.DataManager, "get_historical", fake_get_historical)

    with pytest.raises(ValueError, match="No data found"):
        data_layer.get_data("INVALID_SYMBOL_12345", "2024-01-01", "2024-01-31")


def test_polygon_provider_uses_yahoo_fallback(monkeypatch):
    sample = _sample_uppercase_ohlcv()

    def fake_download(self, symbol, start, end, interval="1d"):  # noqa: ARG001
        return sample

    monkeypatch.setattr(YahooProvider, "download", fake_download)

    provider = PolygonProvider(api_key=None, allow_yahoo_fallback=True)
    out = provider.download("AAPL", "2024-01-01", "2024-01-31")
    assert not out.empty
    assert provider.get_info()["last_source"] == "yahoo-fallback"


def test_polygon_provider_without_fallback_raises():
    provider = PolygonProvider(api_key=None, allow_yahoo_fallback=False)
    with pytest.raises(RuntimeError, match="fallback is disabled"):
        provider.download("AAPL", "2024-01-01", "2024-01-31")


def test_alpaca_provider_uses_yahoo_fallback(monkeypatch):
    sample = _sample_uppercase_ohlcv()

    def fake_download(self, symbol, start, end, interval="1d"):  # noqa: ARG001
        return sample

    monkeypatch.setattr(YahooProvider, "download", fake_download)

    provider = AlpacaProvider(
        api_key=None,
        api_secret=None,
        allow_yahoo_fallback=True,
    )
    out = provider.download("MSFT", "2024-01-01", "2024-01-31")
    assert not out.empty
    assert provider.get_info()["last_source"] == "yahoo-fallback"


def test_alpaca_provider_without_fallback_raises():
    provider = AlpacaProvider(
        api_key=None,
        api_secret=None,
        allow_yahoo_fallback=False,
    )
    with pytest.raises(RuntimeError, match="fallback is disabled"):
        provider.download("MSFT", "2024-01-01", "2024-01-31")
