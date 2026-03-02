"""
Volume Indicators

OBV, VWAP, Accumulation/Distribution, etc.

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def obv(data: pd.DataFrame) -> pd.Series:
    """
    On-Balance Volume (OBV)
    
    Args:
        data: DataFrame with Close and Volume
    
    Returns:
        pd.Series: OBV values
    """
    close = data['Close']
    volume = data['Volume']
    
    # Calculate price direction
    change = close.diff()
    direction = pd.Series(0, index=close.index)
    direction[change > 0] = 1
    direction[change < 0] = -1
    
    # Calculate OBV
    # If change is 0, volume is not added (direction 0)
    signed_volume = volume * direction
    obv_values = signed_volume.cumsum()
    
    # Fill NaN at start
    obv_values.iloc[0] = volume.iloc[0] if not pd.isna(volume.iloc[0]) else 0
    
    logger.debug("Calculated OBV")
    
    return obv_values


def vwap(data: pd.DataFrame) -> pd.Series:
    """
    Volume Weighted Average Price (VWAP)
    
    Note: typical VWAP resets daily. This implementation 
    calculates it over the provided dataframe index accumulating.
    For daily reset, group by date before calling.
    
    Args:
        data: DataFrame with High, Low, Close, Volume
    
    Returns:
        pd.Series: VWAP values
    """
    high = data['High']
    low = data['Low']
    close = data['Close']
    volume = data['Volume']
    
    typical_price = (high + low + close) / 3
    
    vwap_values = (typical_price * volume).cumsum() / volume.cumsum()
    
    logger.debug("Calculated VWAP")
    
    return vwap_values
