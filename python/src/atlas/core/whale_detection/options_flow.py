"""
Unusual options activity detector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

import numpy as np
import pandas as pd


@dataclass(slots=True)
class OptionsFlowSignal:
    timestamp: pd.Timestamp
    contract_type: str
    strike: float
    expiration: str
    volume_oi_ratio: float
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class UnusualOptionsActivity:
    """Flags contracts with unusually high flow relative to open interest."""

    def __init__(self, ratio_threshold: float = 1.5) -> None:
        self.ratio_threshold = float(ratio_threshold)

    def detect(self, options_chain: Optional[pd.DataFrame]) -> List[OptionsFlowSignal]:
        if options_chain is None or options_chain.empty:
            return []

        df = options_chain.copy()
        for col in ["volume", "openInterest", "strike"]:
            if col not in df.columns:
                return []
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if "expiration" not in df.columns:
            df["expiration"] = pd.NaT
        df["expiration"] = pd.to_datetime(df["expiration"], utc=True, errors="coerce")
        if "type" not in df.columns:
            df["type"] = "unknown"

        df = df.dropna(subset=["volume", "openInterest", "strike"])
        if df.empty:
            return []

        oi = df["openInterest"].replace(0, np.nan)
        df["volume_oi_ratio"] = df["volume"] / oi
        df["volume_oi_ratio"] = df["volume_oi_ratio"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
        unusual = df[df["volume_oi_ratio"] >= self.ratio_threshold].sort_values("volume_oi_ratio", ascending=False)

        now = pd.Timestamp.utcnow()
        out: list[OptionsFlowSignal] = []
        for row in unusual.itertuples(index=False):
            ratio = float(row.volume_oi_ratio)
            confidence = min(1.0, ratio / (self.ratio_threshold * 2.0))
            expiration = row.expiration.isoformat() if pd.notna(row.expiration) else ""
            out.append(
                OptionsFlowSignal(
                    timestamp=now,
                    contract_type=str(getattr(row, "type", "unknown")).lower(),
                    strike=float(row.strike),
                    expiration=expiration,
                    volume_oi_ratio=ratio,
                    confidence=float(confidence),
                    metadata={
                        "volume": float(row.volume),
                        "open_interest": float(row.openInterest),
                    },
                )
            )
        return out

