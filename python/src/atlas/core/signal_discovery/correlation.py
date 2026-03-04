"""
Correlation-based signal search.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd


@dataclass(slots=True)
class CorrelationResult:
    feature: str
    lag: int
    correlation: float
    samples: int
    direction: str


class CorrelationFinder:
    """Searches lead/lag correlations between candidate features and target returns."""

    def find(
        self,
        feature_frame: pd.DataFrame,
        target: pd.Series,
        max_lag: int = 5,
        min_abs_corr: float = 0.15,
    ) -> List[CorrelationResult]:
        if feature_frame.empty or target.empty:
            return []

        target = pd.to_numeric(target, errors="coerce")
        out: list[CorrelationResult] = []

        for feature in feature_frame.columns:
            x = pd.to_numeric(feature_frame[feature], errors="coerce")
            best: CorrelationResult | None = None

            for lag in range(-max_lag, max_lag + 1):
                shifted = x.shift(lag)
                joined = pd.DataFrame({"x": shifted, "y": target}).dropna()
                n = len(joined)
                if n < 30:
                    continue
                corr = float(joined["x"].corr(joined["y"]))
                if np.isnan(corr) or abs(corr) < min_abs_corr:
                    continue

                result = CorrelationResult(
                    feature=str(feature),
                    lag=int(lag),
                    correlation=corr,
                    samples=int(n),
                    direction="positive" if corr >= 0 else "negative",
                )
                if best is None or abs(result.correlation) > abs(best.correlation):
                    best = result

            if best is not None:
                out.append(best)

        out.sort(key=lambda r: abs(r.correlation), reverse=True)
        return out

