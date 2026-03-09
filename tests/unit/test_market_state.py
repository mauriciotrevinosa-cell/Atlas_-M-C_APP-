"""
Tests for Market State module

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import pandas as pd
import numpy as np
from atlas.market_state import (
    MarketInternals,
    RegimeDetector,
    SentimentAnalyzer,
    VolatilityRegime,
)


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


class TestSentimentAnalyzer:
    """Test SentimentAnalyzer"""

    def test_positive_trend_scores_positive(self):
        dates = pd.date_range("2024-01-01", periods=80)
        close = np.linspace(100, 130, 80)
        volume = np.linspace(900_000, 1_300_000, 80)

        data = pd.DataFrame(
            {
                "Close": close,
                "Volume": volume,
            },
            index=dates,
        )

        analyzer = SentimentAnalyzer(short_window=5, long_window=20)
        result = analyzer.analyze(data)

        assert result.score > 0
        assert 0 <= result.confidence <= 1
        assert "price_action" in result.source

    def test_external_sentiment_is_used(self):
        dates = pd.date_range("2024-01-01", periods=60)
        close = 100 + np.cumsum(np.random.default_rng(42).normal(0.2, 0.5, size=60))
        volume = 1_000_000 + np.random.default_rng(7).integers(0, 100_000, size=60)

        data = pd.DataFrame(
            {
                "Close": close,
                "Volume": volume,
                "news_sentiment": np.linspace(-0.2, 0.8, 60),
                "social_sentiment": np.linspace(-0.1, 0.7, 60),
            },
            index=dates,
        )

        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(data)

        assert "news" in result.source
        assert "social" in result.source
        assert "news" in result.components
        assert "social" in result.components

    def test_empty_input_returns_neutral(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze(pd.DataFrame())

        assert result.score == 0.0
        assert result.confidence == 0.0
        assert result.source == "empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
