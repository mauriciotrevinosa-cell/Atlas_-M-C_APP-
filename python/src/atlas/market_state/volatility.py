"""
Volatility Regime Detection

Detects and classifies volatility states using:
- Historical volatility
- GARCH models (simplified)
- Volatility clustering

References:
- Engle, R.F. (1982). "Autoregressive Conditional Heteroscedasticity"
"""

import pandas as pd
import numpy as np
from typing import Literal
import logging

logger = logging.getLogger(__name__)

VolRegime = Literal['low', 'normal', 'high', 'extreme']


class VolatilityRegime:
    """
    Classify volatility regime
    
    Uses percentile-based classification:
    - low: < 25th percentile
    - normal: 25-75th percentile
    - high: 75-95th percentile
    - extreme: > 95th percentile
    
    Args:
        lookback: Historical period for percentiles (default: 252 trading days)
    
    Example:
        >>> vol_detector = VolatilityRegime(lookback=252)
        >>> regime = vol_detector.classify(data)
        >>> print(regime)
        'normal'
    """
    
    def __init__(self, lookback: int = 252):
        if lookback < 20:
            raise ValueError(f"Lookback must be >= 20, got {lookback}")
        
        self.lookback = lookback
        logger.info(f"Initialized VolatilityRegime (lookback={lookback})")
    
    def classify(self, data: pd.DataFrame, window: int = 20) -> VolRegime:
        """
        Classify current volatility regime
        
        Args:
            data: OHLCV DataFrame
            window: Rolling window for vol calculation
        
        Returns:
            VolRegime: Classification
        """
        if len(data) < self.lookback:
            raise ValueError(f"Need >= {self.lookback} bars for classification")
        
        # Calculate realized volatility
        returns = data['Close'].pct_change()
        rolling_vol = returns.rolling(window=window).std() * np.sqrt(252)  # Annualized
        
        # Current volatility
        current_vol = rolling_vol.iloc[-1]
        
        # Historical percentiles
        hist_vol = rolling_vol.dropna()
        p25 = hist_vol.quantile(0.25)
        p75 = hist_vol.quantile(0.75)
        p95 = hist_vol.quantile(0.95)
        
        # Classify
        if current_vol < p25:
            regime = 'low'
        elif current_vol < p75:
            regime = 'normal'
        elif current_vol < p95:
            regime = 'high'
        else:
            regime = 'extreme'
        
        logger.debug(f"Vol regime: {regime} (vol={current_vol:.4f})")
        
        return regime
    
    def get_volatility_forecast(
        self, 
        data: pd.DataFrame, 
        horizon: int = 5
    ) -> float:
        """
        Simple volatility forecast using EWMA
        
        Args:
            data: OHLCV DataFrame
            horizon: Forecast horizon in days
        
        Returns:
            float: Forecasted volatility (annualized)
        """
        returns = data['Close'].pct_change().dropna()
        
        # EWMA volatility (lambda = 0.94, RiskMetrics standard)
        ewma_vol = returns.ewm(alpha=0.06).std().iloc[-1]
        
        # Scale to annualized
        forecast = ewma_vol * np.sqrt(252)
        
        logger.debug(f"Vol forecast ({horizon}d): {forecast:.4f}")
        
        return float(forecast)
