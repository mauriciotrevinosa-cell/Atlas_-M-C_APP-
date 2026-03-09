"""
Polygon.io Data Provider

Provider para datos profesionales con fallback seguro a Yahoo cuando no hay
credenciales o el request falla.

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import os

import pandas as pd

from ..base import DataProvider
from ..normalization.normalizer import DataNormalizer
from ..quality.validator import DataValidator
from .traditional.polygon_provider import PolygonProvider as PolygonRESTProvider
from .yahoo import YahooProvider

logger = logging.getLogger("atlas.data_layer")


class PolygonProvider(DataProvider):
    """
    Polygon provider with graceful fallback behavior.

    Primary path:
      - Polygon REST API via `POLYGON_API_KEY`

    Fallback path:
      - Yahoo provider when Polygon is unavailable and fallback is allowed.
    """

    version = "1.1.0"
    supported_assets = ["stocks", "indices", "forex", "crypto"]

    def __init__(self, api_key: str | None = None, allow_yahoo_fallback: bool = True):
        self.api_key = api_key or os.getenv("POLYGON_API_KEY")
        self.allow_yahoo_fallback = allow_yahoo_fallback
        self._last_source = "polygon"
        self._backend: PolygonRESTProvider | None = None

        if self.api_key:
            self._backend = PolygonRESTProvider(api_key=self.api_key)
        else:
            logger.warning(
                "PolygonProvider initialized without API key. "
                "Set POLYGON_API_KEY or use fallback."
            )

    def download(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        """Download historical data from Polygon or fallback provider."""
        if self._backend is not None:
            try:
                data = self._backend.get_historical_data(
                    symbol=symbol,
                    start_date=start,
                    end_date=end,
                    interval=interval,
                )
                if data is not None and not data.empty:
                    self._last_source = "polygon"
                    return self._to_legacy_ohlcv(data)
            except Exception as exc:
                logger.warning("Polygon request failed (%s).", exc)

        if not self.allow_yahoo_fallback:
            raise RuntimeError(
                "Polygon data request failed and fallback is disabled. "
                "Provide POLYGON_API_KEY or enable fallback."
            )

        yahoo = YahooProvider()
        fallback = yahoo.download(symbol, start, end, interval=interval)
        self._last_source = "yahoo-fallback"
        return self._to_legacy_ohlcv(fallback)

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
            "name": "Polygon.io",
            "version": self.version,
            "supported_assets": self.supported_assets,
            "api_key_required": True,
            "api_key_configured": bool(self.api_key),
            "fallback_enabled": self.allow_yahoo_fallback,
            "last_source": self._last_source,
        }

    @staticmethod
    def _to_legacy_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
        mapped = data.rename(
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
        return mapped[expected]
