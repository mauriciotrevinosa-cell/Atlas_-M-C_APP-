"""
Memory & Calibration System
=============================
Stores trading experiences and calibrates model confidence over time.

Copyright (c) 2026 M&C. All rights reserved.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("atlas.memory")


class ExperienceStore:
    """
    Persistent store for trading experiences (signals → outcomes).
    Used for model calibration and learning.
    """

    def __init__(self, store_path: str = "data/memory/experiences.jsonl"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        signal: Dict[str, Any],
        outcome: Dict[str, Any],
        metadata: Optional[Dict] = None,
    ):
        """
        Record a signal → outcome pair.

        Args:
            signal:   The signal that was generated
            outcome:  What actually happened (pnl, direction correct, etc.)
            metadata: Additional context (market state, timestamp, etc.)
        """
        entry = {
            "timestamp": time.time(),
            "signal": signal,
            "outcome": outcome,
            "metadata": metadata or {},
        }

        with open(self.store_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        logger.debug("Experience recorded: %s → %s", signal.get("direction"), outcome.get("correct"))

    def load_all(self) -> List[Dict[str, Any]]:
        """Load all experiences."""
        if not self.store_path.exists():
            return []

        experiences = []
        with open(self.store_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        experiences.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return experiences

    def load_recent(self, n: int = 100) -> List[Dict[str, Any]]:
        """Load last N experiences."""
        all_exp = self.load_all()
        return all_exp[-n:]

    def stats(self) -> Dict[str, Any]:
        """Get experience store statistics."""
        experiences = self.load_all()
        if not experiences:
            return {"total": 0}

        correct = sum(1 for e in experiences if e.get("outcome", {}).get("correct", False))
        return {
            "total": len(experiences),
            "correct": correct,
            "accuracy": round(correct / len(experiences), 3) if experiences else 0,
            "oldest": experiences[0].get("timestamp"),
            "newest": experiences[-1].get("timestamp"),
        }


class CalibrationEngine:
    """
    Calibrate model confidence based on historical accuracy.

    If a model says "80% confident" but is only right 60% of the time,
    we should discount its confidence by 0.75 (60/80).
    """

    def __init__(self, experience_store: ExperienceStore):
        self.store = experience_store
        self._calibration_map: Dict[str, float] = {}

    def calibrate(self, min_samples: int = 20) -> Dict[str, float]:
        """
        Build calibration map from experiences.

        Returns:
            Dict of source_name → calibration_factor (multiply confidence by this)
        """
        experiences = self.store.load_all()
        if not experiences:
            return {}

        # Group by signal source
        by_source: Dict[str, List] = {}
        for exp in experiences:
            source = exp.get("signal", {}).get("source", "unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(exp)

        calibration = {}
        for source, exps in by_source.items():
            if len(exps) < min_samples:
                calibration[source] = 1.0  # Not enough data, no adjustment
                continue

            # Average stated confidence vs actual accuracy
            avg_confidence = sum(
                e.get("signal", {}).get("confidence", 0.5) for e in exps
            ) / len(exps)

            actual_accuracy = sum(
                1 for e in exps if e.get("outcome", {}).get("correct", False)
            ) / len(exps)

            # Calibration factor
            factor = actual_accuracy / avg_confidence if avg_confidence > 0 else 1.0
            calibration[source] = round(min(factor, 2.0), 3)  # Cap at 2x

        self._calibration_map = calibration
        logger.info("Calibration updated: %s", calibration)
        return calibration

    def adjust_confidence(self, source: str, raw_confidence: float) -> float:
        """Apply calibration to a confidence score."""
        factor = self._calibration_map.get(source, 1.0)
        adjusted = raw_confidence * factor
        return round(min(max(adjusted, 0.0), 1.0), 3)
