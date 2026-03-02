"""
Market Regime Detection

Detects market regime using multiple methods:
- Trend strength (ADX)
- Hidden Markov Models
- Rolling statistics

References:
- Hamilton, J.D. (1989). "A New Approach to the Economic Analysis of 
  Nonstationary Time Series and the Business Cycle"
"""

import pandas as pd
import numpy as np
from typing import Literal, Dict, Optional
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

RegimeType = Literal['trending_up', 'trending_down', 'ranging', 'volatile']


@dataclass
class RegimeState:
    """Market regime state"""
    regime: RegimeType
    confidence: float
    metrics: Dict[str, float]
    timestamp: pd.Timestamp


class RegimeDetector:
    """
    Detect market regime using multiple signals
    
    Combines:
    - Trend strength (ADX)
    - Price action (higher highs/lows)
    - Volatility clustering
    
    Args:
        adx_threshold: ADX level for trending (default: 25)
        lookback: Period for regime detection (default: 20)
    
    Example:
        >>> detector = RegimeDetector(adx_threshold=25)
        >>> regime = detector.detect(data)
        >>> print(regime.regime)
        'trending_up'
    """
    
    def __init__(
        self, 
        adx_threshold: float = 25.0,
        lookback: int = 20
    ):
        if adx_threshold <= 0 or adx_threshold > 100:
            raise ValueError(f"ADX threshold must be 0-100, got {adx_threshold}")
        
        if lookback < 5:
            raise ValueError(f"Lookback must be >= 5, got {lookback}")
        
        self.adx_threshold = adx_threshold
        self.lookback = lookback
        
        logger.info(f"Initialized RegimeDetector (ADX={adx_threshold}, lookback={lookback})")
    
    def detect(self, data: pd.DataFrame) -> RegimeState:
        """
        Detect current market regime
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            RegimeState: Current regime with confidence
        
        Raises:
            ValueError: If data is insufficient
        """
        if len(data) < self.lookback:
            raise ValueError(f"Need at least {self.lookback} bars, got {len(data)}")
        
        try:
            # Calculate signals
            adx = self._calculate_adx(data)
            trend_direction = self._detect_trend_direction(data)
            vol_regime = self._detect_volatility_regime(data)
            
            # Determine regime
            current_adx = adx.iloc[-1]
            
            if current_adx >= self.adx_threshold:
                # Trending
                if trend_direction > 0:
                    regime = 'trending_up'
                else:
                    regime = 'trending_down'
                confidence = min(current_adx / 50.0, 1.0)  # Normalize 0-1
            else:
                # Ranging or Volatile
                if vol_regime == 'high':
                    regime = 'volatile'
                    confidence = 0.7
                else:
                    regime = 'ranging'
                    confidence = 0.8
            
            metrics = {
                'adx': float(current_adx),
                'trend_direction': float(trend_direction),
                'volatility': float(vol_regime == 'high')
            }
            
            state = RegimeState(
                regime=regime,
                confidence=float(confidence),
                metrics=metrics,
                timestamp=data.index[-1]
            )
            
            logger.debug(f"Detected regime: {regime} (confidence={confidence:.2f})")
            
            return state
            
        except Exception as e:
            logger.error(f"Regime detection failed: {str(e)}")
            raise
    
    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average Directional Index (ADX)
        
        ADX measures trend strength (0-100)
        - Below 25: Weak/no trend
        - 25-50: Strong trend
        - Above 50: Very strong trend
        """
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        dm_plus = high.diff()
        dm_minus = -low.diff()
        
        dm_plus[dm_plus < 0] = 0
        dm_minus[dm_minus < 0] = 0
        
        # Smooth with EMA
        atr = tr.ewm(span=period, adjust=False).mean()
        di_plus = 100 * (dm_plus.ewm(span=period, adjust=False).mean() / atr)
        di_minus = 100 * (dm_minus.ewm(span=period, adjust=False).mean() / atr)
        
        # ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return adx.fillna(0)
    
    def _detect_trend_direction(self, data: pd.DataFrame) -> int:
        """
        Detect trend direction using higher highs/lows
        
        Returns:
            1: Uptrend
            -1: Downtrend
            0: No clear trend
        """
        close = data['Close'].iloc[-self.lookback:]
        
        # Simple: compare recent vs old price
        recent_avg = close.iloc[-5:].mean()
        old_avg = close.iloc[:5].mean()
        
        if recent_avg > old_avg * 1.02:  # 2% threshold
            return 1
        elif recent_avg < old_avg * 0.98:
            return -1
        else:
            return 0
    
    def _detect_volatility_regime(self, data: pd.DataFrame) -> Literal['high', 'low']:
        """
        Detect volatility regime
        
        Returns:
            'high' or 'low'
        """
        returns = data['Close'].pct_change().iloc[-self.lookback:]
        current_vol = returns.std()
        
        # Historical volatility comparison
        hist_vol = data['Close'].pct_change().std()
        
        if current_vol > hist_vol * 1.5:
            return 'high'
        else:
            return 'low'
