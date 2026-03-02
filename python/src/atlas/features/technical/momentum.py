"""
Momentum Indicators

RSI, Stochastic, Williams %R, ROC, etc.

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index
    
    Measures momentum (0-100):
    - < 30: Oversold
    - > 70: Overbought
    
    Args:
        data: Price series
        period: RSI period (default: 14)
    
    Returns:
        pd.Series: RSI values
    
    Example:
        >>> rsi_14 = rsi(data['Close'], 14)
    
    References:
        - Wilder, J.W. (1978). "New Concepts in Technical Trading Systems"
    """
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")
    
    # Calculate price changes
    delta = data.diff()
    
    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)
    
    # Calculate average gains and losses (Wilder's smoothing)
    avg_gains = gains.ewm(alpha=1/period, adjust=False).mean()
    avg_losses = losses.ewm(alpha=1/period, adjust=False).mean()
    
    # Calculate RS and RSI
    rs = avg_gains / avg_losses
    rsi_values = 100 - (100 / (1 + rs))
    
    logger.debug(f"Calculated RSI({period})")
    
    return rsi_values


def stochastic(
    data: pd.DataFrame, 
    k_period: int = 14, 
    d_period: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator
    
    Measures position within recent range (0-100):
    - %K: Fast line
    - %D: Slow line (SMA of %K)
    
    Args:
        data: OHLC DataFrame
        k_period: %K period (default: 14)
        d_period: %D period (default: 3)
    
    Returns:
        Tuple: (%K, %D)
    
    Example:
        >>> k, d = stochastic(data, 14, 3)
    
    References:
        - Lane, G. (1984). "Lane's Stochastics"
    """
    if k_period < 1 or d_period < 1:
        raise ValueError("Periods must be >= 1")
    
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    # Calculate %K
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    
    # Calculate %D (SMA of %K)
    d = k.rolling(window=d_period).mean()
    
    logger.debug(f"Calculated Stochastic({k_period},{d_period})")
    
    return k, d
