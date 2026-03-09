"""
Atlas Analytics Layer
=====================
Pure-function analytics for returns, volatility, correlation, and risk.

All functions operate on normalized DataFrames (Atlas OHLCV format).
No classes, no side effects — purely functional.

Layers:
  - returns.py     : log/simple returns, multi-asset returns matrix
  - volatility.py  : rolling volatility, historical vol
  - correlation.py : rolling correlation, cross-asset heatmap data
  - risk_metrics.py: max drawdown, drawdown series, Sharpe, Sortino

Copyright (c) 2026 M&C. All rights reserved.
"""

from atlas.analytics.returns import (
    log_returns,
    simple_returns,
    returns_matrix,
)
from atlas.analytics.volatility import (
    rolling_volatility,
    historical_volatility,
    annualized_volatility,
)
from atlas.analytics.correlation import (
    rolling_correlation,
    static_correlation,
    heatmap_data,
)
from atlas.analytics.risk_metrics import (
    max_drawdown,
    drawdown_series,
    sharpe_ratio,
    sortino_ratio,
    calmar_ratio,
)

__all__ = [
    # returns
    "log_returns",
    "simple_returns",
    "returns_matrix",
    # volatility
    "rolling_volatility",
    "historical_volatility",
    "annualized_volatility",
    # correlation
    "rolling_correlation",
    "static_correlation",
    "heatmap_data",
    # risk
    "max_drawdown",
    "drawdown_series",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
]
