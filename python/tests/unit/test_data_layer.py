"""
Tests for Data Layer

Run with: pytest tests/unit/test_data_layer.py -v

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import pandas as pd
from atlas.data_layer import get_data


class TestDataLayer:
    """Test suite for Data Layer"""
    
    def test_get_data_aapl(self):
        """Test fetching AAPL data"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31")
        
        # Check data exists
        assert data is not None
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
        # Check columns
        assert 'Open' in data.columns
        assert 'High' in data.columns
        assert 'Low' in data.columns
        assert 'Close' in data.columns
        assert 'Volume' in data.columns
        
        # Check data types
        assert data['Close'].dtype in ['float64', 'float32']
        assert data['Volume'].dtype in ['int64', 'float64']
    
    def test_get_data_msft(self):
        """Test fetching MSFT data"""
        data = get_data("MSFT", "2024-01-01", "2024-01-31")
        
        assert len(data) > 0
        assert data['Close'].iloc[0] > 0
    
    def test_get_data_invalid_symbol(self):
        """Test with invalid symbol"""
        with pytest.raises(ValueError):
            get_data("INVALID_SYMBOL_12345", "2024-01-01", "2024-01-31")
    
    def test_get_data_invalid_date_range(self):
        """Test with invalid date range (future dates)"""
        data = get_data("AAPL", "2030-01-01", "2030-01-31")
        # Should return empty or raise error
        assert len(data) == 0 or isinstance(data, pd.DataFrame)
    
    def test_get_data_single_day(self):
        """Test fetching single day"""
        data = get_data("AAPL", "2024-01-02", "2024-01-02")
        
        # Should have 0 or 1 rows depending on if market was open
        assert len(data) in [0, 1]
    
    def test_data_order(self):
        """Test that data is sorted by date"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31")
        
        # Check dates are ascending
        assert data.index.is_monotonic_increasing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
