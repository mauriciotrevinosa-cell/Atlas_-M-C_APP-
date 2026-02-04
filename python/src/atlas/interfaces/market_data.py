"""
Market Data Interface Definition
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import pandas as pd

class MarketDataProvider(ABC):
    """
    Abstract Base Class for all market data providers.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
        
    @abstractmethod
    def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: Optional[str] = None, 
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.
        Returns DataFrame with index as DatetimeIndex and columns: Open, High, Low, Close, Volume.
        """
        pass
        
    @abstractmethod
    def get_latest_quote(self, symbol: str) -> Dict[str, float]:
        """
        Get real-time snapshot.
        """
        pass
