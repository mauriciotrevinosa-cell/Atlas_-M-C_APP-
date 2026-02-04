import pandas as pd
import numpy as np
from ..base import Indicator

class SMA(Indicator):
    """Simple Moving Average"""
    def __init__(self, period: int = 20):
        super().__init__("SMA", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        self.validate_inputs(data, ['close'])
        return data['close'].rolling(window=self.period).mean()

class EMA(Indicator):
    """Exponential Moving Average"""
    def __init__(self, period: int = 20):
        super().__init__("EMA", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        self.validate_inputs(data, ['close'])
        return data['close'].ewm(span=self.period, adjust=False).mean()

class WMA(Indicator):
    """Weighted Moving Average"""
    def __init__(self, period: int = 20):
        super().__init__("WMA", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        self.validate_inputs(data, ['close'])
        weights = np.arange(1, self.period + 1)
        return data['close'].rolling(self.period).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )
