"""
Implied volatility surface builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import numpy as np
import pandas as pd

from .fetcher import OptionsChain


@dataclass(slots=True)
class IVSurfacePoint:
    strike: float
    dte_days: float
    iv: float
    option_type: str
    moneyness: float


class ImpliedVolatilitySurface:
    """Converts raw options chain rows into normalized IV surface points."""

    def build(self, chain: OptionsChain) -> List[IVSurfacePoint]:
        points: list[IVSurfacePoint] = []
        for side_name, side_df in (("call", chain.calls), ("put", chain.puts)):
            if side_df is None or side_df.empty:
                continue

            df = side_df.copy()
            df["expiration"] = pd.to_datetime(df["expiration"], utc=True, errors="coerce")
            dte = (df["expiration"] - datetime.now(timezone.utc)).dt.total_seconds() / 86_400.0
            df["dte_days"] = dte.clip(lower=1e-6)

            for row in df.itertuples(index=False):
                strike = float(row.strike)
                iv = float(row.impliedVolatility)
                dte_days = float(row.dte_days)
                if strike <= 0 or iv <= 0 or dte_days <= 0:
                    continue
                points.append(
                    IVSurfacePoint(
                        strike=strike,
                        dte_days=dte_days,
                        iv=iv,
                        option_type=side_name,
                        moneyness=float(strike / max(chain.underlying_price, 1e-9)),
                    )
                )
        points.sort(key=lambda p: (p.dte_days, p.strike, p.option_type))
        return points

    def to_frame(self, points: List[IVSurfacePoint]) -> pd.DataFrame:
        if not points:
            return pd.DataFrame(columns=["strike", "dte_days", "iv", "option_type", "moneyness"])
        return pd.DataFrame(
            {
                "strike": [p.strike for p in points],
                "dte_days": [p.dte_days for p in points],
                "iv": [p.iv for p in points],
                "option_type": [p.option_type for p in points],
                "moneyness": [p.moneyness for p in points],
            }
        )

    def summarize(self, points: List[IVSurfacePoint]) -> dict[str, float]:
        if not points:
            return {"n_points": 0, "atm_iv": 0.0, "iv_skew": 0.0}
        ivs = np.array([p.iv for p in points], dtype=float)
        mny = np.array([p.moneyness for p in points], dtype=float)
        atm_mask = np.abs(mny - 1.0) <= 0.03
        atm_iv = float(np.median(ivs[atm_mask])) if atm_mask.any() else float(np.median(ivs))
        skew = float(np.percentile(ivs[mny < 0.97], 50) - np.percentile(ivs[mny > 1.03], 50)) if (mny < 0.97).any() and (mny > 1.03).any() else 0.0
        return {
            "n_points": float(len(points)),
            "atm_iv": atm_iv,
            "iv_skew": skew,
        }

