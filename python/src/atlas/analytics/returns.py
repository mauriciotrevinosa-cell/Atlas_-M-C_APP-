"""
Returns Computation
===================
Calculate log and simple returns for single and multi-asset datasets.

All functions are pure — they do not modify inputs.

Usage:
    from atlas.analytics.returns import log_returns, returns_matrix

    r = log_returns(df)                          # Series
    mat = returns_matrix({"AAPL": df1, "SPY": df2})  # DataFrame

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.analytics.returns")


def log_returns(
    df: pd.DataFrame,
    column: str = "close",
    dropna: bool = True,
) -> pd.Series:
    """
    Compute log (continuously compounded) returns.

    log_return[t] = ln(P[t] / P[t-1])

    Args:
        df:     Normalized OHLCV DataFrame with DatetimeIndex.
        column: Price column to use (default: "close").
        dropna: Drop the first NaN row (default: True).

    Returns:
        pd.Series with the same DatetimeIndex as df.
    """
    _require_column(df, column)
    r = np.log(df[column] / df[column].shift(1))
    r.name = f"{column}_log_return"
    return r.dropna() if dropna else r


def simple_returns(
    df: pd.DataFrame,
    column: str = "close",
    dropna: bool = True,
) -> pd.Series:
    """
    Compute simple (arithmetic) percentage returns.

    simple_return[t] = (P[t] - P[t-1]) / P[t-1]

    Args:
        df:     Normalized OHLCV DataFrame with DatetimeIndex.
        column: Price column (default: "close").
        dropna: Drop NaN first row.

    Returns:
        pd.Series.
    """
    _require_column(df, column)
    r = df[column].pct_change()
    r.name = f"{column}_simple_return"
    return r.dropna() if dropna else r


def returns_matrix(
    dfs: Dict[str, pd.DataFrame],
    method: str = "log",
    column: str = "close",
    dropna: bool = True,
) -> pd.DataFrame:
    """
    Build a returns matrix for multiple assets.

    Aligns all assets on their shared date range (inner join).

    Args:
        dfs:    Dict mapping ticker → OHLCV DataFrame.
        method: "log" or "simple".
        column: Price column (default: "close").
        dropna: Drop rows with any NaN (default: True).

    Returns:
        DataFrame with DatetimeIndex, columns = tickers.
        Returns empty DataFrame if dfs is empty.
    """
    if not dfs:
        return pd.DataFrame()

    if method not in ("log", "simple"):
        raise ValueError(f"method must be 'log' or 'simple', got '{method}'")

    fn = log_returns if method == "log" else simple_returns

    series_list = []
    for ticker, df in dfs.items():
        if df is None or df.empty:
            logger.warning("returns_matrix: empty DataFrame for %s — skipped", ticker)
            continue
        try:
            r = fn(df, column=column, dropna=False)
            r.name = ticker
            series_list.append(r)
        except (ValueError, KeyError) as e:
            logger.warning("returns_matrix: failed for %s — %s", ticker, e)

    if not series_list:
        return pd.DataFrame()

    mat = pd.concat(series_list, axis=1)

    if dropna:
        mat = mat.dropna()

    logger.debug(
        "returns_matrix: %d tickers, %d rows, %s → %s",
        len(mat.columns), len(mat),
        mat.index.min() if len(mat) else "–",
        mat.index.max() if len(mat) else "–",
    )

    return mat


def cumulative_returns(returns: pd.Series) -> pd.Series:
    """
    Compute cumulative returns from a returns series.

    Args:
        returns: Series of log or simple returns.

    Returns:
        Cumulative return series (as growth factor, e.g. 1.15 = +15%).
    """
    return (1 + returns).cumprod()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_column(df: pd.DataFrame, column: str) -> None:
    if df is None or df.empty:
        raise ValueError("DataFrame is empty")
    if column not in df.columns:
        raise ValueError(
            f"Column '{column}' not found. Available: {list(df.columns)}"
        )
