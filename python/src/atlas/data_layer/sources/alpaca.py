"""
Alpaca Markets Data Provider

Provider para trading real y datos real-time.

Requiere:
- API Key de Alpaca
- Cuenta en Alpaca Markets

STATUS: 🚧 COMING SOON

Copyright (c) 2026 M&C. All rights reserved.
"""

from ..base import DataProvider
import pandas as pd


class AlpacaProvider(DataProvider):
    """
    Alpaca Markets data provider
    
    🚧 COMING SOON
    
    Features planeados:
    - Real-time data streaming
    - Order book Level 2
    - Trade execution
    - Paper trading
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initialize Alpaca provider
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        
        if not api_key:
            raise ValueError("Alpaca API key required. Get it from: alpaca.markets")
    
    def download(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        """Download historical data"""
        raise NotImplementedError("Alpaca provider coming soon. Use 'yahoo' for now.")
    
    def validate(self, data: pd.DataFrame) -> dict:
        """Validate data quality"""
        raise NotImplementedError("Alpaca provider coming soon.")
    
    def normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize data format"""
        raise NotImplementedError("Alpaca provider coming soon.")
