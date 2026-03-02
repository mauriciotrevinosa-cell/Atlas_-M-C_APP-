"""
Data Manager — Central Coordinator
===================================
Single entry point for all data operations in Atlas.
Orchestrates providers, cache, normalization, and validation.

Usage:
    dm = DataManager()
    df = dm.get_historical("AAPL", "2024-01-01", "2024-12-31")
    quote = dm.get_quote("AAPL")

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta  # Ensure dateutil is available or use simple math

import pandas as pd

from atlas.data_layer.cache_store import CacheStore
from atlas.data_layer.normalize import normalize_ohlcv, add_returns
from atlas.data_layer.quality.validator import DataValidator

logger = logging.getLogger("atlas.data_layer")


class DataManager:
    """
    Central data coordinator for Atlas.

    Responsibilities:
      - Route requests to the correct provider
      - Cache results to avoid redundant downloads
      - Normalize all data to standard OHLCV format
      - Validate data quality before returning

    Supported providers:
      - "yahoo"   → Yahoo Finance (free, ~15min delay)
      - "polygon"  → Polygon.io  (requires API key)
      - "ccxt"     → Crypto via CCXT (Binance, Bybit, etc.)
    """

    def __init__(
        self,
        default_provider: str = "yahoo",
        cache_dir: str = "data/cache",
        cache_ttl_hours: int = 24,
        enable_cache: bool = True,
        enable_validation: bool = True,
    ):
        self.default_provider = default_provider
        self.enable_cache = enable_cache
        self.enable_validation = enable_validation

        # Initialize subsystems
        self.cache = CacheStore(cache_dir=cache_dir, ttl_hours=cache_ttl_hours)
        self.validator = DataValidator()

        # Lazy-loaded providers (only instantiate when needed)
        self._providers: Dict[str, Any] = {}

        logger.info(
            "DataManager initialized | provider=%s cache=%s validation=%s",
            default_provider,
            enable_cache,
            enable_validation,
        )

    # ------------------------------------------------------------------
    # Provider management
    # ------------------------------------------------------------------

    def _get_provider(self, name: str):
        """Lazy-load and return a provider instance."""
        if name in self._providers:
            return self._providers[name]

        if name == "yahoo":
            from atlas.data_layer.sources.traditional.yahoo_provider import YahooFinanceProvider
            self._providers[name] = YahooFinanceProvider()

        elif name == "polygon":
            from atlas.data_layer.sources.traditional.polygon_provider import PolygonProvider
            self._providers[name] = PolygonProvider()

        elif name == "ccxt":
            from atlas.data_layer.sources.derivatives.ccxt_provider import CCXTProvider
            self._providers[name] = CCXTProvider()

        else:
            raise ValueError(
                f"Unknown provider: '{name}'. Available: yahoo, polygon, ccxt"
            )

        logger.info("Provider loaded: %s", name)
        return self._providers[name]

    def list_providers(self) -> List[str]:
        """Return names of available providers."""
        return ["yahoo", "polygon", "ccxt"]

    # ------------------------------------------------------------------
    # Helper: Date Resolution
    # ------------------------------------------------------------------

    def _resolve_timeframe(self, timeframe: str) -> Tuple[str, str]:
        """
        Resolve a text timeframe to start/end dates.
        Supported: "max", "ytd", "1d", "5d", "1mo", "3mo", "6mo", "1y", "5y", "10y"
        """
        today = datetime.now().date()
        end_str = today.strftime("%Y-%m-%d")
        
        tf = timeframe.lower().strip()
        
        if tf == "max":
            return "1980-01-01", end_str  # Arbitrary "max" start
        
        if tf == "ytd":
            start = date(today.year, 1, 1)
            return start.strftime("%Y-%m-%d"), end_str

        # Parse value and unit
        unit = tf[-1]
        val_str = tf[:-1]
        
        if tf.endswith("mo"):
            unit = "mo"
            val_str = tf[:-2]
            
        try:
            val = int(val_str)
        except ValueError:
            logger.warning(f"Invalid timeframe: {timeframe}, defaulting to 1y")
            val = 1
            unit = "y"

        if unit == "d":
            start = today - timedelta(days=val)
        elif unit == "w":
            start = today - timedelta(weeks=val)
        elif unit == "mo":
            # Approximate months
            start = today - timedelta(days=val*30) 
        elif unit == "y":
            # Approximate years
            start = today - timedelta(days=val*365)
        else:
            start = today - timedelta(days=365) # Default 1y
            
        return start.strftime("%Y-%m-%d"), end_str

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------

    def get_historical(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        timeframe: Optional[str] = None,
        interval: str = "1d",
        provider: Optional[str] = None,
        use_cache: Optional[bool] = None,
        add_returns_col: bool = False,
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.
        
        Can specify either (start_date, end_date) OR timeframe.
        
        Args:
            symbol:      Ticker symbol
            start_date:  "YYYY-MM-DD"
            end_date:    "YYYY-MM-DD"
            timeframe:   "1y", "ytd", "max", "5d", etc. (Overrides start/end if provided)
            interval:    "1d", "1h", etc.
            ...
        """
        # Resolve dates
        if timeframe:
            s_date, e_date = self._resolve_timeframe(timeframe)
        else:
            s_date = start_date
            e_date = end_date or datetime.now().strftime("%Y-%m-%d")
            
        if not s_date:
            raise ValueError("Must provide either 'start_date' or 'timeframe'")

        provider_name = provider or self.default_provider
        should_cache = use_cache if use_cache is not None else self.enable_cache

        # --- Cache lookup ---
        cache_key = f"{provider_name}_{symbol}_{s_date}_{e_date}_{interval}"

        if should_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT for %s", cache_key)
                return cached

        # --- Fetch from provider ---
        prov = self._get_provider(provider_name)
        logger.info(
            "Fetching %s from %s | %s -> %s @ %s",
            symbol, provider_name, s_date, e_date, interval,
        )

        raw_df = prov.get_historical_data(
            symbol=symbol,
            start_date=s_date,
            end_date=e_date,
            interval=interval,
        )

        if raw_df is None or raw_df.empty:
            logger.warning("No data returned for %s from %s", symbol, provider_name)
            return pd.DataFrame()

        # --- Normalize ---
        df = normalize_ohlcv(raw_df)

        if add_returns_col:
            df = add_returns(df)

        # --- Validate ---
        if self.enable_validation:
            report = self.validator.validate(df)
            if not report["is_valid"]:
                logger.warning(
                    "Data quality issues for %s: %s", symbol, report["issues"]
                )
            # We still return data even with warnings — caller decides

        # --- Cache store ---
        if should_cache:
            self.cache.set(cache_key, df)
            logger.debug("Cache SET for %s", cache_key)

        return df

    # ------------------------------------------------------------------
    # Real-time quotes
    # ------------------------------------------------------------------

    def get_quote(
        self,
        symbol: str,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get latest quote / price snapshot.

        Args:
            symbol:   Ticker symbol
            provider: Override default provider

        Returns:
            Dict with keys: symbol, price, bid, ask, volume, timestamp, provider
        """
        provider_name = provider or self.default_provider
        prov = self._get_provider(provider_name)

        logger.info("Quote request: %s via %s", symbol, provider_name)
        return prov.get_latest_quote(symbol)

    # ------------------------------------------------------------------
    # Validation shortcut
    # ------------------------------------------------------------------

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Run quality validation on any DataFrame."""
        return self.validator.validate(df)

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache. If pattern given, only matching keys."""
        self.cache.clear(pattern=pattern)
        logger.info("Cache cleared (pattern=%s)", pattern)

    def cache_stats(self) -> Dict[str, Any]:
        """Return cache usage statistics."""
        return self.cache.stats()
