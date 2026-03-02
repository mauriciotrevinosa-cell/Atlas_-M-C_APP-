"""
Liquidation Zone Detection
============================
Detects price zones with high concentration of liquidations.
Used for risk management and entry/exit optimization.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.features")


class LiquidationZones:
    """
    Detect and analyze liquidation clusters in price space.

    A cluster is a price zone where many liquidation orders are concentrated.
    When price approaches a cluster, it can trigger a cascade.
    """

    def __init__(
        self,
        bin_size_pct: float = 0.5,
        min_cluster_size: float = 1_000_000,
        cascade_distance_pct: float = 2.0,
    ):
        """
        Args:
            bin_size_pct:          Price bin width as % of current price
            min_cluster_size:      Min USD value to qualify as a cluster
            cascade_distance_pct:  Distance % to flag cascade risk
        """
        self.bin_size_pct = bin_size_pct
        self.min_cluster_size = min_cluster_size
        self.cascade_distance_pct = cascade_distance_pct

    def detect_clusters(
        self,
        liquidation_data: pd.DataFrame,
        current_price: float,
    ) -> List[Dict[str, Any]]:
        """
        Detect liquidation clusters from raw liquidation event data.

        Args:
            liquidation_data: DataFrame with columns:
                - price: liquidation price
                - size: USD value
                - side: 'long' or 'short'
            current_price: Current market price

        Returns:
            List of cluster dicts sorted by proximity to current price
        """
        if liquidation_data.empty:
            return []

        bin_width = current_price * (self.bin_size_pct / 100)

        # Create price bins
        min_price = liquidation_data["price"].min()
        max_price = liquidation_data["price"].max()
        bins = np.arange(min_price, max_price + bin_width, bin_width)

        if len(bins) < 2:
            return []

        liquidation_data = liquidation_data.copy()
        liquidation_data["bin"] = pd.cut(
            liquidation_data["price"], bins=bins, labels=False
        )

        clusters = []
        for bin_idx, group in liquidation_data.groupby("bin"):
            total_size = group["size"].sum()

            if total_size >= self.min_cluster_size:
                bin_center = bins[int(bin_idx)] + bin_width / 2
                distance_pct = abs(bin_center - current_price) / current_price * 100

                # Dominant side
                side_totals = group.groupby("side")["size"].sum()
                dominant_side = side_totals.idxmax() if not side_totals.empty else "unknown"

                clusters.append({
                    "price": round(bin_center, 2),
                    "size_usd": round(total_size, 2),
                    "count": len(group),
                    "side": dominant_side,
                    "distance_pct": round(distance_pct, 2),
                    "is_nearby": distance_pct <= self.cascade_distance_pct,
                })

        # Sort by proximity
        clusters.sort(key=lambda c: c["distance_pct"])
        return clusters

    def cascade_risk(
        self,
        current_price: float,
        clusters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Estimate risk of a liquidation cascade at current price.

        Args:
            current_price: Current market price
            clusters:      Output from detect_clusters()

        Returns:
            Risk assessment dict
        """
        if not clusters:
            return {"risk": "LOW", "nearby_clusters": 0, "total_exposure": 0}

        nearby = [c for c in clusters if c["is_nearby"]]

        if not nearby:
            return {"risk": "LOW", "nearby_clusters": 0, "total_exposure": 0}

        total_exposure = sum(c["size_usd"] for c in nearby)
        nearest = nearby[0]

        if total_exposure > self.min_cluster_size * 10:
            risk = "CRITICAL"
        elif total_exposure > self.min_cluster_size * 5:
            risk = "HIGH"
        elif total_exposure > self.min_cluster_size * 2:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return {
            "risk": risk,
            "nearby_clusters": len(nearby),
            "total_exposure_usd": round(total_exposure, 2),
            "nearest_cluster": nearest,
            "trigger_price": nearest["price"],
            "distance_to_trigger_pct": nearest["distance_pct"],
        }
