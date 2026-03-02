"""
Discrepancy Analysis
=====================
Detects when different analysis engines disagree.
Disagreement often precedes regime changes or volatility events.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger("atlas.discrepancy")


class DiscrepancyAnalyzer:
    """
    Analyze disagreements between engines/signals.

    High discrepancy = uncertainty = reduce position size or stay flat.
    """

    def __init__(self, warning_threshold: float = 0.4, critical_threshold: float = 0.7):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold

    def analyze(self, engine_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare outputs from multiple engines.

        Args:
            engine_outputs: Dict of engine_name → {"direction": ..., "confidence": ...}

        Returns:
            Discrepancy report
        """
        if len(engine_outputs) < 2:
            return {"discrepancy_score": 0.0, "level": "none", "detail": "Need 2+ engines"}

        directions = []
        confidences = []
        for name, output in engine_outputs.items():
            d = output.get("direction", "neutral")
            c = output.get("confidence", 0.5)
            numeric = c if d == "long" else (-c if d == "short" else 0)
            directions.append(numeric)
            confidences.append(c)

        # Discrepancy = standard deviation of numeric signals (normalized)
        std = float(np.std(directions))
        score = min(1.0, std * 2)  # Scale: 0.5 std → 1.0 discrepancy

        if score >= self.critical_threshold:
            level = "critical"
            action = "stay_flat"
        elif score >= self.warning_threshold:
            level = "warning"
            action = "reduce_size"
        else:
            level = "low"
            action = "proceed"

        # Identify the outliers
        mean_dir = float(np.mean(directions))
        outliers = []
        for name, output in engine_outputs.items():
            d = output.get("direction", "neutral")
            c = output.get("confidence", 0.5)
            numeric = c if d == "long" else (-c if d == "short" else 0)
            if abs(numeric - mean_dir) > std:
                outliers.append(name)

        return {
            "discrepancy_score": round(score, 3),
            "level": level,
            "recommended_action": action,
            "engines_analyzed": len(engine_outputs),
            "outlier_engines": outliers,
            "mean_direction": round(mean_dir, 3),
            "direction_std": round(std, 3),
        }
