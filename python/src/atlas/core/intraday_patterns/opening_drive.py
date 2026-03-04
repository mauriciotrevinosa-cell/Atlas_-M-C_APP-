"""
Opening drive detector for intraday momentum.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

import numpy as np
import pandas as pd


@dataclass(slots=True)
class OpeningDriveSignal:
    timestamp: pd.Timestamp
    direction: str
    move_pct: float
    strength: float
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class OpeningDriveDetector:
    """Flags strong open-to-close directional sessions with volume confirmation."""

    def __init__(
        self,
        min_move_pct: float = 0.006,
        volume_window: int = 20,
        min_volume_zscore: float = 0.0,
    ) -> None:
        self.min_move_pct = float(min_move_pct)
        self.volume_window = int(volume_window)
        self.min_volume_zscore = float(min_volume_zscore)

    def detect(self, data: pd.DataFrame) -> List[OpeningDriveSignal]:
        if len(data) < max(self.volume_window + 2, 5):
            return []

        open_col = _col(data, "open")
        close_col = _col(data, "close")
        high_col = _col(data, "high")
        low_col = _col(data, "low")
        vol_col = _col(data, "volume")

        df = data.copy()
        vol_mean = df[vol_col].rolling(self.volume_window, min_periods=self.volume_window).mean()
        vol_std = (
            df[vol_col]
            .rolling(self.volume_window, min_periods=self.volume_window)
            .std()
            .replace(0, np.nan)
        )

        signals: list[OpeningDriveSignal] = []

        for i in range(self.volume_window, len(df)):
            open_px = float(df.iloc[i][open_col])
            close_px = float(df.iloc[i][close_col])
            high_px = float(df.iloc[i][high_col])
            low_px = float(df.iloc[i][low_col])
            if open_px <= 0:
                continue

            move_pct = (close_px - open_px) / open_px
            if abs(move_pct) < self.min_move_pct:
                continue

            z = 0.0
            if pd.notna(vol_mean.iloc[i]) and pd.notna(vol_std.iloc[i]) and float(vol_std.iloc[i]) > 0:
                z = (float(df.iloc[i][vol_col]) - float(vol_mean.iloc[i])) / float(vol_std.iloc[i])
            if z < self.min_volume_zscore:
                continue

            day_range_pct = (high_px - low_px) / open_px if open_px > 0 else 0.0
            direction = "BULLISH" if move_pct > 0 else "BEARISH"
            strength = abs(move_pct) / max(day_range_pct, 1e-8)
            confidence = min(1.0, 0.6 * min(abs(move_pct) / self.min_move_pct, 2.0) / 2.0 + 0.4 * min(max(z, 0.0) / 3.0, 1.0))

            ts = (
                df.index[i]
                if isinstance(df.index, pd.DatetimeIndex)
                else pd.Timestamp.utcnow()
            )
            signals.append(
                OpeningDriveSignal(
                    timestamp=ts,
                    direction=direction,
                    move_pct=float(move_pct),
                    strength=float(strength),
                    confidence=float(confidence),
                    metadata={
                        "bar_index": i,
                        "day_range_pct": float(day_range_pct),
                        "volume_zscore": float(z),
                        "open": open_px,
                        "close": close_px,
                    },
                )
            )

        return signals

    def latest_signal(self, data: pd.DataFrame, lookback_bars: int = 5) -> Optional[OpeningDriveSignal]:
        signals = self.detect(data)
        if not signals:
            return None
        latest_idx = len(data) - 1
        for signal in reversed(signals):
            idx = int(signal.metadata.get("bar_index", -10_000))
            if latest_idx - idx <= lookback_bars:
                return signal
        return None


def _col(frame: pd.DataFrame, name: str) -> str:
    lower_map = {c.lower(): c for c in frame.columns}
    key = name.lower()
    if key not in lower_map:
        raise KeyError(f"Required column '{name}' not found")
    return lower_map[key]

