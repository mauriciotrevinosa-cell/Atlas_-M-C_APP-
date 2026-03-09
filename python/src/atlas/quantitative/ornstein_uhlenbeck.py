"""
Ornstein-Uhlenbeck (OU) Process
================================
Reference: quant-traderr-lab (MIT license), ALGORITHMS_LIBRARY.md

The OU process is the continuous-time equivalent of an AR(1) model.
It describes mean-reverting dynamics: when the process is above its long-run
mean, it tends to drift down; when below, it tends to drift up.

SDE:   dX = θ(μ - X)dt + σdW

Where:
  θ (kappa): mean-reversion speed (higher = reverts faster)
  μ (mu):    long-run mean level
  σ (sigma): diffusion coefficient (volatility of noise)
  W:         Wiener process (Brownian motion)

Exact discretization (Euler-Maruyama → exact for OU):
  X(t+Δt) = X(t)·e^(-θΔt) + μ(1 - e^(-θΔt)) + σ√((1-e^(-2θΔt))/2θ)·Z
  Z ~ N(0,1)

Applications in Atlas:
  1. Pairs trading spread modeling (spread = log(P1/P2))
  2. Short-rate interest rate modeling (Vasicek)
  3. Mean-reversion signal generation
  4. VIX/volatility modeling
  5. Black Swan signal (if spread far from mean → reversion opportunity)

Reference:
  Uhlenbeck, G.E., Ornstein, L.S. (1930). "On the Theory of Brownian Motion"
  Vasicek, O. (1977). "An Equilibrium Characterization of the Term Structure"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

try:
    from scipy.optimize import minimize
    from scipy.stats import norm
    _SCIPY = True
except ImportError:
    _SCIPY = False

logger = logging.getLogger(__name__)


@dataclass
class OUParameters:
    """Fitted OU process parameters."""
    kappa: float    # mean-reversion speed (θ)
    mu:    float    # long-run mean (μ)
    sigma: float    # diffusion (σ)
    # Derived
    half_life:  float = 0.0   # ln(2)/θ — time to halve deviation
    sigma_eq:   float = 0.0   # σ/√(2θ) — equilibrium std dev
    # Diagnostics
    n_obs:      int   = 0
    r_squared:  float = 0.0

    def __post_init__(self):
        self.half_life = math.log(2) / (self.kappa + 1e-9) if self.kappa > 0 else np.inf
        self.sigma_eq  = self.sigma / math.sqrt(2 * self.kappa + 1e-9)

    def to_dict(self) -> Dict:
        return {
            'kappa':      round(self.kappa, 6),
            'mu':         round(self.mu, 6),
            'sigma':      round(self.sigma, 6),
            'half_life':  round(self.half_life, 4),
            'sigma_eq':   round(self.sigma_eq, 6),
            'n_obs':      self.n_obs,
            'r_squared':  round(self.r_squared, 4),
        }


import math


class OrnsteinUhlenbeckProcess:
    """
    Ornstein-Uhlenbeck process — simulation and signal generation.

    Parameters
    ----------
    kappa : mean-reversion speed θ (e.g., 1.0 = reverts to μ in ~1 period)
    mu    : long-run equilibrium level
    sigma : diffusion coefficient
    x0    : initial value (defaults to mu)
    """

    def __init__(
        self,
        kappa: float = 1.0,
        mu:    float = 0.0,
        sigma: float = 0.1,
        x0:    Optional[float] = None,
        dt:    float = 1.0,   # time step (e.g., 1 = daily)
    ):
        self.kappa = kappa
        self.mu    = mu
        self.sigma = sigma
        self.dt    = dt
        self.x     = x0 if x0 is not None else mu

        # Pre-compute exact transition coefficients
        self._e     = math.exp(-kappa * dt)
        self._drift = mu * (1 - self._e)
        self._noise = sigma * math.sqrt((1 - self._e ** 2) / (2 * kappa + 1e-9))

    # ── Simulation ─────────────────────────────────────────────────────────

    def step(self, n_steps: int = 1) -> np.ndarray:
        """
        Simulate n_steps forward.

        Returns array of shape (n_steps,) with the path values.
        """
        path = np.empty(n_steps)
        x    = self.x
        e, drift, noise = self._e, self._drift, self._noise

        for i in range(n_steps):
            x = x * e + drift + noise * np.random.randn()
            path[i] = x

        self.x = x
        return path

    def simulate(
        self,
        n_steps:  int,
        n_paths:  int = 1,
        x0:       Optional[float] = None,
    ) -> np.ndarray:
        """
        Simulate multiple paths from scratch.

        Returns array of shape (n_paths, n_steps).
        """
        x0    = x0 if x0 is not None else self.mu
        e     = self._e
        drift = self._drift
        noise = self._noise

        paths = np.empty((n_paths, n_steps))
        X     = np.full(n_paths, x0)

        for i in range(n_steps):
            Z       = np.random.randn(n_paths)
            X       = X * e + drift + noise * Z
            paths[:, i] = X

        return paths if n_paths > 1 else paths[0]

    def reset(self, x0: Optional[float] = None) -> None:
        """Reset process to x0 (or long-run mean)."""
        self.x = x0 if x0 is not None else self.mu

    # ── Signal Generation ──────────────────────────────────────────────────

    def z_score(self, x: Optional[float] = None) -> float:
        """
        Compute normalized deviation from equilibrium.

        z = (X - μ) / σ_eq  where σ_eq = σ/√(2θ)

        z > 2: overbought (expect reversion down)
        z < -2: oversold (expect reversion up)
        """
        val    = x if x is not None else self.x
        sigma_eq = self.sigma / math.sqrt(2 * self.kappa + 1e-9)
        return (val - self.mu) / (sigma_eq + 1e-9)

    def entry_signal(
        self,
        x:          float,
        entry_z:    float = 2.0,
        exit_z:     float = 0.5,
        current_pos: int  = 0,
    ) -> int:
        """
        Trading signal based on OU z-score.

        Returns:
           +1 = BUY (z < -entry_z, expect mean reversion up)
           -1 = SELL (z > +entry_z, expect mean reversion down)
            0 = HOLD/CLOSE (within exit_z of mean)
        """
        z = self.z_score(x)

        if current_pos == 0:
            if z < -entry_z:  return  1   # Open long
            if z >  entry_z:  return -1   # Open short
        elif current_pos > 0:
            if z > -exit_z:   return  0   # Close long
        elif current_pos < 0:
            if z <  exit_z:   return  0   # Close short

        return current_pos

    def expected_reversion_time(self, x: float) -> float:
        """
        Expected time (in steps) to revert to within 1σ of μ.

        Approximation: t ≈ ln(|x - μ| / σ_eq) / θ
        """
        sigma_eq = self.sigma / math.sqrt(2 * self.kappa + 1e-9)
        deviation = abs(x - self.mu)
        if deviation <= sigma_eq:
            return 0.0
        return math.log(deviation / sigma_eq) / (self.kappa + 1e-9)

    # ── Analytics ──────────────────────────────────────────────────────────

    @property
    def half_life(self) -> float:
        """Time for deviation to halve: ln(2) / θ."""
        return math.log(2) / (self.kappa + 1e-9)

    @property
    def equilibrium_std(self) -> float:
        """Steady-state standard deviation: σ/√(2θ)."""
        return self.sigma / math.sqrt(2 * self.kappa + 1e-9)

    @property
    def autocorrelation(self) -> float:
        """Lag-1 autocorrelation of discrete increments: exp(-θΔt)."""
        return self._e

    def __repr__(self) -> str:
        return (
            f'OUProcess(κ={self.kappa:.4f}, μ={self.mu:.4f}, '
            f'σ={self.sigma:.4f}, half_life={self.half_life:.2f})'
        )


class OUFitter:
    """
    Fit Ornstein-Uhlenbeck parameters from time-series data.

    Methods:
      OLS      — Fast closed-form regression (AR(1))
      MLE      — Maximum Likelihood Estimation (accurate)
    """

    @staticmethod
    def fit_ols(x: np.ndarray, dt: float = 1.0) -> OUParameters:
        """
        Fit OU parameters via OLS regression on AR(1) representation.

        X(t) = A + B·X(t-1) + ε
        → B = e^(-θΔt)  → θ = -ln(B)/Δt
        → A = μ(1 - e^(-θΔt)) → μ = A/(1-B)
        → σ² = Var(ε) × 2θ / (1 - e^(-2θΔt))
        """
        x    = np.asarray(x, dtype=np.float64)
        X    = x[:-1].reshape(-1, 1)
        Y    = x[1:]
        n    = len(Y)

        # OLS: Y = A + B*X
        X_aug = np.column_stack([np.ones(n), X])
        beta  = np.linalg.lstsq(X_aug, Y, rcond=None)[0]
        A, B  = float(beta[0]), float(beta[1])

        # Residuals
        Y_hat = X_aug @ beta
        resid = Y - Y_hat
        var_e = float(np.var(resid, ddof=2))

        # R²
        ss_res = float(np.sum(resid ** 2))
        ss_tot = float(np.sum((Y - Y.mean()) ** 2))
        r2     = 1.0 - ss_res / (ss_tot + 1e-9)

        # Recover OU params
        B     = min(max(B, 1e-6), 1.0 - 1e-6)
        kappa = -math.log(B) / dt
        mu    = A / (1.0 - B)
        e2    = math.exp(-2 * kappa * dt)
        sigma = math.sqrt(var_e * 2 * kappa / (1.0 - e2 + 1e-9))

        return OUParameters(
            kappa=max(kappa, 1e-6), mu=mu, sigma=max(sigma, 1e-9),
            n_obs=n, r_squared=r2,
        )

    @staticmethod
    def fit_mle(x: np.ndarray, dt: float = 1.0) -> OUParameters:
        """
        Fit OU parameters via Maximum Likelihood Estimation.

        More accurate than OLS but slower.
        Uses scipy.optimize.minimize on the negative log-likelihood.
        """
        if not _SCIPY:
            logger.warning('OUFitter.fit_mle: scipy not available. Falling back to OLS.')
            return OUFitter.fit_ols(x, dt)

        x = np.asarray(x, dtype=np.float64)
        n = len(x) - 1

        def neg_log_likelihood(params):
            kappa, mu, sigma = params
            if kappa <= 0 or sigma <= 0:
                return 1e10

            e   = math.exp(-kappa * dt)
            m   = mu * (1 - e)
            s2  = sigma ** 2 * (1 - e ** 2) / (2 * kappa)
            s   = math.sqrt(max(s2, 1e-15))

            residuals = x[1:] - (x[:-1] * e + m)
            nll = n * math.log(s) + 0.5 * float(np.sum(residuals ** 2)) / s2
            return nll

        # Initial guess from OLS
        ols  = OUFitter.fit_ols(x, dt)
        x0   = [ols.kappa, ols.mu, ols.sigma]
        bounds = [(1e-6, 100), (-1e6, 1e6), (1e-9, 100)]

        res  = minimize(neg_log_likelihood, x0, method='L-BFGS-B', bounds=bounds)

        if res.success:
            k, m, s = res.x
            return OUParameters(kappa=k, mu=m, sigma=s, n_obs=n)
        else:
            logger.warning(f'OUFitter.fit_mle: optimizer failed ({res.message}). Returning OLS.')
            return ols

    @staticmethod
    def fit(x: np.ndarray, dt: float = 1.0, method: str = 'ols') -> OUParameters:
        """
        Fit OU parameters. Method: 'ols' (fast) or 'mle' (accurate).
        """
        if method == 'mle':
            return OUFitter.fit_mle(x, dt)
        return OUFitter.fit_ols(x, dt)

    @staticmethod
    def spread_zscore(
        series1:  np.ndarray,
        series2:  np.ndarray,
        hedge_ratio: Optional[float] = None,
        dt:       float = 1.0,
    ) -> Tuple[np.ndarray, OUParameters, float]:
        """
        Compute the OU spread z-score for pairs trading.

        1. Estimates hedge ratio β via OLS (series1 = α + β·series2)
        2. Fits OU to spread = log(series1) - β·log(series2)
        3. Returns z-score series, OU params, hedge ratio

        Returns
        -------
        z_scores    : (N,) normalized OU spread
        ou_params   : fitted OUParameters
        hedge_ratio : estimated β
        """
        log1 = np.log(np.asarray(series1, dtype=np.float64) + 1e-9)
        log2 = np.log(np.asarray(series2, dtype=np.float64) + 1e-9)

        # Estimate hedge ratio
        if hedge_ratio is None:
            X = np.column_stack([np.ones(len(log2)), log2])
            beta = np.linalg.lstsq(X, log1, rcond=None)[0]
            hedge_ratio = float(beta[1])

        spread  = log1 - hedge_ratio * log2
        ou      = OUFitter.fit_ols(spread, dt)
        sigma_e = ou.sigma_eq

        z_scores = (spread - ou.mu) / (sigma_e + 1e-9)
        return z_scores, ou, hedge_ratio
