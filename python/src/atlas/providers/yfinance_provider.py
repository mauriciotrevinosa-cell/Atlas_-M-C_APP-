"""
YFinance Provider
=================
Network-gated wrapper around Yahoo Finance.

Raises NetworkUnavailableError immediately if allow_network=False,
so the DataRouter can catch it and fall back to cache without
making any network calls.

Wraps the existing YahooFinanceProvider in data_layer to avoid
duplication of yfinance logic.

Copyright (c) 2026 M&C. All rights reserved.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("atlas.providers.yfinance")


class NetworkUnavailableError(RuntimeError):
    """Raised when allow_network=False and a live fetch is attempted."""


class YFinanceProvider:
    """
    Yahoo Finance provider with explicit network guard.

    Args:
        allow_network: If False, all fetch methods immediately raise
                       NetworkUnavailableError (no yfinance import, no network call).

    Usage:
        prov = YFinanceProvider(allow_network=True)
        df = prov.get_historical("AAPL", "2024-01-01", "2024-12-31")

        prov_offline = YFinanceProvider(allow_network=False)
        prov_offline.get_historical(...)  # raises NetworkUnavailableError
    """

    def __init__(self, allow_network: bool = True) -> None:
        self.allow_network = allow_network
        self._inner = None  # lazy

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _guard(self) -> None:
        """Raise immediately if network is disabled."""
        if not self.allow_network:
            raise NetworkUnavailableError(
                "YFinanceProvider: network is disabled (allow_network=False). "
                "Use CacheProvider for offline access."
            )

    def _get_inner(self):
        """Lazy-load the underlying YahooFinanceProvider."""
        if self._inner is None:
            from atlas.data_layer.sources.traditional.yahoo_provider import (
                YahooFinanceProvider,
            )
            self._inner = YahooFinanceProvider()
        return self._inner

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_historical(
        self,
        ticker: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data from Yahoo Finance.

        Args:
            ticker:   Ticker symbol (e.g. "AAPL", "BTC-USD", "^GSPC")
            start:    Start date "YYYY-MM-DD"
            end:      End date "YYYY-MM-DD"
            interval: Candle interval — "1d" (default), "1h", "1wk", "1mo"

        Returns:
            DataFrame with OHLCV columns.

        Raises:
            NetworkUnavailableError: if allow_network=False
            RuntimeError: if yfinance fetch fails
        """
        self._guard()
        logger.info("YFinanceProvider: fetching %s  %s→%s  @%s", ticker, start, end, interval)
        return self._get_inner().get_historical_data(
            symbol=ticker,
            start_date=start,
            end_date=end,
            interval=interval,
        )

    def get_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Get latest delayed quote (~15min) from Yahoo Finance.

        Args:
            ticker: Ticker symbol

        Returns:
            Dict with keys: symbol, price, bid, ask, volume, timestamp, provider

        Raises:
            NetworkUnavailableError: if allow_network=False
        """
        self._guard()
        logger.info("YFinanceProvider: quote %s", ticker)
        return self._get_inner().get_latest_quote(ticker)

    def get_many(
        self,
        tickers: List[str],
        start: str,
        end: str,
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """
        Batch-fetch multiple tickers efficiently using yf.download.

        Args:
            tickers:  List of ticker symbols
            start:    Start date "YYYY-MM-DD"
            end:      End date "YYYY-MM-DD"
            interval: Candle interval

        Returns:
            Dict mapping ticker → DataFrame

        Raises:
            NetworkUnavailableError: if allow_network=False
        """
        self._guard()
        logger.info("YFinanceProvider: batch fetch %s", tickers)
        return self._get_inner().get_multiple(
            symbols=tickers,
            start_date=start,
            end_date=end,
            interval=interval,
        )
