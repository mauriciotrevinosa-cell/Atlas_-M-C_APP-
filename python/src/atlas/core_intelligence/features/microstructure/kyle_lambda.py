"""
Kyle's Lambda — Price Impact Coefficient

Estimates market liquidity via the linear relationship between
order-flow imbalance and price changes.

    ΔP = λ * Q + ε

High λ → thin market (low liquidity, high impact per unit).
Low  λ → deep market (high liquidity, low impact).

References:
    Kyle, A.S. (1985). "Continuous Auctions and Insider Trading"
    Econometrica, 53(6), 1315-1335.

    Hasbrouck, J. (2009).
    "Trading Costs and Returns for U.S. Equities: Estimating Effective Costs
    from Daily Data"
    Journal of Finance, 64(3), 1445-1477.

Copyright © 2026 M&C. All Rights Reserved.
"""

from typing import Optional
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class KyleLambda:
    """
    Estimate Kyle's Lambda (price impact coefficient).

    Fits a simple OLS regression:
        ΔP_t = λ * Q_t + ε_t

    where Q_t is signed order flow (buy = +, sell = −).

    A rolling version tracks liquidity regimes over time.

    Example:
        >>> estimator = KyleLambda()
        >>> lam = estimator.estimate(prices, volumes, sides)
        >>> print(f"λ = {lam:.6f}")
    """

    def __init__(self, min_obs: int = 20):
        """
        Args:
            min_obs: Minimum observations required for estimation
        """
        if min_obs < 2:
            raise ValueError(f"min_obs must be >= 2, got {min_obs}")
        self.min_obs = min_obs
        logger.info("Initialized KyleLambda (min_obs=%d)", min_obs)

    def estimate(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        sides: Optional[np.ndarray] = None,
    ) -> float:
        """
        Estimate a single λ from the full sample.

        Args:
            prices:  Trade prices (or closing prices)
            volumes: Trade volumes
            sides:   Trade direction (+1 buy, −1 sell).
                     If None, the tick rule is used.

        Returns:
            float: Estimated Kyle's lambda

        Raises:
            ValueError: Insufficient observations
        """
        if len(prices) < self.min_obs:
            raise ValueError(
                f"Need >= {self.min_obs} observations, got {len(prices)}"
            )
        if len(prices) != len(volumes):
            raise ValueError("prices and volumes must have the same length")

        if sides is None:
            sides = self._tick_rule(prices)

        price_changes = np.diff(prices)
        signed_flow = volumes[1:] * sides[1:]  # align dimensions

        return self._ols(signed_flow, price_changes)

    def rolling_estimate(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        sides: Optional[np.ndarray] = None,
        window: int = 50,
    ) -> pd.Series:
        """
        Compute rolling Kyle's Lambda to track liquidity regimes.

        Args:
            prices:  Trade prices
            volumes: Trade volumes
            sides:   Trade sides (if None, tick rule is used)
            window:  Rolling window in observations

        Returns:
            pd.Series of rolling λ estimates (NaN for insufficient data)
        """
        if sides is None:
            sides = self._tick_rule(prices)

        price_changes = np.diff(prices)
        signed_flow = volumes[1:] * sides[1:]
        n = len(price_changes)

        lambdas = np.full(n, np.nan)
        for i in range(window - 1, n):
            start = i - window + 1
            q_slice = signed_flow[start : i + 1]
            dp_slice = price_changes[start : i + 1]
            lambdas[i] = self._ols(q_slice, dp_slice)

        return pd.Series(lambdas, name="kyle_lambda")

    def interpret(self, lam: float) -> str:
        """Return a human-readable liquidity interpretation."""
        if lam < 0.0001:
            return "Very high liquidity — negligible price impact"
        elif lam < 0.001:
            return "High liquidity"
        elif lam < 0.01:
            return "Normal liquidity"
        elif lam < 0.05:
            return "Low liquidity — moderate price impact"
        else:
            return "Very low liquidity — high price impact risk"

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _ols(X: np.ndarray, y: np.ndarray) -> float:
        """
        OLS coefficient from simple univariate regression y = λ X.

        λ = Cov(X, y) / Var(X)
        """
        var_x = np.var(X)
        if var_x == 0:
            return 0.0
        return float(np.cov(X, y)[0, 1] / var_x)

    @staticmethod
    def _tick_rule(prices: np.ndarray) -> np.ndarray:
        """Classify trades using the tick rule (+1 buy, −1 sell)."""
        n = len(prices)
        sides = np.zeros(n)
        for i in range(1, n):
            if prices[i] > prices[i - 1]:
                sides[i] = 1.0
            elif prices[i] < prices[i - 1]:
                sides[i] = -1.0
            else:
                sides[i] = sides[i - 1]
        sides[0] = sides[1] if n > 1 and sides[1] != 0 else 1.0
        return sides
