"""
AtlasDataHandler — Phase 1 Data Layer

Inspired by Microsoft Qlib's DataHandlerLP pattern (MIT License).
Implements three data keys to prevent train/inference data leakage:

  DK_R = "raw"    → Raw OHLCV exactly as fetched from source
  DK_I = "infer"  → Normalized + derived features, ready for inference
  DK_L = "learn"  → DK_I + forward return label column for ML training

Data flow:
  Source → store() → DK_R cache
  fetch(DK_R) → raw DataFrame
  fetch(DK_I) → normalize + add derived features
  fetch(DK_L) → DK_I + forward return label (tail NaNs dropped)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Optional

from atlas.data_layer.cache_store import CacheStore
from atlas.data_layer.normalize import normalize_data


class AtlasDataHandler:
    """
    Central data access layer for Atlas.

    Provides a unified interface to fetch market data at three levels of
    processing, following the Qlib DK_R / DK_I / DK_L convention.

    Example::

        handler = AtlasDataHandler()

        # Store raw OHLCV (e.g. from Yahoo Finance)
        handler.store("BTC-USD", raw_df)

        # Inference-ready features
        df = handler.fetch("BTC-USD", data_key=AtlasDataHandler.DK_I)

        # ML training set with labels
        train = handler.fetch(
            "BTC-USD",
            data_key=AtlasDataHandler.DK_L,
            start="2022-01-01",
            end="2024-01-01",
        )
    """

    # ── Data key constants ────────────────────────────────────────────────────
    DK_R = "raw"    # Raw OHLCV — no transformation
    DK_I = "infer"  # Normalized + derived features — inference ready
    DK_L = "learn"  # DK_I + forward-return label — ML training ready

    def __init__(
        self,
        cache_dir: str = "data/cache",
        label_horizon: int = 5,
        label_col: str = "label",
    ):
        """
        Args:
            cache_dir:      Directory for Parquet cache files.
            label_horizon:  Number of bars ahead used for the forward-return
                            label added in DK_L.
            label_col:      Name given to the label column in DK_L.
        """
        self.cache = CacheStore(cache_dir)
        self.label_horizon = label_horizon
        self.label_col = label_col

    # ── Public API ────────────────────────────────────────────────────────────

    def fetch(
        self,
        symbol: str,
        data_key: str = DK_I,
        start: Optional[str] = None,
        end: Optional[str] = None,
        source_data: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Fetch data at the requested processing level.

        Args:
            symbol:      Asset ticker, e.g. "BTC-USD" or "AAPL".
            data_key:    One of DK_R / DK_I / DK_L.
            start:       Optional start date "YYYY-MM-DD".
            end:         Optional end date   "YYYY-MM-DD".
            source_data: If provided, uses this DataFrame as raw data instead
                         of loading from cache. Useful for streaming / testing.

        Returns:
            pd.DataFrame indexed by datetime at the requested level.

        Raises:
            ValueError: Unknown data_key or missing data for symbol.
        """
        if data_key not in (self.DK_R, self.DK_I, self.DK_L):
            raise ValueError(
                f"Unknown data_key '{data_key}'. "
                f"Use AtlasDataHandler.DK_R / DK_I / DK_L."
            )

        # Load or use provided raw data
        if source_data is not None:
            raw = source_data.copy()
        else:
            raw = self._load_raw(symbol)
            if raw is None:
                raise ValueError(
                    f"No cached data for '{symbol}'. "
                    "Call handler.store(symbol, df) first."
                )

        # Date slice is applied at raw level before any transformation
        raw = self._slice_dates(raw, start, end)

        if data_key == self.DK_R:
            return raw

        infer = self._build_infer(raw)

        if data_key == self.DK_I:
            return infer

        # DK_L: add labels on top of infer
        return self._build_learn(infer)

    def store(self, symbol: str, df: pd.DataFrame) -> None:
        """
        Persist raw OHLCV data to cache.

        Args:
            symbol: Asset ticker.
            df:     Raw OHLCV DataFrame. Must contain open/high/low/close/volume.
        """
        key = self._cache_key(symbol, self.DK_R)
        # Light normalize before caching (lowercase cols, datetime index)
        self.cache.set(key, normalize_data(df.copy()))

    def list_cached(self) -> List[str]:
        """Return list of symbols currently in cache."""
        parquets = list(Path(self.cache.cache_dir).glob("*_raw.parquet"))
        return [p.stem.replace("_raw", "").replace("_", "-").upper() for p in parquets]

    # ── Internal transforms ───────────────────────────────────────────────────

    def _load_raw(self, symbol: str) -> Optional[pd.DataFrame]:
        key = self._cache_key(symbol, self.DK_R)
        return self.cache.get(key)

    def _build_infer(self, raw: pd.DataFrame) -> pd.DataFrame:
        """
        Raw → Infer transformation.

        Added columns:
          log_return  — log(close_t / close_{t-1}), more stationary than price
          volume_z    — rolling 20-bar z-score of volume
          hl_range    — (high - low) / close, volatility proxy
        """
        df = normalize_data(raw.copy())

        # Log returns
        df["log_return"] = np.log(df["close"] / df["close"].shift(1))

        # Volume z-score (20-bar rolling)
        vol_roll = df["volume"].rolling(20)
        df["volume_z"] = (df["volume"] - vol_roll.mean()) / vol_roll.std().replace(0, 1)

        # High-low range as fraction of close
        df["hl_range"] = (df["high"] - df["low"]) / df["close"]

        # Drop NaN rows introduced by rolling / shift
        return df.dropna()

    def _build_learn(self, infer: pd.DataFrame) -> pd.DataFrame:
        """
        Infer → Learn transformation.

        Adds a forward log-return label over `label_horizon` bars.
        Rows at the tail where future prices don't exist are dropped.
        """
        df = infer.copy()
        df[self.label_col] = np.log(
            df["close"].shift(-self.label_horizon) / df["close"]
        )
        return df.dropna(subset=[self.label_col])

    @staticmethod
    def _slice_dates(
        df: pd.DataFrame,
        start: Optional[str],
        end: Optional[str],
    ) -> pd.DataFrame:
        if start:
            df = df[df.index >= pd.Timestamp(start)]
        if end:
            df = df[df.index <= pd.Timestamp(end)]
        return df

    @staticmethod
    def _cache_key(symbol: str, data_key: str) -> str:
        safe = symbol.replace("/", "_").replace("-", "_").lower()
        return f"{safe}_{data_key}"
