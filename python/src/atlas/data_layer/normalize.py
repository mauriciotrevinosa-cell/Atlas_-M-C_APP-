"""
Data Normalization
==================
Standardize OHLCV DataFrames from any provider into a consistent format.

All data that flows through Atlas passes through these functions.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.data_layer")

# Standard column names used throughout Atlas
STANDARD_COLUMNS = ["open", "high", "low", "close", "volume"]


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize any OHLCV DataFrame to Atlas standard format.

    Steps:
      1. Lowercase all column names
      2. Map common aliases (e.g. "adj close" → "close")
      3. Ensure required columns exist
      4. Convert index to DatetimeIndex
      5. Sort by date ascending
      6. Remove timezone info (store as UTC-naive)
      7. Forward-fill small gaps (≤3 rows)
      8. Drop leading NaNs
      9. Cast numeric types

    Args:
        df: Raw DataFrame from any provider

    Returns:
        Cleaned DataFrame with columns: open, high, low, close, volume
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=STANDARD_COLUMNS)

    result = df.copy()

    # --- Step 1: Lowercase columns ---
    result.columns = [c.strip().lower() for c in result.columns]

    # --- Step 2: Map common aliases ---
    alias_map = {
        "adj close": "close",
        "adjclose": "close",
        "adj_close": "close",
        "vol": "volume",
        "vol.": "volume",
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
    }
    result.rename(columns=alias_map, inplace=True)

    # If both "close" and original close exist after rename, drop duplicate
    result = result.loc[:, ~result.columns.duplicated(keep="last")]

    # --- Step 3: Validate required columns ---
    missing = [c for c in STANDARD_COLUMNS if c not in result.columns]
    if missing:
        raise ValueError(
            f"Missing required columns after normalization: {missing}. "
            f"Available: {list(result.columns)}"
        )

    # Keep only standard columns (drop extras like dividends, stock splits)
    result = result[STANDARD_COLUMNS]

    # --- Step 4: DatetimeIndex ---
    if not isinstance(result.index, pd.DatetimeIndex):
        # Try to convert the index
        try:
            result.index = pd.to_datetime(result.index)
        except Exception:
            # Maybe date is a column, not the index
            for candidate in ["date", "datetime", "timestamp", "time"]:
                if candidate in result.columns:
                    result.index = pd.to_datetime(result[candidate])
                    result.drop(columns=[candidate], inplace=True)
                    break
            else:
                raise ValueError("Cannot determine date column or index")

    result.index.name = "date"

    # --- Step 5: Sort ascending ---
    result.sort_index(inplace=True)

    # --- Step 6: Remove timezone ---
    if result.index.tz is not None:
        result.index = result.index.tz_localize(None)

    # --- Step 7: Forward-fill small gaps ---
    result = result.ffill(limit=3)

    # --- Step 8: Drop leading NaNs ---
    first_valid = result.first_valid_index()
    if first_valid is not None:
        result = result.loc[first_valid:]

    # --- Step 9: Cast numeric ---
    for col in STANDARD_COLUMNS:
        result[col] = pd.to_numeric(result[col], errors="coerce")

    # Volume should be integer-like
    result["volume"] = result["volume"].fillna(0).astype(np.int64)

    logger.debug(
        "Normalized: %d rows, %s → %s",
        len(result),
        result.index.min(),
        result.index.max(),
    )

    return result


def add_returns(
    df: pd.DataFrame,
    column: str = "close",
    method: str = "log",
) -> pd.DataFrame:
    """
    Append a 'returns' column to the DataFrame.

    Args:
        df:     OHLCV DataFrame
        column: Column to compute returns on (default: "close")
        method: "log" for log returns, "simple" for percentage returns

    Returns:
        DataFrame with added 'returns' column
    """
    result = df.copy()

    if method == "log":
        result["returns"] = np.log(result[column] / result[column].shift(1))
    elif method == "simple":
        result["returns"] = result[column].pct_change()
    else:
        raise ValueError(f"Unknown method: {method}. Use 'log' or 'simple'")

    return result


def align_timeframe(
    df: pd.DataFrame,
    target: str = "1D",
) -> pd.DataFrame:
    """
    Resample OHLCV data to a different timeframe.

    Args:
        df:     Normalized OHLCV DataFrame
        target: Pandas frequency string — "1D", "1W", "1h", "4h", etc.

    Returns:
        Resampled DataFrame
    """
    resampled = df.resample(target).agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    })

    return resampled.dropna(subset=["open", "close"])
