"""
Support & Resistance Levels — Phase 2.11
Clusters pivot highs/lows to find significant price zones.
"""
import pandas as pd
import numpy as np
from typing import List, Dict


class SupportResistance:
    """
    Identifies support and resistance zones from price history.

    Method: Cluster pivot highs/lows within a tolerance band.
    The more touches a zone has, the stronger it is.

    Output:
        [
            {'level': 45200.0, 'type': 'resistance', 'strength': 3, 'touches': 3},
            {'level': 43500.0, 'type': 'support', 'strength': 2, 'touches': 2},
        ]
    """

    def __init__(
        self,
        pivot_left: int = 5,
        pivot_right: int = 5,
        tolerance_pct: float = 0.5,
        min_touches: int = 2,
    ):
        """
        Args:
            pivot_left: Bars to look left for pivot detection
            pivot_right: Bars to look right for pivot detection
            tolerance_pct: Price band (% of price) to cluster pivots into a zone
            min_touches: Minimum pivots in a zone to count as valid S/R
        """
        self.pivot_left = pivot_left
        self.pivot_right = pivot_right
        self.tolerance_pct = tolerance_pct
        self.min_touches = min_touches

    def _find_pivots(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Find pivot highs and lows."""
        highs = data["high"]
        lows = data["low"]
        ph = pd.Series(np.nan, index=highs.index)
        pl = pd.Series(np.nan, index=lows.index)

        for i in range(self.pivot_left, len(data) - self.pivot_right):
            window_h = highs.iloc[i - self.pivot_left: i + self.pivot_right + 1]
            window_l = lows.iloc[i - self.pivot_left: i + self.pivot_right + 1]
            if highs.iloc[i] == window_h.max():
                ph.iloc[i] = highs.iloc[i]
            if lows.iloc[i] == window_l.min():
                pl.iloc[i] = lows.iloc[i]

        return {"highs": ph.dropna(), "lows": pl.dropna()}

    def _cluster(self, prices: pd.Series, ref_price: float) -> List[Dict]:
        """Group pivots into zones within tolerance band."""
        tol = ref_price * (self.tolerance_pct / 100)
        used = [False] * len(prices)
        zones = []

        prices_sorted = prices.sort_values()
        vals = prices_sorted.values

        for i, base in enumerate(vals):
            if used[i]:
                continue
            zone_prices = [base]
            used[i] = True
            for j in range(i + 1, len(vals)):
                if used[j]:
                    continue
                if abs(vals[j] - base) <= tol:
                    zone_prices.append(vals[j])
                    used[j] = True

            if len(zone_prices) >= self.min_touches:
                zones.append({
                    "level": float(np.mean(zone_prices)),
                    "touches": len(zone_prices),
                    "strength": len(zone_prices),
                })

        return sorted(zones, key=lambda x: x["level"])

    def calculate(self, data: pd.DataFrame) -> List[Dict]:
        """
        Calculate support and resistance zones.

        Args:
            data: Normalized OHLCV DataFrame

        Returns:
            List of zone dicts sorted by level descending
        """
        pivots = self._find_pivots(data)
        ref_price = float(data["close"].iloc[-1])

        resistance_zones = self._cluster(pivots["highs"], ref_price)
        support_zones = self._cluster(pivots["lows"], ref_price)

        for z in resistance_zones:
            z["type"] = "resistance"
            z["distance_pct"] = round((z["level"] - ref_price) / ref_price * 100, 2)

        for z in support_zones:
            z["type"] = "support"
            z["distance_pct"] = round((z["level"] - ref_price) / ref_price * 100, 2)

        all_zones = resistance_zones + support_zones
        return sorted(all_zones, key=lambda x: x["level"], reverse=True)

    def nearest_levels(self, data: pd.DataFrame, count: int = 3) -> Dict:
        """
        Get the N nearest support and resistance levels to current price.

        Returns:
            {'resistance': [...], 'support': [...], 'current_price': ...}
        """
        zones = self.calculate(data)
        price = float(data["close"].iloc[-1])

        above = sorted(
            [z for z in zones if z["level"] > price],
            key=lambda x: x["level"],
        )[:count]

        below = sorted(
            [z for z in zones if z["level"] <= price],
            key=lambda x: x["level"],
            reverse=True,
        )[:count]

        return {
            "current_price": price,
            "resistance": above,
            "support": below,
        }
