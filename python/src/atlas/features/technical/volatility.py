"""
Volatility Indicators

ATR, Bollinger Bands, Keltner Channels, etc.

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def atr(
    data: pd.DataFrame, 
    period: int = 14
) -> pd.Series:
    """
    Average True Range (ATR)
    
    Args:
        data: OHLC DataFrame
        period: ATR period (default: 14)
    
    Returns:
        pd.Series: ATR values
    """
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")
        
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    # Calculate True Range
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR (Wilder's smoothing)
    atr_values = tr.ewm(alpha=1/period, adjust=False).mean()
    
    logger.debug(f"Calculated ATR({period})")
    
    return atr_values


def bollinger_bands(
    data: pd.Series, 
    period: int = 20, 
    std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands
    
    Args:
        data: Price series
        period: MA period (default: 20)
        std_dev: Standard deviation multiplier (default: 2.0)
    
    Returns:
        Tuple: (upper_band, middle_band, lower_band)
    """
    if period < 1:
        raise ValueError(f"Period must be >= 1, got {period}")
        
    middle_band = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    
    logger.debug(f"Calculated Bollinger Bands({period}, {std_dev})")
    
    return upper_band, middle_band, lower_band
