"""
VPIN (Volume-Synchronized Probability of Informed Trading)

Measures order flow toxicity and informed trading probability.

References:
- Easley, D., López de Prado, M., O'Hara, M. (2012). 
  "Flow Toxicity and Liquidity in a High-frequency World"
- Easley, D., López de Prado, M., O'Hara, M. (2011). 
  "The Microstructure of the 'Flash Crash'"

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


from dataclasses import dataclass

@dataclass
class VPINConfig:
    bucket_size: int = 50000
    n_buckets: int = 50

class VPINCalculator:

    """
    VPIN Calculator
    
    VPIN measures order flow imbalance to detect informed trading.
    High VPIN indicates high probability of informed trading (toxicity).
    
    Algorithm:
    1. Divide volume into buckets
    2. Classify volume as buy/sell using tick rule
    3. Calculate imbalance per bucket
    4. VPIN = moving average of |buy - sell| / total volume
    
    Args:
        bucket_size: Volume per bucket (default: 50,000)
        n_buckets: Number of buckets for VPIN calculation (default: 50)
    
    Example:
        >>> vpin_calc = VPIN(bucket_size=50000, n_buckets=50)
        >>> vpin_series = vpin_calc.calculate(data)
        >>> print(f"Current VPIN: {vpin_series.iloc[-1]:.4f}")
    
    Interpretation:
        - VPIN < 0.3: Low toxicity (normal)
        - VPIN 0.3-0.5: Moderate toxicity
        - VPIN > 0.5: High toxicity (risk of liquidity crisis)
    
    Note:
        - Requires high-frequency data for best results
        - Can use daily data with adjusted bucket sizes
    """
    
    def __init__(
        self, 
        bucket_size: int = 50000,
        n_buckets: int = 50
    ):
        if bucket_size <= 0:
            raise ValueError(f"Bucket size must be > 0, got {bucket_size}")
        
        if n_buckets < 2:
            raise ValueError(f"n_buckets must be >= 2, got {n_buckets}")
        
        self.bucket_size = bucket_size
        self.n_buckets = n_buckets
        
        logger.info(
            f"Initialized VPIN (bucket_size={bucket_size}, "
            f"n_buckets={n_buckets})"
        )
    
    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate VPIN time series
        
        Args:
            data: DataFrame with columns: Close, Volume
                  Optional: Open (for better tick rule)
        
        Returns:
            pd.Series: VPIN values (0-1)
        
        Raises:
            ValueError: If data is insufficient
        """
        if len(data) < self.n_buckets:
            raise ValueError(
                f"Need >= {self.n_buckets} bars, got {len(data)}"
            )
        
        try:
            # Classify trades as buy/sell using tick rule
            buy_volume, sell_volume = self._classify_volume(data)
            
            # Create volume buckets
            buckets = self._create_buckets(data, buy_volume, sell_volume)
            
            # Calculate VPIN for each timestamp
            vpin_series = self._calculate_vpin(buckets)
            
            logger.debug(f"Calculated VPIN series ({len(vpin_series)} points)")
            
            return vpin_series
            
        except Exception as e:
            logger.error(f"VPIN calculation failed: {str(e)}")
            raise
    
    def _classify_volume(
        self, 
        data: pd.DataFrame
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Classify volume as buy/sell using tick rule
        
        Tick Rule:
        - If price increased: buy volume
        - If price decreased: sell volume
        - If unchanged: use previous classification
        
        Returns:
            Tuple: (buy_volume, sell_volume)
        """
        close = data['Close']
        volume = data['Volume']
        
        # Price changes (tick rule)
        price_change = close.diff()
        
        # Initialize buy/sell classification
        classification = pd.Series(0, index=data.index)
        classification[price_change > 0] = 1  # Buy
        classification[price_change < 0] = -1  # Sell
        
        # Forward fill for zero changes
        classification = classification.replace(0, np.nan).ffill()
        classification = classification.fillna(1)  # Default to buy
        
        # Split volume
        buy_volume = volume.where(classification == 1, 0)
        sell_volume = volume.where(classification == -1, 0)
        
        return buy_volume, sell_volume
    
    def _create_buckets(
        self,
        data: pd.DataFrame,
        buy_volume: pd.Series,
        sell_volume: pd.Series
    ) -> pd.DataFrame:
        """
        Create volume buckets
        
        Returns:
            DataFrame: Buckets with buy/sell volume
        """
        total_volume = data['Volume']
        cumulative_volume = total_volume.cumsum()
        
        # Bucket indices
        bucket_indices = (cumulative_volume // self.bucket_size).astype(int)
        
        # Aggregate by bucket
        buckets = pd.DataFrame({
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'total_volume': total_volume,
            'bucket': bucket_indices
        })
        
        buckets_agg = buckets.groupby('bucket').agg({
            'buy_volume': 'sum',
            'sell_volume': 'sum',
            'total_volume': 'sum'
        })
        
        return buckets_agg
    
    def _calculate_vpin(self, buckets: pd.DataFrame) -> pd.Series:
        """
        Calculate VPIN from buckets
        
        VPIN = Average(|buy_volume - sell_volume|) / Average(total_volume)
        """
        # Order flow imbalance per bucket
        imbalance = (buckets['buy_volume'] - buckets['sell_volume']).abs()
        total = buckets['total_volume']
        
        # Rolling average over n_buckets
        avg_imbalance = imbalance.rolling(window=self.n_buckets).sum()
        avg_total = total.rolling(window=self.n_buckets).sum()
        
        # VPIN
        vpin = avg_imbalance / avg_total
        vpin = vpin.fillna(0).clip(0, 1)
        
        return vpin


class VPIN(VPINCalculator):
    """
    Backward-compatible alias expected by legacy tests/code.
    """


__all__ = ["VPINConfig", "VPINCalculator", "VPIN"]
