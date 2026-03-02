"""
Polygon.io Provider
===================
Professional-grade market data with real-time and historical coverage.

Strengths:
  - True real-time data (paid plans)
  - Tick-level granularity
  - Options, forex, crypto support
  - High reliability and uptime

Requirements:
  - API key from https://polygon.io
  - Set POLYGON_API_KEY in .env or environment

Free tier limitations:
  - 5 API calls/minute
  - End-of-day data only
  - Delayed quotes

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from atlas.interfaces.market_data import MarketDataProvider

logger = logging.getLogger("atlas.data_layer")

# Interval mapping: Atlas interval → Polygon multiplier + timespan
INTERVAL_MAP = {
    "1m": (1, "minute"),
    "5m": (5, "minute"),
    "15m": (15, "minute"),
    "30m": (30, "minute"),
    "1h": (1, "hour"),
    "4h": (4, "hour"),
    "1d": (1, "day"),
    "1wk": (1, "week"),
    "1mo": (1, "month"),
}


class PolygonProvider(MarketDataProvider):
    """Polygon.io data provider using REST API."""

    @property
    def name(self) -> str:
        return "polygon"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("POLYGON_API_KEY", "")
        self.base_url = "https://api.polygon.io"

        if not self.api_key:
            logger.warning(
                "Polygon: no API key found. Set POLYGON_API_KEY in .env. "
                "Provider will fail on data requests."
            )

    def _request(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make authenticated request to Polygon API."""
        import requests

        params = params or {}
        params["apiKey"] = self.api_key

        url = f"{self.base_url}{endpoint}"
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 403:
            raise PermissionError(
                "Polygon API: Invalid or missing API key. "
                "Get one at https://polygon.io"
            )
        elif response.status_code == 429:
            raise RuntimeError("Polygon API: Rate limit exceeded. Wait and retry.")

        response.raise_for_status()
        return response.json()

    def get_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV from Polygon.io.

        Args:
            symbol:     Ticker (e.g. "AAPL")
            start_date: "YYYY-MM-DD"
            end_date:   "YYYY-MM-DD" (default: today)
            interval:   "1m","5m","15m","1h","1d","1wk","1mo"

        Returns:
            DataFrame with DatetimeIndex and OHLCV columns.
        """
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if interval not in INTERVAL_MAP:
            raise ValueError(
                f"Unsupported interval: {interval}. "
                f"Supported: {list(INTERVAL_MAP.keys())}"
            )

        multiplier, timespan = INTERVAL_MAP[interval]

        logger.info(
            "Polygon: fetching %s | %s → %s @ %s",
            symbol, start_date, end_date, interval,
        )

        endpoint = (
            f"/v2/aggs/ticker/{symbol}/range"
            f"/{multiplier}/{timespan}/{start_date}/{end_date}"
        )

        data = self._request(endpoint, params={"adjusted": "true", "sort": "asc", "limit": 50000})

        results = data.get("results", [])
        if not results:
            logger.warning("Polygon: no data for %s", symbol)
            return pd.DataFrame()

        df = pd.DataFrame(results)

        # Polygon columns: t(timestamp ms), o, h, l, c, v, vw, n
        df["date"] = pd.to_datetime(df["t"], unit="ms")
        df = df.rename(columns={
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
        })
        df = df.set_index("date")
        df = df[["open", "high", "low", "close", "volume"]]

        logger.info("Polygon: got %d rows for %s", len(df), symbol)
        return df

    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest quote from Polygon.

        Args:
            symbol: Ticker symbol

        Returns:
            Quote dictionary
        """
        data = self._request(f"/v2/last/trade/{symbol}")
        result = data.get("results", {})

        return {
            "symbol": symbol,
            "price": float(result.get("p", 0)),
            "volume": int(result.get("s", 0)),
            "timestamp": str(
                pd.to_datetime(result.get("t", 0), unit="ns")
                if result.get("t")
                else datetime.now()
            ),
            "provider": self.name,
            "delay": "real-time (paid) / EOD (free)",
        }
