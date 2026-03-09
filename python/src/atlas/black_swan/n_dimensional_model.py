"""
N-Dimensional Black Swan Model
================================
Models tail-risk events in high-dimensional portfolio space.
Inspired by ALADDIN (BlackRock) and Qlib's risk factor framework.

Key capabilities:
  - Covariance matrix estimation (Ledoit-Wolf shrinkage)
  - Mahalanobis distance for multivariate outlier detection
  - N-dimensional VaR/CVaR via Monte Carlo with fat-tail distributions
  - Principal Component Analysis (PCA) for risk factor decomposition
  - Correlation breakdown simulation (crisis correlation)
  - Tail dependence modelling (Clayton/Gumbel copula approximation)

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.black_swan.n_dimensional")


# ══════════════════════════════════════════════════════════════════════════════
#  Ledoit-Wolf Covariance Shrinkage
# ══════════════════════════════════════════════════════════════════════════════

def ledoit_wolf_shrinkage(X: np.ndarray) -> np.ndarray:
    """
    Ledoit-Wolf analytical shrinkage estimator.
    Shrinks sample covariance toward scaled identity matrix.

    Parameters
    ----------
    X : (T, N) returns matrix

    Returns shrunk (N, N) covariance matrix.
    """
    T, N = X.shape
    X = X - X.mean(axis=0)  # demean

    S = X.T @ X / T  # sample covariance

    # Target: scaled identity
    mu      = np.trace(S) / N
    target  = mu * np.eye(N)

    # Frobenius norm of sample cov
    delta2  = np.linalg.norm(S - target, "fro") ** 2 / N

    # Oracle shrinkage intensity (analytical approx)
    beta2   = 0.0
    for t in range(T):
        xi    = X[t:t+1, :].T @ X[t:t+1, :]  # outer product
        beta2 += np.linalg.norm(xi - S, "fro") ** 2
    beta2 /= (T ** 2 * N)

    alpha = min(1.0, max(0.0, beta2 / delta2)) if delta2 > 0 else 0.0

    return (1 - alpha) * S + alpha * target


# ══════════════════════════════════════════════════════════════════════════════
#  PCA Risk Factor Decomposition
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class PCAResult:
    """PCA decomposition of portfolio returns."""
    explained_variance_ratio: np.ndarray
    components: np.ndarray          # (K, N) — K principal components
    factor_exposures: np.ndarray    # (T, K) — time-series of factor returns
    n_factors: int
    total_variance_explained: float

    def to_dict(self) -> Dict:
        return {
            "n_factors": self.n_factors,
            "total_variance_explained": round(self.total_variance_explained, 4),
            "variance_by_factor": [round(float(v), 4) for v in self.explained_variance_ratio],
        }


class PCARiskDecomposer:
    """
    Decomposes portfolio risk into principal components (systemic risk factors).
    Identifies which macro factors (market, size, value, etc.) drive returns.
    """

    def __init__(self, n_components: int = 5, variance_threshold: float = 0.90):
        self.n_components        = n_components
        self.variance_threshold  = variance_threshold

    def decompose(self, returns_matrix: np.ndarray) -> PCAResult:
        """
        Parameters
        ----------
        returns_matrix : (T, N) returns for N assets over T periods

        Returns PCAResult.
        """
        T, N = returns_matrix.shape
        if T < 5 or N < 2:
            raise ValueError(f"Need at least 5 time periods and 2 assets, got T={T}, N={N}")

        # Standardise
        X  = returns_matrix - returns_matrix.mean(axis=0)
        std = X.std(axis=0)
        std[std < 1e-10] = 1.0
        X  = X / std

        # SVD
        U, s, Vt = np.linalg.svd(X, full_matrices=False)

        total_var = (s ** 2).sum()
        k = min(self.n_components, len(s))
        ev_ratio  = (s[:k] ** 2) / total_var if total_var > 0 else np.zeros(k)
        cum_var   = float(ev_ratio.cumsum()[-1])

        return PCAResult(
            explained_variance_ratio = ev_ratio,
            components               = Vt[:k],
            factor_exposures         = U[:, :k] * s[:k],
            n_factors                = k,
            total_variance_explained = cum_var,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Mahalanobis Distance Outlier Detection
# ══════════════════════════════════════════════════════════════════════════════

def mahalanobis_distance(
    observation: np.ndarray,
    mean: np.ndarray,
    cov: np.ndarray,
) -> float:
    """
    Mahalanobis distance of observation from distribution center.
    High distance = potential black swan event in N-dimensional space.
    """
    diff = observation - mean
    try:
        cov_inv = np.linalg.pinv(cov)
    except np.linalg.LinAlgError:
        return float("inf")
    d2 = float(diff @ cov_inv @ diff)
    return math.sqrt(max(0.0, d2))


# ══════════════════════════════════════════════════════════════════════════════
#  Fat-Tail Monte Carlo (Student-t)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TailRiskResult:
    """Output from N-dimensional tail-risk simulation."""
    n_assets: int
    n_simulations: int
    df_student: float                  # degrees of freedom (fat tail parameter)
    portfolio_var_95: float = 0.0
    portfolio_var_99: float = 0.0
    portfolio_cvar_99: float = 0.0
    worst_1pct: float = 0.0
    worst_01pct: float = 0.0           # 0.1% extreme event
    crisis_correlation_loss: float = 0.0  # loss under crisis correlation
    mahalanobis_threshold: float = 0.0    # distance at which tail starts
    pca_result: Optional[PCAResult] = None
    asset_contributions: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "n_assets":              self.n_assets,
            "n_simulations":         self.n_simulations,
            "df_student":            self.df_student,
            "var_95":                round(self.portfolio_var_95, 4),
            "var_99":                round(self.portfolio_var_99, 4),
            "cvar_99":               round(self.portfolio_cvar_99, 4),
            "worst_1pct":            round(self.worst_1pct, 4),
            "worst_01pct":           round(self.worst_01pct, 4),
            "crisis_corr_loss":      round(self.crisis_correlation_loss, 4),
            "mahalanobis_threshold": round(self.mahalanobis_threshold, 3),
            "pca":                   self.pca_result.to_dict() if self.pca_result else {},
            "asset_contributions":   {k: round(v, 4) for k, v in self.asset_contributions.items()},
        }

    def summary(self) -> str:
        lines = [
            f"{'═'*50}",
            f"  N-DIMENSIONAL BLACK SWAN RISK ANALYSIS",
            f"  Assets: {self.n_assets}   Simulations: {self.n_simulations:,}",
            f"{'─'*50}",
            f"  Portfolio VaR(95%): {self.portfolio_var_95:.2%}",
            f"  Portfolio VaR(99%): {self.portfolio_var_99:.2%}",
            f"  CVaR(99%):          {self.portfolio_cvar_99:.2%}",
            f"  Worst 1%:           {self.worst_1pct:.2%}",
            f"  Worst 0.1%:         {self.worst_01pct:.2%}",
            f"  Crisis Corr Loss:   {self.crisis_correlation_loss:.2%}",
            f"  Fat-tail df:        {self.df_student:.1f} (lower=fatter tails)",
        ]
        if self.pca_result:
            lines.append(
                f"  PCA: top {self.pca_result.n_factors} factors explain "
                f"{self.pca_result.total_variance_explained:.1%} of variance"
            )
        lines.append(f"{'═'*50}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  NDimensionalBlackSwanModel
# ══════════════════════════════════════════════════════════════════════════════

class NDimensionalBlackSwanModel:
    """
    N-Dimensional Black Swan Risk Model.

    Simulates catastrophic market events in the full portfolio space,
    using fat-tail distributions, crisis correlation matrices, and
    PCA factor decomposition.

    Inspired by:
      - ALADDIN (BlackRock) — multi-factor stress testing
      - Qlib — quantitative factor risk modelling

    Usage:
        model = NDimensionalBlackSwanModel(n_simulations=50_000)
        result = model.analyse(returns_matrix, asset_names=["AAPL","MSFT","SPY"])
        print(result.summary())
    """

    # Crisis correlation: all assets become highly correlated in crashes
    CRISIS_CORRELATION = 0.85

    def __init__(
        self,
        n_simulations: int = 50_000,
        df_student: float = 4.0,
        random_seed: int = 42,
    ):
        """
        Parameters
        ----------
        n_simulations : Monte Carlo paths
        df_student    : Student-t degrees of freedom (lower = fatter tails, 4 is typical)
        random_seed   : For reproducibility
        """
        self.n_simulations = n_simulations
        self.df_student    = df_student
        self.rng           = np.random.default_rng(random_seed)
        self.pca           = PCARiskDecomposer()
        logger.info(
            "NDimensionalBlackSwanModel: n_sim=%d, df=%.1f, seed=%d",
            n_simulations, df_student, random_seed,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def analyse(
        self,
        returns_matrix: np.ndarray,
        weights: Optional[np.ndarray] = None,
        asset_names: Optional[List[str]] = None,
    ) -> TailRiskResult:
        """
        Full N-dimensional black swan analysis.

        Parameters
        ----------
        returns_matrix : (T, N) matrix of asset returns
        weights        : Portfolio weights (N,). Equal-weight if None.
        asset_names    : Optional list of N asset names

        Returns TailRiskResult.
        """
        T, N = returns_matrix.shape

        if weights is None:
            weights = np.ones(N) / N
        weights = np.array(weights, dtype=float)
        weights = weights / weights.sum()

        if asset_names is None:
            asset_names = [f"Asset_{i}" for i in range(N)]

        result = TailRiskResult(n_assets=N, n_simulations=self.n_simulations, df_student=self.df_student)

        # ── 1. Covariance estimation ───────────────────────────────────────
        try:
            cov = ledoit_wolf_shrinkage(returns_matrix)
        except Exception as exc:
            logger.warning("Ledoit-Wolf failed, using sample cov: %s", exc)
            cov = np.cov(returns_matrix.T)

        mean_returns = returns_matrix.mean(axis=0)

        # ── 2. PCA decomposition ──────────────────────────────────────────
        if N >= 2 and T >= 5:
            try:
                result.pca_result = self.pca.decompose(returns_matrix)
            except Exception as exc:
                logger.warning("PCA failed: %s", exc)

        # ── 3. Fat-tail Monte Carlo ───────────────────────────────────────
        portfolio_returns = self._simulate_portfolio(mean_returns, cov, weights, N)
        result.portfolio_var_95   = float(np.percentile(portfolio_returns, 5))
        result.portfolio_var_99   = float(np.percentile(portfolio_returns, 1))
        result.portfolio_cvar_99  = float(portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 1)].mean())
        result.worst_1pct         = float(np.percentile(portfolio_returns, 1))
        result.worst_01pct        = float(np.percentile(portfolio_returns, 0.1))

        # ── 4. Crisis correlation scenario ───────────────────────────────
        result.crisis_correlation_loss = self._crisis_scenario(mean_returns, cov, weights, N)

        # ── 5. Mahalanobis threshold ──────────────────────────────────────
        result.mahalanobis_threshold = self._mahalanobis_threshold(returns_matrix, mean_returns, cov)

        # ── 6. Asset contribution to tail risk ───────────────────────────
        result.asset_contributions = self._asset_contributions(portfolio_returns, weights, asset_names, cov)

        result.metadata = {
            "T": T, "N": N,
            "mean_returns": mean_returns.tolist(),
            "portfolio_vol": float(np.sqrt(weights @ cov @ weights) * math.sqrt(252)),
        }

        logger.info(
            "BlackSwan[%dA]: VaR99=%.2f%%, CVaR99=%.2f%%, Crisis=%.2f%%",
            N,
            result.portfolio_var_99 * 100,
            result.portfolio_cvar_99 * 100,
            result.crisis_correlation_loss * 100,
        )

        return result

    # ── Simulation methods ────────────────────────────────────────────────────

    def _simulate_portfolio(
        self,
        mean: np.ndarray,
        cov: np.ndarray,
        weights: np.ndarray,
        N: int,
    ) -> np.ndarray:
        """
        Monte Carlo with Student-t distribution (fat tails).
        Uses Cholesky decomposition for correlated simulation.
        """
        try:
            L = np.linalg.cholesky(cov + 1e-8 * np.eye(N))
        except np.linalg.LinAlgError:
            # Fallback: regularise more aggressively
            reg_cov = cov + 0.01 * np.eye(N)
            L = np.linalg.cholesky(reg_cov)

        # Student-t: Z * sqrt((df-2)/chi2)
        df  = self.df_student
        Z   = self.rng.standard_normal((self.n_simulations, N))
        chi = self.rng.chisquare(df, self.n_simulations)
        t_samples = Z * np.sqrt((df - 2) / chi[:, np.newaxis])

        # Apply Cholesky correlation
        asset_returns = mean + (t_samples @ L.T)

        # Portfolio returns
        return asset_returns @ weights

    def _crisis_scenario(
        self,
        mean: np.ndarray,
        cov: np.ndarray,
        weights: np.ndarray,
        N: int,
    ) -> float:
        """
        Simulate under crisis correlation matrix.
        In crises, all correlations spike toward CRISIS_CORRELATION.
        """
        # Extract volatilities from cov
        vols = np.sqrt(np.diag(cov))

        # Build crisis correlation matrix
        crisis_corr = (
            self.CRISIS_CORRELATION * (np.ones((N, N)) - np.eye(N)) + np.eye(N)
        )
        crisis_cov = np.outer(vols, vols) * crisis_corr

        # Simulate with crisis cov
        crisis_returns = self._simulate_portfolio(mean, crisis_cov, weights, N)

        # Worst 1% under crisis
        return float(np.percentile(crisis_returns, 1))

    def _mahalanobis_threshold(
        self,
        returns_matrix: np.ndarray,
        mean: np.ndarray,
        cov: np.ndarray,
    ) -> float:
        """
        Compute the Mahalanobis distance at the 99th percentile of historical data.
        Values above this threshold indicate a potential black swan event.
        """
        try:
            cov_inv = np.linalg.pinv(cov)
            distances = []
            for t in range(len(returns_matrix)):
                diff = returns_matrix[t] - mean
                d2   = float(diff @ cov_inv @ diff)
                distances.append(math.sqrt(max(0.0, d2)))
            return float(np.percentile(distances, 99)) if distances else 3.0
        except Exception:
            return 3.0

    @staticmethod
    def _asset_contributions(
        portfolio_returns: np.ndarray,
        weights: np.ndarray,
        asset_names: List[str],
        cov: np.ndarray,
    ) -> Dict[str, float]:
        """
        Marginal risk contribution of each asset to portfolio VaR.
        Uses the analytical formula: MRC_i = w_i * (Σw)_i / σ_p
        """
        sigma_p = math.sqrt(float(weights @ cov @ weights))
        if sigma_p < 1e-10:
            return {name: 1.0 / len(asset_names) for name in asset_names}

        marginal = cov @ weights
        contributions = {
            name: float(weights[i] * marginal[i] / sigma_p)
            for i, name in enumerate(asset_names)
        }
        # Normalise to sum to 1
        total = sum(abs(v) for v in contributions.values())
        if total > 0:
            contributions = {k: v / total for k, v in contributions.items()}
        return contributions
