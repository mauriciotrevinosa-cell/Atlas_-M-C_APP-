"""
Feature Registry

Central registry for managing and calculating all features.

Copyright © 2026 M&C. All Rights Reserved.
"""

from typing import List, Dict, Callable, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class FeatureRegistry:
    """
    Central registry for all feature extractors.
    Allows registering and running multiple features in batch.
    """
    
    def __init__(self):
        self._features: Dict[str, Callable] = {}
        logger.info("Initialized FeatureRegistry")
        
    def register(self, name: str, func: Callable):
        """Register a feature calculation function"""
        self._features[name] = func
        logger.debug(f"Registered feature: {name}")
        
    def calculate_all(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate all registered features"""
        results = pd.DataFrame(index=data.index)
        
        for name, func in self._features.items():
            try:
                # Determine if function takes DataFrame or Series
                # This is a basic heuristic, in production use introspection or standardization
                try:
                    res = func(data)
                except TypeError:
                    # Try with Close price if it fails (standard Series input)
                    res = func(data['Close'])
                    
                # Handle Tuple returns (e.g. MACD, Bollinger)
                if isinstance(res, tuple):
                    for i, r in enumerate(res):
                        results[f"{name}_{i}"] = r
                else:
                    results[name] = res
                    
                logger.debug(f"Calculated {name}")
                
            except Exception as e:
                logger.error(f"Failed to calculate feature {name}: {e}")
                
        return results
