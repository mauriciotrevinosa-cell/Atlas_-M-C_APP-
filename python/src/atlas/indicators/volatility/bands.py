import pandas as pd
import numpy as np
from ..base import Indicator

class ATR(Indicator):
    """Average True Range"""
    def __init__(self, period: int = 14):
        super().__init__("ATR", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        self.validate_inputs(data, ['high', 'low', 'close'])
        
        high = data['high']
        low = data['low']
        close_prev = data['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=self.period).mean()

class BollingerBands(Indicator):
    """Bollinger Bands"""
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__("BollingerBands", {"period": period, "std_dev": std_dev})
        self.period = period
        self.std_dev = std_dev

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        self.validate_inputs(data, ['close'])
        
        sma = data['close'].rolling(window=self.period).mean()
        std = data['close'].rolling(window=self.period).std()
        
        upper = sma + (std * self.std_dev)
        lower = sma - (std * self.std_dev)
        
        return pd.DataFrame({
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'bandwidth': (upper - lower) / sma
        })
