"""
VPIN — Volume-Synchronized Probability of Informed Trading

Measures order-flow toxicity. High VPIN → higher probability of informed
trading → elevated liquidity risk.

References:
    Easley, D., López de Prado, M., O'Hara, M. (2012).
    "Flow Toxicity and Liquidity in a High-frequency World"
    Review of Financial Studies, 25(5), 1457-1493.

Copyright © 2026 M&C. All Rights Reserved.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class VPINConfig:
    """Configuration for VPIN calculation"""
    bucket_size: int = 50        # Volume units per bucket
    window: int = 50             # Rolling window (number of buckets)
    classification_method: str = "tick"   # "tick" or "bulk"

    def __post_init__(self):
        if self.bucket_size < 1:
            raise ValueError(f"bucket_size must be positive, got {self.bucket_size}")
        if self.window < 1:
            raise ValueError(f"window must be positive, got {self.window}")
        if self.classification_method not in ("tick", "bulk"):
            raise ValueError("classification_method must be 'tick' or 'bulk'")


class VPINCalculator:
    """
    Calculate VPIN (Volume-Synchronized Probability of Informed Trading).

    VPIN quantifies the probability that informed traders are present,
    based on buy/sell volume imbalances within equal-volume buckets.

    Interpretation:
        VPIN < 0.3   → low toxicity (normal)
        VPIN 0.3-0.5 → moderate toxicity
        VPIN > 0.5   → high toxicity (liquidity risk)
        VPIN > 0.7   → extreme toxicity (flash-crash risk)

    Example:
        >>> cfg = VPINConfig(bucket_size=50, window=50)
        >>> calc = VPINCalculator(cfg)
        >>> vpin = calc.calculate(prices, volumes)
        >>> print(f"Latest VPIN: {vpin[-1]:.4f}")
    """

    def __init__(self, config: VPINConfig):
        self.config = config
        logger.info(
            "Initialized VPINCalculator — "
            f"bucket_size={config.bucket_size}, window={config.window}"
        )

    def calculate(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        sides: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Calculate VPIN time series.

        Args:
            prices:  Array of trade prices (or OHLCV Close series)
            volumes: Array of trade volumes
            sides:   Optional trade sides (+1=buy, -1=sell).
                     If None, the tick rule is applied automatically.

        Returns:
            np.ndarray of VPIN values (same length as number of buckets)

        Raises:
            ValueError: If prices and volumes have different lengths
        """
        if len(prices) != len(volumes):
            raise ValueError("prices and volumes must have the same length")

        if sides is None:
            sides = self._classify_tick_rule(prices)

        buy_bkt, sell_bkt = self._create_buckets(volumes, sides)
        return self._calculate_from_buckets(buy_bkt, sell_bkt)

    def calculate_from_ohlcv(self, data: pd.DataFrame) -> np.ndarray:
        """
        Convenience wrapper for OHLCV DataFrames.

        Args:
            data: DataFrame with columns ['Close', 'Volume']

        Returns:
            np.ndarray of VPIN values
        """
        prices = data["Close"].values
        volumes = data["Volume"].values
        return self.calculate(prices, volumes)

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _classify_tick_rule(self, prices: np.ndarray) -> np.ndarray:
        """
        Classify trades as buy (+1) or sell (-1) using the tick rule.

        Rule: compare each price to the previous.
        Unchanged price → inherit the previous classification.
        """
        n = len(prices)
        sides = np.zeros(n)
        for i in range(1, n):
            if prices[i] > prices[i - 1]:
                sides[i] = 1
            elif prices[i] < prices[i - 1]:
                sides[i] = -1
            else:
                sides[i] = sides[i - 1]
        # Default first trade to buy if undetermined
        if sides[0] == 0 and n > 1:
            sides[0] = sides[1] if sides[1] != 0 else 1
        return sides

    def _create_buckets(
        self, volumes: np.ndarray, sides: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Accumulate trades into equal-volume buckets.

        Returns:
            (buy_volumes_per_bucket, sell_volumes_per_bucket)
        """
        size = self.config.bucket_size
        buy_list, sell_list = [], []
        cur_buy = cur_sell = cum_vol = 0.0

        for vol, side in zip(volumes, sides):
            if side == 1:
                cur_buy += vol
            elif side == -1:
                cur_sell += vol
            cum_vol += vol

            if cum_vol >= size:
                buy_list.append(cur_buy)
                sell_list.append(cur_sell)
                cur_buy = cur_sell = cum_vol = 0.0

        return np.array(buy_list), np.array(sell_list)

    def _calculate_from_buckets(
        self, buy_vols: np.ndarray, sell_vols: np.ndarray
    ) -> np.ndarray:
        """
        VPIN_t = (1/n) Σ |V_buy − V_sell| / (V_buy + V_sell)
        """
        total = buy_vols + sell_vols
        imbalance = np.abs(buy_vols - sell_vols)

        with np.errstate(divide="ignore", invalid="ignore"):
            norm = np.where(total > 0, imbalance / total, 0.0)

        vpin = (
            pd.Series(norm)
            .rolling(window=self.config.window, min_periods=1)
            .mean()
            .values
        )
        return vpin

    def bulk_volume_classification(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        bucket_size: Optional[int] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Bulk Volume Classification (BVC) as in Easley et al. (2012) §2.2.

        Instead of classifying each trade, classify the entire bucket's
        volume based on the net price movement within the bucket.

        Returns:
            (buy_volumes_per_bucket, sell_volumes_per_bucket)
        """
        size = bucket_size or self.config.bucket_size
        buy_list, sell_list = [], []
        i = 0

        while i < len(volumes):
            start_price = prices[i]
            bkt_vol = 0.0
            end_idx = i

            while bkt_vol < size and end_idx < len(volumes):
                bkt_vol += volumes[end_idx]
                end_idx += 1

            end_price = prices[end_idx - 1]

            if end_price > start_price:
                buy_list.append(bkt_vol)
                sell_list.append(0.0)
            elif end_price < start_price:
                buy_list.append(0.0)
                sell_list.append(bkt_vol)
            else:
                buy_list.append(bkt_vol / 2)
                sell_list.append(bkt_vol / 2)

            i = end_idx

        return np.array(buy_list), np.array(sell_list)
