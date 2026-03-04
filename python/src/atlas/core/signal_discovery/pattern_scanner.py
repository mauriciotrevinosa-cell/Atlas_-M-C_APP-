"""
Pattern scanning utilities for signal discovery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

import numpy as np
import pandas as pd


@dataclass(slots=True)
class PatternResult:
    name: str
    strength: float
    hit_rate: float
    samples: int
    metadata: dict[str, Any] = field(default_factory=dict)


class PatternScanner:
    """Detects simple statistically testable price patterns."""

    def __init__(self, min_samples: int = 12) -> None:
        self.min_samples = int(min_samples)

    def scan(self, data: pd.DataFrame, horizon: int = 5) -> List[PatternResult]:
        if data.empty or len(data) < max(40, horizon + 3):
            return []

        close = _series(data, "close")
        volume = _series(data, "volume").fillna(0.0)
        returns = close.pct_change()
        future = close.pct_change(horizon).shift(-horizon)
        out: list[PatternResult] = []

        # Gap continuation proxy
        prev_close = close.shift(1)
        gap_pct = (data[_col(data, "open")] - prev_close) / prev_close
        mask_gap_up = gap_pct > 0.01
        mask_gap_down = gap_pct < -0.01
        out.extend(
            [
                self._evaluate_pattern("gap_up_continuation", mask_gap_up, future),
                self._evaluate_pattern("gap_down_continuation", mask_gap_down, -future),
            ]
        )

        # Breakout with volume confirmation
        breakout = close > close.rolling(20, min_periods=20).max().shift(1)
        vol_confirm = volume > volume.rolling(20, min_periods=20).mean() * 1.2
        out.append(self._evaluate_pattern("volume_breakout", breakout & vol_confirm, future))

        # Short-term mean reversion
        z = (returns - returns.rolling(20, min_periods=20).mean()) / (
            returns.rolling(20, min_periods=20).std().replace(0, np.nan)
        )
        out.append(self._evaluate_pattern("mean_reversion_long", z < -1.5, future))
        out.append(self._evaluate_pattern("mean_reversion_short", z > 1.5, -future))

        filtered = [p for p in out if p.samples >= self.min_samples and p.strength > 0]
        filtered.sort(key=lambda p: p.strength, reverse=True)
        return filtered

    def _evaluate_pattern(self, name: str, mask: pd.Series, target: pd.Series) -> PatternResult:
        aligned = pd.DataFrame({"mask": mask.astype(bool), "target": target}).dropna()
        subset = aligned[aligned["mask"]]
        samples = int(len(subset))
        if samples == 0:
            return PatternResult(name=name, strength=0.0, hit_rate=0.0, samples=0)

        vals = subset["target"].to_numpy(dtype=float)
        hit_rate = float(np.mean(vals > 0))
        effect = float(np.mean(vals))
        # Balanced score: favors both hit-rate quality and return magnitude
        strength = max(0.0, (hit_rate - 0.5) * 2.0 * min(1.0, abs(effect) * 20.0))

        return PatternResult(
            name=name,
            strength=float(strength),
            hit_rate=hit_rate,
            samples=samples,
            metadata={
                "avg_forward_return": effect,
                "median_forward_return": float(np.median(vals)),
            },
        )


def _col(frame: pd.DataFrame, name: str) -> str:
    lower_map = {c.lower(): c for c in frame.columns}
    key = name.lower()
    if key not in lower_map:
        raise KeyError(f"Required column '{name}' not found")
    return lower_map[key]


def _series(frame: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(frame[_col(frame, name)], errors="coerce")

