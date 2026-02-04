import pandas as pd
import numpy as np

def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize OHLCV dataframe.
    Ensures standard columns, index, and removes basic anomalies.
    """
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    
    # Lowercase columns
    df.columns = [c.lower() for c in df.columns]
    
    # Check requirements
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")
            
    # Forward fill gaps
    df = df.ffill()
    
    # Drop NaNs at start
    df = df.dropna()
    
    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    return df
