"""
Base Provider for Market Data

Abstract class that all data providers must implement

Copyright (c) 2026 M&C. All rights reserved.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime


class DataProvider(ABC):
    """
    Abstract base class for market data providers
    
    All providers (Yahoo, Alpaca, etc.) must implement these methods
    """
    
    def __init__(self, name: str):
        """
        Initialize provider
        
        Args:
            name: Provider name (e.g., "yahoo", "alpaca")
        """
        self.name = name
    
    @abstractmethod
    def get_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Get historical data
        
        Args:
            symbol: Ticker symbol (e.g., "AAPL")
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Data interval (1d, 1h, 1m, etc.)
            
        Returns:
            DataFrame with OHLCV data
        """
        pass
    
    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest quote (real-time or near real-time)
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            Dictionary with quote data:
            {
                'symbol': str,
                'price': float,
                'bid': float,
                'ask': float,
                'volume': int,
                'timestamp': datetime
            }
        """
        pass
    
    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol exists
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            True if valid, False otherwise
        """
        pass
    
    def __repr__(self):
        return f"DataProvider({self.name})"