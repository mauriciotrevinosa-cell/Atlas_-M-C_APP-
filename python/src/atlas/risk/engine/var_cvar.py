"""
Value-at-Risk (VaR) and Conditional Value-at-Risk (CVaR) — Phase 7

CVaR (Expected Shortfall) is a coherent risk measure that captures
tail risk better than VaR.

References:
    Rockafellar, R.T., Uryasev, S. (2000).
    "Optimization of Conditional Value-at-Risk"
    Journal of Risk, 2(3), 21-41.

    Acerbi, C., Tasche, D. (2002).
    "Expected Shortfall: A Natural Coherent Alternative to Value at Risk"
    Economic Notes, 31(2), 379-388.

Copyright © 2026 M&C. All Rights Reserved.
"""

from typing import Dict, Tuple
import numpy as np
import pandas as pd
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class VaRCVaR:
    """
    Value-at-Risk and Conditional Value-at-Risk calculator.

    Supports three estimation methods:
    - historical: non-parametric empirical distribution
    - parametric: Gaussian approximation
    - monte_carlo: simulation-based

    Example:
        >>> calc = VaRCVaR(confidence=0.95)
        >>> result = calc.calculate(returns)
        >>> print(f"VaR={result['var']:.4f}, CVaR={result['cvar']:.4f}")
    """

    def __init__(self, confidence: float = 0.95):
        """
        Args:
            confidence: Confidence level (e.g. 0.95 for 95% VaR/CVaR)
        """
        if not 0 < confidence < 1:
            raise ValueError(f"confidence must be in (0,1), got {confidence}")
        self.confidence = confidence
        self.alpha = 1 - confidence   # tail probability
        logger.info("Initialized VaRCVaR (confidence=%.2f)", confidence)

    def calculate(
        self,
        returns: pd.Series,
        method: str = "historical",
    ) -> Dict[str, float]:
        """
        Calculate VaR and CVaR for a return series.

        Args:
            returns: Daily return series (as decimals, e.g. 0.01 for +1%)
            method:  "historical", "parametric", or "monte_carlo"

        Returns:
            dict with keys: var, cvar, method, confidence
        """
        if len(returns) < 20:
            raise ValueError("Need at least 20 return observations")

        if method == "historical":
            var, cvar = self._historical(returns.values)
        elif method == "parametric":
            var, cvar = self._parametric(returns.values)
        elif method == "monte_carlo":
            var, cvar = self._monte_carlo(returns.values)
        else:
            raise ValueError(f"Unknown method: {method}")

        logger.debug(
            "VaR=%.4f, CVaR=%.4f (method=%s, α=%.2f)",
            var, cvar, method, self.alpha,
        )
        return {
            "var": float(var),
            "cvar": float(cvar),
            "method": method,
            "confidence": self.confidence,
            "alpha": self.alpha,
        }

    def rolling(
        self,
        returns: pd.Series,
        window: int = 60,
        method: str = "historical",
    ) -> pd.DataFrame:
        """
        Calculate rolling VaR and CVaR.

        Args:
            returns: Daily return series
            window:  Rolling window (days)
            method:  Estimation method

        Returns:
            DataFrame with columns ["var", "cvar"]
        """
        var_list, cvar_list = [], []
        idx = []

        for i in range(window - 1, len(returns)):
            window_returns = returns.iloc[i - window + 1 : i + 1]
            res = self.calculate(window_returns, method)
            var_list.append(res["var"])
            cvar_list.append(res["cvar"])
            idx.append(returns.index[i])

        return pd.DataFrame({"var": var_list, "cvar": cvar_list}, index=idx)

    # ------------------------------------------------------------------ #
    # Estimation methods                                                   #
    # ------------------------------------------------------------------ #

    def _historical(self, returns: np.ndarray) -> Tuple[float, float]:
        """Historical simulation (non-parametric)."""
        losses = -returns
        losses_sorted = np.sort(losses)

        idx = int(np.ceil(len(losses) * (1 - self.confidence)))
        var = float(losses_sorted[-idx]) if idx > 0 else float(losses_sorted[-1])
        cvar = float(np.mean(losses_sorted[-idx:])) if idx > 0 else var
        return var, cvar

    def _parametric(self, returns: np.ndarray) -> Tuple[float, float]:
        """
        Gaussian parametric VaR/CVaR.

        CVaR_α = −(μ − σ * φ(Φ⁻¹(α)) / α)
        """
        mu = np.mean(returns)
        sigma = np.std(returns, ddof=1)

        z = stats.norm.ppf(self.alpha)
        var = float(-(mu + sigma * z))

        phi = stats.norm.pdf(stats.norm.ppf(self.alpha))
        cvar = float(-(mu - sigma * phi / self.alpha))
        return var, cvar

    def _monte_carlo(
        self,
        returns: np.ndarray,
        n_scenarios: int = 10_000,
    ) -> Tuple[float, float]:
        """Bootstrap-based Monte Carlo CVaR."""
        rng = np.random.default_rng()
        simulated = rng.choice(returns, size=n_scenarios, replace=True)
        return self._historical(simulated)


class StressTesting:
    """
    Apply historical and hypothetical stress scenarios to a portfolio.

    Example:
        >>> st = StressTesting()
        >>> results = st.apply_scenarios(returns, portfolio_value=100_000)
    """

    SCENARIOS = {
        "2008_financial_crisis": -0.40,
        "2020_covid_crash":      -0.34,
        "2022_bear_market":      -0.25,
        "dot_com_burst":         -0.49,
        "black_monday_1987":     -0.22,
        "mild_correction":       -0.10,
        "severe_correction":     -0.20,
    }

    def apply_scenarios(
        self,
        returns: pd.Series,
        portfolio_value: float = 100_000,
    ) -> pd.DataFrame:
        """
        Apply predefined stress scenarios.

        Args:
            returns:         Historical return series
            portfolio_value: Current portfolio NAV

        Returns:
            DataFrame with scenario names, shock sizes, and $ losses
        """
        rows = []
        for name, shock in self.SCENARIOS.items():
            loss_pct = abs(shock)
            loss_usd = portfolio_value * loss_pct
            rows.append({
                "scenario": name,
                "shock_pct": shock * 100,
                "loss_pct": loss_pct * 100,
                "loss_usd": loss_usd,
                "remaining_usd": portfolio_value + portfolio_value * shock,
            })

        # Also add worst historical single-day and monthly losses
        if len(returns) >= 20:
            worst_day = returns.min()
            rows.append({
                "scenario": "worst_historical_day",
                "shock_pct": worst_day * 100,
                "loss_pct": abs(worst_day) * 100,
                "loss_usd": portfolio_value * abs(worst_day),
                "remaining_usd": portfolio_value * (1 + worst_day),
            })

        return pd.DataFrame(rows)
