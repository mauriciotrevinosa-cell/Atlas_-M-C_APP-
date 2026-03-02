"""
SMA Crossover Engine
===================

A classic rule-based strategy:
- BUY when Fast SMA crosses above Slow SMA
- SELL when Fast SMA crosses below Slow SMA

Copyright (c) 2026 M&C. All rights reserved.
"""

import pandas as pd
from typing import List, Optional, Dict
from ..base_engine import BaseEngine, EngineType, Signal

class SMACrossoverEngine(BaseEngine):
    """
    Simple Moving Average Crossover Strategy
    """
    
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__(
            name=f"SMA_Cross_{fast_period}_{slow_period}",
            engine_type=EngineType.RULE_BASED,
            config={"fast": fast_period, "slow": slow_period}
        )
        self.fast = fast_period
        self.slow = slow_period
        
    def analyze(self, data: pd.DataFrame, context: Optional[Dict] = None) -> List[Signal]:
        """
        Generate signals based on SMA crossover
        """
        signals = []
        if not self.validate_data(data):
            return signals
            
        # Calculate Indicators
        closes = data['Close']
        fast_sma = closes.rolling(window=self.fast).mean()
        slow_sma = closes.rolling(window=self.slow).mean()
        
        # We need at least 'slow' periods
        if len(data) < self.slow:
            return signals
            
        # Check Crossover on the last bar
        # Current values
        curr_fast = fast_sma.iloc[-1]
        curr_slow = slow_sma.iloc[-1]
        
        # Previous values
        prev_fast = fast_sma.iloc[-2]
        prev_slow = slow_sma.iloc[-2]
        
        timestamp = data.index[-1]
        symbol = context.get("symbol", "UNKNOWN") if context else "UNKNOWN"
        
        # Golden Cross (Bullish)
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            signals.append(Signal(
                symbol=symbol,
                action="BUY",
                confidence=0.8, # Static high confidence for pure crossover
                engine_name=self.name,
                timestamp=timestamp,
                metadata={"reason": "Golden Cross", "fast": curr_fast, "slow": curr_slow}
            ))
            
        # Death Cross (Bearish)
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            signals.append(Signal(
                symbol=symbol,
                action="SELL",
                confidence=0.8,
                engine_name=self.name,
                timestamp=timestamp,
                metadata={"reason": "Death Cross", "fast": curr_fast, "slow": curr_slow}
            ))
            
        return signals
