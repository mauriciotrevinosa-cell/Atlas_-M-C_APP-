"""
Integration Tests - Full Workflow

Tests that multiple components work together.

Run with: pytest tests/integration/test_full_workflow.py -v

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
from atlas.data_layer import get_data
from atlas.features.technical import TechnicalIndicators


class TestFullWorkflow:
    """Test complete workflows"""
    
    def test_data_to_indicators(self):
        """Test: Data Layer → Indicators"""
        # Get data
        data = get_data("AAPL", "2024-01-01", "2024-12-31")
        
        # Calculate indicators
        rsi = TechnicalIndicators.rsi(data['Close'])
        macd_df = TechnicalIndicators.macd(data['Close'])
        bb_df = TechnicalIndicators.bollinger_bands(data['Close'])
        
        # Verify all indicators calculated
        assert len(rsi) == len(data)
        assert len(macd_df) == len(data)
        assert len(bb_df) == len(data)
        
        # Verify RSI in valid range
        rsi_valid = rsi.dropna()
        assert (rsi_valid >= 0).all()
        assert (rsi_valid <= 100).all()
        
        # Verify MACD has correct columns
        assert 'macd_line' in macd_df.columns
        assert 'signal_line' in macd_df.columns
        assert 'histogram' in macd_df.columns
        
        # Verify Bollinger Bands structure
        assert 'bb_upper' in bb_df.columns
        assert 'bb_middle' in bb_df.columns
        assert 'bb_lower' in bb_df.columns
        
        # Verify BB upper > middle > lower
        bb_valid = bb_df.dropna()
        assert (bb_valid['bb_upper'] >= bb_valid['bb_middle']).all()
        assert (bb_valid['bb_middle'] >= bb_valid['bb_lower']).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
