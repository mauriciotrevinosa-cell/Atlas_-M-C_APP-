"""
Volatility Analytics
====================
Rolling and historical volatility for single and multi-asset datasets.

Conventions:
  - Volatility is always expressed as annualized standard deviation.
  - Annualization factor: sqrt(252) for daily data.

Usage:
    from atlas.analytics.volatility import rolling_volatility, historical_volatility

    vol = rolling_volatility(df, window=21)     # 21-day rolling vol
    hv  = historical_volatility(df)             # single scalar

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

from atlas.analytics.returns import log_returns

logger = logging.getLogger("atlas.analytics.volatility")

_TRADING_DAYS_PER_YEAR = 252


def rolling_volatility(
    df: pd.DataFrame,
    window: int = 21,
    column: str = "close",
    annualize: bool = True,
    trading_days: int = _TRADING_DAYS_PER_YEAR,
) -> pd.Series:
    """
    Rolling realized volatility (standard deviation of log returns).

    Args:
        df:           Normalized OHLCV DataFrame.
        window:       Lookback window in bars (default: 21 trading days ≈ 1 month).
        column:       Price column (default: "close").
        annualize:    Multiply by sqrt(trading_days) to annualize (default: True).
        trading_days: Annualization factor (default: 252).

    Returns:
        pd.Series of rolling volatility, same index as df.
        NaN for the first (window) rows.
    """
    r = log_returns(df, column=column, dropna=False)
    vol = r.rolling(window=window, min_periods=window).std()

    if annualize:
        vol = vol * np.sqrt(trading_days)

    vol.name = f"vol_{window}d"
    logger.debug(
        "rolling_volatility: window=%d, annualize=%s, latest=%.4f",
        window, annualize, vol.dropna().iloc[-1] if vol.dropna().size else float("nan"),
    )
    return vol


def historical_volatility(
    df: pd.DataFrame,
    column: str = "close",
    annualize: bool = True,
    trading_days: int = _TRADING_DAYS_PER_YEAR,
) -> float:
    """
    Full-period historical volatility as a single scalar.

    Args:
        df:           Normalized OHLCV DataFrame.
        column:       Price column (default: "close").
        annualize:    If True, result is annualized.
        trading_days: Annualization factor.

    Returns:
        Float. Returns 0.0 on insufficient data.
    """
    r = log_returns(df, column=column, dropna=True)
    if r.empty:
        return 0.0
    vol = float(r.std())
    if annualize:
        vol *= np.sqrt(trading_days)
    return round(vol, 6)


def annualized_volatility(
    returns: pd.Series,
    trading_days: int = _TRADING_DAYS_PER_YEAR,
) -> float:
    """
    Annualize volatility from a returns Series.

    Args:
        returns:      Pre-computed returns (log or simple).
        trading_days: Annualization factor.

    Returns:
        Annualized volatility as float.
    """
    if returns.empty:
        return 0.0
    return float(returns.std() * np.sqrt(trading_days))


def multi_asset_volatility(
    dfs: Dict[str, pd.DataFrame],
    window: int = 21,
    column: str = "close",
    annualize: bool = True,
) -> pd.DataFrame:
    """
    Rolling volatility for multiple assets.

    Args:
        dfs:      Dict mapping ticker → OHLCV DataFrame.
        window:   Rolling window in bars.
        column:   Price column.
        annualize: Annualize output.

    Returns:
        DataFrame with tickers as columns, DatetimeIndex as rows.
    """
    vol_series = {}
    for ticker, df in dfs.items():
        if df is None or df.empty:
            logger.warning("multi_asset_volatility: skipping empty %s", ticker)
            continue
        try:
            vol_series[ticker] = rolling_volatility(
                df, window=window, column=column, annualize=annualize
            )
        except Exception as e:
            logger.warning("multi_asset_volatility: %s failed — %s", ticker, e)

    if not vol_series:
        return pd.DataFrame()

    return pd.concat(vol_series, axis=1)
