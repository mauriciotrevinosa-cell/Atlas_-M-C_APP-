"""
Correlation Analytics
=====================
Rolling and static correlation for multi-asset portfolios.

Supports:
  - Rolling pairwise correlation over time
  - Static correlation matrix (full period)
  - Heatmap-ready data extraction

Usage:
    from atlas.analytics.correlation import static_correlation, heatmap_data

    mat = static_correlation(returns_df)   # n×n correlation matrix
    hm  = heatmap_data(mat)               # list of (row, col, value) triples

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from atlas.analytics.returns import returns_matrix

logger = logging.getLogger("atlas.analytics.correlation")


def static_correlation(
    returns_df: pd.DataFrame,
    method: str = "pearson",
    min_periods: int = 30,
) -> pd.DataFrame:
    """
    Full-period correlation matrix for a returns DataFrame.

    Args:
        returns_df:  DataFrame with columns = tickers, rows = dates.
                     Typically output of returns_matrix().
        method:      Correlation method: "pearson", "spearman", or "kendall".
        min_periods: Minimum observations required for a valid value.

    Returns:
        Symmetric n×n correlation matrix (DataFrame).
        Values in [-1, 1]. NaN if insufficient data.
    """
    if returns_df.empty:
        return pd.DataFrame()

    corr = returns_df.corr(method=method, min_periods=min_periods)

    logger.debug(
        "static_correlation: %d assets | %d rows | method=%s",
        len(corr), len(returns_df), method,
    )
    return corr


def rolling_correlation(
    returns_df: pd.DataFrame,
    window: int = 63,
    method: str = "pearson",
    pair: Optional[Tuple[str, str]] = None,
) -> pd.DataFrame:
    """
    Rolling pairwise correlation over time.

    If `pair` is given, returns a single-column DataFrame for that pair.
    Otherwise, returns ALL unique pairs stacked as columns.

    Args:
        returns_df: Multi-asset returns DataFrame (tickers as columns).
        window:     Rolling window in bars (default: 63 trading days ≈ 1 quarter).
        method:     Correlation method ("pearson" | "spearman").
        pair:       Optional (ticker_a, ticker_b) — compute only this pair.

    Returns:
        DataFrame with DatetimeIndex. Columns are "A_vs_B" pair labels.
    """
    if returns_df.empty or len(returns_df.columns) < 2:
        return pd.DataFrame()

    tickers = list(returns_df.columns)
    result_series: Dict[str, pd.Series] = {}

    if pair:
        a, b = pair
        if a not in tickers or b not in tickers:
            raise ValueError(f"Pair tickers not in data: {pair}. Available: {tickers}")
        label = f"{a}_vs_{b}"
        result_series[label] = (
            returns_df[a]
            .rolling(window=window, min_periods=window // 2)
            .corr(returns_df[b])
        )

    else:
        # All unique pairs
        for i, a in enumerate(tickers):
            for b in tickers[i + 1:]:
                label = f"{a}_vs_{b}"
                result_series[label] = (
                    returns_df[a]
                    .rolling(window=window, min_periods=window // 2)
                    .corr(returns_df[b])
                )

    if not result_series:
        return pd.DataFrame()

    out = pd.concat(result_series, axis=1)
    logger.debug(
        "rolling_correlation: %d pairs | window=%d | %d rows",
        len(out.columns), window, len(out),
    )
    return out


def heatmap_data(
    corr_matrix: pd.DataFrame,
    round_digits: int = 4,
) -> List[Dict]:
    """
    Convert correlation matrix to a list of records for heatmap rendering.

    Each record: {"row": str, "col": str, "value": float}

    Args:
        corr_matrix:  Square correlation DataFrame.
        round_digits: Decimal places for values.

    Returns:
        List of dicts suitable for plotting or JSON serialization.
    """
    if corr_matrix.empty:
        return []

    records = []
    for row_label in corr_matrix.index:
        for col_label in corr_matrix.columns:
            val = corr_matrix.loc[row_label, col_label]
            if pd.notna(val):
                records.append({
                    "row":   str(row_label),
                    "col":   str(col_label),
                    "value": round(float(val), round_digits),
                })

    return records


def cross_asset_correlation_from_dfs(
    dfs: Dict[str, pd.DataFrame],
    method: str = "log",
    corr_method: str = "pearson",
    window: Optional[int] = None,
) -> pd.DataFrame:
    """
    Compute correlation matrix from raw OHLCV DataFrames.

    Convenience wrapper: builds returns matrix then computes correlation.

    Args:
        dfs:         Dict mapping ticker → OHLCV DataFrame.
        method:      Returns method: "log" or "simple".
        corr_method: Correlation method.
        window:      If set, compute rolling correlation with this window.
                     If None, compute static (full-period) correlation.

    Returns:
        Correlation matrix or rolling correlation DataFrame.
    """
    ret_mat = returns_matrix(dfs, method=method)

    if ret_mat.empty:
        return pd.DataFrame()

    if window:
        return rolling_correlation(ret_mat, window=window, method=corr_method)
    else:
        return static_correlation(ret_mat, method=corr_method)
