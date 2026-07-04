"""
Unified DataProviderRegistry for Project Atlas

Manages multiple provider types with automatic fallback, rate limiting,
caching, and configuration from environment variables.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import re
import time
import threading
from collections import defaultdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timedelta, timezone

import pandas as pd

logger = logging.getLogger("atlas.data_layer.provider_registry")


class ProviderType(Enum):
    """Supported provider types"""
    MARKET_DATA = "market_data"
    MACRO = "macro"
    NEWS = "news"
    FILINGS = "filings"
    SENTIMENT = "sentiment"
    WEATHER = "weather"


class RateLimiter:
    """Simple thread-safe rate limiter"""

    def __init__(self, calls_per_minute: int):
        """
        Initialize rate limiter.

        Args:
            calls_per_minute: Maximum calls allowed per minute
        """
        self.calls_per_minute = calls_per_minute
        self.calls = []
        self.lock = threading.Lock()

    def wait_if_needed(self) -> None:
        """Block until rate limit allows another call"""
        with self.lock:
            now = time.time()
            cutoff = now - 60.0

            # Remove calls older than 1 minute
            self.calls = [t for t in self.calls if t > cutoff]

            if len(self.calls) >= self.calls_per_minute:
                sleep_time = 60.0 - (now - self.calls[0])
                if sleep_time > 0:
                    logger.debug(
                        f"Rate limiter: sleeping {sleep_time:.2f}s "
                        f"({len(self.calls)} calls in last minute)"
                    )
                    time.sleep(sleep_time)
                    now = time.time()

            self.calls.append(now)


class CacheEntry:
    """Cache entry with TTL"""

    def __init__(self, data: Any, ttl_seconds: int = 3600):
        """
        Initialize cache entry.

        Args:
            data: Data to cache
            ttl_seconds: Time-to-live in seconds (default 1 hour)
        """
        self.data = data
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.created_at > self.ttl_seconds


class DataProviderRegistry:
    """
    Unified registry for multiple data providers.

    Features:
    - Manages providers by type (MARKET_DATA, MACRO, NEWS, FILINGS, SENTIMENT)
    - Automatic fallback: if provider 1 fails, tries provider 2, etc.
    - Rate limiting per provider
    - Integrated caching (checks cache before API calls)
    - Configuration from environment variables
    - Logging of which provider served each request
    - Thread-safe operations

    Example::

        registry = DataProviderRegistry()

        # Get price data with automatic fallback
        df = registry.get_price("AAPL", "2024-01-01", "2024-12-31")

        # Get macro data
        macro = registry.get_macro("GDP")

        # Get news
        news = registry.get_news("technology")
    """

    def __init__(
        self,
        cache_ttl_seconds: int = 3600,
        auto_register_defaults: bool = True,
    ):
        """
        Initialize provider registry.

        Args:
            cache_ttl_seconds: Cache TTL in seconds (default 1 hour)
            auto_register_defaults: Register built-in providers automatically
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_lock = threading.Lock()

        # Provider registry: type -> [(provider_name, provider_instance, rate_limiter)]
        self.providers: Dict[ProviderType, List[tuple]] = defaultdict(list)

        # Request logging
        self.request_log: List[Dict] = []
        self.log_lock = threading.Lock()
        self._defaults_registered = False

        logger.info("DataProviderRegistry initialized")
        if auto_register_defaults:
            self.register_default_providers()

    def register_provider(
        self,
        provider_type: ProviderType,
        provider_name: str,
        provider_instance: Any,
        calls_per_minute: int = 60,
        priority: int = 0,
    ) -> None:
        """
        Register a provider.

        Args:
            provider_type: Type of provider (MARKET_DATA, MACRO, etc.)
            provider_name: Name of provider (FRED, AlphaVantage, etc.)
            provider_instance: Provider instance
            calls_per_minute: Rate limit (default 60)
            priority: Priority level (higher = tried first)
        """
        rate_limiter = RateLimiter(calls_per_minute)
        self.providers[provider_type].append(
            (provider_name, provider_instance, rate_limiter, priority)
        )

        # Sort by priority (descending)
        self.providers[provider_type].sort(key=lambda x: x[3], reverse=True)

        logger.info(
            f"Registered {provider_name} for {provider_type.value} "
            f"(priority={priority}, rate_limit={calls_per_minute}/min)"
        )

    def register_default_providers(self) -> int:
        """
        Register Atlas' built-in provider set once.

        Returns:
            Number of providers registered during this call.
        """
        if self._defaults_registered:
            return 0

        from atlas.data_layer.sources.traditional import (
            AlphaVantageProvider,
            BLSProvider,
            FREDProvider,
            FinnhubProvider,
            HuggingFaceProvider,
            IMFDataMapperProvider,
            NewsAPIProvider,
            SECEDGARProvider,
            TreasuryFiscalProvider,
            WorldBankProvider,
            YahooFinanceProvider,
        )
        from atlas.data_layer.sources.alternative import OpenMeteoProvider

        try:
            from atlas.data_layer.sources.traditional import PolygonProvider
        except ImportError:
            PolygonProvider = None

        registered = 0

        def _safe_register(
            provider_type: ProviderType,
            provider_name: str,
            provider_factory: Callable[[], Any],
            calls_per_minute: int,
            priority: int,
        ) -> None:
            nonlocal registered
            try:
                provider = provider_factory()
                self.register_provider(
                    provider_type=provider_type,
                    provider_name=provider_name,
                    provider_instance=provider,
                    calls_per_minute=calls_per_minute,
                    priority=priority,
                )
                registered += 1
            except Exception as exc:
                logger.warning("Could not initialize %s provider: %s", provider_name, exc)

        if PolygonProvider is not None:
            _safe_register(ProviderType.MARKET_DATA, "Polygon", PolygonProvider, 5, 100)
        _safe_register(ProviderType.MARKET_DATA, "Finnhub", FinnhubProvider, 60, 90)
        _safe_register(ProviderType.MARKET_DATA, "AlphaVantage", AlphaVantageProvider, 5, 80)
        _safe_register(ProviderType.MARKET_DATA, "YahooFinance", YahooFinanceProvider, 30, 10)

        _safe_register(ProviderType.MACRO, "FRED", FREDProvider, 120, 100)
        _safe_register(ProviderType.MACRO, "BLS", BLSProvider, 25, 80)
        _safe_register(ProviderType.MACRO, "WorldBank", WorldBankProvider, 60, 70)
        _safe_register(ProviderType.MACRO, "TreasuryFiscal", TreasuryFiscalProvider, 60, 60)
        _safe_register(ProviderType.MACRO, "IMFDataMapper", IMFDataMapperProvider, 60, 50)

        _safe_register(ProviderType.NEWS, "Finnhub", FinnhubProvider, 60, 100)
        _safe_register(ProviderType.NEWS, "NewsAPI", NewsAPIProvider, 30, 90)

        _safe_register(ProviderType.FILINGS, "SECEDGAR", SECEDGARProvider, 600, 100)

        _safe_register(ProviderType.SENTIMENT, "HuggingFace", HuggingFaceProvider, 30, 100)
        _safe_register(ProviderType.SENTIMENT, "Finnhub", FinnhubProvider, 60, 80)

        _safe_register(ProviderType.WEATHER, "OpenMeteo", OpenMeteoProvider, 60, 100)

        self._defaults_registered = True
        logger.info("Registered %d default providers", registered)
        return registered

    def get_price(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str = "1d",
    ) -> Optional[pd.DataFrame]:
        """
        Get price data with automatic fallback.

        Args:
            symbol: Ticker symbol
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            interval: Timeframe (1d, 1h, 5m, etc.)

        Returns:
            DataFrame with OHLCV data or None if all providers fail
        """
        cache_key = f"price:{symbol}:{start}:{end}:{interval}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        result = self._try_providers(
            ProviderType.MARKET_DATA,
            lambda p: self._get_market_data_from_provider(p, symbol, start, end, interval),
            f"price for {symbol}",
        )

        if result is not None:
            self._set_cache(cache_key, result)

        return result

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest quote data with automatic fallback.

        Args:
            symbol: Ticker symbol

        Returns:
            Normalized quote dict or None if all providers fail
        """
        cache_key = f"quote:{symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        result = self._try_providers(
            ProviderType.MARKET_DATA,
            lambda p: self._get_quote_from_provider(p, symbol),
            f"quote for {symbol}",
        )

        if result is not None:
            self._set_cache(cache_key, result)

        return result

    def get_macro(
        self,
        series_id: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Get macroeconomic data.

        Args:
            series_id: Series identifier (GDP, CPI, UNEMPLOYMENT, etc.)
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)

        Returns:
            DataFrame with macro data or None if all providers fail
        """
        cache_key = f"macro:{series_id}:{start}:{end}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        result = self._try_providers(
            ProviderType.MACRO,
            lambda p: p.get_series(series_id, start, end)
            if hasattr(p, "get_series")
            else None,
            f"macro data for {series_id}",
        )

        if result is not None:
            self._set_cache(cache_key, result)

        return result

    def get_news(
        self,
        query: Optional[str] = None,
        category: str = "general",
    ) -> Optional[List[Dict]]:
        """
        Get news articles.

        Args:
            query: Search query
            category: News category

        Returns:
            List of news articles or None if all providers fail
        """
        cache_key = f"news:{query}:{category}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        result = self._try_providers(
            ProviderType.NEWS,
            lambda p: self._get_news_from_provider(p, query, category),
            f"news for {query or category}",
        )

        if result is not None:
            self._set_cache(cache_key, result)

        return result

    def get_filings(
        self,
        ticker: str,
        filing_type: str = "10-K",
        count: int = 5,
    ) -> Optional[List[Dict]]:
        """
        Get SEC filings.

        Args:
            ticker: Stock ticker
            filing_type: Type of filing (10-K, 10-Q, 8-K, etc.)
            count: Number of filings to return

        Returns:
            List of filings or None if all providers fail
        """
        cache_key = f"filings:{ticker}:{filing_type}:{count}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        result = self._try_providers(
            ProviderType.FILINGS,
            lambda p: p.get_filings(ticker, filing_type, count)
            if hasattr(p, "get_filings")
            else None,
            f"filings for {ticker}",
        )

        if result is not None:
            self._set_cache(cache_key, result)

        return result

    def get_sentiment(
        self,
        symbol: Optional[str] = None,
        text: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Get sentiment data.

        Args:
            symbol: Stock symbol
            text: Text to analyze

        Returns:
            Sentiment data or None if all providers fail
        """
        key_param = symbol or text or "unknown"
        cache_key = f"sentiment:{key_param}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        if symbol:
            result = self._try_providers(
                ProviderType.SENTIMENT,
                lambda p: p.get_sentiment(symbol)
                if hasattr(p, "get_sentiment")
                else None,
                f"sentiment for {symbol}",
            )
        else:
            result = self._try_providers(
                ProviderType.SENTIMENT,
                lambda p: self._get_text_sentiment_from_provider(p, text),
                "text sentiment analysis",
            )

        if result is not None:
            self._set_cache(cache_key, result)

        return result

    def get_weather(
        self,
        latitude: float,
        longitude: float,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Get weather context data with automatic fallback.

        Args:
            latitude: WGS84 latitude
            longitude: WGS84 longitude
            start: Optional start date YYYY-MM-DD
            end: Optional end date YYYY-MM-DD

        Returns:
            DataFrame with weather variables or None if all providers fail
        """
        cache_key = f"weather:{latitude}:{longitude}:{start}:{end}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        result = self._try_providers(
            ProviderType.WEATHER,
            lambda p: p.get_weather(latitude, longitude, start=start, end=end)
            if hasattr(p, "get_weather")
            else None,
            f"weather for {latitude},{longitude}",
        )

        if result is not None:
            self._set_cache(cache_key, result)

        return result

    def _try_providers(
        self,
        provider_type: ProviderType,
        call_fn: Callable,
        description: str,
    ) -> Optional[Any]:
        """
        Try providers in priority order until one succeeds.

        Args:
            provider_type: Type of provider to use
            call_fn: Function that calls the provider
            description: Description for logging

        Returns:
            Result from first successful provider or None
        """
        if provider_type not in self.providers:
            logger.warning(f"No providers registered for {provider_type.value}")
            return None

        for provider_name, provider_instance, rate_limiter, _ in self.providers[
            provider_type
        ]:
            try:
                # Check if provider is available
                if hasattr(provider_instance, "available") and not provider_instance.available:
                    logger.debug(f"Provider {provider_name} not available (no API key)")
                    continue

                # Apply rate limit
                rate_limiter.wait_if_needed()

                # Call provider
                result = call_fn(provider_instance)

                # Empty frames/collections are not a successful answer. Treat
                # them as unavailable so lower-priority providers can supply
                # real data instead of silently stopping the fallback chain.
                is_empty = bool(getattr(result, "empty", False))
                if isinstance(result, (list, tuple, dict, set)):
                    is_empty = len(result) == 0

                if result is not None and not is_empty:
                    self._log_request(provider_name, description, success=True)
                    logger.info(
                        f"Got {description} from {provider_name}"
                    )
                    return result

                self._log_request(
                    provider_name,
                    description,
                    success=False,
                    error="provider returned no data",
                )

            except Exception as e:
                logger.warning(
                    f"Provider {provider_name} failed for {description}: {e}"
                )
                self._log_request(provider_name, description, success=False, error=str(e))

        logger.error(f"All providers failed for {description}")
        return None

    def _get_market_data_from_provider(
        self,
        provider: Any,
        symbol: str,
        start: str,
        end: str,
        interval: str,
    ) -> Optional[pd.DataFrame]:
        if hasattr(provider, "get_daily"):
            data = provider.get_daily(symbol, outputsize="full")
            return self._normalize_market_frame(data, start, end)

        if hasattr(provider, "get_candles"):
            resolution = self._resolve_candle_resolution(interval)
            from_ts = int(pd.Timestamp(start).timestamp())
            to_ts = int(pd.Timestamp(end).timestamp())
            data = provider.get_candles(symbol, resolution, from_ts, to_ts)
            return self._normalize_market_frame(data, start, end)

        if hasattr(provider, "get_historical_data"):
            data = provider.get_historical_data(symbol, start, end, interval)
            return self._normalize_market_frame(data, start, end)

        return None

    def _get_quote_from_provider(self, provider: Any, symbol: str) -> Optional[Dict[str, Any]]:
        provider_name = getattr(provider, "name", provider.__class__.__name__.replace("Provider", ""))

        if hasattr(provider, "get_quote"):
            quote = provider.get_quote(symbol)
            if not quote:
                return None

            if isinstance(quote, dict) and {"c", "h", "l", "o", "pc"}.intersection(quote):
                return {
                    "symbol": symbol.upper(),
                    "price": quote.get("c"),
                    "open": quote.get("o"),
                    "high": quote.get("h"),
                    "low": quote.get("l"),
                    "previous_close": quote.get("pc"),
                    "timestamp": quote.get("t"),
                    "provider": provider_name,
                }

            if isinstance(quote, dict):
                normalized = dict(quote)
                normalized.setdefault("symbol", symbol.upper())
                normalized.setdefault("provider", provider_name)
                return normalized

        if hasattr(provider, "get_latest_quote"):
            quote = provider.get_latest_quote(symbol)
            if isinstance(quote, dict) and quote:
                normalized = dict(quote)
                normalized.setdefault("symbol", symbol.upper())
                normalized.setdefault("provider", provider_name)
                return normalized

        return None

    def _get_news_from_provider(
        self,
        provider: Any,
        query: Optional[str],
        category: str,
    ) -> Optional[List[Dict[str, Any]]]:
        if hasattr(provider, "get_headlines"):
            return provider.get_headlines(query=query, category=category)

        if query and self._looks_like_symbol(query) and hasattr(provider, "get_company_news"):
            today = datetime.now(timezone.utc).date()
            from_date = (today - timedelta(days=7)).isoformat()
            return provider.get_company_news(query.upper(), from_date, today.isoformat())

        if hasattr(provider, "get_news"):
            return provider.get_news(category=category)

        return None

    def _get_text_sentiment_from_provider(
        self,
        provider: Any,
        text: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        if hasattr(provider, "analyze_financial_sentiment"):
            result = provider.analyze_financial_sentiment(text)
            if result is not None:
                return result

        if hasattr(provider, "analyze_sentiment"):
            return provider.analyze_sentiment(text)

        return None

    def _normalize_market_frame(
        self,
        data: Optional[pd.DataFrame],
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        if data is None or not isinstance(data, pd.DataFrame) or data.empty:
            return None

        df = data.copy()
        rename_map = {}
        for col in df.columns:
            key = str(col).strip().lower()
            if key in {"adj close", "adj_close"}:
                rename_map[col] = "close"
            elif key in {"open", "high", "low", "close", "volume"}:
                rename_map[col] = key

        df = df.rename(columns=rename_map)
        required = ["open", "high", "low", "close", "volume"]
        if not all(col in df.columns for col in required):
            return None

        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception:
                return None

        if start:
            df = df[df.index >= pd.Timestamp(start)]
        if end:
            df = df[df.index <= pd.Timestamp(end)]

        if df.empty:
            return None

        return df[required].sort_index()

    @staticmethod
    def _resolve_candle_resolution(interval: str) -> str:
        mapping = {
            "1m": "1",
            "5m": "5",
            "15m": "15",
            "30m": "30",
            "1h": "60",
            "1d": "D",
            "1wk": "W",
            "1mo": "M",
        }
        return mapping.get(interval, "D")

    @staticmethod
    def _looks_like_symbol(value: Optional[str]) -> bool:
        if not value or " " in value.strip():
            return False
        return bool(re.fullmatch(r"[A-Za-z0-9\-\.\^=]{1,15}", value.strip()))

    def _get_cache(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        with self.cache_lock:
            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    return entry.data
                else:
                    del self.cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Set cache value"""
        with self.cache_lock:
            self.cache[key] = CacheEntry(value, self.cache_ttl_seconds)

    def _log_request(
        self,
        provider_name: str,
        description: str,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Log a provider request"""
        with self.log_lock:
            self.request_log.append(
                {
                    "timestamp": datetime.now(timezone.utc),
                    "provider": provider_name,
                    "description": description,
                    "success": success,
                    "error": error,
                }
            )

    def get_request_log(self, limit: int = 100) -> List[Dict]:
        """Get request log (most recent first)"""
        with self.log_lock:
            return self.request_log[-limit:][::-1]

    def clear_cache(self, key_prefix: Optional[str] = None) -> int:
        """
        Clear cache.

        Args:
            key_prefix: If provided, only clear keys starting with this prefix

        Returns:
            Number of entries cleared
        """
        with self.cache_lock:
            if key_prefix is None:
                count = len(self.cache)
                self.cache.clear()
                return count

            keys_to_delete = [k for k in self.cache.keys() if k.startswith(key_prefix)]
            for k in keys_to_delete:
                del self.cache[k]
            return len(keys_to_delete)

    def get_provider_info(self) -> Dict[str, Any]:
        """Get info about registered providers"""
        info = {}
        for provider_type, providers in self.providers.items():
            info[provider_type.value] = [
                {
                    "name": name,
                    "available": getattr(provider, "available", True),
                    "priority": priority,
                }
                for name, provider, _, priority in providers
            ]
        return info


# Module-level singleton
_registry: Optional[DataProviderRegistry] = None


def get_registry(cache_ttl_seconds: int = 3600) -> DataProviderRegistry:
    """
    Get or create the module-level shared registry.

    Args:
        cache_ttl_seconds: Cache TTL in seconds

    Returns:
        Shared DataProviderRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = DataProviderRegistry(cache_ttl_seconds=cache_ttl_seconds)
    return _registry
