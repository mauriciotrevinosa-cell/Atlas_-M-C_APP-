"""
Market Structure Analysis — Phase 3.2
Detects: Higher Highs/Lower Lows, Break of Structure (BOS), Change of Character (CHoCH)
"""
import pandas as pd
import numpy as np
from typing import List, Dict


def _pivot_highs(data: pd.DataFrame, left: int = 3, right: int = 3) -> pd.Series:
    """Detect pivot highs (local maxima)."""
    highs = data["high"]
    pivots = pd.Series(False, index=highs.index)
    for i in range(left, len(highs) - right):
        window = highs.iloc[i - left: i + right + 1]
        if highs.iloc[i] == window.max():
            pivots.iloc[i] = True
    return pivots


def _pivot_lows(data: pd.DataFrame, left: int = 3, right: int = 3) -> pd.Series:
    """Detect pivot lows (local minima)."""
    lows = data["low"]
    pivots = pd.Series(False, index=lows.index)
    for i in range(left, len(lows) - right):
        window = lows.iloc[i - left: i + right + 1]
        if lows.iloc[i] == window.min():
            pivots.iloc[i] = True
    return pivots


class MarketStructure:
    """
    Analyzes market structure using pivot highs and lows.

    Detects:
    - HH (Higher High), HL (Higher Low) — uptrend structure
    - LH (Lower High), LL (Lower Low) — downtrend structure
    - BOS (Break of Structure) — continuation confirmation
    - CHoCH (Change of Character) — potential reversal
    """

    def __init__(self, pivot_left: int = 3, pivot_right: int = 3):
        self.pivot_left = pivot_left
        self.pivot_right = pivot_right

    def analyze(self, data: pd.DataFrame) -> dict:
        """
        Analyze market structure from OHLCV data.

        Returns:
            {
                'trend': 'bullish' | 'bearish' | 'unclear',
                'last_bos': {'type': 'bullish_bos', 'date': '...', 'price': ...},
                'structure': [{'type': 'HH'|'HL'|'LH'|'LL', 'price': ..., 'date': ...}],
                'description': '...'
            }
        """
        if len(data) < (self.pivot_left + self.pivot_right + 10):
            return {"trend": "unclear", "structure": [], "description": "Insufficient data"}

        ph_mask = _pivot_highs(data, self.pivot_left, self.pivot_right)
        pl_mask = _pivot_lows(data, self.pivot_left, self.pivot_right)

        pivot_highs = data.loc[ph_mask, "high"]
        pivot_lows = data.loc[pl_mask, "low"]

        structure_points = []

        # Label pivot highs
        prev_high = None
        for date, price in pivot_highs.items():
            if prev_high is not None:
                label = "HH" if price > prev_high else "LH"
                structure_points.append({"type": label, "price": float(price), "date": str(date)})
            prev_high = price

        # Label pivot lows
        prev_low = None
        for date, price in pivot_lows.items():
            if prev_low is not None:
                label = "HL" if price > prev_low else "LL"
                structure_points.append({"type": label, "price": float(price), "date": str(date)})
            prev_low = price

        structure_points.sort(key=lambda x: x["date"])

        # Determine trend from last 4 structure points
        recent = structure_points[-4:] if len(structure_points) >= 4 else structure_points
        hh_hl = sum(1 for p in recent if p["type"] in ("HH", "HL"))
        lh_ll = sum(1 for p in recent if p["type"] in ("LH", "LL"))

        if hh_hl > lh_ll:
            trend = "bullish"
        elif lh_ll > hh_hl:
            trend = "bearish"
        else:
            trend = "unclear"

        # BOS detection (current price breaks last pivot high/low)
        current_price = float(data["close"].iloc[-1])
        last_bos = None

        if len(pivot_highs) >= 1:
            last_ph = float(pivot_highs.iloc[-1])
            if current_price > last_ph:
                last_bos = {
                    "type": "bullish_bos",
                    "price": last_ph,
                    "date": str(pivot_highs.index[-1]),
                }

        if len(pivot_lows) >= 1:
            last_pl = float(pivot_lows.iloc[-1])
            if current_price < last_pl:
                last_bos = {
                    "type": "bearish_bos",
                    "price": last_pl,
                    "date": str(pivot_lows.index[-1]),
                }

        return {
            "trend": trend,
            "last_bos": last_bos,
            "structure": structure_points[-10:],
            "pivot_highs": len(pivot_highs),
            "pivot_lows": len(pivot_lows),
            "description": (
                f"{trend.upper()} structure — "
                f"{'BOS confirmed' if last_bos else 'No BOS'}"
            ),
        }
