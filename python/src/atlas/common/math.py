"""
Common Mathematical Utilities for Atlas
"""
import numpy as np
import pandas as pd
from typing import Union, List

def calculate_returns(prices: pd.Series, period: int = 1) -> pd.Series:
    """Calculate simple percentage returns."""
    return prices.pct_change(period)

def calculate_log_returns(prices: pd.Series) -> pd.Series:
    """Calculate logarithmic returns."""
    return np.log(prices / prices.shift(1))

def exponential_moving_average(series: pd.Series, span: int) -> pd.Series:
    """Calculate EMA."""
    return series.ewm(span=span, adjust=False).mean()

def simple_moving_average(series: pd.Series, window: int) -> pd.Series:
    """Calculate SMA."""
    return series.rolling(window=window).mean()
