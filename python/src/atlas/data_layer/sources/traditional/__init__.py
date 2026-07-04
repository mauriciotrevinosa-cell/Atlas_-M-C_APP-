"""
Traditional Market Data Sources
================================
Providers for equities, ETFs, indices, forex, macro data, news, filings,
and sentiment analysis via standard APIs.

Includes:
- FREDProvider: Federal Reserve Economic Data
- WorldBankProvider: World Bank annual macro indicators
- BLSProvider: Bureau of Labor Statistics time series
- TreasuryFiscalProvider: U.S. Treasury FiscalData series
- IMFDataMapperProvider: IMF country macro indicators
- AlphaVantageProvider: OHLCV, intraday, fundamentals
- FinnhubProvider: Real-time quotes, candles, news, sentiment
- SECEDGARProvider: SEC filings and company facts
- NewsAPIProvider: News headlines and articles
- HuggingFaceProvider: Sentiment analysis and embeddings
- YahooFinanceProvider: Yahoo Finance data
- PolygonProvider: Polygon.io data (optional, requires API key)

Copyright (c) 2026 M&C. All rights reserved.
"""

from atlas.data_layer.sources.traditional.yahoo_provider import YahooFinanceProvider
from atlas.data_layer.sources.traditional.fred_provider import FREDProvider
from atlas.data_layer.sources.traditional.worldbank_provider import WorldBankProvider
from atlas.data_layer.sources.traditional.bls_provider import BLSProvider
from atlas.data_layer.sources.traditional.treasury_provider import TreasuryFiscalProvider
from atlas.data_layer.sources.traditional.imf_provider import IMFDataMapperProvider
from atlas.data_layer.sources.traditional.alphavantage_provider import AlphaVantageProvider
from atlas.data_layer.sources.traditional.finnhub_provider import FinnhubProvider
from atlas.data_layer.sources.traditional.sec_edgar_provider import SECEDGARProvider
from atlas.data_layer.sources.traditional.newsapi_provider import NewsAPIProvider
from atlas.data_layer.sources.traditional.huggingface_provider import HuggingFaceProvider

__all__ = [
    "YahooFinanceProvider",
    "FREDProvider",
    "WorldBankProvider",
    "BLSProvider",
    "TreasuryFiscalProvider",
    "IMFDataMapperProvider",
    "AlphaVantageProvider",
    "FinnhubProvider",
    "SECEDGARProvider",
    "NewsAPIProvider",
    "HuggingFaceProvider",
]

# Polygon is optional (requires API key)
try:
    from atlas.data_layer.sources.traditional.polygon_provider import PolygonProvider
    __all__.append("PolygonProvider")
except ImportError:
    pass
