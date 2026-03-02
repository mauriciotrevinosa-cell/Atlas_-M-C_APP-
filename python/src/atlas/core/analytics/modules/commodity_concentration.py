"""
Demo commodity concentration monitor module.
"""

from __future__ import annotations

from collections import deque
from random import Random

from atlas.core.analytics.artifacts import Artifact, ArtifactType
from atlas.core.analytics.modules.base import AnalysisModule, ArtifactPublisher, SimulationTickContext


class CommodityConcentrationMonitorModule(AnalysisModule):
    module_id = "commodity_concentration"
    title = "Commodity Concentration Monitor"
    description = "Tracks concentration risk and emits threshold alerts."

    def __init__(self, threshold: float = 65.0, seed: int = 13, max_points: int = 180) -> None:
        self.threshold = threshold
        self._rng = Random(seed)
        self._weights = {
            "Gold": 0.32,
            "Oil": 0.28,
            "Copper": 0.23,
            "Lithium": 0.17,
        }
        self._history: deque[tuple[int, float]] = deque(maxlen=max_points)

    def on_tick(self, context: SimulationTickContext, publish: ArtifactPublisher) -> None:
        for commodity in self._weights:
            self._weights[commodity] = max(
                0.05,
                self._weights[commodity] + self._rng.uniform(-0.025, 0.025),
            )

        total_weight = sum(self._weights.values())
        for commodity in self._weights:
            self._weights[commodity] /= total_weight

        concentration_hhi = sum((weight * 100.0) ** 2 for weight in self._weights.values()) / 100.0
        concentration_score = round(concentration_hhi, 2)
        self._history.append((context.tick, concentration_score))
        top_commodity = max(self._weights, key=self._weights.get)

        status = "normal"
        severity = "info"
        if concentration_score >= 80:
            status = "critical"
            severity = "error"
        elif concentration_score >= self.threshold:
            status = "warning"
            severity = "warning"

        publish(
            Artifact(
                artifact_type=ArtifactType.SCALAR,
                title="Concentration Gauge",
                module_id=self.module_id,
                payload={
                    "value": concentration_score,
                    "unit": "hhi",
                    "min": 0.0,
                    "max": 100.0,
                    "threshold": self.threshold,
                    "status": status,
                },
                tags=["concentration", "scalar", "gauge"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.TABLE,
                title="Commodity Weights",
                module_id=self.module_id,
                payload={
                    "columns": ["Commodity", "Weight (%)"],
                    "rows": [
                        [commodity, round(weight * 100.0, 2)]
                        for commodity, weight in sorted(
                            self._weights.items(),
                            key=lambda item: item[1],
                            reverse=True,
                        )
                    ],
                },
                tags=["concentration", "table"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.TIMESERIES,
                title="Concentration Trend",
                module_id=self.module_id,
                payload={
                    "points": [
                        {"x": tick, "y": score, "series": "concentration_hhi"}
                        for tick, score in self._history
                    ],
                    "x_label": "tick",
                    "y_label": "hhi",
                },
                tags=["concentration", "timeseries"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.LOG,
                title="Concentration Engine Log",
                module_id=self.module_id,
                payload={
                    "message": (
                        f"tick={context.tick} hhi={concentration_score:.2f} "
                        f"top={top_commodity}={self._weights[top_commodity] * 100.0:.2f}%"
                    ),
                    "values": {
                        "concentration_hhi": concentration_score,
                        "top_commodity": top_commodity,
                        "top_weight_pct": round(self._weights[top_commodity] * 100.0, 2),
                    },
                },
                tags=["log", "diagnostic"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        if severity != "info":
            publish(
                Artifact(
                    artifact_type=ArtifactType.EVENT,
                    title="Concentration Threshold Event",
                    module_id=self.module_id,
                    payload={
                        "message": (
                            f"Concentration score {concentration_score:.2f} exceeds "
                            f"threshold {self.threshold:.2f}"
                        ),
                        "severity": severity,
                    },
                    tags=["alert", "concentration"],
                    published_by=self.module_id,
                    tick=context.tick,
                )
            )

