"""
Orchestrator for intraday pattern detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List

import numpy as np
import pandas as pd

from .gap_analyzer import GapAnalyzer
from .opening_drive import OpeningDriveDetector
from .session_model import SessionVolatilityModel


@dataclass(slots=True)
class IntradayPattern:
    pattern_type: str
    timestamp: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class IntradayReport:
    symbol: str
    generated_at_utc: str
    patterns: List[IntradayPattern]
    summary: dict[str, Any]


class IntradayPatternEngine:
    """Combines gap, opening-drive, and session volatility context."""

    def __init__(
        self,
        gap_analyzer: GapAnalyzer | None = None,
        opening_drive: OpeningDriveDetector | None = None,
        session_model: SessionVolatilityModel | None = None,
    ) -> None:
        self.gap_analyzer = gap_analyzer or GapAnalyzer()
        self.opening_drive = opening_drive or OpeningDriveDetector()
        self.session_model = session_model or SessionVolatilityModel()

    def analyze(self, data: pd.DataFrame, symbol: str = "UNKNOWN") -> IntradayReport:
        if data.empty:
            return IntradayReport(
                symbol=symbol,
                generated_at_utc=datetime.now(timezone.utc).isoformat(),
                patterns=[],
                summary={"rows": 0, "signal_strength": 0.0},
            )

        patterns: list[IntradayPattern] = []

        gap = self.gap_analyzer.latest_event(data)
        if gap is not None:
            score = min(
                1.0,
                abs(gap.gap_pct) * 20.0 * max(0.5, gap.opening_volume_ratio / 2.0),
            )
            patterns.append(
                IntradayPattern(
                    pattern_type="gap_continuation",
                    timestamp=str(gap.timestamp),
                    score=float(score),
                    payload={
                        "gap_type": gap.gap_type.value,
                        "gap_pct": gap.gap_pct,
                        "opening_volume_ratio": gap.opening_volume_ratio,
                        "continuation_probability": gap.continuation_probability,
                    },
                )
            )

        drive = self.opening_drive.latest_signal(data)
        if drive is not None:
            patterns.append(
                IntradayPattern(
                    pattern_type="opening_drive",
                    timestamp=str(drive.timestamp),
                    score=float(min(1.0, drive.confidence)),
                    payload={
                        "direction": drive.direction,
                        "move_pct": drive.move_pct,
                        "strength": drive.strength,
                        "confidence": drive.confidence,
                    },
                )
            )

        session = self.session_model.fit(data)
        session_score = (
            0.8 if session.volatility_regime == "high" else 0.4 if session.volatility_regime == "normal" else 0.2
        )
        patterns.append(
            IntradayPattern(
                pattern_type="session_volatility",
                timestamp=str(data.index[-1]),
                score=float(session_score),
                payload={
                    "current_session": session.current_session,
                    "current_volatility": session.current_volatility,
                    "volatility_regime": session.volatility_regime,
                    "by_session": session.by_session,
                },
            )
        )

        signal_strength = float(np.mean([p.score for p in patterns])) if patterns else 0.0
        summary = {
            "rows": int(len(data)),
            "patterns_found": int(len(patterns)),
            "signal_strength": signal_strength,
            "latest_close": float(_close(data).iloc[-1]),
        }

        return IntradayReport(
            symbol=symbol,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            patterns=patterns,
            summary=summary,
        )


def _close(frame: pd.DataFrame) -> pd.Series:
    lower_map = {c.lower(): c for c in frame.columns}
    col = lower_map.get("close")
    if col is None:
        raise KeyError("Required column 'close' not found")
    return pd.to_numeric(frame[col], errors="coerce")

