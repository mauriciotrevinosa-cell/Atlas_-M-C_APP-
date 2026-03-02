"""
CCXT Crypto Provider
====================
Universal crypto exchange provider using the CCXT library.
Supports 100+ exchanges including Binance, Bybit, Coinbase, Kraken, etc.

Strengths:
  - Unified API for all exchanges
  - Spot + Futures support
  - OHLCV, order book, tickers
  - Free for public data (no API key needed for historical)

Requirements:
  - pip install ccxt

For private endpoints (trading):
  - Set CCXT_API_KEY and CCXT_SECRET in .env

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from atlas.interfaces.market_data import MarketDataProvider

logger = logging.getLogger("atlas.data_layer")

# Interval mapping: Atlas → CCXT timeframe strings
INTERVAL_MAP = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "3d": "3d",
    "1wk": "1w",
    "1mo": "1M",
}


class CCXTProvider(MarketDataProvider):
    """
    Crypto exchange data provider via CCXT.

    Default exchange is Binance. Can be changed at init.

    Usage:
        provider = CCXTProvider(exchange="binance")
        df = provider.get_historical_data("BTC/USDT", "2024-01-01", "2024-12-31")
    """

    @property
    def name(self) -> str:
        return f"ccxt_{self._exchange_name}"

    def __init__(
        self,
        exchange: str = "binance",
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        try:
            import ccxt  # noqa: F401
        except ImportError:
            raise ImportError(
                "ccxt is required for crypto data. "
                "Install with: pip install ccxt"
            )

        self._exchange_name = exchange.lower()

        # Resolve API credentials
        api_key = api_key or os.getenv("CCXT_API_KEY", "")
        secret = secret or os.getenv("CCXT_SECRET", "")

        # Initialize exchange
        import ccxt as ccxt_lib

        exchange_class = getattr(ccxt_lib, self._exchange_name, None)
        if exchange_class is None:
            raise ValueError(
                f"Unknown exchange: {exchange}. "
                f"Available: {', '.join(ccxt_lib.exchanges[:20])}..."
            )

        config = {"enableRateLimit": True}
        if api_key:
            config["apiKey"] = api_key
        if secret:
            config["secret"] = secret

        self.exchange = exchange_class(config)

        logger.info("CCXT: initialized %s", self._exchange_name)

    def get_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV from crypto exchange.

        Args:
            symbol:     Trading pair (e.g. "BTC/USDT", "ETH/USDT")
            start_date: "YYYY-MM-DD"
            end_date:   "YYYY-MM-DD" (default: now)
            interval:   Candle interval

        Returns:
            DataFrame with DatetimeIndex and OHLCV columns.
        """
        if interval not in INTERVAL_MAP:
            raise ValueError(
                f"Unsupported interval: {interval}. "
                f"Supported: {list(INTERVAL_MAP.keys())}"
            )

        timeframe = INTERVAL_MAP[interval]

        # Convert dates to millisecond timestamps
        since_ms = int(
            datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000
        )
        end_ms = (
            int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)
            if end_date
            else int(datetime.now().timestamp() * 1000)
        )

        logger.info(
            "CCXT (%s): fetching %s | %s → %s @ %s",
            self._exchange_name, symbol, start_date, end_date, interval,
        )

        # CCXT returns max ~1000 candles per request, so we paginate
        all_candles: List[list] = []
        current_since = since_ms
        limit = 1000

        while current_since < end_ms:
            candles = self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=current_since,
                limit=limit,
            )

            if not candles:
                break

            all_candles.extend(candles)

            # Move cursor forward
            last_timestamp = candles[-1][0]
            if last_timestamp <= current_since:
                break  # No progress, avoid infinite loop
            current_since = last_timestamp + 1

        if not all_candles:
            logger.warning("CCXT: no data for %s on %s", symbol, self._exchange_name)
            return pd.DataFrame()

        # CCXT format: [timestamp_ms, open, high, low, close, volume]
        df = pd.DataFrame(
            all_candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("date")
        df = df[["open", "high", "low", "close", "volume"]]

        # Filter to requested date range
        if end_date:
            df = df[df.index <= end_date]

        # Remove duplicates (pagination overlap)
        df = df[~df.index.duplicated(keep="first")]

        logger.info("CCXT: got %d candles for %s", len(df), symbol)
        return df

    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest ticker from exchange.

        Args:
            symbol: Trading pair (e.g. "BTC/USDT")

        Returns:
            Quote dictionary
        """
        ticker = self.exchange.fetch_ticker(symbol)

        return {
            "symbol": symbol,
            "price": float(ticker.get("last", 0)),
            "bid": float(ticker.get("bid", 0) or 0),
            "ask": float(ticker.get("ask", 0) or 0),
            "volume": float(ticker.get("baseVolume", 0) or 0),
            "high_24h": float(ticker.get("high", 0) or 0),
            "low_24h": float(ticker.get("low", 0) or 0),
            "change_24h_pct": float(ticker.get("percentage", 0) or 0),
            "timestamp": str(
                pd.to_datetime(ticker.get("timestamp", 0), unit="ms")
            ),
            "provider": self.name,
            "exchange": self._exchange_name,
            "delay": "real-time",
        }

    def list_markets(self) -> List[str]:
        """Return available trading pairs on this exchange."""
        self.exchange.load_markets()
        return list(self.exchange.markets.keys())
