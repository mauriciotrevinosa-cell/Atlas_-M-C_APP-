"""
Funding Rate Feature Analysis
===============================
Extract trading features from funding rate data.
Includes divergence detection and reversal signals.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.features")


class FundingAnalysis:
    """
    Extract actionable features from funding rate data.
    """

    def __init__(
        self,
        divergence_threshold: float = 0.05,
        reversal_lookback: int = 6,
        extreme_threshold: float = 0.10,
    ):
        self.divergence_threshold = divergence_threshold
        self.reversal_lookback = reversal_lookback
        self.extreme_threshold = extreme_threshold
        
    def extract_features(
        self,
        funding_series: pd.Series,
    ) -> Dict[str, float]:
        """
        Extract numerical features from funding series for ML models.

        Returns dict of feature_name → float value.
        """
        if funding_series.empty:
            return {}

        return {
            "funding_current": float(funding_series.iloc[-1]),
            "funding_mean_7d": float(funding_series.tail(21).mean()),  # ~7 days of 8h readings
            "funding_std_7d": float(funding_series.tail(21).std()),
            "funding_zscore": float(
                (funding_series.iloc[-1] - funding_series.mean()) / funding_series.std()
                if funding_series.std() > 0 else 0
            ),
            "funding_is_extreme": float(abs(funding_series.iloc[-1]) > self.extreme_threshold),
            "funding_sign_changes_7d": float(
                (np.diff(np.sign(funding_series.tail(21).values)) != 0).sum()
            ),
            "funding_cumulative_7d": float(funding_series.tail(21).sum()),
        }

    def funding_divergence(
        self,
        funding_a: float,
        funding_b: float,
        symbol_a: str = "BTC",
        symbol_b: str = "ETH",
    ) -> Dict[str, Any]:
        """
        Detect funding divergence between two symbols (pairs trade signal).
        """
        diff = abs(funding_a - funding_b)

        if diff < self.divergence_threshold:
            return {
                "signal": "no_divergence",
                "difference": round(diff, 6),
            }

        overpriced = symbol_a if funding_a > funding_b else symbol_b
        underpriced = symbol_b if funding_a > funding_b else symbol_a

        return {
            "signal": "divergence",
            "difference": round(diff, 6),
            "overpriced": overpriced,
            "underpriced": underpriced,
            "trade": f"short_{overpriced}_long_{underpriced}",
            "confidence": "high" if diff > self.divergence_threshold * 2 else "medium",
        }

    def funding_reversal_signal(
        self,
        funding_history: pd.Series,
    ) -> Dict[str, Any]:
        """
        Detect funding rate reversals (sentiment shift).

        A reversal = funding crosses zero after sustained period on one side.
        """
        if len(funding_history) < self.reversal_lookback:
            return {"signal": "insufficient_data"}

        recent = funding_history.tail(self.reversal_lookback)
        current = float(recent.iloc[-1])
        previous_avg = float(recent.iloc[:-1].mean())

        # Check for sign change
        if np.sign(previous_avg) != np.sign(current) and abs(previous_avg) > 0.01:
            if previous_avg > 0:
                return {
                    "signal": "long_exhaustion",
                    "interpretation": "Funding flipped negative — longs exiting",
                    "previous_avg": round(previous_avg, 6),
                    "current": round(current, 6),
                    "trade_bias": "bearish",
                }
            else:
                return {
                    "signal": "short_exhaustion",
                    "interpretation": "Funding flipped positive — shorts covering",
                    "previous_avg": round(previous_avg, 6),
                    "current": round(current, 6),
                    "trade_bias": "bullish",
                }

        return {
            "signal": "no_reversal",
            "current": round(current, 6),
            "trend": "positive" if current > 0 else "negative",
        }
