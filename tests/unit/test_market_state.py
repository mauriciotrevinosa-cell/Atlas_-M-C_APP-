"""
Tests for Market State module

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import pandas as pd
import numpy as np
from atlas.market_state import RegimeDetector, VolatilityRegime, MarketInternals


class TestRegimeDetector:
    """Test RegimeDetector"""
    
    def test_initialization(self):
        """Test normal init"""
        detector = RegimeDetector(adx_threshold=25, lookback=20)
        assert detector.adx_threshold == 25
        assert detector.lookback == 20
    
    def test_invalid_adx(self):
        """Test invalid ADX"""
        with pytest.raises(ValueError):
            RegimeDetector(adx_threshold=-1)
    
    def test_detection(self):
        """Test detection"""
        # Create test data
        dates = pd.date_range('2024-01-01', periods=50)
        close = np.linspace(100, 120, 50)
        
        data = pd.DataFrame({
            'Open': close,
            'High': close * 1.01,
            'Low': close * 0.99,
            'Close': close,
            'Volume': [1000000] * 50
        }, index=dates)
        
        detector = RegimeDetector()
        regime = detector.detect(data)
        
        assert regime.regime in ['trending_up', 'trending_down', 'ranging', 'volatile']
        assert 0 <= regime.confidence <= 1


class TestVolatilityRegime:
    """Test VolatilityRegime"""
    
    def test_classification(self):
        """Test classification"""
        dates = pd.date_range('2024-01-01', periods=300)
        data = pd.DataFrame({
            'Close': 100 + np.random.randn(300).cumsum()
        }, index=dates)
        
        detector = VolatilityRegime(lookback=252)
        regime = detector.classify(data)
        
        assert regime in ['low', 'normal', 'high', 'extreme']


class TestMarketInternals:
    """Test MarketInternals"""
    
    def test_calculation(self):
        """Test calculation"""
        dates = pd.date_range('2024-01-01', periods=50)
        data = pd.DataFrame({
            'Close': range(100, 150),
            'Volume': [1000000] * 50
        }, index=dates)
        
        internals = MarketInternals()
        metrics = internals.calculate(data)
        
        assert 'strength' in metrics
        assert 'volume_ratio' in metrics
        assert isinstance(metrics['strength'], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
