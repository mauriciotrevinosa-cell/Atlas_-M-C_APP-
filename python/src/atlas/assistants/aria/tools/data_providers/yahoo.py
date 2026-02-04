"""
Yahoo Finance Data Provider

Provides historical data with ~15min delay

Copyright (c) 2026 M&C. All rights reserved.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any
from .base import DataProvider


class YahooProvider(DataProvider):
    """
    Yahoo Finance data provider
    
    Good for:
    - Historical data (free, reliable)
    - Recent quotes (~15min delay)
    
    Limitations:
    - Not true real-time
    - Rate limits (undocumented)
    """
    
    def __init__(self):
        super().__init__("yahoo")
    
    def get_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Get historical data from Yahoo Finance
        
        Args:
            symbol: Ticker (e.g., "AAPL")
            start_date: Start (YYYY-MM-DD)
            end_date: End (YYYY-MM-DD)
            interval: 1d, 1h, 1m, etc.
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval
            )
            
            if data.empty:
                raise ValueError(f"No data found for {symbol}")
            
            return data
            
        except Exception as e:
            raise Exception(f"Yahoo Finance error: {e}")
    
    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest quote from Yahoo Finance
        
        Note: Has ~15min delay
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            Quote dictionary
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Get most recent price
            history = ticker.history(period="1d", interval="1m")
            if history.empty:
                raise ValueError(f"No recent data for {symbol}")
            
            latest = history.iloc[-1]
            
            return {
                'symbol': symbol,
                'price': float(latest['Close']),
                'bid': float(info.get('bid', latest['Close'])),
                'ask': float(info.get('ask', latest['Close'])),
                'volume': int(latest['Volume']),
                'timestamp': latest.name,
                'provider': self.name,
                'delay': '~15min'
            }
            
        except Exception as e:
            raise Exception(f"Yahoo Finance quote error: {e}")
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol exists in Yahoo Finance
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            True if valid
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Check if we got valid data
            return 'symbol' in info or 'shortName' in info
            
        except:
            return False