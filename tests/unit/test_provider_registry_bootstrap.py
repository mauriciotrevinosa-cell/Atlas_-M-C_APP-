from __future__ import annotations

from atlas.data_layer import get_provider_registry
from atlas.data_layer.provider_registry import DataProviderRegistry, ProviderType
import pandas as pd


def test_get_provider_registry_returns_shared_instance():
    first = get_provider_registry()
    second = get_provider_registry()
    assert first is second


def test_default_bootstrap_registers_core_channels():
    registry = DataProviderRegistry()
    info = registry.get_provider_info()

    assert "market_data" in info
    assert "filings" in info

    market_names = {item["name"] for item in info["market_data"]}
    filings_names = {item["name"] for item in info["filings"]}

    assert "YahooFinance" in market_names
    assert "SECEDGAR" in filings_names


def test_get_quote_uses_latest_quote_fallback():
    class FakeQuoteProvider:
        name = "fake_quote"

        def get_latest_quote(self, symbol: str):
            return {
                "symbol": symbol,
                "price": 101.25,
                "open": 100.0,
                "high": 102.0,
                "low": 99.5,
                "provider": self.name,
            }

    registry = DataProviderRegistry(auto_register_defaults=False)
    registry.register_provider(
        ProviderType.MARKET_DATA,
        "FakeQuote",
        FakeQuoteProvider(),
        priority=100,
    )

    quote = registry.get_quote("AAPL")
    assert quote is not None
    assert quote["symbol"] == "AAPL"
    assert quote["provider"] == "fake_quote"


def test_macro_fallback_skips_empty_provider_result():
    class EmptyProvider:
        available = True

        def get_series(self, series_id, start, end):
            return pd.DataFrame()

    class WorkingProvider:
        available = True

        def get_series(self, series_id, start, end):
            return pd.DataFrame({"value": [2.5]}, index=[pd.Timestamp("2024-01-01")])

    registry = DataProviderRegistry(auto_register_defaults=False)
    registry.register_provider(ProviderType.MACRO, "Empty", EmptyProvider(), priority=100)
    registry.register_provider(ProviderType.MACRO, "Working", WorkingProvider(), priority=50)

    result = registry.get_macro("GDP_REAL_GROWTH", "2024-01-01", "2024-12-31")

    assert result is not None
    assert result.iloc[0]["value"] == 2.5
