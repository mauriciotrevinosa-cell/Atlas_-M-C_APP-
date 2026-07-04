"""
Yahoo Finance Data Provider (Traditional)
Phase 1.1 — Traditional Data Ingestion
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from ...normalize import normalize_data
from ...cache_store import CacheStore

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class YahooProvider:
    """
    Fetches OHLCV data from Yahoo Finance via yfinance.
    Normalizes output to Atlas standard format.
    Supports caching via CacheStore.
    """

    def __init__(self, cache: Optional[CacheStore] = None):
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance not installed. Run: pip install yfinance")
        self.cache = cache or CacheStore()

    def get_ohlcv(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        period: Optional[str] = None,
        interval: str = "1d",
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol.

        Args:
            symbol: Ticker symbol (e.g. 'AAPL', 'BTC-USD')
            start: Start date 'YYYY-MM-DD' (ignored if period given)
            end: End date 'YYYY-MM-DD' (defaults to today)
            period: yfinance period string ('1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','ytd','max')
            interval: Bar interval ('1m','5m','15m','30m','60m','1d','1wk','1mo')
            use_cache: Use local parquet cache

        Returns:
            Normalized OHLCV DataFrame with DatetimeIndex
        """
        cache_key = f"{symbol}_{period or f'{start}_{end}'}_{interval}"

        if use_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        ticker = yf.Ticker(symbol)

        if period:
            raw = ticker.history(period=period, interval=interval)
        else:
            if end is None:
                end = datetime.today().strftime("%Y-%m-%d")
            if start is None:
                start = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
            raw = ticker.history(start=start, end=end, interval=interval)

        if raw.empty:
            raise ValueError(f"No data returned for symbol '{symbol}'")

        # Rename columns to Atlas standard (lowercase)
        raw = raw.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })

        # Keep only OHLCV
        df = raw[["open", "high", "low", "close", "volume"]].copy()

        # Normalize (UTC index, NaN handling, etc.)
        df = normalize_data(df)

        if use_cache:
            self.cache.set(cache_key, df)

        return df

    def get_info(self, symbol: str) -> dict:
        """Return basic metadata for a symbol."""
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        return {
            "symbol": symbol,
            "name": info.get("longName", info.get("shortName", symbol)),
            "sector": info.get("sector", "Unknown"),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", "Unknown"),
        }
