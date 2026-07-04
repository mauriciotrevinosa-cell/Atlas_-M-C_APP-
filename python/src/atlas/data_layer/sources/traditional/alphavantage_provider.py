"""
Alpha Vantage Data Provider

Fetches OHLCV, intraday, and fundamental data from Alpha Vantage API.
Uses requests library directly to avoid heavy dependencies.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import os
from typing import Dict, Any

import pandas as pd

logger = logging.getLogger("atlas.data_layer.alphavantage_provider")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class AlphaVantageProvider:
    """
    Fetches market data and fundamentals from Alpha Vantage API.

    Requires ALPHA_VANTAGE_KEY environment variable.
    Rate limit: 5 calls/min (free tier), 25 calls/day (free tier total).

    Example::

        provider = AlphaVantageProvider()
        if provider.available:
            daily = provider.get_daily("AAPL")
            intraday = provider.get_intraday("AAPL", interval="5min")
            fundamentals = provider.get_fundamentals("AAPL")
    """

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self):
        """Initialize Alpha Vantage provider with API key from environment"""
        self.available = False
        self.api_key = os.environ.get("ALPHA_VANTAGE_KEY")

        if not self.api_key:
            logger.warning("ALPHA_VANTAGE_KEY not found in environment")
            return

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")
            return

        self.available = True
        logger.info("Alpha Vantage provider initialized")

    def get_daily(
        self,
        symbol: str,
        outputsize: str = "compact",
    ) -> pd.DataFrame:
        """
        Get daily OHLCV data.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            outputsize: "compact" (latest 100 days) or "full" (all available)

        Returns:
            DataFrame with columns [open, high, low, close, volume].
            Returns empty DataFrame on failure.

        Example::

            df = provider.get_daily("AAPL")
            # Returns:
            #             open    high     low   close    volume
            # 2024-01-01  150.25  151.50  149.75  150.75  50000000
            # ...
        """
        if not self.available:
            logger.warning("Alpha Vantage provider not available")
            return pd.DataFrame()

        try:
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": outputsize,
                "apikey": self.api_key,
            }

            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if "Error Message" in data:
                logger.error(f"Alpha Vantage error: {data['Error Message']}")
                return pd.DataFrame()

            if "Time Series (Daily)" not in data:
                logger.warning(
                    f"No daily data for {symbol}. Response: {list(data.keys())}"
                )
                return pd.DataFrame()

            ts = data["Time Series (Daily)"]

            # Parse data
            rows = []
            for date_str, values in ts.items():
                try:
                    rows.append(
                        {
                            "open": float(values["1. open"]),
                            "high": float(values["2. high"]),
                            "low": float(values["3. low"]),
                            "close": float(values["4. close"]),
                            "volume": int(float(values["5. volume"])),
                        }
                    )
                except (KeyError, ValueError) as e:
                    logger.warning(f"Error parsing row for {date_str}: {e}")

            if not rows:
                logger.warning(f"No valid data rows for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(rows, index=pd.to_datetime(list(ts.keys())))
            df.index.name = "date"
            df = df.sort_index()

            logger.info(f"Got {len(df)} daily bars for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch daily data for {symbol}: {e}")
            return pd.DataFrame()

    def get_intraday(
        self,
        symbol: str,
        interval: str = "5min",
        outputsize: str = "compact",
    ) -> pd.DataFrame:
        """
        Get intraday OHLCV data.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            interval: Candle interval ("1min", "5min", "15min", "30min", "60min")
            outputsize: "compact" (latest 100 candles) or "full" (all available)

        Returns:
            DataFrame with columns [open, high, low, close, volume].
            Returns empty DataFrame on failure.
        """
        if not self.available:
            logger.warning("Alpha Vantage provider not available")
            return pd.DataFrame()

        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": symbol,
                "interval": interval,
                "outputsize": outputsize,
                "apikey": self.api_key,
            }

            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if "Error Message" in data:
                logger.error(f"Alpha Vantage error: {data['Error Message']}")
                return pd.DataFrame()

            key = f"Time Series ({interval})"
            if key not in data:
                logger.warning(f"No intraday data for {symbol}. Response: {list(data.keys())}")
                return pd.DataFrame()

            ts = data[key]

            # Parse data
            rows = []
            for ts_str, values in ts.items():
                try:
                    rows.append(
                        {
                            "open": float(values["1. open"]),
                            "high": float(values["2. high"]),
                            "low": float(values["3. low"]),
                            "close": float(values["4. close"]),
                            "volume": int(float(values["5. volume"])),
                        }
                    )
                except (KeyError, ValueError) as e:
                    logger.warning(f"Error parsing intraday row for {ts_str}: {e}")

            if not rows:
                logger.warning(f"No valid intraday data for {symbol}")
                return pd.DataFrame()

            df = pd.DataFrame(rows, index=pd.to_datetime(list(ts.keys())))
            df.index.name = "timestamp"
            df = df.sort_index()

            logger.info(f"Got {len(df)} intraday bars ({interval}) for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch intraday data for {symbol}: {e}")
            return pd.DataFrame()

    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """
        Get fundamental data (overview, income statement, balance sheet).

        Args:
            symbol: Stock symbol (e.g., "AAPL")

        Returns:
            Dict with keys: overview, income_statement, balance_sheet.
            Returns empty dict on failure.

        Example::

            fund = provider.get_fundamentals("AAPL")
            overview = fund.get("overview", {})
            income = fund.get("income_statement", {})
        """
        if not self.available:
            logger.warning("Alpha Vantage provider not available")
            return {}

        try:
            result = {}

            # Get overview
            overview_params = {
                "function": "OVERVIEW",
                "symbol": symbol,
                "apikey": self.api_key,
            }
            overview_response = requests.get(
                self.BASE_URL, params=overview_params, timeout=10
            )
            overview_response.raise_for_status()
            overview = overview_response.json()

            if "Error Message" not in overview and "Symbol" in overview:
                result["overview"] = overview
            else:
                logger.warning(f"No overview data for {symbol}")

            # Get income statement
            income_params = {
                "function": "INCOME_STATEMENT",
                "symbol": symbol,
                "apikey": self.api_key,
            }
            income_response = requests.get(
                self.BASE_URL, params=income_params, timeout=10
            )
            income_response.raise_for_status()
            income = income_response.json()

            if "annualReports" in income:
                result["income_statement"] = income.get("annualReports", [])
            else:
                logger.warning(f"No income statement data for {symbol}")

            # Get balance sheet
            balance_params = {
                "function": "BALANCE_SHEET",
                "symbol": symbol,
                "apikey": self.api_key,
            }
            balance_response = requests.get(
                self.BASE_URL, params=balance_params, timeout=10
            )
            balance_response.raise_for_status()
            balance = balance_response.json()

            if "annualReports" in balance:
                result["balance_sheet"] = balance.get("annualReports", [])
            else:
                logger.warning(f"No balance sheet data for {symbol}")

            logger.info(f"Got fundamentals for {symbol} ({len(result)} sections)")
            return result

        except Exception as e:
            logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
            return {}

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "name": "Alpha Vantage",
            "available": self.available,
            "api_key_set": bool(self.api_key),
            "library_available": REQUESTS_AVAILABLE,
            "rate_limit": "5 calls/min (free tier)",
            "daily_limit": "25 calls/day (free tier)",
        }
