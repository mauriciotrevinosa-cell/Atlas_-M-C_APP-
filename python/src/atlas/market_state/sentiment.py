"""
Market Sentiment Analysis

Builds a bounded sentiment score (-1 to 1) from market data and optional
external sentiment columns (news/social).

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SentimentScore:
    """Output schema for sentiment analysis."""

    score: float
    confidence: float
    source: str
    components: Dict[str, float] = field(default_factory=dict)


class SentimentAnalyzer:
    """
    Estimate market sentiment from price/volume and optional external features.

    Expected base columns:
      - Close (required)
      - Volume (optional but recommended)

    Optional external columns:
      - news_sentiment   (expected range -1..1)
      - social_sentiment (expected range -1..1)
    """

    def __init__(
        self,
        short_window: int = 5,
        long_window: int = 20,
        high_vol_threshold: float = 0.03,
    ):
        if short_window < 2:
            raise ValueError(f"short_window must be >= 2, got {short_window}")
        if long_window <= short_window:
            raise ValueError("long_window must be greater than short_window")
        if high_vol_threshold <= 0:
            raise ValueError("high_vol_threshold must be > 0")

        self.short_window = short_window
        self.long_window = long_window
        self.high_vol_threshold = high_vol_threshold
        logger.info(
            "Initialized SentimentAnalyzer(short=%s, long=%s, vol_thr=%.4f)",
            short_window,
            long_window,
            high_vol_threshold,
        )

    def analyze(self, data: pd.DataFrame) -> SentimentScore:
        """
        Analyze sentiment from an OHLCV-like DataFrame.

        Returns neutral low-confidence score when data is empty.
        """
        if data is None or data.empty:
            return SentimentScore(
                score=0.0,
                confidence=0.0,
                source="empty",
                components={},
            )

        close = self._select_series(data, "close")
        if close is None:
            raise ValueError("SentimentAnalyzer requires Close/close column")

        close = close.astype(float)
        returns = close.pct_change().dropna()
        if returns.empty:
            return SentimentScore(
                score=0.0,
                confidence=0.1,
                source="price_action",
                components={"price_action": 0.0},
            )

        components: List[tuple[str, float, float]] = []
        source_parts: List[str] = []

        price_score = self._price_action_score(close)
        components.append(("price_action", price_score, 0.65))
        source_parts.append("price_action")

        volume_score = self._volume_confirmation_score(data=data, returns=returns)
        if volume_score is not None:
            components.append(("volume", volume_score, 0.15))
            source_parts.append("volume")

        news_score = self._external_score(data, "news_sentiment")
        if news_score is not None:
            components.append(("news", news_score, 0.10))
            source_parts.append("news")

        social_score = self._external_score(data, "social_sentiment")
        if social_score is not None:
            components.append(("social", social_score, 0.10))
            source_parts.append("social")

        score = self._weighted_score(components)
        confidence = self._estimate_confidence(
            returns=returns,
            n_rows=len(data),
            component_values=[value for _, value, _ in components],
            has_external=("news" in source_parts or "social" in source_parts),
        )

        result = SentimentScore(
            score=float(np.clip(score, -1.0, 1.0)),
            confidence=float(np.clip(confidence, 0.0, 1.0)),
            source="+".join(source_parts),
            components={name: float(value) for name, value, _ in components},
        )
        logger.debug(
            "Sentiment score=%.4f confidence=%.4f source=%s",
            result.score,
            result.confidence,
            result.source,
        )
        return result

    def _price_action_score(self, close: pd.Series) -> float:
        short_n = min(self.short_window, len(close))
        long_n = min(self.long_window, len(close))

        short_ret = close.iloc[-1] / close.iloc[-short_n] - 1.0 if short_n > 1 else 0.0
        long_ret = close.iloc[-1] / close.iloc[-long_n] - 1.0 if long_n > 1 else 0.0

        recent = close.pct_change().tail(long_n).dropna()
        trend_consistency = 0.0
        if not recent.empty:
            up_ratio = float((recent > 0).mean())
            trend_consistency = (up_ratio * 2.0) - 1.0

        raw = (3.0 * short_ret) + (2.0 * long_ret) + (0.75 * trend_consistency)
        return float(np.tanh(raw))

    def _volume_confirmation_score(
        self,
        data: pd.DataFrame,
        returns: pd.Series,
    ) -> float | None:
        volume = self._select_series(data, "volume")
        if volume is None:
            return None

        volume = volume.astype(float)
        lookback = min(self.long_window, len(volume))
        if lookback < 3:
            return None

        recent = volume.tail(lookback)
        avg = recent.mean()
        if avg <= 0:
            return 0.0

        vol_ratio = float(recent.iloc[-1] / avg)
        ret_direction = float(np.sign(returns.tail(self.short_window).mean()))
        confirmation = (vol_ratio - 1.0) * ret_direction
        return float(np.tanh(confirmation))

    def _external_score(self, data: pd.DataFrame, column: str) -> float | None:
        if column not in data.columns:
            return None
        value = data[column].dropna()
        if value.empty:
            return None
        return float(np.clip(value.iloc[-1], -1.0, 1.0))

    def _weighted_score(self, components: List[tuple[str, float, float]]) -> float:
        if not components:
            return 0.0
        total_weight = sum(weight for _, _, weight in components)
        if total_weight <= 0:
            return 0.0
        weighted = sum(value * weight for _, value, weight in components)
        return weighted / total_weight

    def _estimate_confidence(
        self,
        returns: pd.Series,
        n_rows: int,
        component_values: List[float],
        has_external: bool,
    ) -> float:
        # Data sufficiency: ramps to 1 around long_window bars.
        length_factor = min(float(n_rows) / float(self.long_window), 1.0)

        # Component agreement: lower dispersion -> higher agreement.
        if component_values:
            dispersion = float(np.std(component_values))
            agreement = float(np.clip(1.0 - (dispersion / 1.5), 0.0, 1.0))
        else:
            agreement = 0.0

        # Stable volatility tends to improve confidence.
        recent_vol = float(returns.tail(self.long_window).std()) if not returns.empty else 0.0
        vol_penalty = float(np.clip(recent_vol / self.high_vol_threshold, 0.0, 1.0))
        stability = 1.0 - (0.5 * vol_penalty)

        external_bonus = 0.08 if has_external else 0.0

        confidence = (
            0.20
            + (0.45 * length_factor)
            + (0.22 * agreement)
            + (0.13 * stability)
            + external_bonus
        )
        return confidence

    def _select_series(self, data: pd.DataFrame, base_name: str) -> pd.Series | None:
        direct = data.get(base_name)
        if direct is not None:
            return direct

        title = base_name.capitalize()
        titled = data.get(title)
        if titled is not None:
            return titled

        upper = data.get(base_name.upper())
        if upper is not None:
            return upper

        return None
