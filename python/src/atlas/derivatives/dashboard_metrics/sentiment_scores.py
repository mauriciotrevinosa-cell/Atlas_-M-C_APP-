"""
Derivatives Sentiment Scores — Phase 12.3
Aggregates funding, OI, LSR into a composite derivatives sentiment score.
"""
from typing import Dict, Optional


class DerivativesSentimentScorer:
    """
    Combines multiple derivatives signals into a single sentiment score.

    Score range: -1.0 (extreme bearish) to +1.0 (extreme bullish)
    Based on: funding rates, OI/price divergence, long/short ratio

    Output:
        {
            'funding_score': -0.8,
            'oi_score': 0.2,
            'lsr_score': -0.6,
            'composite_score': -0.4,
            'sentiment': 'bearish',
            'description': '...'
        }
    """

    def __init__(self):
        # Weights for composite score
        self._weights = {
            "funding": 0.40,
            "oi": 0.30,
            "lsr": 0.30,
        }

    def score_funding(self, funding_rate: float) -> float:
        """
        Convert funding rate to sentiment score (-1 to 1).
        Positive funding → longs overheated → bearish sentiment score
        """
        # Clamp to [-0.3%, +0.3%] range
        clamped = max(-0.3, min(0.3, funding_rate))
        # Invert: high positive funding = bearish contrarian signal
        return -clamped / 0.3

    def score_oi(self, oi_pattern: str) -> float:
        """Convert OI pattern classification to sentiment score."""
        mapping = {
            "strong_bullish": 0.8,
            "short_covering": 0.4,
            "neutral": 0.0,
            "distribution": -0.4,
            "capitulation": -0.6,
            "unknown": 0.0,
        }
        return mapping.get(oi_pattern, 0.0)

    def score_lsr(self, long_pct: float) -> float:
        """
        Convert LSR to sentiment score (contrarian).
        High long% → bearish sentiment (too bullish = contrarian short)
        """
        # 50% = neutral (0), 70% = extreme long = score -1, 30% = extreme short = score +1
        return -(long_pct - 50) / 20  # Scale: 70% → -1, 30% → +1
        # Clamp
        return max(-1.0, min(1.0, -(long_pct - 50) / 20))

    def compute(
        self,
        funding_rate: Optional[float] = None,
        oi_pattern: Optional[str] = None,
        long_pct: Optional[float] = None,
    ) -> Dict:
        """
        Compute composite derivatives sentiment score.

        Args:
            funding_rate: Current funding rate % (e.g. 0.05)
            oi_pattern: OI/Price pattern from OIAnalysis
            long_pct: Long/Short ratio long percentage (0-100)

        Returns:
            Sentiment score dict
        """
        scores = {}
        weighted_sum = 0.0
        total_weight = 0.0

        if funding_rate is not None:
            s = round(self.score_funding(funding_rate), 3)
            scores["funding_score"] = s
            weighted_sum += s * self._weights["funding"]
            total_weight += self._weights["funding"]

        if oi_pattern is not None:
            s = round(self.score_oi(oi_pattern), 3)
            scores["oi_score"] = s
            weighted_sum += s * self._weights["oi"]
            total_weight += self._weights["oi"]

        if long_pct is not None:
            s = round(max(-1.0, min(1.0, self.score_lsr(long_pct))), 3)
            scores["lsr_score"] = s
            weighted_sum += s * self._weights["lsr"]
            total_weight += self._weights["lsr"]

        composite = round(weighted_sum / total_weight, 3) if total_weight > 0 else 0.0

        if composite > 0.5:
            sentiment = "strong_bullish"
        elif composite > 0.2:
            sentiment = "bullish"
        elif composite < -0.5:
            sentiment = "strong_bearish"
        elif composite < -0.2:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        return {
            **scores,
            "composite_score": composite,
            "sentiment": sentiment,
            "description": (
                f"Derivatives sentiment: {sentiment.upper()} "
                f"(score={composite:+.3f})"
            ),
        }
