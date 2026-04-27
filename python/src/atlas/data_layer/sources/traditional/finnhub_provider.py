"""
Finnhub Data Provider

Fetches real-time quotes, candles, news, sentiment, and recommendations
from the Finnhub API. Uses requests library directly.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import os
from typing import Optional, Dict, List, Any

import pandas as pd

logger = logging.getLogger("atlas.data_layer.finnhub_provider")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class FinnhubProvider:
    """
    Fetches financial data from Finnhub API.

    Provides real-time quotes, candles, news, sentiment, and recommendations.
    Requires FINNHUB_API_KEY environment variable.

    Example::

        provider = FinnhubProvider()
        if provider.available:
            quote = provider.get_quote("AAPL")
            candles = provider.get_candles("AAPL", "D", 1704067200, 1704153600)
            news = provider.get_news(category="forex")
            sentiment = provider.get_sentiment("AAPL")
    """

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self):
        """Initialize Finnhub provider with API key from environment"""
        self.available = False
        self.api_key = os.environ.get("FINNHUB_API_KEY")

        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not found in environment")
            return

        if not REQUESTS_AVAILABLE:
            logger.warning("requests not installed. Install with: pip install requests")
            return

        self.available = True
        logger.info("Finnhub provider initialized")

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """
        Make authenticated request to Finnhub API.

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters

        Returns:
            JSON response or None on failure
        """
        if params is None:
            params = {}

        params["token"] = self.api_key

        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Finnhub API request failed ({endpoint}): {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time quote data.

        Args:
            symbol: Stock symbol (e.g., "AAPL")

        Returns:
            Dict with keys: c (price), h (high), l (low), o (open),
            pc (previous close), t (timestamp).
            Returns None on failure.

        Example::

            quote = provider.get_quote("AAPL")
            # Returns:
            # {
            #     "c": 150.25,
            #     "h": 151.50,
            #     "l": 149.75,
            #     "o": 150.00,
            #     "pc": 149.50,
            #     "t": 1234567890
            # }
        """
        if not self.available:
            logger.warning("Finnhub provider not available")
            return None

        try:
            data = self._make_request("quote", {"symbol": symbol})

            if data is None:
                return None

            if "error" in data:
                logger.warning(f"Finnhub error for {symbol}: {data['error']}")
                return None

            logger.info(f"Got quote for {symbol}: {data.get('c', 'N/A')}")
            return data

        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None

    def get_candles(
        self,
        symbol: str,
        resolution: str,
        from_ts: int,
        to_ts: int,
    ) -> pd.DataFrame:
        """
        Get historical candles.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            resolution: Bar resolution ("1", "5", "15", "30", "60", "D", "W", "M")
            from_ts: From timestamp (Unix seconds)
            to_ts: To timestamp (Unix seconds)

        Returns:
            DataFrame with columns [open, high, low, close, volume].
            Returns empty DataFrame on failure.

        Example::

            df = provider.get_candles("AAPL", "D", 1704067200, 1704153600)
        """
        if not self.available:
            logger.warning("Finnhub provider not available")
            return pd.DataFrame()

        try:
            params = {
                "symbol": symbol,
                "resolution": resolution,
                "from": from_ts,
                "to": to_ts,
            }

            data = self._make_request("stock/candle", params)

            if data is None or "o" not in data:
                logger.warning(f"No candle data for {symbol}")
                return pd.DataFrame()

            # Build DataFrame
            df = pd.DataFrame(
                {
                    "open": data.get("o", []),
                    "high": data.get("h", []),
                    "low": data.get("l", []),
                    "close": data.get("c", []),
                    "volume": data.get("v", []),
                },
                index=pd.to_datetime(data.get("t", []), unit="s"),
            )

            df.index.name = "timestamp"
            df = df.sort_index()

            logger.info(f"Got {len(df)} candles for {symbol} ({resolution})")
            return df

        except Exception as e:
            logger.error(f"Failed to get candles for {symbol}: {e}")
            return pd.DataFrame()

    def get_news(
        self,
        category: str = "general",
        min_id: int = 0,
    ) -> List[Dict]:
        """
        Get news articles.

        Args:
            category: News category ("general", "forex", "crypto", "merger")
            min_id: Minimum article ID to return

        Returns:
            List of news articles with keys: headline, summary, source, etc.
            Returns empty list on failure.

        Example::

            news = provider.get_news(category="general")
            for article in news:
                print(f"{article['headline']} ({article['source']})")
        """
        if not self.available:
            logger.warning("Finnhub provider not available")
            return []

        try:
            params = {
                "category": category,
                "minId": min_id,
            }

            data = self._make_request("news", params)

            if data is None:
                return []

            articles = data.get("news", [])
            logger.info(f"Got {len(articles)} news articles for category {category}")
            return articles

        except Exception as e:
            logger.error(f"Failed to get news for category {category}: {e}")
            return []

    def get_company_news(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
    ) -> List[Dict]:
        """
        Get company-specific news.

        Args:
            symbol: Stock symbol (e.g., "AAPL")
            from_date: From date in YYYY-MM-DD format
            to_date: To date in YYYY-MM-DD format

        Returns:
            List of news articles.
            Returns empty list on failure.
        """
        if not self.available:
            logger.warning("Finnhub provider not available")
            return []

        try:
            params = {
                "symbol": symbol,
                "from": from_date,
                "to": to_date,
            }

            data = self._make_request("company-news", params)

            if data is None:
                return []

            articles = data if isinstance(data, list) else data.get("news", [])
            logger.info(
                f"Got {len(articles)} news articles for {symbol} "
                f"({from_date} to {to_date})"
            )
            return articles

        except Exception as e:
            logger.error(f"Failed to get company news for {symbol}: {e}")
            return []

    def get_sentiment(self, symbol: str) -> Optional[Dict]:
        """
        Get sentiment data for a symbol.

        Args:
            symbol: Stock symbol (e.g., "AAPL")

        Returns:
            Dict with sentiment metrics (bullish, bearish, neutral percentages).
            Returns None on failure.

        Example::

            sentiment = provider.get_sentiment("AAPL")
            # Returns:
            # {
            #     "symbol": "AAPL",
            #     "sentiment": {
            #         "bullish": 0.65,
            #         "bearish": 0.25,
            #         "neutral": 0.10
            #     },
            #     "data": [...]
            # }
        """
        if not self.available:
            logger.warning("Finnhub provider not available")
            return None

        try:
            data = self._make_request("stock/insider-sentiment", {"symbol": symbol})

            if data is None:
                return None

            logger.info(f"Got sentiment data for {symbol}")
            return data

        except Exception as e:
            logger.error(f"Failed to get sentiment for {symbol}: {e}")
            return None

    def get_recommendation(self, symbol: str) -> List[Dict]:
        """
        Get analyst recommendations.

        Args:
            symbol: Stock symbol (e.g., "AAPL")

        Returns:
            List of recommendation records with buy/hold/sell counts.
            Returns empty list on failure.

        Example::

            recs = provider.get_recommendation("AAPL")
            for rec in recs:
                print(f"{rec['symbol']}: {rec['buy']} buy, {rec['hold']} hold, {rec['sell']} sell")
        """
        if not self.available:
            logger.warning("Finnhub provider not available")
            return []

        try:
            data = self._make_request("stock/recommendation", {"symbol": symbol})

            if data is None:
                return []

            recs = data if isinstance(data, list) else []
            logger.info(f"Got {len(recs)} recommendation records for {symbol}")
            return recs

        except Exception as e:
            logger.error(f"Failed to get recommendations for {symbol}: {e}")
            return []

    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "name": "Finnhub",
            "available": self.available,
            "api_key_set": bool(self.api_key),
            "library_available": REQUESTS_AVAILABLE,
        }
