"""
Multi-Asset Monte Carlo Simulator
===================================
Correlated Geometric Brownian Motion simulation across multiple assets.

Theory
------
Each asset follows GBM:

    dS_i / S_i = μ_i dt + σ_i dW_i

where the Brownian increments [dW_1, …, dW_n]^T are correlated via:

    dW = L dZ,   Z ~ N(0, I),   L = chol(Σ)

This preserves the empirical correlation structure estimated from
historical returns.  The portfolio path is:

    V(t) = Σ_i  w_i · S_i(t) / S_i(0)

starting at V(0) = 1.0.

Variance Reduction
------------------
When VarianceReduction.ANTITHETIC is selected (default) the simulator
generates Z_half random paths and appends their negatives −Z_half,
halving variance with no extra model calls.

Usage
-----
    from atlas.monte_carlo.multi_asset import MultiAssetSimulator, PortfolioSimConfig
    from atlas.analytics.returns import returns_matrix

    # From a pre-built returns DataFrame (columns = tickers)
    ret_df = returns_matrix(dfs)
    sim = MultiAssetSimulator()
    results = sim.simulate_from_returns(
        ret_df,
        weights={"AAPL": 0.5, "MSFT": 0.3, "SPY": 0.2},
    )
    print(results.summary())
    print(results.risk_metrics)

    # Full pipeline: DataRouter → returns → simulation
    from atlas.data_router import DataRouter
    router = DataRouter(allow_network=False)
    results = sim.simulate_from_router(
        router,
        tickers=["AAPL", "MSFT", "SPY"],
        weights={"AAPL": 0.5, "MSFT": 0.3, "SPY": 0.2},
        start="2022-01-01",
        end="2023-12-31",
    )

References
----------
    Glasserman, P. (2004). Monte Carlo Methods in Financial Engineering.
    Jäckel, P. (2002). Monte Carlo Methods in Finance.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from atlas.monte_carlo.simulator import VarianceReduction

logger = logging.getLogger("atlas.monte_carlo.multi_asset")

_TRADING_DAYS = 252


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PortfolioSimConfig:
    """
    Configuration for a multi-asset correlated Monte Carlo simulation.

    Attributes:
        n_paths:            Number of Monte Carlo paths (default 10 000).
        n_steps:            Simulation horizon in trading days (default 252 = 1 year).
        dt:                 Time step in years (default 1/252 = 1 trading day).
        variance_reduction: Variance reduction technique (default ANTITHETIC).
        seed:               Random seed for reproducibility. ``None`` = random.
    """

    n_paths: int = 10_000
    n_steps: int = _TRADING_DAYS
    dt: float = 1.0 / _TRADING_DAYS
    variance_reduction: VarianceReduction = VarianceReduction.ANTITHETIC
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.n_paths < 1:
            raise ValueError("n_paths must be a positive integer")
        if self.n_steps < 1:
            raise ValueError("n_steps must be a positive integer")
        if self.dt <= 0:
            raise ValueError("dt must be positive")


# ─────────────────────────────────────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PortfolioSimResults:
    """
    Results from a multi-asset correlated Monte Carlo simulation.

    Attributes:
        portfolio_paths:   (n_paths × n_steps) portfolio values (V(0) = 1.0).
        asset_paths:       Per-ticker normalised price paths S_i(t)/S_i(0).
                           Each value is an (n_paths × n_steps) array.
        weights:           Normalised allocation weights {ticker: weight}.
        tickers:           Ordered list of asset tickers.
        config:            PortfolioSimConfig used.
        corr_matrix:       Empirical correlation matrix (DataFrame).
        cov_matrix:        Empirical daily covariance matrix (DataFrame).
        mean_returns:      Per-asset empirical daily mean return (Series).
        percentiles:       {0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95} →
                           (n_steps,) array of portfolio path percentiles.
        risk_metrics:      Portfolio-level terminal distribution risk metrics.
    """

    portfolio_paths: np.ndarray
    asset_paths: Dict[str, np.ndarray]
    weights: Dict[str, float]
    tickers: List[str]
    config: PortfolioSimConfig
    corr_matrix: pd.DataFrame
    cov_matrix: pd.DataFrame
    mean_returns: pd.Series
    percentiles: Dict[float, np.ndarray] = field(default_factory=dict)
    risk_metrics: Dict[str, float] = field(default_factory=dict)

    def summary(self) -> pd.DataFrame:
        """
        Summary table of terminal portfolio value distribution.

        Returns:
            DataFrame with Metric / Value columns describing the final
            value distribution across all simulated paths.
        """
        fv = self.portfolio_paths[:, -1]
        return pd.DataFrame(
            {
                "Metric": [
                    "Mean final value",
                    "Median final value",
                    "Std dev final value",
                    "5th percentile",
                    "25th percentile",
                    "75th percentile",
                    "95th percentile",
                    "Min",
                    "Max",
                    "Skewness",
                    "Kurtosis",
                ],
                "Value": [
                    float(np.mean(fv)),
                    float(np.median(fv)),
                    float(np.std(fv)),
                    float(np.percentile(fv, 5)),
                    float(np.percentile(fv, 25)),
                    float(np.percentile(fv, 75)),
                    float(np.percentile(fv, 95)),
                    float(np.min(fv)),
                    float(np.max(fv)),
                    float(stats.skew(fv)),
                    float(stats.kurtosis(fv)),
                ],
            }
        )


# ─────────────────────────────────────────────────────────────────────────────
# Simulator
# ─────────────────────────────────────────────────────────────────────────────

class MultiAssetSimulator:
    """
    Correlated multi-asset Monte Carlo simulator (Cholesky-based GBM).

    The simulator is stateless — all configuration is passed per call.

    Methods
    -------
    simulate_from_returns(returns_df, weights, config)
        Fit parameters from a historical returns DataFrame and simulate.

    simulate_from_router(router, tickers, weights, start, end, config)
        Full pipeline: fetch data via DataRouter → compute returns → simulate.
    """

    # ── Public API ────────────────────────────────────────────────────────

    def simulate_from_returns(
        self,
        returns_df: pd.DataFrame,
        weights: Dict[str, float],
        config: Optional[PortfolioSimConfig] = None,
    ) -> PortfolioSimResults:
        """
        Fit parameters from historical returns and run correlated GBM simulation.

        Args:
            returns_df: DataFrame of daily returns (log or simple).
                        Columns must include all tickers in ``weights``.
            weights:    Dict {ticker: weight}. Auto-normalised to sum = 1.
            config:     Simulation configuration. Uses defaults if None.

        Returns:
            PortfolioSimResults

        Raises:
            ValueError: If any weight ticker is absent from returns_df.
        """
        config = config or PortfolioSimConfig()

        tickers = [t for t in weights if t in returns_df.columns]
        missing = [t for t in weights if t not in returns_df.columns]
        if missing:
            raise ValueError(
                f"Tickers not found in returns_df: {missing}. "
                f"Available: {list(returns_df.columns)}"
            )

        ret = returns_df[tickers].dropna()
        if len(ret) < 2:
            raise ValueError("Need at least 2 observations to estimate parameters.")

        w_arr = self._normalize_weights(weights, tickers)
        mu, cov, corr = self._fit(ret)
        return self._run(mu, cov, corr, w_arr, tickers, config, ret)

    def simulate_from_router(
        self,
        router,
        tickers: List[str],
        weights: Dict[str, float],
        start: str,
        end: str,
        config: Optional[PortfolioSimConfig] = None,
        return_method: str = "log",
    ) -> PortfolioSimResults:
        """
        Full pipeline: DataRouter → returns_matrix → simulate.

        Args:
            router:        DataRouter instance (allow_network True/False).
            tickers:       List of ticker symbols to fetch.
            weights:       Dict {ticker: weight}.
            start:         Start date "YYYY-MM-DD".
            end:           End date "YYYY-MM-DD".
            config:        PortfolioSimConfig (defaults if None).
            return_method: "log" | "simple" (default "log").

        Returns:
            PortfolioSimResults

        Raises:
            ValueError: If no data is available for the requested tickers/dates.
        """
        from atlas.analytics.returns import returns_matrix

        dfs = router.get(tickers, start, end)
        ret_df = returns_matrix(dfs, method=return_method)

        if ret_df.empty:
            raise ValueError(
                f"No returns data available for {tickers} between {start} and {end}. "
                "Check DataRouter cache or enable allow_network=True."
            )

        return self.simulate_from_returns(ret_df, weights, config)

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _normalize_weights(
        weights: Dict[str, float],
        tickers: List[str],
    ) -> np.ndarray:
        """Return unit-sum weight array aligned to ``tickers`` order."""
        w = np.array([weights[t] for t in tickers], dtype=float)
        total = w.sum()
        if total <= 0:
            raise ValueError("Weights must sum to a positive number.")
        return w / total

    @staticmethod
    def _fit(
        ret: pd.DataFrame,
    ) -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
        """
        Estimate daily mean returns and covariance matrix from a returns DataFrame.

        Returns:
            mu:   (n_assets,) daily mean return vector.
            cov:  (n_assets, n_assets) daily covariance matrix.
            corr: DataFrame — Pearson correlation matrix (for reporting).
        """
        mu = ret.mean().values          # daily mean
        cov = ret.cov().values          # daily covariance
        corr = ret.corr()
        return mu, cov, corr

    def _run(
        self,
        mu: np.ndarray,
        cov: np.ndarray,
        corr: pd.DataFrame,
        weights: np.ndarray,
        tickers: List[str],
        config: PortfolioSimConfig,
        ret_df: pd.DataFrame,
    ) -> PortfolioSimResults:
        """
        Core simulation engine: correlated GBM via Cholesky decomposition.

        Algorithm
        ---------
        1. Cholesky-decompose the covariance matrix: Σ = L Lᵀ
        2. Generate i.i.d. standard normals Z of shape (n_paths, n_steps, n_assets).
           If ANTITHETIC, Z = [Z_half ; −Z_half].
        3. Correlate: corr_Z = Z @ Lᵀ  (shape unchanged).
        4. Compute log increments: drift·dt + sqrt(dt)·corr_Z.
        5. Cumulative sum → log-price paths → exponentiate → S(t)/S(0).
        6. Weighted sum → portfolio paths V(t).
        """
        n_assets = len(tickers)
        n_paths = config.n_paths
        n_steps = config.n_steps
        dt = config.dt
        rng = np.random.default_rng(config.seed)

        # ── Cholesky (with jitter for near-singular matrices) ────────────
        try:
            L = np.linalg.cholesky(cov)
        except np.linalg.LinAlgError:
            logger.warning(
                "Covariance matrix is not positive-definite; adding numerical jitter."
            )
            cov_reg = cov + np.eye(n_assets) * 1e-8
            L = np.linalg.cholesky(cov_reg)

        # ── GBM drift: (μ − σ²/2) dt  ───────────────────────────────────
        sigma_sq = np.diag(cov)                     # per-asset daily variance
        drift = (mu - 0.5 * sigma_sq) * dt          # (n_assets,)

        # ── Random normals with optional antithetic variates ─────────────
        use_antithetic = (config.variance_reduction == VarianceReduction.ANTITHETIC)
        if use_antithetic:
            half = n_paths // 2
            Z_half = rng.standard_normal((half, n_steps, n_assets))
            Z = np.concatenate([Z_half, -Z_half], axis=0)   # (n_paths, T, N)
        else:
            Z = rng.standard_normal((n_paths, n_steps, n_assets))

        # ── Correlate via Cholesky: corr_Z[p, t] = L @ Z[p, t] ──────────
        # Using broadcasting: Z @ Lᵀ applies L-multiplication per (p, t) row.
        corr_Z = Z @ L.T                             # (n_paths, n_steps, n_assets)

        # ── Log-price increments ──────────────────────────────────────────
        # drift shape (n_assets,) broadcasts across (n_paths, n_steps, n_assets)
        increments = drift[np.newaxis, np.newaxis, :] + np.sqrt(dt) * corr_Z

        # ── Cumulative log-prices → normalised prices S(t)/S(0) ──────────
        log_paths = np.cumsum(increments, axis=1)    # (n_paths, n_steps, n_assets)
        asset_paths_arr = np.exp(log_paths)           # (n_paths, n_steps, n_assets)

        # ── Portfolio path: V(t) = Σ_i w_i · S_i(t)/S_i(0) ─────────────
        portfolio_paths = (
            asset_paths_arr * weights[np.newaxis, np.newaxis, :]
        ).sum(axis=2)                                # (n_paths, n_steps)

        # ── Percentiles over paths ────────────────────────────────────────
        pct_levels = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
        percentiles = {
            p: np.percentile(portfolio_paths, p * 100, axis=0)
            for p in pct_levels
        }

        # ── Per-asset path dictionary (n_paths × n_steps) ────────────────
        asset_paths = {
            tickers[i]: asset_paths_arr[:, :, i]
            for i in range(n_assets)
        }

        # ── Terminal-distribution risk metrics ────────────────────────────
        fv = portfolio_paths[:, -1]
        risk_metrics = self._terminal_risk_metrics(fv, portfolio_paths)

        logger.info(
            "MultiAssetSimulator: %d paths × %d steps, %d assets, "
            "variance_reduction=%s",
            n_paths, n_steps, n_assets, config.variance_reduction.value,
        )

        return PortfolioSimResults(
            portfolio_paths=portfolio_paths,
            asset_paths=asset_paths,
            weights={t: float(weights[i]) for i, t in enumerate(tickers)},
            tickers=tickers,
            config=config,
            corr_matrix=corr,
            cov_matrix=pd.DataFrame(cov, index=tickers, columns=tickers),
            mean_returns=pd.Series(mu, index=tickers, name="mean_daily_return"),
            percentiles=percentiles,
            risk_metrics=risk_metrics,
        )

    @staticmethod
    def _terminal_risk_metrics(
        final_values: np.ndarray,
        paths: np.ndarray,
    ) -> Dict[str, float]:
        """
        Compute risk metrics from the terminal distribution and path history.

        All VaR / CVaR values are expressed as positive numbers (losses).

        Args:
            final_values: (n_paths,) terminal portfolio values (V(0) = 1.0).
            paths:        (n_paths, n_steps) full path array.

        Returns:
            Dict with keys:
                var_95, cvar_95, var_99, cvar_99 — tail loss metrics
                max_drawdown_median               — median of per-path worst DD
                prob_loss                         — fraction of paths with loss
                expected_return                   — mean total return
                std_return                        — std dev of total returns
        """
        total_returns = final_values - 1.0  # total return over horizon

        # VaR (5th / 1st percentile of return distribution → loss)
        var_95 = float(np.percentile(total_returns, 5))
        var_99 = float(np.percentile(total_returns, 1))

        # CVaR (conditional mean below threshold)
        tail_95 = total_returns[total_returns <= var_95]
        tail_99 = total_returns[total_returns <= var_99]
        cvar_95 = float(tail_95.mean()) if len(tail_95) > 0 else var_95
        cvar_99 = float(tail_99.mean()) if len(tail_99) > 0 else var_99

        # Drawdown: running max deviation per path
        running_max = np.maximum.accumulate(paths, axis=1)   # (P, T)
        drawdowns = (paths - running_max) / running_max       # ≤ 0
        max_dd_per_path = drawdowns.min(axis=1)               # (P,) worst per path
        max_dd_median = float(np.median(max_dd_per_path))

        return {
            # VaR / CVaR expressed as positive losses
            "var_95":              -var_95,
            "cvar_95":             -cvar_95,
            "var_99":              -var_99,
            "cvar_99":             -cvar_99,
            "max_drawdown_median": max_dd_median,   # ≤ 0 (convention)
            "prob_loss":           float((total_returns < 0).mean()),
            "expected_return":     float(np.mean(total_returns)),
            "std_return":          float(np.std(total_returns)),
        }
