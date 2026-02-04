import pandas as pd
from typing import Dict, List
from atlas.indicators.registry import IndicatorRegistry

class SignalEngine:
    """
    Combines raw indicators into directional signals (-1 to 1).
    Does NOT determine probability, just raw technical bias.
    """
    
    def __init__(self):
        # Default simple strategy weights (Phase 4.1)
        self.strategies = {
            "trend_following": ["SMA", "EMA", "MACD"],
            "mean_reversion": ["RSI", "BB", "STOCH"]
        }
    
    def evaluate(self, data: pd.DataFrame, strategy: str = "trend_following") -> pd.DataFrame:
        """
        Evaluate normalized data against selected strategy.
        Returns a DataFrame with 'signal' column (-1=Short, 0=Neutral, 1=Long).
        """
        signals = pd.DataFrame(index=data.index)
        signals['combined_score'] = 0.0
        
        indicators = self.strategies.get(strategy, [])
        
        for name in indicators:
            ind = IndicatorRegistry.create(name)
            res = ind.calculate(data)
            
            # Normalize indicator output to -1..1 score (Simplified logic for V1)
            score = self._normalize_score(name, res)
            signals['combined_score'] += score
            
        # Final Signal Logic
        signals['signal'] = 0
        signals.loc[signals['combined_score'] > 0.5, 'signal'] = 1
        signals.loc[signals['combined_score'] < -0.5, 'signal'] = -1
        
        return signals

    def _normalize_score(self, name: str, value: pd.Series) -> pd.Series:
        """Normalize indicator values to -1/0/1 bias."""
        # Very basic logic for MVP - to be expanded in Dynamic Weights
        if name == "RSI":
            return value.apply(lambda x: -1 if x > 70 else (1 if x < 30 else 0))
        elif name == "MACD":
            # Assuming value is DataFrame from MACD
            return value['hist'].apply(lambda x: 1 if x > 0 else -1)
        elif name == "SMA":
            # This needs price data context, simplified for now
            return pd.Series(0, index=value.index) 
        
        return pd.Series(0, index=value.index)
