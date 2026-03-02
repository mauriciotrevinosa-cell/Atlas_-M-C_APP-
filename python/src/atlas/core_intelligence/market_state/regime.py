"""
Market Regime Analyzer
=====================

Detects market state (Bull/Bear/Sideways) and volatility.
"""

from enum import Enum
from dataclasses import dataclass
import pandas as pd
import numpy as np

class MarketRegime(Enum):
    BULL_TREND = "BULL_TREND"
    BEAR_TREND = "BEAR_TREND"
    SIDEWAYS = "SIDEWAYS"
    UNKNOWN = "UNKNOWN"

@dataclass
class MarketState:
    regime: MarketRegime
    confidence: float
    volatility_state: str # LOW, HIGH, EXTREME
    trend_strength: float # ADX or similar score

class MarketStateAnalyzer:
    """Basic Market Regime Analysis"""
    
    def analyze(self, data: pd.DataFrame) -> MarketState:
        """
        Determine market regime from OHLCV data
        """
        if len(data) < 50:
             return MarketState(MarketRegime.UNKNOWN, 0.0, "UNKNOWN", 0.0)
             
        # Simple Logic: SMA Slope + ADX-like proxy
        close = data['Close']
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        
        # Current values
        current_close = close.iloc[-1]
        current_sma50 = sma50.iloc[-1]
        
        # Volatility (ATR-like proxy)
        tr = np.maximum(data['High'] - data['Low'], 
                       np.abs(data['High'] - data['Close'].shift(1)), 
                       np.abs(data['Low'] - data['Close'].shift(1)))
        atr = tr.rolling(14).mean().iloc[-1]
        avg_price = current_close
        vol_pct = (atr / avg_price) * 100
        
        vol_state = "LOW"
        if vol_pct > 1.5: vol_state = "HIGH"
        if vol_pct > 3.0: vol_state = "EXTREME"
        
        # Regime Logic
        regime = MarketRegime.SIDEWAYS
        confidence = 50.0
        strength = 0.0
        
        # Bullish: Price > SMA50 > SMA200 (if data allows)
        # Simplified: Price > SMA50
        if current_close > current_sma50:
            regime = MarketRegime.BULL_TREND
            confidence = 70.0
            strength = (current_close / current_sma50 - 1) * 100
        elif current_close < current_sma50:
            regime = MarketRegime.BEAR_TREND
            confidence = 70.0
            strength = (1 - current_close / current_sma50) * 100
            
        return MarketState(
            regime=regime,
            confidence=confidence,
            volatility_state=vol_state,
            trend_strength=abs(strength)
        )
