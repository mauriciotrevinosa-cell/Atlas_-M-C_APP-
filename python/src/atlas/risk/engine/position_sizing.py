"""
Position Sizing — Phase 7

Multiple position-sizing algorithms:
  - Kelly Criterion (full & fractional)
  - Fixed Fractional
  - Volatility Targeting
  - Risk Parity

References:
    Kelly, J.L. (1956). "A New Interpretation of Information Rate"
    Bell System Technical Journal, 35(4), 917-926.

    Thorp, E.O. (2006). "The Kelly Criterion in Blackjack, Sports Betting
    and the Stock Market."

Copyright © 2026 M&C. All Rights Reserved.
"""

from typing import Dict, Optional
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Compute optimal position sizes using multiple strategies.

    All methods return a fraction of the trading capital (0.0 – 1.0).

    Example:
        >>> sizer = PositionSizer(max_position=0.25)
        >>> f = sizer.kelly(win_rate=0.55, avg_win=1.5, avg_loss=1.0)
        >>> print(f"Kelly fraction: {f:.2%}")
    """

    def __init__(self, max_position: float = 0.25):
        """
        Args:
            max_position: Hard cap on fraction (default 25% of capital)
        """
        if not 0 < max_position <= 1:
            raise ValueError("max_position must be in (0, 1]")
        self.max_position = max_position
        logger.info("Initialized PositionSizer (max_position=%.0f%%)", max_position * 100)

    # ------------------------------------------------------------------ #
    # Kelly Criterion                                                      #
    # ------------------------------------------------------------------ #

    def kelly(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        fraction: float = 0.5,
    ) -> float:
        """
        Kelly Criterion position size.

        Full Kelly:  f* = (p/a − q/b)  where p=win_rate, q=1−p, a=avg_loss, b=avg_win
        Fractional:  f  = fraction * f*

        Args:
            win_rate:  Historical win probability [0,1]
            avg_win:   Average win as multiple of risk (e.g. 1.5 = risk:reward 1:1.5)
            avg_loss:  Average loss as multiple of risk (typically 1.0)
            fraction:  Kelly fraction (0.5 = half-Kelly, recommended)

        Returns:
            float: Position fraction [0, max_position]
        """
        if not 0 < win_rate < 1:
            raise ValueError(f"win_rate must be in (0,1), got {win_rate}")
        if avg_win <= 0 or avg_loss <= 0:
            raise ValueError("avg_win and avg_loss must be positive")

        q = 1 - win_rate
        f_full = win_rate / avg_loss - q / avg_win
        f = fraction * max(f_full, 0.0)

        result = min(f, self.max_position)
        logger.debug(
            "Kelly full=%.3f, fractional(%.1f)=%.3f, capped=%.3f",
            f_full, fraction, f, result,
        )
        return round(result, 4)

    def kelly_from_returns(
        self,
        returns: pd.Series,
        fraction: float = 0.5,
    ) -> float:
        """
        Estimate Kelly fraction from a historical return series.

        Uses empirical win rate, average win, and average loss.
        """
        wins = returns[returns > 0]
        losses = returns[returns < 0]

        if len(wins) == 0 or len(losses) == 0:
            return 0.0

        win_rate = len(wins) / len(returns)
        avg_win = float(wins.mean())
        avg_loss = float(abs(losses.mean()))

        return self.kelly(win_rate, avg_win, avg_loss, fraction)

    # ------------------------------------------------------------------ #
    # Fixed Fractional                                                     #
    # ------------------------------------------------------------------ #

    def fixed_fractional(
        self,
        risk_per_trade: float,
        stop_distance_pct: float,
    ) -> float:
        """
        Fixed Fractional position sizing.

        f = risk_per_trade / stop_distance_pct

        Args:
            risk_per_trade:    Max % of capital to risk (e.g. 0.01 = 1%)
            stop_distance_pct: Distance to stop loss as % of price (e.g. 0.02)

        Returns:
            float: Position fraction [0, max_position]
        """
        if stop_distance_pct <= 0:
            raise ValueError("stop_distance_pct must be positive")

        f = risk_per_trade / stop_distance_pct
        return min(f, self.max_position)

    # ------------------------------------------------------------------ #
    # Volatility Targeting                                                 #
    # ------------------------------------------------------------------ #

    def volatility_target(
        self,
        target_vol: float,
        realized_vol: float,
        current_size: float = 1.0,
    ) -> float:
        """
        Scale position so portfolio hits target annualised volatility.

        f = (target_vol / realized_vol) * current_size

        Args:
            target_vol:   Desired portfolio volatility (annualised, e.g. 0.15)
            realized_vol: Current/recent realised volatility (annualised)
            current_size: Base position size before scaling

        Returns:
            float: Scaled position fraction [0, max_position]
        """
        if realized_vol <= 0:
            raise ValueError("realized_vol must be positive")

        f = (target_vol / realized_vol) * current_size
        return min(max(f, 0.0), self.max_position)

    # ------------------------------------------------------------------ #
    # Risk Parity                                                          #
    # ------------------------------------------------------------------ #

    def risk_parity(
        self,
        volatilities: Dict[str, float],
        total_capital: float = 1.0,
    ) -> Dict[str, float]:
        """
        Equal risk contribution (naïve risk parity).

        Each asset gets weight ∝ 1/σ_i.

        Args:
            volatilities: {asset: annualised_vol}
            total_capital: Total fraction to allocate (≤ 1.0)

        Returns:
            {asset: position_fraction}
        """
        if not volatilities:
            raise ValueError("volatilities dict cannot be empty")

        inv_vols = {k: 1.0 / v for k, v in volatilities.items() if v > 0}
        total_inv = sum(inv_vols.values())

        weights = {k: (v / total_inv) * total_capital for k, v in inv_vols.items()}

        # Cap individual positions
        weights = {k: min(w, self.max_position) for k, w in weights.items()}

        logger.debug("Risk parity weights: %s", weights)
        return weights

    # ------------------------------------------------------------------ #
    # Summary                                                              #
    # ------------------------------------------------------------------ #

    def size_summary(
        self,
        returns: pd.Series,
        target_vol: float = 0.15,
        risk_per_trade: float = 0.01,
        stop_pct: float = 0.02,
    ) -> pd.DataFrame:
        """
        Return all sizing methods side by side for comparison.

        Args:
            returns:       Historical daily returns
            target_vol:    Volatility target (annualised)
            risk_per_trade: Fixed-fraction risk per trade
            stop_pct:       Stop loss distance as fraction

        Returns:
            DataFrame comparing all methods
        """
        realized_vol = float(returns.std() * np.sqrt(252))

        rows = [
            {"method": "Half-Kelly", "fraction": self.kelly_from_returns(returns, 0.5)},
            {"method": "Quarter-Kelly", "fraction": self.kelly_from_returns(returns, 0.25)},
            {"method": "Fixed Fractional (1% risk)", "fraction": self.fixed_fractional(risk_per_trade, stop_pct)},
            {"method": f"Vol Target ({target_vol:.0%})", "fraction": self.volatility_target(target_vol, realized_vol)},
        ]
        return pd.DataFrame(rows)
