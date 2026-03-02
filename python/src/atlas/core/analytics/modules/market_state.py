"""
Demo market-state module that publishes observable artifacts every tick.
"""

from __future__ import annotations

from collections import deque
from math import cos, sin
from random import Random

from atlas.core.analytics.artifacts import Artifact, ArtifactType
from atlas.core.analytics.modules.base import AnalysisModule, ArtifactPublisher, SimulationTickContext


class MarketStateModule(AnalysisModule):
    module_id = "market_state"
    title = "Market State"
    description = "Publishes regime probabilities and a synthetic risk score."

    def __init__(self, seed: int = 7, max_points: int = 180) -> None:
        self._rng = Random(seed)
        self._risk_history: deque[tuple[int, float]] = deque(maxlen=max_points)

    def on_tick(self, context: SimulationTickContext, publish: ArtifactPublisher) -> None:
        trend_raw = 0.45 + 0.22 * sin(context.tick / 5.0) + self._rng.uniform(-0.03, 0.03)
        range_raw = 0.35 + 0.18 * cos(context.tick / 8.0) + self._rng.uniform(-0.03, 0.03)
        stress_raw = 0.20 + self._rng.uniform(-0.03, 0.03)

        total = max(trend_raw + range_raw + stress_raw, 1e-9)
        trend_prob = max(0.0, trend_raw / total)
        range_prob = max(0.0, range_raw / total)
        stress_prob = max(0.0, stress_raw / total)

        risk_score = round(min(100.0, max(0.0, stress_prob * 100.0 + self._rng.uniform(-4.0, 4.0))), 2)
        self._risk_history.append((context.tick, risk_score))

        publish(
            Artifact(
                artifact_type=ArtifactType.HISTOGRAM,
                title="Regime Probabilities",
                module_id=self.module_id,
                payload={
                    "bins": ["Trending", "Ranging", "Stressed"],
                    "counts": [
                        round(trend_prob * 100.0, 2),
                        round(range_prob * 100.0, 2),
                        round(stress_prob * 100.0, 2),
                    ],
                    "unit": "percent",
                },
                tags=["regime", "histogram", "demo"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        status = "normal"
        if risk_score >= 80:
            status = "critical"
        elif risk_score >= 65:
            status = "warning"

        publish(
            Artifact(
                artifact_type=ArtifactType.SCALAR,
                title="Risk Score",
                module_id=self.module_id,
                payload={
                    "value": risk_score,
                    "unit": "score",
                    "min": 0.0,
                    "max": 100.0,
                    "threshold": 65.0,
                    "status": status,
                },
                tags=["risk", "scalar"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.TIMESERIES,
                title="Risk Score Trend",
                module_id=self.module_id,
                payload={
                    "points": [
                        {"x": tick, "y": score, "series": "risk_score"}
                        for tick, score in self._risk_history
                    ],
                    "x_label": "tick",
                    "y_label": "risk_score",
                },
                tags=["risk", "timeseries"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.LOG,
                title="Risk Engine Log",
                module_id=self.module_id,
                payload={
                    "message": (
                        f"tick={context.tick} trend={trend_prob:.2f} range={range_prob:.2f} "
                        f"stress={stress_prob:.2f} risk={risk_score:.2f}"
                    ),
                    "values": {
                        "trend_prob": round(trend_prob, 4),
                        "range_prob": round(range_prob, 4),
                        "stress_prob": round(stress_prob, 4),
                        "risk_score": risk_score,
                    },
                },
                tags=["log", "diagnostic"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        if status in {"warning", "critical"}:
            publish(
                Artifact(
                    artifact_type=ArtifactType.EVENT,
                    title="Risk Threshold Event",
                    module_id=self.module_id,
                    payload={
                        "message": f"Risk score {risk_score:.2f} crossed threshold 65",
                        "severity": "error" if status == "critical" else "warning",
                    },
                    tags=["alert", "risk"],
                    published_by=self.module_id,
                    tick=context.tick,
                )
            )

