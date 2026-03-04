"""
Whale detection orchestrator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

import pandas as pd

from .flow import InstitutionalFlowTracker
from .options_flow import UnusualOptionsActivity
from .volume import VolumeAnomalyDetector


@dataclass(slots=True)
class WhaleSignal:
    source: str
    timestamp: str
    strength: float
    direction: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class WhaleReport:
    symbol: str
    generated_at_utc: str
    signals: List[WhaleSignal]
    summary: dict[str, Any]


class WhaleDetectionEngine:
    """Combines volume, signed flow, and options anomalies."""

    def __init__(
        self,
        volume_detector: VolumeAnomalyDetector | None = None,
        flow_tracker: InstitutionalFlowTracker | None = None,
        options_activity: UnusualOptionsActivity | None = None,
    ) -> None:
        self.volume_detector = volume_detector or VolumeAnomalyDetector()
        self.flow_tracker = flow_tracker or InstitutionalFlowTracker()
        self.options_activity = options_activity or UnusualOptionsActivity()

    def analyze(
        self,
        data: pd.DataFrame,
        symbol: str = "UNKNOWN",
        options_chain: Optional[pd.DataFrame] = None,
    ) -> WhaleReport:
        if data.empty:
            return WhaleReport(
                symbol=symbol,
                generated_at_utc=datetime.now(timezone.utc).isoformat(),
                signals=[],
                summary={"rows": 0, "signal_strength": 0.0},
            )

        signals: list[WhaleSignal] = []
        for event in self.volume_detector.detect(data):
            strength = min(1.0, event.relative_volume / 6.0)
            signals.append(
                WhaleSignal(
                    source="volume",
                    timestamp=str(event.timestamp),
                    strength=float(strength),
                    direction=event.direction,
                    metadata=event.metadata,
                )
            )

        for event in self.flow_tracker.detect(data):
            signals.append(
                WhaleSignal(
                    source="flow",
                    timestamp=str(event.timestamp),
                    strength=float(event.confidence),
                    direction=event.direction,
                    metadata={"net_flow_score": event.net_flow_score, **event.metadata},
                )
            )

        for event in self.options_activity.detect(options_chain):
            direction = "BULLISH" if event.contract_type == "call" else "BEARISH" if event.contract_type == "put" else "NEUTRAL"
            signals.append(
                WhaleSignal(
                    source="options",
                    timestamp=str(event.timestamp),
                    strength=float(event.confidence),
                    direction=direction,
                    metadata={
                        "type": event.contract_type,
                        "strike": event.strike,
                        "expiration": event.expiration,
                        "volume_oi_ratio": event.volume_oi_ratio,
                        **event.metadata,
                    },
                )
            )

        signals.sort(key=lambda item: item.strength, reverse=True)
        summary = {
            "rows": int(len(data)),
            "signal_count": int(len(signals)),
            "signal_strength": float(sum(s.strength for s in signals) / len(signals)) if signals else 0.0,
            "top_signal_source": signals[0].source if signals else None,
        }

        return WhaleReport(
            symbol=symbol,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            signals=signals,
            summary=summary,
        )

