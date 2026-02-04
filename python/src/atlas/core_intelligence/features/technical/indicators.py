"""
Technical Indicators Implementation
"""
import pandas as pd
import numpy as np
from atlas.common.math import exponential_moving_average, simple_moving_average

class TechnicalIndicators:
    """
    Standard Technical Indicators Library.
    """
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        
        avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """Moving Average Convergence Divergence."""
        ema_fast = exponential_moving_average(prices, span=fast)
        ema_slow = exponential_moving_average(prices, span=slow)
        macd_line = ema_fast - ema_slow
        signal_line = exponential_moving_average(macd_line, span=signal)
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram
        })

    @staticmethod
    def bollinger_bands(prices: pd.Series, window: int = 20, num_std: float = 2.0):
        """Bollinger Bands."""
        sma = simple_moving_average(prices, window=window)
        std = prices.rolling(window=window).std()
        upper = sma + (std * num_std)
        lower = sma - (std * num_std)
        
        return pd.DataFrame({
            'bb_upper': upper,
            'bb_middle': sma,
            'bb_lower': lower
        })
