"""
Liquidation Calculator — Phase 7.5
Calculates liquidation prices and safe leverage for leveraged positions.
"""
from typing import Dict, Optional


class LiquidationCalculator:
    """
    Computes liquidation prices and recommends safe leverage levels.

    Supports: perpetual futures (cross/isolated margin)
    """

    # Maintenance margin rates by exchange (approximate)
    MAINTENANCE_MARGINS = {
        "binance": 0.004,    # 0.4%
        "bybit": 0.005,      # 0.5%
        "hyperliquid": 0.003, # 0.3%
        "default": 0.005,
    }

    def liquidation_price(
        self,
        entry: float,
        leverage: float,
        side: str,
        exchange: str = "default",
    ) -> float:
        """
        Calculate the liquidation price for a position.

        Args:
            entry: Entry price
            leverage: Leverage multiplier
            side: 'long' or 'short'
            exchange: Exchange name (for maintenance margin)

        Returns:
            Liquidation price
        """
        mm = self.MAINTENANCE_MARGINS.get(exchange.lower(), self.MAINTENANCE_MARGINS["default"])

        if side == "long":
            liq = entry * (1 - 1 / leverage + mm)
        else:
            liq = entry * (1 + 1 / leverage - mm)

        return round(liq, 4)

    def safe_leverage(
        self,
        entry: float,
        stop_price: float,
        side: str,
        safety_buffer_pct: float = 20.0,
        exchange: str = "default",
    ) -> float:
        """
        Calculate the maximum safe leverage given a stop price.
        Ensures liquidation is NOT hit before the stop.

        Args:
            entry: Entry price
            stop_price: Stop loss price
            side: 'long' or 'short'
            safety_buffer_pct: Extra buffer between stop and liquidation (%)
            exchange: Exchange name

        Returns:
            Maximum safe leverage (integer)
        """
        mm = self.MAINTENANCE_MARGINS.get(exchange.lower(), self.MAINTENANCE_MARGINS["default"])
        stop_dist = abs(entry - stop_price) / entry

        # Liquidation must be beyond stop by safety_buffer
        # liq_dist = stop_dist * (1 + safety_buffer_pct/100)
        liq_dist = stop_dist * (1 + safety_buffer_pct / 100)

        # liq_dist = 1/leverage - mm → leverage = 1 / (liq_dist + mm)
        max_lev = 1 / (liq_dist + mm)

        return max(1.0, round(max_lev, 1))

    def analyze(
        self,
        entry: float,
        leverage: float,
        side: str,
        current_price: float,
        exchange: str = "default",
        stop_price: Optional[float] = None,
    ) -> Dict:
        """
        Full liquidation analysis for a position.

        Returns:
            {
                'liq_price': ...,
                'liq_distance_pct': ...,
                'risk_level': 'LOW'|'MEDIUM'|'HIGH'|'CRITICAL',
                'description': '...'
            }
        """
        liq = self.liquidation_price(entry, leverage, side, exchange)
        liq_dist_pct = abs(current_price - liq) / current_price * 100

        if liq_dist_pct < 2:
            risk = "CRITICAL"
        elif liq_dist_pct < 5:
            risk = "HIGH"
        elif liq_dist_pct < 15:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        result = {
            "entry": entry,
            "leverage": leverage,
            "side": side,
            "liq_price": liq,
            "current_price": current_price,
            "liq_distance_pct": round(liq_dist_pct, 2),
            "risk_level": risk,
            "description": (
                f"{risk} risk — liquidation at ${liq:.2f} "
                f"({liq_dist_pct:.1f}% from current ${current_price:.2f})"
            ),
        }

        if stop_price:
            safe_lev = self.safe_leverage(entry, stop_price, side, exchange=exchange)
            result["stop_price"] = stop_price
            result["safe_leverage"] = safe_lev
            if leverage > safe_lev:
                result["warning"] = (
                    f"Leverage {leverage}x exceeds safe limit {safe_lev}x for your stop. "
                    f"Lower leverage or widen stop."
                )

        return result
