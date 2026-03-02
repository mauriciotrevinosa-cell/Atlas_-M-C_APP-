"""
Yahoo Finance Provider
======================
Free provider for historical OHLCV data and delayed quotes.

Strengths:
  - Free, no API key required
  - Reliable for daily/weekly data
  - Covers equities, ETFs, indices, forex, crypto

Limitations:
  - ~15 minute delay on quotes
  - Rate limits (undocumented, ~2000 req/hour safe)
  - Intraday data limited to last 60 days

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pandas as pd

from atlas.interfaces.market_data import MarketDataProvider

logger = logging.getLogger("atlas.data_layer")


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance data provider via yfinance."""

    @property
    def name(self) -> str:
        return "yahoo"

    def __init__(self):
        try:
            import yfinance  # noqa: F401
        except ImportError:
            raise ImportError(
                "yfinance is required for Yahoo provider. "
                "Install with: pip install yfinance"
            )

    def get_historical_data(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None,
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV from Yahoo Finance.

        Args:
            symbol:     Ticker (e.g. "AAPL", "BTC-USD", "^SPX")
            start_date: "YYYY-MM-DD"
            end_date:   "YYYY-MM-DD" (default: today)
            interval:   "1m","5m","15m","30m","1h","1d","1wk","1mo"

        Returns:
            DataFrame with DatetimeIndex and OHLCV columns.
        """
        import yfinance as yf

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(
            "Yahoo: fetching %s | %s → %s @ %s", symbol, start_date, end_date, interval
        )

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=True,   # Use adjusted close as close
                actions=False,      # Skip dividends/splits columns
            )

            if df.empty:
                logger.warning("Yahoo: no data for %s in range %s→%s", symbol, start_date, end_date)
                return pd.DataFrame()

            logger.info("Yahoo: got %d rows for %s", len(df), symbol)
            return df

        except Exception as e:
            logger.error("Yahoo error for %s: %s", symbol, e)
            raise RuntimeError(f"Yahoo Finance fetch failed for {symbol}: {e}") from e

    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get delayed quote (~15min) from Yahoo Finance.

        Args:
            symbol: Ticker symbol

        Returns:
            Dict with: symbol, price, bid, ask, volume, timestamp, provider
        """
        import yfinance as yf

        try:
            ticker = yf.Ticker(symbol)

            # Fast method: use last 1-day 1-minute data
            recent = ticker.history(period="1d", interval="1m")

            if recent.empty:
                # Fallback: use daily
                recent = ticker.history(period="5d", interval="1d")

            if recent.empty:
                raise ValueError(f"No recent data available for {symbol}")

            last_row = recent.iloc[-1]

            # Try to get bid/ask from info (may fail)
            info = {}
            try:
                info = ticker.info or {}
            except Exception:
                pass

            return {
                "symbol": symbol,
                "price": round(float(last_row["Close"]), 4),
                "open": round(float(last_row["Open"]), 4),
                "high": round(float(last_row["High"]), 4),
                "low": round(float(last_row["Low"]), 4),
                "volume": int(last_row["Volume"]),
                "bid": float(info.get("bid", last_row["Close"])),
                "ask": float(info.get("ask", last_row["Close"])),
                "timestamp": str(last_row.name),
                "provider": self.name,
                "delay": "~15min",
            }

        except Exception as e:
            logger.error("Yahoo quote error for %s: %s", symbol, e)
            raise RuntimeError(f"Yahoo quote failed for {symbol}: {e}") from e

    def get_multiple(
        self,
        symbols: list,
        start_date: str,
        end_date: Optional[str] = None,
        interval: str = "1d",
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple symbols at once (more efficient).

        Args:
            symbols:    List of tickers ["AAPL", "MSFT", "GOOG"]
            start_date: "YYYY-MM-DD"
            end_date:   "YYYY-MM-DD"
            interval:   Candle interval

        Returns:
            Dict mapping symbol → DataFrame
        """
        import yfinance as yf

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        tickers_str = " ".join(symbols)
        logger.info("Yahoo: batch fetch %s", tickers_str)

        try:
            data = yf.download(
                tickers_str,
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=True,
                group_by="ticker",
                threads=True,
            )

            result = {}
            for sym in symbols:
                try:
                    if len(symbols) == 1:
                        sym_df = data
                    else:
                        sym_df = data[sym].dropna(how="all")
                    if not sym_df.empty:
                        result[sym] = sym_df
                except (KeyError, TypeError):
                    logger.warning("Yahoo batch: no data for %s", sym)

            return result

        except Exception as e:
            logger.error("Yahoo batch error: %s", e)
            raise RuntimeError(f"Yahoo batch fetch failed: {e}") from e
