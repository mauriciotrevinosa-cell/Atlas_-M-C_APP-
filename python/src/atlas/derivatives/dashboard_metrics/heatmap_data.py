"""
Liquidation Heatmap Data — Phase 12.3
Prepares binned liquidation data for the derivatives dashboard.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class HeatmapDataBuilder:
    """
    Transforms raw liquidation events into binned heatmap data
    suitable for the Derivatives Dashboard frontend.

    Output format:
        [
            {'price_bin': 44000, 'long_usd': 5200000, 'short_usd': 1000000},
            ...
        ]
    """

    def __init__(self, bins: int = 60):
        self.bins = bins

    def build(
        self,
        liquidation_df: pd.DataFrame,
        current_price: float,
        price_range_pct: float = 10.0,
    ) -> List[Dict]:
        """
        Build heatmap data from raw liquidation events.

        Args:
            liquidation_df: DataFrame with [long_liq_usd, short_liq_usd] indexed by timestamp
            current_price: Current market price (center of heatmap)
            price_range_pct: % above/below current price to include

        Returns:
            List of price bin dicts
        """
        low = current_price * (1 - price_range_pct / 100)
        high = current_price * (1 + price_range_pct / 100)
        edges = np.linspace(low, high, self.bins + 1)
        mid_prices = [(edges[i] + edges[i + 1]) / 2 for i in range(self.bins)]

        result = []
        for mid in mid_prices:
            result.append({
                "price_bin": round(mid, 2),
                "long_usd": 0.0,
                "short_usd": 0.0,
                "distance_pct": round((mid - current_price) / current_price * 100, 2),
            })

        # If we have actual liquidation data, distribute it
        if not liquidation_df.empty and "long_liq_usd" in liquidation_df.columns:
            # For time-series liquidations, distribute proportionally
            total_long = float(liquidation_df["long_liq_usd"].sum())
            total_short = float(liquidation_df["short_liq_usd"].sum())

            # Distribute across bins with slight concentration above/below price
            for i, bin_dict in enumerate(result):
                dist = abs(bin_dict["distance_pct"]) / price_range_pct
                if bin_dict["price_bin"] > current_price:
                    # Long liquidations cluster above current price
                    weight = np.exp(-dist * 2)
                    bin_dict["long_usd"] = round(total_long * weight / self.bins * 5, 0)
                else:
                    # Short liquidations cluster below current price
                    weight = np.exp(-dist * 2)
                    bin_dict["short_usd"] = round(total_short * weight / self.bins * 5, 0)

        return result

    def to_dataframe(self, heatmap_data: List[Dict]) -> pd.DataFrame:
        """Convert heatmap list to DataFrame."""
        return pd.DataFrame(heatmap_data)

    def get_hottest_zones(self, heatmap_data: List[Dict], top_n: int = 5) -> Dict:
        """
        Return the top N price zones with highest liquidation concentration.

        Returns:
            {'long_danger': [...], 'short_danger': [...]}
        """
        df = self.to_dataframe(heatmap_data)

        top_long = df.nlargest(top_n, "long_usd")[["price_bin", "long_usd", "distance_pct"]].to_dict("records")
        top_short = df.nlargest(top_n, "short_usd")[["price_bin", "short_usd", "distance_pct"]].to_dict("records")

        return {"long_danger_zones": top_long, "short_danger_zones": top_short}
