"""
Open Interest Feature Analysis
================================
Extract features from OI data for signal generation.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.features")


class OIAnalysis:
    """Extract actionable features from Open Interest data."""

    def __init__(self, significance_threshold: float = 0.05):
        self.significance_threshold = significance_threshold

    def oi_price_divergence(
        self,
        oi_data: pd.Series,
        price_data: pd.Series,
        window: int = 10,
    ) -> Dict[str, Any]:
        """
        Detect OI vs Price divergence.

        Args:
            oi_data:    Open Interest time series
            price_data: Price time series (aligned index)
            window:     Lookback window for change calculation
        """
        if len(oi_data) < window or len(price_data) < window:
            return {"signal": "insufficient_data"}

        oi_change = (oi_data.iloc[-1] - oi_data.iloc[-window]) / oi_data.iloc[-window]
        price_change = (price_data.iloc[-1] - price_data.iloc[-window]) / price_data.iloc[-window]

        oi_up = oi_change > self.significance_threshold
        oi_down = oi_change < -self.significance_threshold
        price_up = price_change > self.significance_threshold / 2
        price_down = price_change < -self.significance_threshold / 2

        if oi_up and price_up:
            signal = "strong_trend"
            interpretation = "New money entering in trend direction — momentum confirmed"
            confidence = "high"
        elif oi_up and price_down:
            signal = "distribution"
            interpretation = "Weak hands adding shorts into decline — potential squeeze"
            confidence = "medium"
        elif oi_down and price_up:
            signal = "short_covering"
            interpretation = "Rally driven by closing positions, not new conviction"
            confidence = "medium"
        elif oi_down and price_down:
            signal = "capitulation"
            interpretation = "Longs liquidating — potential bottom if extreme"
            confidence = "medium"
        else:
            signal = "neutral"
            interpretation = "No significant divergence"
            confidence = "low"

        return {
            "signal": signal,
            "interpretation": interpretation,
            "confidence": confidence,
            "oi_change_pct": round(float(oi_change), 4),
            "price_change_pct": round(float(price_change), 4),
            "window": window,
        }

    def extract_features(
        self,
        oi_series: pd.Series,
        price_series: pd.Series,
    ) -> Dict[str, float]:
        """
        Extract numerical features for ML pipelines.
        """
        if oi_series.empty or price_series.empty:
            return {}

        oi_ret = oi_series.pct_change().dropna()
        px_ret = price_series.pct_change().dropna()

        # Correlation between OI changes and price changes
        min_len = min(len(oi_ret), len(px_ret))
        if min_len > 5:
            corr = float(np.corrcoef(oi_ret.tail(min_len).values, px_ret.tail(min_len).values)[0, 1])
        else:
            corr = 0.0

        return {
            "oi_current": float(oi_series.iloc[-1]),
            "oi_change_1d": float(oi_series.pct_change().iloc[-1]) if len(oi_series) > 1 else 0.0,
            "oi_change_7d": float(
                (oi_series.iloc[-1] - oi_series.iloc[-7]) / oi_series.iloc[-7]
            ) if len(oi_series) >= 7 else 0.0,
            "oi_price_correlation": round(corr, 4),
            "oi_zscore": float(
                (oi_series.iloc[-1] - oi_series.mean()) / oi_series.std()
                if oi_series.std() > 0 else 0
            ),
        }
