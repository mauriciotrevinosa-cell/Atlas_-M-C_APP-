import pandas as pd
import numpy as np
from ..base import Indicator

class OBV(Indicator):
    """On-Balance Volume"""
    def __init__(self):
        super().__init__("OBV")

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        self.validate_inputs(data, ['close', 'volume'])
        
        change = data['close'].diff()
        direction = np.where(change > 0, 1, -1)
        direction[change == 0] = 0
        
        return (direction * data['volume']).cumsum()

class VWAP(Indicator):
    """Volume Weighted Average Price (Intraday)"""
    def __init__(self):
        super().__init__("VWAP")

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        self.validate_inputs(data, ['high', 'low', 'close', 'volume'])
        
        typical_price = (data['high'] + data['low'] + data['close']) / 3
        volume = data['volume']
        
        # NOTE: This implementation assumes data is typically daily or single session for simplicity.
        # For true intraday anchors, we need timestamp logic (Phase 3).
        return (typical_price * volume).cumsum() / volume.cumsum()
