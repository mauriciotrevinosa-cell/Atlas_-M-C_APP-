"""
Risk Management Engine
========================
Position sizing, VaR/CVaR, drawdown control, kill switches, and liquidation risk.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.risk")


# ---------------------------------------------------------------------------
# Position Sizing
# ---------------------------------------------------------------------------

class PositionSizer:
    """Calculate optimal position size using multiple methods."""

    def kelly_criterion(
        self, win_rate: float, avg_win: float, avg_loss: float,
    ) -> float:
        """
        Kelly criterion for optimal fraction of capital to risk.
        Returns fraction (0-1). Use half-Kelly for safety.
        """
        if avg_loss == 0:
            return 0.0
        b = avg_win / abs(avg_loss)  # Win/loss ratio
        p = win_rate
        q = 1 - p
        kelly = (b * p - q) / b
        return max(0.0, min(kelly, 1.0))

    def volatility_target(
        self, capital: float, target_vol: float, asset_vol: float, price: float,
    ) -> Dict[str, float]:
        """
        Size position to achieve target portfolio volatility.

        Args:
            capital:    Total account capital
            target_vol: Target annualized volatility (e.g. 0.15 = 15%)
            asset_vol:  Asset annualized volatility
            price:      Current asset price
        """
        if asset_vol <= 0:
            return {"shares": 0, "notional": 0, "leverage": 0}
        notional = capital * (target_vol / asset_vol)
        shares = notional / price
        leverage = notional / capital
        return {
            "shares": round(shares, 4),
            "notional": round(notional, 2),
            "leverage": round(leverage, 2),
            "pct_of_capital": round((notional / capital) * 100, 1),
        }

    def fixed_risk(
        self, capital: float, risk_pct: float, entry: float, stop: float,
    ) -> Dict[str, float]:
        """
        Size position based on fixed risk percentage and stop distance.
        """
        risk_amount = capital * risk_pct
        stop_distance = abs(entry - stop)
        if stop_distance == 0:
            return {"shares": 0, "risk_amount": risk_amount}
        shares = risk_amount / stop_distance
        return {
            "shares": round(shares, 4),
            "risk_amount": round(risk_amount, 2),
            "notional": round(shares * entry, 2),
        }


# ---------------------------------------------------------------------------
# Value at Risk
# ---------------------------------------------------------------------------

class VaRCalculator:
    """Calculate Value at Risk and Conditional VaR."""

    def historical_var(
        self, returns: pd.Series, confidence: float = 0.95, horizon_days: int = 1,
    ) -> Dict[str, float]:
        """Historical VaR."""
        if returns.empty:
            return {"var": 0.0, "cvar": 0.0}
        sorted_returns = returns.sort_values()
        idx = int((1 - confidence) * len(sorted_returns))
        var = float(-sorted_returns.iloc[idx]) * np.sqrt(horizon_days)
        cvar = float(-sorted_returns.iloc[:idx + 1].mean()) * np.sqrt(horizon_days)
        return {
            "var": round(var, 6),
            "cvar": round(cvar, 6),
            "confidence": confidence,
            "horizon_days": horizon_days,
            "method": "historical",
        }

    def parametric_var(
        self, returns: pd.Series, confidence: float = 0.95, horizon_days: int = 1,
    ) -> Dict[str, float]:
        """Parametric (Gaussian) VaR."""
        from scipy.stats import norm
        mu = float(returns.mean())
        sigma = float(returns.std())
        z = norm.ppf(1 - confidence)
        var = -(mu + z * sigma) * np.sqrt(horizon_days)
        return {
            "var": round(var, 6),
            "mean": round(mu, 6),
            "volatility": round(sigma, 6),
            "confidence": confidence,
            "method": "parametric",
        }


# ---------------------------------------------------------------------------
# Drawdown Control
# ---------------------------------------------------------------------------

class DrawdownController:
    """Monitor and control portfolio drawdown."""

    def __init__(
        self,
        max_drawdown: float = 0.20,
        warning_drawdown: float = 0.10,
    ):
        self.max_drawdown = max_drawdown
        self.warning_drawdown = warning_drawdown
        self.peak_equity = 0.0

    def update(self, current_equity: float) -> Dict[str, Any]:
        """
        Update with current equity and check drawdown limits.
        """
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        if self.peak_equity <= 0:
            return {"drawdown": 0.0, "status": "ok"}

        drawdown = (self.peak_equity - current_equity) / self.peak_equity

        if drawdown >= self.max_drawdown:
            status = "KILL"
            action = "Close all positions immediately"
        elif drawdown >= self.warning_drawdown:
            status = "WARNING"
            action = "Reduce position sizes by 50%"
        else:
            status = "OK"
            action = "Normal trading"

        return {
            "drawdown": round(drawdown, 4),
            "peak_equity": round(self.peak_equity, 2),
            "current_equity": round(current_equity, 2),
            "status": status,
            "action": action,
        }


# ---------------------------------------------------------------------------
# Kill Switch
# ---------------------------------------------------------------------------

class KillSwitch:
    """Emergency stop for catastrophic scenarios."""

    def __init__(
        self,
        max_daily_loss_pct: float = 0.05,
        max_consecutive_losses: int = 5,
        max_drawdown: float = 0.20,
    ):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.max_drawdown = max_drawdown
        self.consecutive_losses = 0
        self.is_killed = False
        self.kill_reason = None

    def check(
        self, daily_pnl_pct: float, drawdown: float, trade_won: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Check kill conditions.
        """
        if trade_won is not None:
            if not trade_won:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0

        triggers = []
        if daily_pnl_pct < -self.max_daily_loss_pct:
            triggers.append(f"Daily loss {daily_pnl_pct:.2%} exceeds limit {self.max_daily_loss_pct:.2%}")
        if self.consecutive_losses >= self.max_consecutive_losses:
            triggers.append(f"{self.consecutive_losses} consecutive losses")
        if drawdown >= self.max_drawdown:
            triggers.append(f"Drawdown {drawdown:.2%} exceeds max {self.max_drawdown:.2%}")

        if triggers:
            self.is_killed = True
            self.kill_reason = "; ".join(triggers)

        return {
            "is_killed": self.is_killed,
            "kill_reason": self.kill_reason,
            "consecutive_losses": self.consecutive_losses,
            "triggers_active": triggers,
        }

    def reset(self):
        """Manual reset after review."""
        self.is_killed = False
        self.kill_reason = None
        self.consecutive_losses = 0


# ---------------------------------------------------------------------------
# Liquidation Risk (for leveraged/futures)
# ---------------------------------------------------------------------------

class LiquidationRiskManager:
    """Manage liquidation risk for leveraged positions."""

    def calculate_liquidation_price(
        self, entry: float, leverage: float, side: str, maintenance_margin: float = 0.005,
    ) -> float:
        """Calculate liquidation price for a leveraged position."""
        if side == "long":
            return entry * (1 - (1 / leverage) + maintenance_margin)
        else:
            return entry * (1 + (1 / leverage) - maintenance_margin)

    def safe_leverage(
        self, entry: float, stop_loss: float, side: str, buffer_pct: float = 0.02,
    ) -> float:
        """Calculate max safe leverage given a stop loss."""
        distance = abs(entry - stop_loss) / entry
        if distance == 0:
            return 1.0
        safe_lev = 1 / (distance + buffer_pct)
        return round(min(safe_lev, 100), 1)

    def check_cluster_avoidance(
        self, entry: float, leverage: float, side: str, clusters: list,
    ) -> Dict[str, Any]:
        """
        Check if liquidation price overlaps with known liquidation clusters.
        """
        liq_price = self.calculate_liquidation_price(entry, leverage, side)

        for cluster in clusters:
            cluster_price = cluster.get("price", 0)
            distance_pct = abs(liq_price - cluster_price) / entry * 100

            if distance_pct < 1.0:  # Within 1% of a cluster
                safe_lev = self.safe_leverage(entry, cluster_price, side, buffer_pct=0.03)
                return {
                    "warning": True,
                    "message": f"Liquidation at ${liq_price:.2f} overlaps cluster at ${cluster_price:.2f}",
                    "cluster_size_usd": cluster.get("size_usd", 0),
                    "recommendation": f"Lower leverage to {safe_lev}x or adjust entry",
                    "safe_leverage": safe_lev,
                }

        return {
            "warning": False,
            "liquidation_price": round(liq_price, 2),
            "message": "No cluster overlap detected",
        }


# ---------------------------------------------------------------------------
# Unified Risk Engine
# ---------------------------------------------------------------------------

class RiskEngine:
    """Unified risk management facade."""

    def __init__(self):
        self.sizer = PositionSizer()
        self.var = VaRCalculator()
        self.drawdown = DrawdownController()
        self.kill_switch = KillSwitch()
        self.liquidation = LiquidationRiskManager()

    def full_assessment(
        self,
        capital: float,
        current_equity: float,
        returns: pd.Series,
        daily_pnl_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """Run complete risk assessment."""
        dd = self.drawdown.update(current_equity)
        ks = self.kill_switch.check(daily_pnl_pct, dd["drawdown"])
        var_result = self.var.historical_var(returns) if not returns.empty else {}

        return {
            "drawdown": dd,
            "kill_switch": ks,
            "var": var_result,
            "can_trade": not ks["is_killed"] and dd["status"] != "KILL",
        }
