"""
Gap analysis for intraday continuation behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

import pandas as pd


class GapType(str, Enum):
    GAP_UP = "gap_up"
    GAP_DOWN = "gap_down"


@dataclass(slots=True)
class GapEvent:
    timestamp: pd.Timestamp
    gap_type: GapType
    gap_pct: float
    opening_volume_ratio: float
    continuation_probability: float
    metadata: dict[str, Any] = field(default_factory=dict)


class GapAnalyzer:
    """Detects opening gaps and estimates continuation odds from local history."""

    def __init__(
        self,
        min_gap_pct: float = 0.01,
        volume_window: int = 20,
        history_window: int = 80,
    ) -> None:
        self.min_gap_pct = float(min_gap_pct)
        self.volume_window = int(volume_window)
        self.history_window = int(history_window)

    def detect(self, data: pd.DataFrame) -> List[GapEvent]:
        if len(data) < max(self.volume_window + 2, 3):
            return []

        open_col = _col(data, "open")
        close_col = _col(data, "close")
        vol_col = _col(data, "volume")

        df = data.copy()
        rolling_volume = (
            df[vol_col].rolling(self.volume_window, min_periods=self.volume_window).mean()
        )

        events: list[GapEvent] = []
        history: list[tuple[GapType, bool]] = []

        for i in range(1, len(df)):
            prev_close = float(df.iloc[i - 1][close_col])
            open_px = float(df.iloc[i][open_col])
            close_px = float(df.iloc[i][close_col])
            if prev_close <= 0:
                continue

            gap_pct = (open_px - prev_close) / prev_close
            if abs(gap_pct) < self.min_gap_pct:
                continue

            gap_type = GapType.GAP_UP if gap_pct > 0 else GapType.GAP_DOWN
            continued = bool((gap_type == GapType.GAP_UP and close_px >= open_px) or (gap_type == GapType.GAP_DOWN and close_px <= open_px))

            relevant = [flag for gt, flag in history[-self.history_window :] if gt == gap_type]
            continuation_prob = (
                float(sum(relevant)) / float(len(relevant))
                if relevant
                else 0.5
            )

            rv = rolling_volume.iloc[i]
            volume_ratio = (
                float(df.iloc[i][vol_col]) / float(rv)
                if pd.notna(rv) and float(rv) > 0
                else 1.0
            )

            ts = (
                df.index[i]
                if isinstance(df.index, pd.DatetimeIndex)
                else pd.Timestamp.utcnow()
            )
            events.append(
                GapEvent(
                    timestamp=ts,
                    gap_type=gap_type,
                    gap_pct=float(gap_pct),
                    opening_volume_ratio=float(volume_ratio),
                    continuation_probability=float(continuation_prob),
                    metadata={
                        "continued": continued,
                        "open": open_px,
                        "prev_close": prev_close,
                        "close": close_px,
                        "bar_index": i,
                    },
                )
            )
            history.append((gap_type, continued))

        return events

    def latest_event(self, data: pd.DataFrame, lookback_bars: int = 5) -> Optional[GapEvent]:
        events = self.detect(data)
        if not events:
            return None
        latest_idx = len(data) - 1
        for event in reversed(events):
            idx = int(event.metadata.get("bar_index", -10_000))
            if latest_idx - idx <= lookback_bars:
                return event
        return None


def _col(frame: pd.DataFrame, name: str) -> str:
    lower_map = {c.lower(): c for c in frame.columns}
    key = name.lower()
    if key not in lower_map:
        raise KeyError(f"Required column '{name}' not found")
    return lower_map[key]

