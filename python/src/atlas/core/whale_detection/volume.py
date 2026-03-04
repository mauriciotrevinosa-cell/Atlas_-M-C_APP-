"""
Atlas - Whale Detection Engine: Volume Anomaly Detector
Detects unusual volume spikes indicating institutional participant activity.
Copyright (c) 2026 M&C. All Rights Reserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class VolumeAnomaly:
    """A single detected volume anomaly event."""
    timestamp: pd.Timestamp
    relative_volume: float   # volume / rolling_avg_volume
    direction: str           # BULLISH or BEARISH based on close vs open
    is_climactic: bool       # very high volume + small price move
    metadata: dict = field(default_factory=dict)


class VolumeAnomalyDetector:
    """
    Detects volume spikes relative to a rolling average.

    Parameters
    ----------
    rolling_window : int
        Look-back window for computing rolling average volume (default 20).
    spike_threshold : float
        relative_volume must exceed this multiplier to be flagged (default 2.0).
    climactic_threshold : float
        relative_volume must exceed this for climactic classification (default 4.0).
    """

    def __init__(
        self,
        rolling_window: int = 20,
        spike_threshold: float = 2.0,
        climactic_threshold: float = 4.0,
    ) -> None:
        self.rolling_window = rolling_window
        self.spike_threshold = spike_threshold
        self.climactic_threshold = climactic_threshold

    # ------------------------------------------------------------------

    def detect(self, data: pd.DataFrame) -> List[VolumeAnomaly]:
        """
        Detect volume spikes vs rolling average.

        relative_volume = current_volume / rolling_mean(volume, window)
        is_climactic when relative_volume > climactic_threshold
                        AND price_range < 0.5 * avg_range
        Direction: BULLISH if close >= open, BEARISH otherwise.
        """
        if len(data) < self.rolling_window + 1:
            logger.debug("VolumeAnomalyDetector: insufficient data (%d rows)", len(data))
            return []

        df = data.copy()
        rolling_mean = (
            df["volume"]
            .rolling(window=self.rolling_window, min_periods=self.rolling_window)
            .mean()
        )
        avg_range = (
            (df["high"] - df["low"])
            .rolling(window=self.rolling_window, min_periods=self.rolling_window)
            .mean()
        )

        anomalies: List[VolumeAnomaly] = []

        for i in range(self.rolling_window, len(df)):
            row = df.iloc[i]
            rv = rolling_mean.iloc[i]
            if pd.isna(rv) or rv <= 0:
                continue

            relative_vol = float(row["volume"]) / float(rv)
            if relative_vol < self.spike_threshold:
                continue

            price_range = float(row["high"]) - float(row["low"])
            avg_r = float(avg_range.iloc[i]) if not pd.isna(avg_range.iloc[i]) else 0.0
            is_climactic = (
                relative_vol >= self.climactic_threshold
                and avg_r > 0
                and price_range < 0.5 * avg_r
            )
            direction = "BULLISH" if float(row["close"]) >= float(row["open"]) else "BEARISH"

            if isinstance(df.index, pd.DatetimeIndex):
                ts = df.index[i]
            else:
                ts = pd.Timestamp.now(tz="UTC")

            anomalies.append(
                VolumeAnomaly(
                    timestamp=ts,
                    relative_volume=round(relative_vol, 4),
                    direction=direction,
                    is_climactic=is_climactic,
                    metadata={
                        "bar_index": i,
                        "price_range": round(price_range, 6),
                        "avg_range": round(avg_r, 6),
                        "volume": int(row["volume"]),
                        "rolling_avg_volume": round(float(rv), 2),
                    },
                )
            )

        return anomalies

    def get_latest_anomaly(self, data: pd.DataFrame) -> Optional[VolumeAnomaly]:
        """Returns the most recent anomaly if one exists within the last 5 bars."""
        anomalies = self.detect(data)
        if not anomalies:
            return None
        last_bar = len(data) - 1
        for anomaly in reversed(anomalies):
            bar_idx = anomaly.metadata.get("bar_index", -999)
            if last_bar - bar_idx <= 5:
                return anomaly
        return None
