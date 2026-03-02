"""
Trend Indicators

SMA, EMA, MACD, ADX, Ichimoku, etc.

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
from typing import Union, Tuple
import logging

logger = logging.getLogger(__name__)


def sma(data: pd.Series, period: int) -> pd.Series:
    """
    Simple Moving Average
    
    Args:
        data: Price series
        period: SMA period
    
    Returns:
        pd.Series: SMA values
    
    Example:
        >>> sma_20 = sma(data['Close'], 20)
    """
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")
    
    result = data.rolling(window=period).mean()
    
    logger.debug(f"Calculated SMA({period})")
    return result


def ema(data: pd.Series, period: int) -> pd.Series:
    """
    Exponential Moving Average
    
    Args:
        data: Price series
        period: EMA period
    
    Returns:
        pd.Series: EMA values
    
    Example:
        >>> ema_12 = ema(data['Close'], 12)
    """
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")
    
    result = data.ewm(span=period, adjust=False).mean()
    
    logger.debug(f"Calculated EMA({period})")
    return result


def macd(
    data: pd.Series, 
    fast: int = 12, 
    slow: int = 26, 
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence)
    
    Args:
        data: Price series
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)
    
    Returns:
        Tuple: (macd_line, signal_line, histogram)
    
    Example:
        >>> macd_line, signal_line, hist = macd(data['Close'])
    
    References:
        - Appel, G. (1979). "The Moving Average Convergence-Divergence 
          Trading Method"
    """
    if fast >= slow:
        raise ValueError(f"Fast period must be < slow period")
    
    ema_fast = ema(data, fast)
    ema_slow = ema(data, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    logger.debug(f"Calculated MACD({fast},{slow},{signal})")
    
    return macd_line, signal_line, histogram
