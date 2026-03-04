"""
Institutional flow proxy from price-volume behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

import numpy as np
import pandas as pd


@dataclass(slots=True)
class FlowSignal:
    timestamp: pd.Timestamp
    net_flow_score: float
    direction: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class InstitutionalFlowTracker:
    """Tracks unusually large signed dollar-flow bars."""

    def __init__(self, window: int = 20, z_threshold: float = 2.0) -> None:
        self.window = int(window)
        self.z_threshold = float(z_threshold)

    def detect(self, data: pd.DataFrame) -> List[FlowSignal]:
        if len(data) < max(self.window + 2, 8):
            return []

        open_col = _col(data, "open")
        close_col = _col(data, "close")
        vol_col = _col(data, "volume")

        df = data.copy()
        close = pd.to_numeric(df[close_col], errors="coerce")
        open_px = pd.to_numeric(df[open_col], errors="coerce")
        volume = pd.to_numeric(df[vol_col], errors="coerce").fillna(0.0)
        signed_flow = (close - open_px).apply(np.sign) * close * volume

        mean = signed_flow.rolling(self.window, min_periods=self.window).mean()
        std = signed_flow.rolling(self.window, min_periods=self.window).std().replace(0, np.nan)
        z = (signed_flow - mean) / std

        out: list[FlowSignal] = []
        for i in range(self.window, len(df)):
            z_i = float(z.iloc[i]) if pd.notna(z.iloc[i]) else 0.0
            if abs(z_i) < self.z_threshold:
                continue

            direction = "ACCUMULATION" if z_i > 0 else "DISTRIBUTION"
            confidence = min(1.0, abs(z_i) / (self.z_threshold * 2.0))
            ts = (
                df.index[i]
                if isinstance(df.index, pd.DatetimeIndex)
                else pd.Timestamp.utcnow()
            )
            out.append(
                FlowSignal(
                    timestamp=ts,
                    net_flow_score=float(z_i),
                    direction=direction,
                    confidence=float(confidence),
                    metadata={
                        "bar_index": i,
                        "signed_dollar_flow": float(signed_flow.iloc[i]),
                    },
                )
            )
        return out


def _col(frame: pd.DataFrame, name: str) -> str:
    lower_map = {c.lower(): c for c in frame.columns}
    key = name.lower()
    if key not in lower_map:
        raise KeyError(f"Required column '{name}' not found")
    return lower_map[key]

