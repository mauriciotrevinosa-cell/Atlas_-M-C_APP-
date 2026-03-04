"""
Feature ranking by predictive relevance and stability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


@dataclass(slots=True)
class FeatureImportance:
    feature: str
    score: float
    correlation: float
    stability: float
    samples: int


class FeatureRanker:
    """Ranks features by out-of-sample friendly statistics (correlation + stability)."""

    def rank(
        self,
        feature_frame: pd.DataFrame,
        target: pd.Series,
        min_samples: int = 40,
    ) -> List[FeatureImportance]:
        if feature_frame.empty or target.empty:
            return []

        target = pd.to_numeric(target, errors="coerce")
        out: list[FeatureImportance] = []

        for feature in feature_frame.columns:
            x = pd.to_numeric(feature_frame[feature], errors="coerce")
            joined = pd.DataFrame({"x": x, "y": target}).dropna()
            n = len(joined)
            if n < min_samples:
                continue

            corr = float(joined["x"].corr(joined["y"], method="spearman"))
            if np.isnan(corr):
                continue

            half = n // 2
            corr_1 = float(joined.iloc[:half]["x"].corr(joined.iloc[:half]["y"], method="spearman"))
            corr_2 = float(joined.iloc[half:]["x"].corr(joined.iloc[half:]["y"], method="spearman"))
            corr_1 = 0.0 if np.isnan(corr_1) else corr_1
            corr_2 = 0.0 if np.isnan(corr_2) else corr_2
            stability = max(0.0, 1.0 - abs(corr_1 - corr_2))

            score = abs(corr) * stability * min(1.0, n / 250.0)
            out.append(
                FeatureImportance(
                    feature=str(feature),
                    score=float(score),
                    correlation=float(corr),
                    stability=float(stability),
                    samples=int(n),
                )
            )

        out.sort(key=lambda item: item.score, reverse=True)
        return out

