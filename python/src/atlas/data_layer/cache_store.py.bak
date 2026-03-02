import os
import pandas as pd
from pathlib import Path
from datetime import datetime

class CacheStore:
    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def get(self, key: str) -> pd.DataFrame:
        """Retrieve dataframe from parquet cache."""
        path = self.cache_dir / f"{key}.parquet"
        if path.exists():
            return pd.read_parquet(path)
        return None
        
    def set(self, key: str, df: pd.DataFrame):
        """Save dataframe to parquet cache."""
        path = self.cache_dir / f"{key}.parquet"
        df.to_parquet(path)
