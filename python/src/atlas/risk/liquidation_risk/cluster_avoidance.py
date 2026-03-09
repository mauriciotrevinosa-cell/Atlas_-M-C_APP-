"""
Liquidation Cluster Avoidance — Phase 7.5
Checks if a proposed position's liquidation price falls near a known
liquidation cluster, and recommends adjustments.
"""
from typing import Dict, List, Optional
from .liquidation_calculator import LiquidationCalculator


class ClusterAvoidance:
    """
    Cross-references a trade's liquidation price with known liquidation clusters.
    If the liquidation price is near a cluster, warns the trader and
    suggests safer alternatives.
    """

    def __init__(self, proximity_pct: float = 1.5):
        """
        Args:
            proximity_pct: Distance in % within which a cluster is considered "nearby"
        """
        self.proximity_pct = proximity_pct
        self._calc = LiquidationCalculator()

    def check(
        self,
        entry: float,
        leverage: float,
        side: str,
        clusters: List[Dict],
        current_price: float,
        exchange: str = "default",
    ) -> Dict:
        """
        Check if liquidation price is near a known liquidation cluster.

        Args:
            entry: Entry price
            leverage: Leverage multiplier
            side: 'long' or 'short'
            clusters: List of cluster dicts from LiquidationZones.detect_clusters()
            current_price: Current price (for risk assessment)
            exchange: Exchange name

        Returns:
            {
                'safe': True|False,
                'liq_price': ...,
                'nearby_clusters': [...],
                'recommendation': '...',
                'suggested_leverage': ...
            }
        """
        liq_price = self._calc.liquidation_price(entry, leverage, side, exchange)

        nearby_clusters = []
        for cluster in clusters:
            cluster_price = cluster.get("price", 0)
            dist = abs(cluster_price - liq_price) / liq_price * 100
            if dist <= self.proximity_pct:
                nearby_clusters.append({**cluster, "dist_pct": round(dist, 2)})

        is_safe = len(nearby_clusters) == 0
        total_nearby_usd = sum(c.get("size_usd", 0) for c in nearby_clusters)

        recommendation = ""
        suggested_leverage = leverage

        if not is_safe:
            # Find safe leverage: keep liquidation away from ALL clusters
            # Try reducing leverage until no clusters are nearby
            for test_lev in [l / 2 for l in range(int(leverage * 2), 1, -1)]:
                test_liq = self._calc.liquidation_price(entry, test_lev, side, exchange)
                still_near = any(
                    abs(c["price"] - test_liq) / test_liq * 100 <= self.proximity_pct
                    for c in clusters
                )
                if not still_near:
                    suggested_leverage = round(test_lev, 1)
                    break

            recommendation = (
                f"Liquidation at ${liq_price:.2f} overlaps with ${total_nearby_usd/1e6:.1f}M "
                f"liquidation cluster. Consider leverage {suggested_leverage}x "
                f"(liq=${self._calc.liquidation_price(entry, suggested_leverage, side, exchange):.2f})."
            )
        else:
            recommendation = (
                f"No nearby clusters. Liquidation at ${liq_price:.2f} appears safe."
            )

        return {
            "safe": is_safe,
            "liq_price": liq_price,
            "nearby_clusters": nearby_clusters,
            "total_cluster_usd": total_nearby_usd,
            "suggested_leverage": suggested_leverage,
            "recommendation": recommendation,
        }
