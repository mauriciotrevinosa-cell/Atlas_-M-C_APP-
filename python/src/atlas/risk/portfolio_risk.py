"""
Portfolio Risk Manager
======================
Multi-asset portfolio risk assessment using historical simulation.

What this module provides
--------------------------
1. **Historical Portfolio VaR / CVaR** — weighted portfolio returns series,
   with 95 % and 99 % confidence levels at any horizon (scaled via √T).

2. **Component VaR** — per-asset decomposition showing how much each
   position contributes to total portfolio risk.
   Formula:  ComponentVaR_i = w_i · β_i · PortfolioVaR
   where     β_i = cov(R_i, R_p) / var(R_p)

3. **Marginal VaR** — sensitivity of portfolio VaR to a small weight change.
   Formula:  MarginalVaR_i = β_i · PortfolioVaR / w_i  (per unit weight)

4. **Stress Testing** — four built-in macro scenarios:
   • 2008 Global Financial Crisis  (S&P −56 %, Bonds +6 %)
   • 2020 COVID Crash              (S&P −34 % in 33 days)
   • Dot-com Bust (2000-2002)      (NASDAQ −78 %, S&P −49 %)
   • Rate Shock 2022               (S&P −19 %, TLT −31 %, CRB +20 %)
   Shocks are applied per asset-class (EQUITY / BOND / COMMODITY / …).

5. **Ratio Metrics** — Sharpe, Sortino, and Calmar ratios on the
   weighted portfolio returns series.

6. **Risk Warnings** — auto-generated alerts when thresholds are breached
   (VaR > 5 %, max drawdown < −20 %, Sharpe < 0.5).

Integration
-----------
Returns data comes from ``atlas.analytics.returns.returns_matrix()``,
which aligns multiple DataFrames from the DataRouter onto a common index.

    from atlas.analytics.returns import returns_matrix
    from atlas.data_router import DataRouter
    from atlas.risk.portfolio_risk import PortfolioRiskManager

    router = DataRouter(allow_network=False)
    dfs   = router.get(["AAPL", "MSFT", "SPY"], "2022-01-01", "2023-12-31")
    ret_df = returns_matrix(dfs)

    mgr    = PortfolioRiskManager()
    result = mgr.assess(ret_df, weights={"AAPL": 0.5, "MSFT": 0.3, "SPY": 0.2})
    print(result.summary_table())
    print(result.to_dict())

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy import stats

from atlas.analytics.risk_metrics import (
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    calmar_ratio,
)

logger = logging.getLogger("atlas.risk.portfolio_risk")

_TRADING_DAYS = 252


# ─────────────────────────────────────────────────────────────────────────────
# Built-in stress scenarios
# Source: empirical peak-to-trough drawdowns per asset class.
# ─────────────────────────────────────────────────────────────────────────────

_STRESS_SCENARIOS: Dict[str, Dict[str, float]] = {
    "2008_gfc": {
        # S&P 500 peak-to-trough −56.8 %,  Bonds flight-to-quality +6 %
        "EQUITY":    -0.565,
        "BOND":       0.063,
        "COMMODITY": -0.300,
        "ETF":       -0.550,
        "INDEX":     -0.565,
        "CRYPTO":    -0.300,   # proxy
        "FOREX":     -0.100,
        "DEFAULT":   -0.500,
    },
    "2020_covid": {
        # S&P 500 −34 % in 33 days (fastest bear market on record)
        "EQUITY":    -0.340,
        "BOND":       0.020,
        "COMMODITY": -0.200,
        "ETF":       -0.320,
        "INDEX":     -0.340,
        "CRYPTO":    -0.500,
        "FOREX":     -0.050,
        "DEFAULT":   -0.300,
    },
    "dot_com_bust": {
        # NASDAQ −78 %, S&P 500 −49 % (2000-2002)
        "EQUITY":    -0.490,
        "BOND":       0.085,
        "COMMODITY":  0.050,
        "ETF":       -0.450,
        "INDEX":     -0.490,
        "CRYPTO":    -0.490,   # proxy
        "FOREX":     -0.080,
        "DEFAULT":   -0.400,
    },
    "rate_shock_2022": {
        # Fed tightening cycle: S&P −19 %, TLT −31 %, CRB +20 %
        "EQUITY":    -0.190,
        "BOND":      -0.130,
        "COMMODITY":  0.230,
        "ETF":       -0.180,
        "INDEX":     -0.190,
        "CRYPTO":    -0.650,
        "FOREX":      0.050,
        "DEFAULT":   -0.200,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ComponentVaRResult:
    """
    VaR decomposition for a single asset in the portfolio.

    Attributes:
        ticker:          Asset ticker symbol.
        weight:          Normalised portfolio weight (0–1).
        asset_var:       Individual asset historical VaR at 95 % (positive = loss).
        component_var:   Contribution to portfolio VaR (positive = loss).
        marginal_var:    Marginal VaR per unit weight (positive = loss).
        pct_contribution: component_var / portfolio_var  (0–1, or negative if hedge).
    """

    ticker: str
    weight: float
    asset_var: float
    component_var: float
    marginal_var: float
    pct_contribution: float


@dataclass
class PortfolioRiskResult:
    """
    Complete portfolio risk assessment.

    Attributes:
        portfolio_var:        Historical 95 % VaR on portfolio returns (positive = loss).
        portfolio_cvar:       Historical 95 % CVaR / Expected Shortfall.
        portfolio_var_99:     Historical 99 % VaR.
        portfolio_cvar_99:    Historical 99 % CVaR.
        portfolio_volatility: Annualised portfolio volatility.
        sharpe:               Annualised Sharpe ratio.
        sortino:              Annualised Sortino ratio.
        calmar:               Calmar ratio (annualised return / |max drawdown|).
        max_drawdown:         Worst historical drawdown on portfolio (≤ 0).
        component_var:        List of ComponentVaRResult (one per asset).
        stress_scenarios:     Dict {scenario: estimated loss} under macro shocks.
        tickers:              Asset tickers included in the assessment.
        weights:              Normalised weights used.
        n_obs:                Number of daily observations.
        warnings:             List of auto-generated risk alert strings.
    """

    portfolio_var: float
    portfolio_cvar: float
    portfolio_var_99: float
    portfolio_cvar_99: float
    portfolio_volatility: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    component_var: List[ComponentVaRResult]
    stress_scenarios: Dict[str, float]
    tickers: List[str]
    weights: Dict[str, float]
    n_obs: int
    warnings: List[str] = field(default_factory=list)

    # ── Serialisation ─────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        """Return a plain dict suitable for JSON serialisation."""
        return {
            "portfolio_var_95":       round(self.portfolio_var, 6),
            "portfolio_cvar_95":      round(self.portfolio_cvar, 6),
            "portfolio_var_99":       round(self.portfolio_var_99, 6),
            "portfolio_cvar_99":      round(self.portfolio_cvar_99, 6),
            "portfolio_volatility":   round(self.portfolio_volatility, 6),
            "sharpe":                 round(self.sharpe, 4),
            "sortino":                round(self.sortino, 4),
            "calmar":                 round(self.calmar, 4),
            "max_drawdown":           round(self.max_drawdown, 6),
            "component_var": [
                {
                    "ticker":           c.ticker,
                    "weight":           round(c.weight, 4),
                    "asset_var":        round(c.asset_var, 6),
                    "component_var":    round(c.component_var, 6),
                    "marginal_var":     round(c.marginal_var, 6),
                    "pct_contribution": round(c.pct_contribution, 4),
                }
                for c in self.component_var
            ],
            "stress_scenarios":   {k: round(v, 4) for k, v in self.stress_scenarios.items()},
            "n_obs":              self.n_obs,
            "tickers":            self.tickers,
            "weights":            {k: round(v, 4) for k, v in self.weights.items()},
            "warnings":           self.warnings,
        }

    def summary_table(self) -> pd.DataFrame:
        """Top-level risk metrics as a two-column DataFrame (Metric / Value)."""
        rows = [
            ("VaR 95% (1-day)",     f"{self.portfolio_var:.2%}"),
            ("CVaR 95% (1-day)",    f"{self.portfolio_cvar:.2%}"),
            ("VaR 99% (1-day)",     f"{self.portfolio_var_99:.2%}"),
            ("CVaR 99% (1-day)",    f"{self.portfolio_cvar_99:.2%}"),
            ("Ann. Volatility",     f"{self.portfolio_volatility:.2%}"),
            ("Sharpe Ratio",        f"{self.sharpe:.2f}"),
            ("Sortino Ratio",       f"{self.sortino:.2f}"),
            ("Calmar Ratio",        f"{self.calmar:.2f}"),
            ("Max Drawdown",        f"{self.max_drawdown:.2%}"),
            ("Observations",        str(self.n_obs)),
        ]
        return pd.DataFrame(rows, columns=["Metric", "Value"])


# ─────────────────────────────────────────────────────────────────────────────
# Manager
# ─────────────────────────────────────────────────────────────────────────────

class PortfolioRiskManager:
    """
    Portfolio-level risk assessment with VaR decomposition and stress testing.

    The manager is stateless — all data is supplied per call.

    Quick start::

        from atlas.risk.portfolio_risk import PortfolioRiskManager
        from atlas.analytics.returns import returns_matrix

        ret_df = returns_matrix(dfs)        # from DataRouter
        mgr    = PortfolioRiskManager()
        result = mgr.assess(
            ret_df,
            weights={"AAPL": 0.5, "MSFT": 0.3, "SPY": 0.2},
        )
        print(result.summary_table())
    """

    def assess(
        self,
        returns_df: pd.DataFrame,
        weights: Dict[str, float],
        confidence: float = 0.95,
        risk_free_rate: float = 0.04,
        horizon_days: int = 1,
        asset_classes: Optional[Dict[str, str]] = None,
        run_stress: bool = True,
    ) -> PortfolioRiskResult:
        """
        Run a full portfolio risk assessment.

        Args:
            returns_df:    DataFrame of daily returns (columns = tickers).
                           Use ``atlas.analytics.returns.returns_matrix()`` to build.
            weights:       Dict {ticker: weight}. Auto-normalised to sum = 1.
            confidence:    VaR confidence level (default 0.95).
            risk_free_rate: Annual risk-free rate for Sharpe / Sortino (default 0.04).
            horizon_days:  VaR horizon scaling factor (default 1 = 1-day VaR).
                           Scales VaR by √horizon_days.
            asset_classes: Optional dict {ticker: "EQUITY"|"BOND"|…} for stress
                           scenario shocks.  Uses "DEFAULT" shock if omitted.
            run_stress:    If True (default), compute all four stress scenarios.

        Returns:
            PortfolioRiskResult
        """
        tickers = [t for t in weights if t in returns_df.columns]
        missing = [t for t in weights if t not in returns_df.columns]
        warnings: List[str] = []

        if missing:
            warnings.append(f"Tickers excluded (not in returns_df): {missing}")
            logger.warning("Missing tickers in returns_df: %s", missing)

        if not tickers:
            raise ValueError(
                "No valid tickers found in returns_df. "
                f"Requested: {list(weights)}, Available: {list(returns_df.columns)}"
            )

        ret = returns_df[tickers].dropna()
        n_obs = len(ret)

        if n_obs < 30:
            warnings.append(
                f"Only {n_obs} observations — VaR estimates may be unreliable "
                f"(recommended: 252+)."
            )

        # ── Normalise weights ─────────────────────────────────────────────
        w_arr, w_dict = self._normalise_weights(weights, tickers)

        # ── Portfolio returns series ──────────────────────────────────────
        # Dot product: shape (n_obs,)
        portfolio_ret: pd.Series = (ret * w_arr).sum(axis=1)

        # ── Aggregate VaR / CVaR ──────────────────────────────────────────
        p_var    = self._hist_var(portfolio_ret,  confidence,  horizon_days)
        p_cvar   = self._hist_cvar(portfolio_ret, confidence,  horizon_days)
        p_var_99 = self._hist_var(portfolio_ret,  0.99,        horizon_days)
        p_cvar_99 = self._hist_cvar(portfolio_ret, 0.99,       horizon_days)

        # ── Ratio metrics ─────────────────────────────────────────────────
        p_vol    = float(portfolio_ret.std() * np.sqrt(_TRADING_DAYS))
        sharpe   = sharpe_ratio(portfolio_ret,  risk_free_rate, _TRADING_DAYS)
        sortino  = sortino_ratio(portfolio_ret, risk_free_rate, _TRADING_DAYS)
        calmar   = calmar_ratio(portfolio_ret,  _TRADING_DAYS)
        mdd      = max_drawdown(portfolio_ret)

        # ── Component VaR decomposition ───────────────────────────────────
        comp_var_list = self._component_var(
            ret, w_arr, w_dict, tickers, portfolio_ret, p_var, confidence
        )

        # ── Stress scenarios ──────────────────────────────────────────────
        stress_results: Dict[str, float] = {}
        if run_stress:
            stress_results = self._stress_test(w_dict, asset_classes)

        # ── Auto-warnings ─────────────────────────────────────────────────
        if p_var > 0.05:
            warnings.append(
                f"High 1-day 95% VaR ({p_var:.2%}) — exceeds 5% daily risk threshold."
            )
        if mdd < -0.20:
            warnings.append(
                f"Severe max drawdown ({mdd:.2%}) — consider reducing concentration."
            )
        if 0 < sharpe < 0.5:
            warnings.append(
                f"Low Sharpe ratio ({sharpe:.2f}) — risk-adjusted returns are weak."
            )

        logger.info(
            "PortfolioRiskManager.assess: tickers=%s, n_obs=%d, VaR95=%.4f, "
            "Sharpe=%.2f, MaxDD=%.4f",
            tickers, n_obs, p_var, sharpe, mdd,
        )

        return PortfolioRiskResult(
            portfolio_var=p_var,
            portfolio_cvar=p_cvar,
            portfolio_var_99=p_var_99,
            portfolio_cvar_99=p_cvar_99,
            portfolio_volatility=p_vol,
            sharpe=sharpe,
            sortino=sortino,
            calmar=calmar,
            max_drawdown=mdd,
            component_var=comp_var_list,
            stress_scenarios=stress_results,
            tickers=tickers,
            weights=w_dict,
            n_obs=n_obs,
            warnings=warnings,
        )

    def assess_from_router(
        self,
        router,
        tickers: List[str],
        weights: Dict[str, float],
        start: str,
        end: str,
        **kwargs,
    ) -> PortfolioRiskResult:
        """
        Convenience: fetch data → compute returns → assess.

        Args:
            router:  DataRouter instance.
            tickers: List of ticker symbols to fetch.
            weights: Dict {ticker: weight}.
            start:   Start date "YYYY-MM-DD".
            end:     End date "YYYY-MM-DD".
            **kwargs: Forwarded to ``assess()``.

        Returns:
            PortfolioRiskResult
        """
        from atlas.analytics.returns import returns_matrix

        dfs = router.get(tickers, start, end)
        ret_df = returns_matrix(dfs)
        return self.assess(ret_df, weights, **kwargs)

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _normalise_weights(
        weights: Dict[str, float],
        tickers: List[str],
    ):
        """Return (np.ndarray, Dict) of unit-sum weights aligned to ``tickers``."""
        w = np.array([weights[t] for t in tickers], dtype=float)
        w /= w.sum()
        return w, {t: float(w[i]) for i, t in enumerate(tickers)}

    @staticmethod
    def _hist_var(
        returns: pd.Series,
        confidence: float,
        horizon_days: int,
    ) -> float:
        """
        Historical VaR (positive = loss).

        Scales to the requested horizon by multiplying by √horizon_days.
        """
        pct = (1.0 - confidence) * 100.0
        var_1d = -np.percentile(returns, pct)
        return float(var_1d * np.sqrt(horizon_days))

    @staticmethod
    def _hist_cvar(
        returns: pd.Series,
        confidence: float,
        horizon_days: int,
    ) -> float:
        """
        Historical CVaR / Expected Shortfall (positive = loss).

        Conditional mean of returns that fall at or below the VaR threshold.
        """
        pct = (1.0 - confidence) * 100.0
        threshold = np.percentile(returns, pct)
        tail = returns[returns <= threshold]
        cvar_1d = -tail.mean() if len(tail) > 0 else -threshold
        return float(cvar_1d * np.sqrt(horizon_days))

    def _component_var(
        self,
        ret: pd.DataFrame,
        w: np.ndarray,
        w_dict: Dict[str, float],
        tickers: List[str],
        portfolio_ret: pd.Series,
        portfolio_var: float,
        confidence: float,
    ) -> List[ComponentVaRResult]:
        """
        Decompose portfolio VaR into per-asset component contributions.

        Uses the covariance-beta approach:

            β_i         = cov(R_i, R_p) / var(R_p)
            ComponentVaR_i = w_i · β_i · PortfolioVaR
            MarginalVaR_i  = β_i · PortfolioVaR

        This satisfies the Euler homogeneity property:
            Σ_i  ComponentVaR_i  =  PortfolioVaR   (exactly, up to float rounding)
        """
        p_var_float = float(portfolio_ret.var())

        results: List[ComponentVaRResult] = []
        for i, ticker in enumerate(tickers):
            cov_i_p = float(ret[ticker].cov(portfolio_ret))
            beta_i = cov_i_p / p_var_float if p_var_float > 1e-12 else 0.0

            comp_i    = w[i] * beta_i * portfolio_var
            marginal_i = beta_i * portfolio_var
            asset_var_i = self._hist_var(ret[ticker], confidence, 1)
            pct_i = comp_i / portfolio_var if abs(portfolio_var) > 1e-12 else 0.0

            results.append(
                ComponentVaRResult(
                    ticker=ticker,
                    weight=w_dict[ticker],
                    asset_var=asset_var_i,
                    component_var=comp_i,
                    marginal_var=marginal_i,
                    pct_contribution=pct_i,
                )
            )

        return results

    @staticmethod
    def _stress_test(
        weights: Dict[str, float],
        asset_classes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, float]:
        """
        Estimate portfolio loss under four predefined macro stress scenarios.

        Each scenario applies a different shock multiplier per asset class.
        If ``asset_classes`` is not provided, the "DEFAULT" shock is used for
        all assets.

        Args:
            weights:      Normalised {ticker: weight} dict.
            asset_classes: Optional {ticker: "EQUITY"|"BOND"|"COMMODITY"|…}.

        Returns:
            Dict {scenario_name: estimated_loss}  (positive = loss).
        """
        results: Dict[str, float] = {}
        ac = asset_classes or {}

        for scenario_name, shocks in _STRESS_SCENARIOS.items():
            loss = 0.0
            for ticker, w in weights.items():
                asset_class = ac.get(ticker, "DEFAULT")
                shock = shocks.get(asset_class, shocks["DEFAULT"])
                # shock is negative for losses; flip sign → positive = loss
                loss += w * (-shock)
            results[scenario_name] = round(loss, 6)

        return results
