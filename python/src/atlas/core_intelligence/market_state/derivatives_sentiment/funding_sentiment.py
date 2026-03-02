"""
Funding Rate Sentiment Analysis
================================
Analyzes funding rates across exchanges to determine market sentiment.

Extreme positive funding = overleveraged longs (contrarian short signal)
Extreme negative funding = overleveraged shorts (contrarian long signal)

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.market_state")


class FundingSentiment:
    """
    Derive market sentiment from perpetual futures funding rates.

    Funding rate > 0: Longs pay shorts (bullish consensus)
    Funding rate < 0: Shorts pay longs (bearish consensus)
    """

    # Thresholds (annualized-equivalent basis points)
    EXTREME_POSITIVE = 0.10   # >0.10% per 8h = extreme long
    EXTREME_NEGATIVE = -0.10  # <-0.10% per 8h = extreme short
    ELEVATED_POSITIVE = 0.05
    ELEVATED_NEGATIVE = -0.05

    def __init__(
        self,
        extreme_threshold: float = 0.10,
        lookback_periods: int = 90,
    ):
        self.extreme_threshold = extreme_threshold
        self.lookback_periods = lookback_periods

    def analyze(self, funding_rate: float) -> Dict[str, Any]:
        """
        Classify single funding rate reading.

        Args:
            funding_rate: Current 8h funding rate (e.g. 0.01 = 0.01%)

        Returns:
            Dict with sentiment, signal, and metadata
        """
        if funding_rate > self.extreme_threshold:
            sentiment = "extreme_long"
            signal = "contrarian_short"
            strength = min(1.0, funding_rate / (self.extreme_threshold * 2))
        elif funding_rate > self.ELEVATED_POSITIVE:
            sentiment = "elevated_long"
            signal = "cautious_long"
            strength = 0.5
        elif funding_rate < -self.extreme_threshold:
            sentiment = "extreme_short"
            signal = "contrarian_long"
            strength = min(1.0, abs(funding_rate) / (self.extreme_threshold * 2))
        elif funding_rate < self.ELEVATED_NEGATIVE:
            sentiment = "elevated_short"
            signal = "cautious_short"
            strength = 0.5
        else:
            sentiment = "neutral"
            signal = "no_signal"
            strength = 0.0

        return {
            "funding_rate": funding_rate,
            "sentiment": sentiment,
            "signal": signal,
            "strength": round(strength, 3),
            "is_extreme": abs(funding_rate) > self.extreme_threshold,
        }

    def analyze_history(self, funding_series: pd.Series) -> Dict[str, Any]:
        """
        Analyze funding rate time series for trends and reversals.

        Args:
            funding_series: Series of funding rates indexed by datetime

        Returns:
            Dict with trend, reversal signals, and statistics
        """
        if funding_series.empty or len(funding_series) < 3:
            return {"error": "insufficient_data", "min_required": 3}

        current = float(funding_series.iloc[-1])
        mean = float(funding_series.mean())
        std = float(funding_series.std())

        # Z-score of current reading
        z_score = (current - mean) / std if std > 0 else 0.0

        # Detect reversal: was positive, now negative (or vice versa)
        recent_3 = funding_series.tail(3)
        reversal = False
        reversal_type = None

        if len(recent_3) >= 3:
            prev_sign = np.sign(recent_3.iloc[0])
            curr_sign = np.sign(recent_3.iloc[-1])
            if prev_sign != curr_sign and prev_sign != 0:
                reversal = True
                reversal_type = (
                    "long_exhaustion" if prev_sign > 0
                    else "short_exhaustion"
                )

        # Trend: are rates consistently rising or falling?
        if len(funding_series) >= 5:
            recent_slope = np.polyfit(
                range(min(10, len(funding_series))),
                funding_series.tail(min(10, len(funding_series))).values,
                1,
            )[0]
        else:
            recent_slope = 0.0

        return {
            "current": self.analyze(current),
            "statistics": {
                "mean": round(mean, 6),
                "std": round(std, 6),
                "z_score": round(z_score, 2),
                "max": round(float(funding_series.max()), 6),
                "min": round(float(funding_series.min()), 6),
            },
            "reversal": {
                "detected": reversal,
                "type": reversal_type,
            },
            "trend_slope": round(float(recent_slope), 8),
        }

    def funding_divergence(
        self,
        funding_a: float,
        funding_b: float,
        symbol_a: str = "BTC",
        symbol_b: str = "ETH",
        threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Detect funding rate divergence between two symbols.

        Large divergence = pairs trade opportunity.

        Args:
            funding_a: Funding rate for symbol A
            funding_b: Funding rate for symbol B
            symbol_a:  Name of symbol A
            symbol_b:  Name of symbol B
            threshold: Min difference to trigger signal

        Returns:
            Divergence analysis
        """
        diff = funding_a - funding_b

        if abs(diff) < threshold:
            return {
                "signal": "no_divergence",
                "difference": round(diff, 6),
                "symbols": [symbol_a, symbol_b],
            }

        overpriced = symbol_a if diff > 0 else symbol_b
        underpriced = symbol_b if diff > 0 else symbol_a

        return {
            "signal": "divergence",
            "difference": round(abs(diff), 6),
            "overpriced": overpriced,
            "underpriced": underpriced,
            "trade": f"short_{overpriced}_long_{underpriced}",
            "rationale": (
                f"{overpriced} longs paying "
                f"{abs(diff)/min(abs(funding_a), abs(funding_b), 0.001):.1f}x "
                f"more funding than {underpriced}"
            ),
            "confidence": "high" if abs(diff) > threshold * 2 else "medium",
        }
