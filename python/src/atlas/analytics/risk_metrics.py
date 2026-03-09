"""
Risk Metrics
============
Portfolio and position-level risk analytics.

Complements atlas/risk/risk_engine.py (VaR, CVaR, position sizing).
This module adds portfolio-level metrics: drawdown, Sharpe, Sortino, Calmar.

All functions are pure — no state, no side effects.

Usage:
    from atlas.analytics.risk_metrics import max_drawdown, drawdown_series, sharpe_ratio

    mdd  = max_drawdown(returns)          # scalar
    dd   = drawdown_series(returns)       # Series
    sr   = sharpe_ratio(returns)          # scalar

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.analytics.risk_metrics")

_TRADING_DAYS = 252


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------

def drawdown_series(returns: pd.Series) -> pd.Series:
    """
    Compute the drawdown series from a returns stream.

    Drawdown[t] = (wealth[t] - peak_wealth[t]) / peak_wealth[t]

    Values are ≤ 0 (0 = at all-time high, -0.3 = 30% below peak).

    Args:
        returns: Series of period returns (log or simple).

    Returns:
        Series of drawdown values with same index.
    """
    if returns.empty:
        return pd.Series(dtype=float)

    wealth = (1 + returns).cumprod()
    peak = wealth.cummax()
    dd = (wealth - peak) / peak
    dd.name = "drawdown"
    return dd


def max_drawdown(returns: pd.Series) -> float:
    """
    Maximum drawdown over the full returns series.

    Args:
        returns: Series of period returns.

    Returns:
        Float in [-1, 0]. E.g. -0.35 means 35% maximum drawdown.
    """
    if returns.empty:
        return 0.0
    dd = drawdown_series(returns)
    return float(dd.min())


def drawdown_summary(returns: pd.Series) -> dict:
    """
    Full drawdown summary: max, average, current.

    Returns:
        Dict with max_drawdown, avg_drawdown, current_drawdown,
        recovery_periods (count of times back to new high), time_underwater.
    """
    if returns.empty:
        return {
            "max_drawdown":        0.0,
            "avg_drawdown":        0.0,
            "current_drawdown":    0.0,
            "time_underwater_pct": 0.0,
        }

    dd = drawdown_series(returns)
    underwater = (dd < 0).sum()

    return {
        "max_drawdown":        round(float(dd.min()), 6),
        "avg_drawdown":        round(float(dd[dd < 0].mean()) if (dd < 0).any() else 0.0, 6),
        "current_drawdown":    round(float(dd.iloc[-1]), 6),
        "time_underwater_pct": round(float(underwater / len(dd) * 100), 2),
    }


# ---------------------------------------------------------------------------
# Risk-Adjusted Returns
# ---------------------------------------------------------------------------

def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    trading_days: int = _TRADING_DAYS,
) -> float:
    """
    Annualized Sharpe ratio.

    Sharpe = (mean_return - risk_free) / std_return * sqrt(trading_days)

    Args:
        returns:       Series of daily returns.
        risk_free_rate: Daily risk-free rate (default: 0).
                        For annual rate r, use r / trading_days.
        trading_days:  Days per year (default: 252).

    Returns:
        Float. Positive = alpha over risk-free rate.
        Returns 0.0 if std is zero or returns is empty.
    """
    if returns.empty:
        return 0.0
    excess = returns - risk_free_rate
    std = float(excess.std())
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(trading_days))


def sortino_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    trading_days: int = _TRADING_DAYS,
) -> float:
    """
    Annualized Sortino ratio (penalizes only downside volatility).

    Sortino = (mean_return - risk_free) / downside_std * sqrt(trading_days)

    Args:
        returns:        Series of daily returns.
        risk_free_rate: Daily risk-free rate.
        trading_days:   Days per year.

    Returns:
        Float.
    """
    if returns.empty:
        return 0.0
    excess = returns - risk_free_rate
    downside = excess[excess < 0]
    if downside.empty:
        return float("inf")  # No downside — infinite Sortino
    downside_std = float(downside.std())
    if downside_std == 0:
        return 0.0
    return float(excess.mean() / downside_std * np.sqrt(trading_days))


def calmar_ratio(
    returns: pd.Series,
    trading_days: int = _TRADING_DAYS,
) -> float:
    """
    Calmar ratio: annualized return / |max drawdown|.

    Higher is better. Common benchmark: >1 is acceptable, >3 is excellent.

    Args:
        returns:      Series of daily returns.
        trading_days: Days per year for annualization.

    Returns:
        Float. Returns 0.0 if max drawdown is zero.
    """
    if returns.empty:
        return 0.0
    ann_return = float(returns.mean() * trading_days)
    mdd = abs(max_drawdown(returns))
    if mdd == 0:
        return 0.0
    return round(ann_return / mdd, 4)


# ---------------------------------------------------------------------------
# Historical VaR / CVaR (standalone, no class required)
# ---------------------------------------------------------------------------

def historical_var(
    returns: pd.Series,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> dict:
    """
    Historical Value at Risk and Conditional VaR.

    Args:
        returns:     Daily returns series.
        confidence:  Confidence level (default: 0.95 → 95%).
        horizon_days: Horizon for scaling (default: 1 day).

    Returns:
        Dict with "var", "cvar", "confidence", "horizon_days".
    """
    if returns.empty:
        return {"var": 0.0, "cvar": 0.0, "confidence": confidence}

    sorted_r = returns.sort_values()
    idx = int((1 - confidence) * len(sorted_r))
    var  = float(-sorted_r.iloc[idx]) * np.sqrt(horizon_days)
    cvar = float(-sorted_r.iloc[:idx + 1].mean()) * np.sqrt(horizon_days)

    return {
        "var":          round(var, 6),
        "cvar":         round(cvar, 6),
        "confidence":   confidence,
        "horizon_days": horizon_days,
        "method":       "historical",
    }
