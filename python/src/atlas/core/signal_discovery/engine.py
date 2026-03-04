"""
Automated signal discovery orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List

import pandas as pd

from .correlation import CorrelationFinder, CorrelationResult
from .feature_ranker import FeatureImportance, FeatureRanker
from .pattern_scanner import PatternResult, PatternScanner


@dataclass(slots=True)
class DiscoveredSignal:
    name: str
    score: float
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DiscoveryReport:
    generated_at_utc: str
    signals: List[DiscoveredSignal]
    pattern_results: List[PatternResult]
    correlations: List[CorrelationResult]
    feature_importance: List[FeatureImportance]


class SignalDiscoveryEngine:
    """Discovers candidate signals from historical OHLCV data."""

    def __init__(
        self,
        pattern_scanner: PatternScanner | None = None,
        correlation_finder: CorrelationFinder | None = None,
        feature_ranker: FeatureRanker | None = None,
    ) -> None:
        self.pattern_scanner = pattern_scanner or PatternScanner()
        self.correlation_finder = correlation_finder or CorrelationFinder()
        self.feature_ranker = feature_ranker or FeatureRanker()

    def discover(
        self,
        data: pd.DataFrame,
        max_signals: int = 20,
        target_horizon: int = 5,
    ) -> DiscoveryReport:
        if data.empty:
            return DiscoveryReport(
                generated_at_utc=datetime.now(timezone.utc).isoformat(),
                signals=[],
                pattern_results=[],
                correlations=[],
                feature_importance=[],
            )

        features, target = self._build_feature_frame(data, target_horizon=target_horizon)
        pattern_results = self.pattern_scanner.scan(data, horizon=target_horizon)
        correlations = self.correlation_finder.find(features, target)
        feature_importance = self.feature_ranker.rank(features, target)

        signals: list[DiscoveredSignal] = []
        for pattern in pattern_results:
            signals.append(
                DiscoveredSignal(
                    name=f"pattern::{pattern.name}",
                    score=float(pattern.strength),
                    rationale=f"hit_rate={pattern.hit_rate:.2f}, samples={pattern.samples}",
                    metadata=pattern.metadata,
                )
            )
        for corr in correlations[:10]:
            signals.append(
                DiscoveredSignal(
                    name=f"corr::{corr.feature}",
                    score=float(abs(corr.correlation)),
                    rationale=f"lag={corr.lag}, corr={corr.correlation:.3f}, n={corr.samples}",
                    metadata={"direction": corr.direction},
                )
            )
        for feat in feature_importance[:10]:
            signals.append(
                DiscoveredSignal(
                    name=f"feature::{feat.feature}",
                    score=float(feat.score),
                    rationale=f"spearman={feat.correlation:.3f}, stability={feat.stability:.2f}",
                    metadata={"samples": feat.samples},
                )
            )

        signals.sort(key=lambda s: s.score, reverse=True)
        signals = signals[: max(1, int(max_signals))]

        return DiscoveryReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            signals=signals,
            pattern_results=pattern_results,
            correlations=correlations,
            feature_importance=feature_importance,
        )

    def _build_feature_frame(
        self,
        data: pd.DataFrame,
        target_horizon: int,
    ) -> tuple[pd.DataFrame, pd.Series]:
        close = _series(data, "close")
        high = _series(data, "high")
        low = _series(data, "low")
        volume = _series(data, "volume").fillna(0.0)

        returns_1d = close.pct_change()
        features = pd.DataFrame(index=data.index)
        features["ret_1d"] = returns_1d
        features["ret_5d"] = close.pct_change(5)
        features["ret_20d"] = close.pct_change(20)
        features["vol_20d"] = returns_1d.rolling(20, min_periods=20).std()
        features["range_pct"] = (high - low) / close.replace(0, pd.NA)
        features["close_vs_sma20"] = close / close.rolling(20, min_periods=20).mean() - 1.0
        features["volume_z"] = (
            volume - volume.rolling(20, min_periods=20).mean()
        ) / volume.rolling(20, min_periods=20).std().replace(0, pd.NA)

        target = close.pct_change(target_horizon).shift(-target_horizon)
        return features, target


def _col(frame: pd.DataFrame, name: str) -> str:
    lower_map = {c.lower(): c for c in frame.columns}
    key = name.lower()
    if key not in lower_map:
        raise KeyError(f"Required column '{name}' not found")
    return lower_map[key]


def _series(frame: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(frame[_col(frame, name)], errors="coerce")

