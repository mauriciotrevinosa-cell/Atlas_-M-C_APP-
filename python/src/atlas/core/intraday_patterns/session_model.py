"""
Session-level volatility profile for intraday behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(slots=True)
class SessionProfile:
    by_session: dict[str, float]
    current_session: str
    current_volatility: float
    volatility_regime: str
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionVolatilityModel:
    """Builds a volatility profile by time-of-day buckets."""

    def __init__(self, n_buckets: int = 6) -> None:
        self.n_buckets = max(1, int(n_buckets))

    def fit(self, data: pd.DataFrame) -> SessionProfile:
        close_col = _col(data, "close")
        if len(data) < 8:
            return SessionProfile(
                by_session={"session_0": 0.0},
                current_session="session_0",
                current_volatility=0.0,
                volatility_regime="normal",
                metadata={"rows": len(data)},
            )

        df = data.copy()
        df["ret"] = pd.to_numeric(df[close_col], errors="coerce").pct_change().fillna(0.0)

        if isinstance(df.index, pd.DatetimeIndex) and df.index.tz is not None:
            hours = df.index.tz_convert("UTC").hour
            bucket_series = (hours * self.n_buckets // 24).astype(int)
        elif isinstance(df.index, pd.DatetimeIndex):
            hours = df.index.hour
            bucket_series = (hours * self.n_buckets // 24).astype(int)
        else:
            bucket_series = (np.arange(len(df)) * self.n_buckets // max(len(df), 1)).astype(int)

        bucket_series = np.clip(bucket_series, 0, self.n_buckets - 1)
        df["bucket"] = bucket_series

        grouped = df.groupby("bucket", dropna=False)["ret"].std(ddof=0).fillna(0.0)
        by_session = {f"session_{int(k)}": float(v) for k, v in grouped.items()}

        current_bucket = int(bucket_series[-1]) if len(bucket_series) else 0
        current_session = f"session_{current_bucket}"
        current_vol = float(by_session.get(current_session, 0.0))

        all_vals = np.array(list(by_session.values()), dtype=float)
        p25 = float(np.percentile(all_vals, 25)) if len(all_vals) else 0.0
        p75 = float(np.percentile(all_vals, 75)) if len(all_vals) else 0.0
        if current_vol < p25:
            regime = "low"
        elif current_vol > p75:
            regime = "high"
        else:
            regime = "normal"

        return SessionProfile(
            by_session=by_session,
            current_session=current_session,
            current_volatility=current_vol,
            volatility_regime=regime,
            metadata={"rows": len(df), "n_buckets": self.n_buckets},
        )


def _col(frame: pd.DataFrame, name: str) -> str:
    lower_map = {c.lower(): c for c in frame.columns}
    key = name.lower()
    if key not in lower_map:
        raise KeyError(f"Required column '{name}' not found")
    return lower_map[key]

