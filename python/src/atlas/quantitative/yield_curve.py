"""
Yield Curve Analysis — Nelson-Siegel(-Svensson) Model.

Implements:
  · NelsonSiegel      — 3-factor term structure model
  · NelsonSiegelSvensson — 4-factor extended model (better long-end fit)
  · YieldCurveAnalyzer — curvature, slope, level metrics + regime signals

Mathematical basis:
  Nelson-Siegel (1987):
    y(τ) = β₀ + β₁·[(1-e^(-λτ))/(λτ)] + β₂·[(1-e^(-λτ))/(λτ) - e^(-λτ)]

  Where:
    β₀ = long-term level (→ y as τ→∞)
    β₁ = slope    (short-term contribution; negative → upward sloping)
    β₂ = curvature (hump factor; peaks at τ* = 1/λ · ln((β₀+β₂)/β₀))
    λ  = decay parameter (controls peak location)

  Svensson extension adds a second hump:
    y(τ) = NS(τ) + β₃·[(1-e^(-λ₂τ))/(λ₂τ) - e^(-λ₂τ)]

  Key Signals:
    Inversion      : y(2Y) > y(10Y) → recession signal
    Steepening     : 10Y-2Y spread rising → reflation
    Bear flattening: short rates rise faster → hawkish Fed
    Bull steepening: long rates rise, short rates anchored → inflation expectations
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from scipy.optimize import minimize
    _SCIPY = True
except ImportError:
    _SCIPY = False


# ── Nelson-Siegel ──────────────────────────────────────────────────────────────

@dataclass
class NSParameters:
    """Fitted Nelson-Siegel parameters."""
    beta0:    float   # long-term level
    beta1:    float   # slope
    beta2:    float   # curvature
    lam:      float   # decay lambda
    rmse:     float   # root mean squared fit error
    r_squared: float  # goodness of fit

    def to_dict(self) -> Dict:
        return {
            'beta0':     round(self.beta0, 6),
            'beta1':     round(self.beta1, 6),
            'beta2':     round(self.beta2, 6),
            'lambda':    round(self.lam, 6),
            'rmse':      round(self.rmse, 6),
            'r_squared': round(self.r_squared, 4),
        }


@dataclass
class NSSParameters:
    """Fitted Nelson-Siegel-Svensson parameters."""
    beta0:    float
    beta1:    float
    beta2:    float
    beta3:    float
    lam1:     float
    lam2:     float
    rmse:     float
    r_squared: float

    def to_dict(self) -> Dict:
        return {
            'beta0':     round(self.beta0, 6),
            'beta1':     round(self.beta1, 6),
            'beta2':     round(self.beta2, 6),
            'beta3':     round(self.beta3, 6),
            'lambda1':   round(self.lam1, 6),
            'lambda2':   round(self.lam2, 6),
            'rmse':      round(self.rmse, 6),
            'r_squared': round(self.r_squared, 4),
        }


class NelsonSiegel:
    """
    Nelson-Siegel term structure model.

    Usage
    -----
    ns = NelsonSiegel()
    params = ns.fit(maturities, yields)
    curve  = ns.predict(maturities, params)
    """

    # ── Forward functions ─────────────────────────────────────────────────────

    @staticmethod
    def basis(tau: np.ndarray, lam: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute the three Nelson-Siegel basis functions.

        Returns (f1, f2, f3) each of shape (len(tau),)
          f1 = 1                                     (level)
          f2 = (1 - exp(-λτ)) / (λτ)               (slope)
          f3 = (1 - exp(-λτ)) / (λτ) - exp(-λτ)   (curvature)
        """
        t   = np.asarray(tau, dtype=np.float64)
        lt  = lam * t
        # Avoid division by zero for τ=0
        with np.errstate(divide='ignore', invalid='ignore'):
            e   = np.exp(-lt)
            f2  = np.where(lt > 1e-8, (1.0 - e) / lt, 1.0)
            f3  = f2 - e
        return np.ones_like(t), f2, f3

    @staticmethod
    def predict_yield(
        tau:    np.ndarray,
        beta0:  float,
        beta1:  float,
        beta2:  float,
        lam:    float,
    ) -> np.ndarray:
        """Evaluate Nelson-Siegel yield at maturities τ."""
        f1, f2, f3 = NelsonSiegel.basis(tau, lam)
        return beta0 * f1 + beta1 * f2 + beta2 * f3

    # ── Fitting ───────────────────────────────────────────────────────────────

    def fit(
        self,
        maturities: np.ndarray,
        yields:     np.ndarray,
        lam_grid:   Optional[np.ndarray] = None,
    ) -> NSParameters:
        """
        Fit Nelson-Siegel model via OLS (for fixed λ) + grid search over λ.

        For each candidate λ, the model is linear in β → exact OLS.
        Select λ minimizing RMSE.

        Parameters
        ----------
        maturities : array of maturities in years (e.g. [0.25, 0.5, 1, 2, 5, 10, 30])
        yields     : observed yields (same length as maturities)
        lam_grid   : optional grid of λ values to search over

        Returns
        -------
        NSParameters with best-fit β₀, β₁, β₂, λ
        """
        tau = np.asarray(maturities, dtype=np.float64)
        y   = np.asarray(yields,     dtype=np.float64)

        if lam_grid is None:
            # Grid over λ: corresponds to peak maturities 0.5–15 years
            lam_grid = np.linspace(0.01, 3.0, 200)

        best_rmse   = np.inf
        best_params = None

        for lam in lam_grid:
            f1, f2, f3 = self.basis(tau, lam)
            A = np.column_stack([f1, f2, f3])

            # OLS: β = (AᵀA)⁻¹Aᵀy
            try:
                betas, _, _, _ = np.linalg.lstsq(A, y, rcond=None)
            except np.linalg.LinAlgError:
                continue

            y_hat = A @ betas
            rmse  = float(np.sqrt(np.mean((y - y_hat) ** 2)))

            if rmse < best_rmse:
                best_rmse   = rmse
                best_params = (float(betas[0]), float(betas[1]), float(betas[2]), float(lam))

        if best_params is None:
            # Fallback: flat curve
            best_params = (float(y.mean()), 0.0, 0.0, 0.5)
            best_rmse   = float(np.std(y))

        b0, b1, b2, lam = best_params
        y_fit  = self.predict_yield(tau, b0, b1, b2, lam)
        ss_res = float(np.sum((y - y_fit) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2     = 1.0 - ss_res / (ss_tot + 1e-12)

        return NSParameters(
            beta0=b0, beta1=b1, beta2=b2, lam=lam,
            rmse=best_rmse, r_squared=r2,
        )

    def predict(self, maturities: np.ndarray, params: NSParameters) -> np.ndarray:
        """Generate model yields at given maturities."""
        return self.predict_yield(
            np.asarray(maturities, dtype=np.float64),
            params.beta0, params.beta1, params.beta2, params.lam,
        )

    def __repr__(self) -> str:
        return 'NelsonSiegel()'


class NelsonSiegelSvensson(NelsonSiegel):
    """
    Nelson-Siegel-Svensson (4-factor) term structure model.

    Adds a second hump term for better long-end fitting.
    """

    @staticmethod
    def basis_nss(
        tau:  np.ndarray,
        lam1: float,
        lam2: float,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """4-factor NSS basis functions."""
        f1, f2, f3 = NelsonSiegel.basis(tau, lam1)
        t   = np.asarray(tau, dtype=np.float64)
        lt2 = lam2 * t
        with np.errstate(divide='ignore', invalid='ignore'):
            e2 = np.exp(-lt2)
            f4 = np.where(lt2 > 1e-8, (1.0 - e2) / lt2 - e2, 0.0)
        return f1, f2, f3, f4

    @staticmethod
    def predict_yield_nss(
        tau: np.ndarray,
        b0: float, b1: float, b2: float, b3: float,
        lam1: float, lam2: float,
    ) -> np.ndarray:
        f1, f2, f3, f4 = NelsonSiegelSvensson.basis_nss(tau, lam1, lam2)
        return b0 * f1 + b1 * f2 + b2 * f3 + b3 * f4

    def fit_nss(
        self,
        maturities: np.ndarray,
        yields:     np.ndarray,
    ) -> NSSParameters:
        """
        Fit NSS model via scipy optimization.
        Falls back to NS (β₃=0) if scipy unavailable.
        """
        tau = np.asarray(maturities, dtype=np.float64)
        y   = np.asarray(yields,     dtype=np.float64)

        if not _SCIPY:
            # Fallback: fit NS and set β₃=0
            ns_params = self.fit(tau, y)
            return NSSParameters(
                beta0=ns_params.beta0, beta1=ns_params.beta1,
                beta2=ns_params.beta2, beta3=0.0,
                lam1=ns_params.lam, lam2=ns_params.lam,
                rmse=ns_params.rmse, r_squared=ns_params.r_squared,
            )

        def _loss(params):
            b0, b1, b2, b3, lam1, lam2 = params
            if lam1 <= 0 or lam2 <= 0:
                return 1e9
            y_hat = self.predict_yield_nss(tau, b0, b1, b2, b3, lam1, lam2)
            return float(np.sum((y - y_hat) ** 2))

        # Initial guess from NS
        ns_p = self.fit(tau, y)
        x0   = [ns_p.beta0, ns_p.beta1, ns_p.beta2, 0.01, ns_p.lam, ns_p.lam * 0.5]
        bounds = [
            (None, None), (None, None), (None, None), (None, None),
            (0.001, 10.0), (0.001, 10.0),
        ]

        res = minimize(_loss, x0, bounds=bounds, method='L-BFGS-B')
        b0, b1, b2, b3, lam1, lam2 = res.x

        y_fit  = self.predict_yield_nss(tau, b0, b1, b2, b3, lam1, lam2)
        rmse   = float(np.sqrt(np.mean((y - y_fit) ** 2)))
        ss_res = float(np.sum((y - y_fit) ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2     = 1.0 - ss_res / (ss_tot + 1e-12)

        return NSSParameters(
            beta0=float(b0), beta1=float(b1), beta2=float(b2), beta3=float(b3),
            lam1=float(lam1), lam2=float(lam2),
            rmse=rmse, r_squared=r2,
        )


# ── Yield Curve Analyzer ───────────────────────────────────────────────────────

class YieldCurveAnalyzer:
    """
    High-level yield curve analysis.

    Computes standard market metrics and generates regime signals.
    """

    # Standard tenors (years)
    STANDARD_TENORS = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0]

    def __init__(self):
        self._ns  = NelsonSiegel()
        self._nss = NelsonSiegelSvensson()

    # ── Curve metrics ─────────────────────────────────────────────────────────

    def metrics(
        self,
        maturities: np.ndarray,
        yields:     np.ndarray,
    ) -> Dict:
        """
        Compute standard yield curve metrics.

        Returns dict with level, slope, curvature, spreads, inversion flags.
        """
        tau = np.asarray(maturities, dtype=np.float64)
        y   = np.asarray(yields,     dtype=np.float64)

        # Interpolate to standard tenors
        def _interp(t):
            return float(np.interp(t, tau, y))

        y_3m  = _interp(0.25)
        y_6m  = _interp(0.5)
        y_1y  = _interp(1.0)
        y_2y  = _interp(2.0)
        y_5y  = _interp(5.0)
        y_10y = _interp(10.0)
        y_30y = _interp(30.0) if tau.max() >= 30 else _interp(tau.max())

        # Level: 10Y yield
        level     = y_10y

        # Slope: 10Y - 2Y (classic term premium proxy)
        slope_10_2 = y_10y - y_2y

        # Slope: 10Y - 3M (recession indicator)
        slope_10_3m = y_10y - y_3m

        # Curvature: 2×5Y - 2Y - 10Y (butterfly)
        curvature = 2.0 * y_5y - y_2y - y_10y

        # Inversions
        inverted_2_10  = slope_10_2  < 0.0
        inverted_3m_10 = slope_10_3m < 0.0

        # Fit Nelson-Siegel
        try:
            ns_params = self._ns.fit(tau, y)
            ns_dict   = ns_params.to_dict()
        except Exception:
            ns_dict = {}

        # Regime signal
        regime = self._regime_signal(slope_10_2, slope_10_3m, curvature)

        return {
            # Point rates
            'y_3m':   round(y_3m, 4),
            'y_6m':   round(y_6m, 4),
            'y_1y':   round(y_1y, 4),
            'y_2y':   round(y_2y, 4),
            'y_5y':   round(y_5y, 4),
            'y_10y':  round(y_10y, 4),
            'y_30y':  round(y_30y, 4),
            # Metrics
            'level':            round(level, 4),
            'slope_10y_2y':     round(slope_10_2, 4),
            'slope_10y_3m':     round(slope_10_3m, 4),
            'curvature':        round(curvature, 4),
            # Inversion flags
            'inverted_2_10':    inverted_2_10,
            'inverted_3m_10':   inverted_3m_10,
            # Regime
            'regime':           regime,
            # Model
            'nelson_siegel':    ns_dict,
        }

    # ── Regime signals ────────────────────────────────────────────────────────

    @staticmethod
    def _regime_signal(
        slope_10_2:  float,
        slope_10_3m: float,
        curvature:   float,
    ) -> str:
        """
        Classify yield curve regime.

        Returns one of:
          NORMAL_STEEP   : upward sloping, reflation
          NORMAL_FLAT    : flattening, late cycle
          INVERTED       : both 2Y>10Y and 3M>10Y → recession risk
          HUMPED         : positive curvature, mixed signals
          BEAR_FLAT      : flattening with rising rates
        """
        if slope_10_3m < -0.10 and slope_10_2 < -0.10:
            return 'INVERTED'
        elif slope_10_2 > 0.50:
            return 'NORMAL_STEEP'
        elif slope_10_2 < 0.10:
            return 'NORMAL_FLAT'
        elif curvature > 0.20:
            return 'HUMPED'
        else:
            return 'TRANSITIONING'

    # ── Forward rates ─────────────────────────────────────────────────────────

    @staticmethod
    def forward_rate(
        t1: float,
        t2: float,
        y1: float,
        y2: float,
    ) -> float:
        """
        Compute forward rate f(t1, t2) implied by spot rates y1 and y2.

        f(t1, t2) = (y2 × t2 - y1 × t1) / (t2 - t1)
        """
        if abs(t2 - t1) < 1e-9:
            return y1
        return (y2 * t2 - y1 * t1) / (t2 - t1)

    def forward_curve(
        self,
        maturities: np.ndarray,
        yields:     np.ndarray,
        tenors:     Optional[List[float]] = None,
    ) -> List[Dict]:
        """
        Compute instantaneous forward curve from spot yields.

        Returns list of {from_tenor, to_tenor, forward_rate}
        """
        tau = np.asarray(maturities, dtype=np.float64)
        y   = np.asarray(yields,     dtype=np.float64)

        ts  = np.asarray(tenors or self.STANDARD_TENORS, dtype=np.float64)
        ts  = ts[ts <= tau.max()]

        result = []
        for i in range(len(ts) - 1):
            t1   = ts[i]
            t2   = ts[i + 1]
            y1   = float(np.interp(t1, tau, y))
            y2   = float(np.interp(t2, tau, y))
            fwd  = self.forward_rate(t1, t2, y1, y2)
            result.append({
                'from_tenor':   t1,
                'to_tenor':     t2,
                'forward_rate': round(fwd, 4),
            })

        return result

    # ── Fitted curve ──────────────────────────────────────────────────────────

    def fit_and_predict(
        self,
        maturities: np.ndarray,
        yields:     np.ndarray,
        predict_at: Optional[np.ndarray] = None,
        model:      str = 'ns',
    ) -> Dict:
        """
        Fit NS/NSS model and predict at fine grid.

        Parameters
        ----------
        model : 'ns' for Nelson-Siegel, 'nss' for Svensson extension

        Returns dict with params, fitted_yields, grid_yields
        """
        tau = np.asarray(maturities, dtype=np.float64)
        y   = np.asarray(yields,     dtype=np.float64)
        grid = predict_at if predict_at is not None else np.linspace(tau.min(), tau.max(), 100)

        if model == 'nss':
            params    = self._nss.fit_nss(tau, y)
            fitted    = self._nss.predict_yield_nss(tau, params.beta0, params.beta1,
                                                     params.beta2, params.beta3,
                                                     params.lam1, params.lam2)
            grid_vals = self._nss.predict_yield_nss(grid, params.beta0, params.beta1,
                                                      params.beta2, params.beta3,
                                                      params.lam1, params.lam2)
            params_dict = params.to_dict()
        else:
            params    = self._ns.fit(tau, y)
            fitted    = self._ns.predict(tau, params)
            grid_vals = self._ns.predict(grid, params)
            params_dict = params.to_dict()

        return {
            'model':         model.upper(),
            'params':        params_dict,
            'maturities':    tau.tolist(),
            'observed':      y.tolist(),
            'fitted':        fitted.tolist(),
            'grid_maturities': grid.tolist(),
            'grid_yields':   grid_vals.tolist(),
        }

    def __repr__(self) -> str:
        return 'YieldCurveAnalyzer(models=[NelsonSiegel, NelsonSiegelSvensson])'
