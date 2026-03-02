"""
Long/Short Ratio Analysis
===========================
Contrarian sentiment indicator from aggregate positioning data.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.features")


class LSRAnalysis:
    """
    Analyze Long/Short Ratio for contrarian signals.

    Extreme readings (>70% long or >70% short) historically precede reversals.
    """

    def __init__(
        self,
        extreme_long_threshold: float = 70.0,
        extreme_short_threshold: float = 30.0,
    ):
        self.extreme_long = extreme_long_threshold
        self.extreme_short = extreme_short_threshold

    def analyze(self, long_pct: float) -> Dict[str, Any]:
        """
        Analyze a single LSR reading.

        Args:
            long_pct: Percentage of longs (0-100). short_pct = 100 - long_pct.
        """
        short_pct = 100.0 - long_pct

        if long_pct >= self.extreme_long:
            signal = "contrarian_short"
            sentiment = "extreme_long"
            strength = min(1.0, (long_pct - self.extreme_long) / 20)
        elif long_pct <= self.extreme_short:
            signal = "contrarian_long"
            sentiment = "extreme_short"
            strength = min(1.0, (self.extreme_short - long_pct) / 20)
        else:
            signal = "no_signal"
            sentiment = "neutral"
            strength = 0.0

        return {
            "long_pct": round(long_pct, 1),
            "short_pct": round(short_pct, 1),
            "ratio": round(long_pct / short_pct, 2) if short_pct > 0 else float("inf"),
            "sentiment": sentiment,
            "signal": signal,
            "strength": round(strength, 3),
        }

    def analyze_history(self, lsr_series: pd.Series) -> Dict[str, Any]:
        """
        Analyze LSR time series for trends and extremes.

        Args:
            lsr_series: Series of long_pct values over time
        """
        if lsr_series.empty:
            return {"error": "empty_series"}

        current = self.analyze(float(lsr_series.iloc[-1]))

        return {
            "current": current,
            "mean": round(float(lsr_series.mean()), 1),
            "std": round(float(lsr_series.std()), 1),
            "max_long_pct": round(float(lsr_series.max()), 1),
            "min_long_pct": round(float(lsr_series.min()), 1),
            "time_in_extreme": round(
                float(((lsr_series > self.extreme_long) | (lsr_series < self.extreme_short)).mean()), 3
            ),
        }

    def extract_features(self, lsr_series: pd.Series) -> Dict[str, float]:
        """Extract numerical features for ML."""
        if lsr_series.empty:
            return {}

        current = float(lsr_series.iloc[-1])
        return {
            "lsr_current": current,
            "lsr_mean_7d": float(lsr_series.tail(7).mean()),
            "lsr_zscore": float(
                (current - lsr_series.mean()) / lsr_series.std()
                if lsr_series.std() > 0 else 0
            ),
            "lsr_is_extreme_long": float(current >= self.extreme_long),
            "lsr_is_extreme_short": float(current <= self.extreme_short),
            "lsr_distance_from_neutral": abs(current - 50.0),
        }
