"""
Market Internals

Breadth indicators and market health metrics:
- Advance/Decline ratio
- New Highs/Lows
- Up/Down volume

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class MarketInternals:
    """
    Calculate market breadth and internals
    
    Note: Requires multiple securities data
    Currently simplified for single asset
    
    Example:
        >>> internals = MarketInternals()
        >>> metrics = internals.calculate(data)
        >>> print(metrics['breadth_ratio'])
    """
    
    def __init__(self):
        logger.info("Initialized MarketInternals")
    
    def calculate(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate market internals (simplified for single asset)
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            dict: Internal metrics
        """
        close = data['Close']
        volume = data['Volume']
        
        # Price momentum
        returns_5d = close.pct_change(5).iloc[-1]
        returns_20d = close.pct_change(20).iloc[-1]
        
        # Volume trend
        vol_avg_20d = volume.rolling(20).mean().iloc[-1]
        vol_current = volume.iloc[-1]
        vol_ratio = vol_current / vol_avg_20d if vol_avg_20d > 0 else 1.0
        
        # Simplified breadth (for single asset, use price action)
        recent_highs = (close.iloc[-5:] == close.iloc[-20:].max()).sum()
        breadth_ratio = recent_highs / 5.0
        
        metrics = {
            'returns_5d': float(returns_5d),
            'returns_20d': float(returns_20d),
            'volume_ratio': float(vol_ratio),
            'breadth_ratio': float(breadth_ratio),
            'strength': float((returns_5d + returns_20d) / 2)
        }
        
        logger.debug(f"Internals calculated: strength={metrics['strength']:.4f}")
        
        return metrics
