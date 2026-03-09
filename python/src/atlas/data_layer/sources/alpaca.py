"""
Alpaca Markets Data Provider

Provider para trading real-time con fallback seguro a Yahoo cuando faltan
credenciales o dependencia de Alpaca.

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import pandas as pd

from ..base import DataProvider
from ..normalization.normalizer import DataNormalizer
from ..quality.validator import DataValidator
from .yahoo import YahooProvider

logger = logging.getLogger("atlas.data_layer")


class AlpacaProvider(DataProvider):
    """
    Alpaca provider with optional fallback behavior.

    Primary path:
      - Alpaca API via `alpaca-py` + ALPACA_API_KEY/ALPACA_SECRET_KEY

    Fallback path:
      - Yahoo provider when Alpaca is unavailable and fallback is allowed.
    """

    version = "1.1.0"
    supported_assets = ["stocks"]

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        allow_yahoo_fallback: bool = True,
    ):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.api_secret = api_secret or os.getenv("ALPACA_SECRET_KEY")
        self.allow_yahoo_fallback = allow_yahoo_fallback
        self._client: Any | None = None
        self._StockBarsRequest: Any | None = None
        self._TimeFrame: Any | None = None
        self._last_source = "alpaca"
        self._init_client()

    def _init_client(self) -> None:
        if not (self.api_key and self.api_secret):
            logger.warning(
                "AlpacaProvider initialized without credentials. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY or use fallback."
            )
            return

        try:
            from alpaca.data import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
        except ImportError:
            logger.warning("alpaca-py is not installed; using fallback path when needed.")
            return

        self._client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.api_secret,
        )
        self._StockBarsRequest = StockBarsRequest
        self._TimeFrame = TimeFrame

    def download(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        """Download historical data from Alpaca or fallback provider."""
        if self._client and self._StockBarsRequest and self._TimeFrame:
            try:
                timeframe = self._map_timeframe(interval)
                request = self._StockBarsRequest(
                    symbol_or_symbols=symbol,
                    start=start,
                    end=end,
                    timeframe=timeframe,
                )
                bars = self._client.get_stock_bars(request)
                frame = getattr(bars, "df", pd.DataFrame())
                if frame is not None and not frame.empty:
                    self._last_source = "alpaca"
                    return self._to_legacy_ohlcv(frame, symbol=symbol)
            except Exception as exc:
                logger.warning("Alpaca request failed (%s).", exc)

        if not self.allow_yahoo_fallback:
            raise RuntimeError(
                "Alpaca data request failed and fallback is disabled. "
                "Configure alpaca-py + credentials or enable fallback."
            )

        yahoo = YahooProvider()
        fallback = yahoo.download(symbol, start, end, interval=interval)
        self._last_source = "yahoo-fallback"
        return self._to_legacy_ohlcv(fallback, symbol=symbol)

    def validate(self, data: pd.DataFrame) -> dict:
        """Validate data quality using Atlas validator."""
        normalized_cols = data.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        return DataValidator().validate(normalized_cols)

    def normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize data format to Atlas standard."""
        return DataNormalizer.to_atlas_format(data, provider=self._last_source)

    def get_info(self) -> dict:
        return {
            "name": "Alpaca Markets",
            "version": self.version,
            "supported_assets": self.supported_assets,
            "api_key_required": True,
            "credentials_configured": bool(self.api_key and self.api_secret),
            "fallback_enabled": self.allow_yahoo_fallback,
            "last_source": self._last_source,
        }

    def _map_timeframe(self, interval: str):
        tf = self._TimeFrame
        mapping = {
            "1m": tf.Minute,
            "5m": tf(5, tf.Unit.Minute),
            "15m": tf(15, tf.Unit.Minute),
            "1h": tf.Hour,
            "1d": tf.Day,
        }
        return mapping.get(interval, tf.Day)

    @staticmethod
    def _to_legacy_ohlcv(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        frame = data.copy()

        # Alpaca bars commonly come as MultiIndex(symbol, timestamp).
        if isinstance(frame.index, pd.MultiIndex):
            if "symbol" in frame.index.names:
                try:
                    frame = frame.xs(symbol, level="symbol")
                except KeyError:
                    frame = frame.droplevel(0)
            else:
                frame = frame.droplevel(0)

        if not isinstance(frame.index, pd.DatetimeIndex):
            if "timestamp" in frame.columns:
                frame["timestamp"] = pd.to_datetime(frame["timestamp"])
                frame = frame.set_index("timestamp")
            else:
                frame.index = pd.to_datetime(frame.index)

        mapped = frame.rename(
            columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
            }
        ).copy()

        expected = ["Open", "High", "Low", "Close", "Volume"]
        for col in expected:
            if col not in mapped.columns:
                mapped[col] = pd.NA
        if isinstance(mapped.index, pd.DatetimeIndex) and mapped.index.tz is not None:
            mapped.index = mapped.index.tz_localize(None)
        mapped = mapped.sort_index()
        return mapped[expected]
