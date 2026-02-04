"""
Alpaca Data Provider

Provides TRUE real-time market data (FREE)

Copyright (c) 2026 M&C. All rights reserved.
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from .base import DataProvider


class AlpacaProvider(DataProvider):
    """
    Alpaca data provider
    
    Good for:
    - TRUE real-time quotes (0 delay)
    - US stocks
    - Free tier: 200 requests/minute
    
    Requirements:
    - Alpaca account (free)
    - API key + secret
    
    Limitations:
    - Only US markets
    - Need API credentials
    """
    
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None):
        """
        Initialize Alpaca provider
        
        Args:
            api_key: Alpaca API key (or from env var)
            secret_key: Alpaca secret key (or from env var)
        """
        super().__init__("alpaca")
        
        # Import here to make it optional
        try:
            from alpaca.data import StockHistoricalDataClient
            from alpaca.data.requests import (
                StockLatestQuoteRequest,
                StockBarsRequest
            )
            from alpaca.data.timeframe import TimeFrame
            
            self.StockHistoricalDataClient = StockHistoricalDataClient
            self.StockLatestQuoteRequest = StockLatestQuoteRequest
            self.StockBarsRequest = StockBarsRequest
            self.TimeFrame = TimeFrame
            
        except ImportError:
            raise ImportError(
                "Alpaca not installed. Install with: "
                "pip install alpaca-py"
            )
        
        # Get credentials
        import os
        self.api_key = api_key or os.getenv("ALPACA_API_KEY")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY")
        
        if not self.api_key or not self.secret_key:
            raise ValueError(
                "Alpaca credentials not found. "
                "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env"
            )
        
        # Initialize client
        self.client = self.StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
    
    def get_historical(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Get historical data from Alpaca
        
        Args:
            symbol: Ticker
            start_date: Start (YYYY-MM-DD)
            end_date: End (YYYY-MM-DD)
            interval: 1d, 1h, 1m (maps to Alpaca TimeFrame)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Map interval to Alpaca TimeFrame
            timeframe_map = {
                "1m": self.TimeFrame.Minute,
                "5m": self.TimeFrame(5, self.TimeFrame.Unit.Minute),
                "15m": self.TimeFrame(15, self.TimeFrame.Unit.Minute),
                "1h": self.TimeFrame.Hour,
                "1d": self.TimeFrame.Day,
            }
            
            timeframe = timeframe_map.get(interval, self.TimeFrame.Day)
            
            # Create request
            request = self.StockBarsRequest(
                symbol_or_symbols=symbol,
                start=start_date,
                end=end_date,
                timeframe=timeframe
            )
            
            # Get data
            bars = self.client.get_stock_bars(request)
            
            # Convert to DataFrame
            df = bars.df
            
            if df.empty:
                raise ValueError(f"No data found for {symbol}")
            
            # Reset index and rename columns to match Yahoo format
            df = df.reset_index()
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            return df
            
        except Exception as e:
            raise Exception(f"Alpaca historical data error: {e}")
    
    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest quote from Alpaca (TRUE real-time)
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            Quote dictionary
        """
        try:
            # Create request
            request = self.StockLatestQuoteRequest(
                symbol_or_symbols=symbol
            )
            
            # Get quote
            quotes = self.client.get_stock_latest_quote(request)
            quote = quotes[symbol]
            
            return {
                'symbol': symbol,
                'price': float((quote.ask_price + quote.bid_price) / 2),
                'bid': float(quote.bid_price),
                'ask': float(quote.ask_price),
                'bid_size': int(quote.bid_size),
                'ask_size': int(quote.ask_size),
                'timestamp': quote.timestamp,
                'provider': self.name,
                'delay': 'real-time'
            }
            
        except Exception as e:
            raise Exception(f"Alpaca quote error: {e}")
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate symbol by attempting to get latest quote
        
        Args:
            symbol: Ticker symbol
            
        Returns:
            True if valid
        """
        try:
            self.get_latest_quote(symbol)
            return True
        except:
            return False