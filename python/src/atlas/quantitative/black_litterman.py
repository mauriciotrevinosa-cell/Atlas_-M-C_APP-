"""
Black-Litterman Portfolio Optimization Model
=============================================
Reference: ALGORITHMS_LIBRARY.md — Algorithm #7

Mathematical Foundation:
  Prior (market equilibrium):
    μ_prior ~ N(Π, τΣ)         where Π = δΣw_mkt (reverse optimization)

  Views (investor expressed):
    Pμ = Q + ε,   ε ~ N(0, Ω)

  Posterior (Bayesian update):
    μ_BL = [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹ · [(τΣ)⁻¹Π + PᵀΩ⁻¹Q]
    Σ_BL = [(τΣ)⁻¹ + PᵀΩ⁻¹P]⁻¹ + Σ

Academic references:
  Black, F., Litterman, R. (1992). "Global Portfolio Optimization". FAJ.
  He, G., Litterman, R. (1999). "The Intuition Behind Black-Litterman". Goldman Sachs.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from scipy.optimize import minimize
    _SCIPY = True
except ImportError:
    _SCIPY = False

logger = logging.getLogger(__name__)


class BlackLittermanModel:
    """
    Black-Litterman Bayesian portfolio optimization.

    Combines market equilibrium returns with investor views to produce
    posterior expected returns and a posterior covariance matrix.
    These are then fed into a Markowitz optimizer to derive weights.

    Parameters
    ----------
    sigma       : (N, N) asset covariance matrix
    w_market    : (N,) market-cap weights (sum to 1)
    delta       : float, risk aversion coefficient (default 2.5)
    tau         : float, uncertainty scalar (default 0.025)

    Usage
    -----
    model = BlackLittermanModel(sigma, w_market)
    model.add_view(
        assets=['AAPL', 'MSFT', 'GOOGL'],
        weights=[1, -1, 0],       # AAPL outperforms MSFT
        return_target=0.02,       # by 2%
        confidence=0.0001         # Ω element
    )
    mu_bl, sigma_bl = model.posterior()
    weights = model.optimize()
    """

    def __init__(
        self,
        sigma:    np.ndarray,
        w_market: np.ndarray,
        delta:    float = 2.5,
        tau:      float = 0.025,
        asset_names: Optional[List[str]] = None,
    ):
        self.sigma    = np.asarray(sigma,    dtype=np.float64)
        self.w_market = np.asarray(w_market, dtype=np.float64)
        self.delta    = float(delta)
        self.tau      = float(tau)
        self.n        = len(w_market)

        self.asset_names = asset_names or [f'A{i}' for i in range(self.n)]

        # Implied equilibrium excess returns: Π = δΣw
        self._pi = self.delta * self.sigma @ self.w_market

        # Views storage
        self._P: List[np.ndarray] = []    # Pick matrices
        self._Q: List[float]      = []    # View returns
        self._omega: List[float]  = []    # View uncertainties

        self._mu_bl:    Optional[np.ndarray] = None
        self._sigma_bl: Optional[np.ndarray] = None

    # ── View Building ──────────────────────────────────────────────────────

    def add_view(
        self,
        assets: List[str],
        weights: List[float],
        return_target: float,
        confidence: float = 0.0001,
    ) -> 'BlackLittermanModel':
        """
        Add an investor view.

        Parameters
        ----------
        assets       : list of asset names involved in the view
        weights      : portfolio weights for the view (e.g., [1, -1] = A - B)
        return_target: expected return of the view (e.g., 0.02 = 2%)
        confidence   : uncertainty of the view (Ω element); smaller = more confident

        Example
        -------
        "AAPL will outperform MSFT by 2% with high confidence"
        model.add_view(['AAPL', 'MSFT'], [1, -1], 0.02, confidence=0.0001)
        """
        p = np.zeros(self.n)
        for asset, w in zip(assets, weights):
            if asset in self.asset_names:
                p[self.asset_names.index(asset)] = w
            else:
                logger.warning(f'BlackLitterman: asset "{asset}" not in universe. Skipped.')

        if np.abs(p).sum() < 1e-9:
            logger.warning('BlackLitterman: view has zero exposure — skipped.')
            return self

        self._P.append(p)
        self._Q.append(float(return_target))
        self._omega.append(float(confidence))
        # Invalidate cache
        self._mu_bl    = None
        self._sigma_bl = None
        return self

    def add_absolute_view(
        self,
        asset: str,
        return_target: float,
        confidence: float = 0.001,
    ) -> 'BlackLittermanModel':
        """
        Add an absolute view: "Asset X will return R%".

        Internally represented as P = [0...1...0], Q = [R].
        """
        p = np.zeros(self.n)
        if asset in self.asset_names:
            p[self.asset_names.index(asset)] = 1.0
        else:
            logger.warning(f'BlackLitterman: asset "{asset}" not found.')
            return self
        self._P.append(p)
        self._Q.append(float(return_target))
        self._omega.append(float(confidence))
        self._mu_bl = self._sigma_bl = None
        return self

    def clear_views(self) -> 'BlackLittermanModel':
        """Remove all investor views (resets to pure equilibrium)."""
        self._P, self._Q, self._omega = [], [], []
        self._mu_bl = self._sigma_bl = None
        return self

    # ── Core Computation ───────────────────────────────────────────────────

    def posterior(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Black-Litterman posterior expected returns and covariance.

        Returns
        -------
        mu_BL    : (N,) posterior mean returns
        sigma_BL : (N, N) posterior covariance matrix
        """
        if self._mu_bl is not None and self._sigma_bl is not None:
            return self._mu_bl, self._sigma_bl

        tau_sigma     = self.tau * self.sigma
        tau_sigma_inv = np.linalg.inv(tau_sigma + 1e-8 * np.eye(self.n))

        if not self._P:
            # No views — return prior equilibrium
            logger.info('BlackLitterman: No views — returning equilibrium returns.')
            self._mu_bl    = self._pi.copy()
            self._sigma_bl = self.sigma + tau_sigma
            return self._mu_bl, self._sigma_bl

        P   = np.vstack(self._P)           # (K, N)
        Q   = np.array(self._Q)            # (K,)
        Omega = np.diag(self._omega)       # (K, K)

        try:
            omega_inv   = np.linalg.inv(Omega)
            # A = (τΣ)⁻¹ + PᵀΩ⁻¹P
            A           = tau_sigma_inv + P.T @ omega_inv @ P
            # b = (τΣ)⁻¹Π + PᵀΩ⁻¹Q
            b           = tau_sigma_inv @ self._pi + P.T @ omega_inv @ Q

            self._mu_bl    = np.linalg.solve(A, b)
            self._sigma_bl = np.linalg.inv(A) + self.sigma
        except np.linalg.LinAlgError as exc:
            logger.error(f'BlackLitterman: Singular matrix — {exc}. Using prior.')
            self._mu_bl    = self._pi.copy()
            self._sigma_bl = self.sigma + tau_sigma

        return self._mu_bl, self._sigma_bl

    # ── Portfolio Optimization ─────────────────────────────────────────────

    def optimize(
        self,
        target_return:  Optional[float] = None,
        risk_aversion:  float = 2.5,
        long_only:      bool  = True,
        max_weight:     float = 1.0,
        min_weight:     float = 0.0,
    ) -> Dict:
        """
        Optimize portfolio weights using BL posterior returns.

        If target_return is None, maximizes Sharpe (μ - λ·w'Σw).

        Parameters
        ----------
        target_return  : float or None — targeted portfolio return
        risk_aversion  : Markowitz risk aversion λ
        long_only      : if True, weights ≥ 0
        max_weight     : maximum per-asset weight

        Returns
        -------
        dict with keys: weights, expected_return, portfolio_variance, sharpe
        """
        mu_bl, sigma_bl = self.posterior()

        if not _SCIPY:
            # Fallback: equal weights
            w = np.ones(self.n) / self.n
            return self._package_result(w, mu_bl, sigma_bl, 'equal-weight (scipy missing)')

        bounds = [(0.0 if long_only else -1.0, max_weight)] * self.n

        def neg_sharpe(w):
            ret = float(w @ mu_bl)
            var = float(w @ sigma_bl @ w)
            return -(ret / (np.sqrt(var) + 1e-9))

        def portfolio_var(w):
            return float(w @ sigma_bl @ w)

        constraints = [{'type': 'eq', 'fun': lambda w: w.sum() - 1.0}]
        if target_return is not None:
            constraints.append({
                'type': 'eq',
                'fun': lambda w, r=target_return: float(w @ mu_bl) - r
            })
            objective = portfolio_var
        else:
            objective = neg_sharpe

        w0  = np.ones(self.n) / self.n
        res = minimize(
            objective, w0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'ftol': 1e-9, 'maxiter': 1000},
        )

        if res.success:
            w = np.maximum(res.x, 0.0) if long_only else res.x
            w /= (w.sum() + 1e-9)
        else:
            logger.warning(f'BlackLitterman: Optimizer did not converge ({res.message}). Using 1/N.')
            w = np.ones(self.n) / self.n

        return self._package_result(w, mu_bl, sigma_bl, 'Black-Litterman SLSQP')

    def _package_result(
        self,
        w:        np.ndarray,
        mu_bl:    np.ndarray,
        sigma_bl: np.ndarray,
        method:   str,
    ) -> Dict:
        ret = float(w @ mu_bl)
        var = float(w @ sigma_bl @ w)
        return {
            'weights':   {a: round(float(wi), 6) for a, wi in zip(self.asset_names, w)},
            'weights_arr': w,
            'expected_return': round(ret, 6),
            'portfolio_variance': round(var, 8),
            'portfolio_vol': round(float(np.sqrt(var)), 6),
            'sharpe': round(ret / (float(np.sqrt(var)) + 1e-9), 4),
            'equilibrium_returns': {a: round(float(p), 6) for a, p in zip(self.asset_names, self._pi)},
            'bl_returns': {a: round(float(m), 6) for a, m in zip(self.asset_names, mu_bl)},
            'n_views': len(self._P),
            'method': method,
        }

    # ── Diagnostics ────────────────────────────────────────────────────────

    @property
    def equilibrium_returns(self) -> Dict[str, float]:
        """Implied equilibrium returns Π = δΣw_mkt."""
        return {a: round(float(p), 6) for a, p in zip(self.asset_names, self._pi)}

    @property
    def view_count(self) -> int:
        return len(self._P)

    def __repr__(self) -> str:
        return (
            f'BlackLittermanModel(n={self.n}, δ={self.delta}, τ={self.tau}, '
            f'views={len(self._P)})'
        )
