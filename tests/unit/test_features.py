"""
Tests for Features Module

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import pandas as pd
import numpy as np
from atlas.features import FeatureRegistry
from atlas.features.technical import trend, momentum, volatility, volume
from atlas.features.microstructure import vpin, kyle_lambda, order_book_imbalance

class TestFeatures:
    """Test suite for Features module"""
    
    @pytest.fixture
    def sample_data(self):
        dates = pd.date_range('2024-01-01', periods=100)
        data = pd.DataFrame({
            'Open': np.linspace(100, 110, 100) + np.random.randn(100),
            'High': np.linspace(102, 112, 100) + np.random.randn(100),
            'Low': np.linspace(98, 108, 100) + np.random.randn(100),
            'Close': np.linspace(100, 110, 100) + np.random.randn(100),
            'Volume': np.random.randint(1000, 10000, 100)
        }, index=dates)
        return data

    def test_trend_indicators(self, sample_data):
        sma = trend.sma(sample_data['Close'], 20)
        assert len(sma) == len(sample_data)
        
        macd_line, signal, hist = trend.macd(sample_data['Close'])
        assert len(macd_line) == len(sample_data)

    def test_momentum_indicators(self, sample_data):
        rsi = momentum.rsi(sample_data['Close'], 14)
        assert len(rsi) == len(sample_data)
        assert rsi.max() <= 100
        assert rsi.min() >= 0

    def test_volatility_indicators(self, sample_data):
        atr_val = volatility.atr(sample_data, 14)
        assert len(atr_val) == len(sample_data)
        assert (atr_val.dropna() >= 0).all()

    def test_microstructure(self, sample_data):
        vpin_calc = vpin.VPIN(bucket_size=5000, n_buckets=5)
        res = vpin_calc.calculate(sample_data)
        assert len(res) > 0
        
        klam = kyle_lambda.estimate_kyle_lambda(sample_data, window=20)
        assert len(klam) == len(sample_data)

    def test_registry(self, sample_data):
        reg = FeatureRegistry()
        reg.register("sma_10", lambda d: trend.sma(d['Close'], 10))
        res = reg.calculate_all(sample_data)
        assert "sma_10" in res.columns
