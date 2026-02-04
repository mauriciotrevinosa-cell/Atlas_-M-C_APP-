import pandas as pd
import numpy as np
from ..base import Indicator

class RSI(Indicator):
    """Relative Strength Index"""
    def __init__(self, period: int = 14):
        super().__init__("RSI", {"period": period})
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        self.validate_inputs(data, ['close'])
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

class MACD(Indicator):
    """Moving Average Convergence Divergence"""
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD", {"fast": fast, "slow": slow, "signal": signal})
        self.fast = fast
        self.slow = slow
        self.signal_period = signal

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        self.validate_inputs(data, ['close'])
        ema_fast = data['close'].ewm(span=self.fast, adjust=False).mean()
        ema_slow = data['close'].ewm(span=self.slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'hist': histogram
        })

class Stochastic(Indicator):
    """Stochastic Oscillator"""
    def __init__(self, k_period: int = 14, d_period: int = 3):
        super().__init__("Stochastic", {"k": k_period, "d": d_period})
        self.k_period = k_period
        self.d_period = d_period

    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        self.validate_inputs(data, ['high', 'low', 'close'])
        
        low_min = data['low'].rolling(window=self.k_period).min()
        high_max = data['high'].rolling(window=self.k_period).max()
        
        k = 100 * ((data['close'] - low_min) / (high_max - low_min))
        d = k.rolling(window=self.d_period).mean()
        
        return pd.DataFrame({'k': k, 'd': d})
