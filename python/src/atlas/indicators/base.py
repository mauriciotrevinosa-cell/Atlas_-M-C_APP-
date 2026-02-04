from abc import ABC, abstractmethod
import pandas as pd

class Indicator(ABC):
    """
    Base class for all Atlas indicators.
    Enforces stateless, pure function behavior where possible.
    """
    
    def __init__(self, name: str, params: dict = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate the indicator.
        
        Args:
            data: DataFrame containing OHLCV data (normalized).
            
        Returns:
            pd.Series or pd.DataFrame with the indicator values.
        """
        pass

    def validate_inputs(self, data: pd.DataFrame, required_columns: list):
        """Helper to ensure data has required columns."""
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"Indicator {self.name} requires column: {col}")
