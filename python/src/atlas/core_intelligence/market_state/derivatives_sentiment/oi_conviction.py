"""
Open Interest Conviction Analysis
===================================
Analyzes the relationship between Open Interest changes and Price changes
to determine market conviction and positioning.

OI ↑ + Price ↑ = Strong bullish conviction (new longs entering)
OI ↑ + Price ↓ = Distribution / weak hands (new shorts or trapped longs)
OI ↓ + Price ↑ = Short covering / profit taking
OI ↓ + Price ↓ = Capitulation (longs closing)

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.market_state")


# Conviction matrix
CONVICTION_MATRIX = {
    ("up", "up"): {
        "pattern": "strong_bullish",
        "interpretation": "New longs entering with conviction",
        "bias": "bullish",
        "strength": 0.8,
    },
    ("up", "down"): {
        "pattern": "distribution",
        "interpretation": "Weak hands adding — potential short trap or long exhaustion",
        "bias": "bearish",
        "strength": 0.6,
    },
    ("down", "up"): {
        "pattern": "short_covering",
        "interpretation": "Short squeeze or profit taking — rally may lack conviction",
        "bias": "neutral_bullish",
        "strength": 0.4,
    },
    ("down", "down"): {
        "pattern": "capitulation",
        "interpretation": "Longs giving up — potential bottom formation",
        "bias": "bearish",
        "strength": 0.7,
    },
}


class OIConviction:
    """
    Analyze Open Interest vs Price dynamics for conviction signals.
    """

    def __init__(
        self,
        oi_change_threshold: float = 0.02,
        price_change_threshold: float = 0.005,
    ):
        """
        Args:
            oi_change_threshold:    Min OI % change to consider significant (2%)
            price_change_threshold: Min price % change to consider significant (0.5%)
        """
        self.oi_threshold = oi_change_threshold
        self.price_threshold = price_change_threshold

    def analyze(
        self,
        oi_current: float,
        oi_previous: float,
        price_current: float,
        price_previous: float,
    ) -> Dict[str, Any]:
        """
        Analyze single OI vs Price snapshot.

        Args:
            oi_current:     Current open interest value
            oi_previous:    Previous open interest value
            price_current:  Current price
            price_previous: Previous price

        Returns:
            Conviction analysis dict
        """
        oi_change_pct = (oi_current - oi_previous) / oi_previous if oi_previous > 0 else 0
        price_change_pct = (price_current - price_previous) / price_previous if price_previous > 0 else 0

        # Classify direction
        if abs(oi_change_pct) < self.oi_threshold:
            oi_dir = "flat"
        else:
            oi_dir = "up" if oi_change_pct > 0 else "down"

        if abs(price_change_pct) < self.price_threshold:
            price_dir = "flat"
        else:
            price_dir = "up" if price_change_pct > 0 else "down"

        # Lookup conviction
        key = (oi_dir, price_dir)
        if key in CONVICTION_MATRIX:
            result = dict(CONVICTION_MATRIX[key])
        else:
            result = {
                "pattern": "inconclusive",
                "interpretation": "Changes too small to determine conviction",
                "bias": "neutral",
                "strength": 0.0,
            }

        result.update({
            "oi_change_pct": round(oi_change_pct, 4),
            "price_change_pct": round(price_change_pct, 4),
            "oi_direction": oi_dir,
            "price_direction": price_dir,
        })

        return result

    def analyze_series(
        self,
        oi_series: pd.Series,
        price_series: pd.Series,
        window: int = 5,
    ) -> Dict[str, Any]:
        """
        Analyze OI vs Price divergence over a rolling window.

        Args:
            oi_series:    OI time series
            price_series: Price time series (same index)
            window:       Rolling window for change calculation

        Returns:
            Series analysis with dominant pattern
        """
        if len(oi_series) < window + 1 or len(price_series) < window + 1:
            return {"error": "insufficient_data", "min_required": window + 1}

        # Align series
        common_idx = oi_series.index.intersection(price_series.index)
        oi = oi_series.loc[common_idx]
        price = price_series.loc[common_idx]

        # Rolling changes
        oi_changes = oi.pct_change(window).dropna()
        price_changes = price.pct_change(window).dropna()

        # Classify each period
        patterns = []
        for i in range(len(oi_changes)):
            oi_chg = oi_changes.iloc[i]
            px_chg = price_changes.iloc[i]

            oi_d = "up" if oi_chg > self.oi_threshold else ("down" if oi_chg < -self.oi_threshold else "flat")
            px_d = "up" if px_chg > self.price_threshold else ("down" if px_chg < -self.price_threshold else "flat")

            key = (oi_d, px_d)
            if key in CONVICTION_MATRIX:
                patterns.append(CONVICTION_MATRIX[key]["pattern"])
            else:
                patterns.append("inconclusive")

        # Find dominant pattern
        if patterns:
            from collections import Counter
            counts = Counter(patterns)
            dominant = counts.most_common(1)[0]
        else:
            dominant = ("inconclusive", 0)

        # Current snapshot
        current = self.analyze(
            float(oi.iloc[-1]), float(oi.iloc[-2]),
            float(price.iloc[-1]), float(price.iloc[-2]),
        )

        return {
            "current": current,
            "dominant_pattern": dominant[0],
            "dominant_count": dominant[1],
            "total_periods": len(patterns),
            "pattern_distribution": dict(Counter(patterns)) if patterns else {},
            "oi_total_change_pct": round(float((oi.iloc[-1] - oi.iloc[0]) / oi.iloc[0]), 4),
            "price_total_change_pct": round(float((price.iloc[-1] - price.iloc[0]) / price.iloc[0]), 4),
        }

    def divergence_score(
        self,
        oi_series: pd.Series,
        price_series: pd.Series,
    ) -> float:
        """
        Calculate a single divergence score: -1 (bearish divergence) to +1 (bullish divergence).

        Divergence = OI and Price moving in opposite directions.
        """
        if len(oi_series) < 5 or len(price_series) < 5:
            return 0.0

        oi_return = (oi_series.iloc[-1] - oi_series.iloc[0]) / oi_series.iloc[0]
        px_return = (price_series.iloc[-1] - price_series.iloc[0]) / price_series.iloc[0]

        # If same direction → no divergence (score near 0)
        # If opposite → divergence (magnitude indicates strength)
        if np.sign(oi_return) == np.sign(px_return):
            return 0.0

        # Bearish div: OI up, price down
        if oi_return > 0 and px_return < 0:
            return -min(1.0, abs(oi_return) + abs(px_return))

        # Bullish div: OI down, price up (short covering)
        if oi_return < 0 and px_return > 0:
            return min(1.0, abs(oi_return) + abs(px_return))

        return 0.0
