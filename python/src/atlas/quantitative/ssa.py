"""
Singular Spectrum Analysis (SSA).

SSA is a non-parametric technique for time series decomposition:
  1. Embedding  : form trajectory matrix X (N-L+1 × L Hankel matrix)
  2. SVD        : X = UΣVᵀ (singular values λ₁ ≥ λ₂ ≥ ... ≥ λᵣ)
  3. Grouping   : split components into trend, oscillation, noise
  4. Diagonal averaging (anti-diagonal mean) → reconstructed components

Applications (from quant-traderr-lab):
  · Trend extraction from noisy financial time series
  · Cycle detection (periodicity via SVD pairs)
  · Denoising (keep first K eigentriples)
  · Forecasting via recurrent SSA (rSSA)
  · Regime change detection via variance of components

References:
  Golyandina, Nekrutkin, Zhigljavsky (2001) — Analysis of Time Series Structure
  Hassani (2007) — Singular Spectrum Analysis: Methodology and Comparison
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


# ── Result types ───────────────────────────────────────────────────────────────

@dataclass
class SSAResult:
    """Output of SSAnalyzer.decompose()."""
    original:      np.ndarray           # original time series
    components:    List[np.ndarray]     # reconstructed components (1 per eigentriple)
    eigenvalues:   np.ndarray           # singular values squared
    explained_var: np.ndarray           # fraction of variance per component
    window:        int                  # L (window/embedding dimension)
    n:             int                  # series length N

    @property
    def trend(self) -> np.ndarray:
        """First component (usually trend)."""
        return self.components[0] if self.components else self.original

    @property
    def noise(self) -> np.ndarray:
        """Sum of all but first component (approximation)."""
        if len(self.components) < 2:
            return np.zeros_like(self.original)
        return sum(self.components[1:])

    def reconstruct(self, n_components: int = None) -> np.ndarray:
        """Sum first n_components reconstructed signals."""
        k = n_components or len(self.components)
        k = min(k, len(self.components))
        if k == 0:
            return np.zeros(self.n)
        return sum(self.components[:k])

    def to_dict(self) -> Dict:
        return {
            'n':            self.n,
            'window':       self.window,
            'eigenvalues':  self.eigenvalues.tolist(),
            'explained_var': self.explained_var.tolist(),
            'n_components': len(self.components),
            'trend':        self.trend.tolist(),
        }


# ── SSA core ──────────────────────────────────────────────────────────────────

class SSAnalyzer:
    """
    Singular Spectrum Analysis engine.

    Parameters
    ----------
    window     : embedding dimension L (default = N//2, but ≤ N//2 for symmetry)
    n_components : number of eigentriples to reconstruct (None = all)
    """

    def __init__(
        self,
        window:       Optional[int] = None,
        n_components: Optional[int] = None,
    ):
        self.window       = window
        self.n_components = n_components

    # ── Step 1: Embedding ─────────────────────────────────────────────────────

    @staticmethod
    def embed(x: np.ndarray, L: int) -> np.ndarray:
        """
        Form trajectory (Hankel) matrix.

        Parameters
        ----------
        x : 1-D array of length N
        L : window (embedding dimension)

        Returns
        -------
        X : (L × K) trajectory matrix  where K = N - L + 1
        """
        N = len(x)
        K = N - L + 1
        if K < 1:
            raise ValueError(f'Window L={L} too large for series length N={N}. Need L ≤ N.')

        X = np.zeros((L, K))
        for i in range(L):
            X[i] = x[i: i + K]
        return X

    # ── Step 2: SVD ───────────────────────────────────────────────────────────

    @staticmethod
    def _svd(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Economy SVD of trajectory matrix X.

        Returns U, s (singular values), Vt
        """
        U, s, Vt = np.linalg.svd(X, full_matrices=False)
        return U, s, Vt

    # ── Step 3: Diagonal averaging (Hankelization) ────────────────────────────

    @staticmethod
    def _diagonal_avg(M: np.ndarray) -> np.ndarray:
        """
        Anti-diagonal averaging (Hankelization) of matrix M (L × K).

        Reconstructs a 1-D time series of length N = L + K - 1 from a matrix
        by averaging along anti-diagonals.
        """
        L, K = M.shape
        N    = L + K - 1
        out  = np.zeros(N)
        cnt  = np.zeros(N)

        for i in range(L):
            for j in range(K):
                out[i + j] += M[i, j]
                cnt[i + j] += 1.0

        return out / (cnt + 1e-12)

    # ── Main decomposition ────────────────────────────────────────────────────

    def decompose(self, x: np.ndarray) -> SSAResult:
        """
        Full SSA decomposition.

        Parameters
        ----------
        x : time series (1-D array)

        Returns
        -------
        SSAResult with individual reconstructed components
        """
        x = np.asarray(x, dtype=np.float64)
        N = len(x)

        # Determine window L
        L = self.window or max(2, N // 2)
        L = min(L, N - 1)

        # Step 1: Embed
        X = self.embed(x, L)

        # Step 2: SVD
        U, s, Vt = self._svd(X)

        # Eigenvalues λ_i = s_i²
        eigenvalues  = s ** 2
        total_var    = eigenvalues.sum() + 1e-12
        explained    = eigenvalues / total_var

        # Step 3 & 4: Reconstruct each eigentriple as separate component
        r = min(
            len(s),
            self.n_components or len(s),
        )

        components: List[np.ndarray] = []
        for i in range(r):
            # Rank-1 outer product contribution: s_i × u_i × v_i
            Xi = s[i] * np.outer(U[:, i], Vt[i, :])
            rc = self._diagonal_avg(Xi)
            components.append(rc)

        return SSAResult(
            original=x,
            components=components,
            eigenvalues=eigenvalues[:r],
            explained_var=explained[:r],
            window=L,
            n=N,
        )

    # ── Denoising ────────────────────────────────────────────────────────────

    def denoise(
        self,
        x:           np.ndarray,
        n_signal:    Optional[int] = None,
        threshold:   Optional[float] = None,
    ) -> np.ndarray:
        """
        Denoise a time series by keeping the top-K SSA components.

        Parameters
        ----------
        x          : input series
        n_signal   : keep first N signal components (overrides threshold)
        threshold  : cumulative explained variance threshold (e.g. 0.90)

        Returns
        -------
        Denoised series (same length as x)
        """
        result = self.decompose(x)

        if n_signal is not None:
            k = min(n_signal, len(result.components))
        elif threshold is not None:
            cumvar = np.cumsum(result.explained_var)
            k      = int(np.searchsorted(cumvar, threshold)) + 1
            k      = max(1, min(k, len(result.components)))
        else:
            # Default: keep components explaining 90% variance
            cumvar = np.cumsum(result.explained_var)
            k      = int(np.searchsorted(cumvar, 0.90)) + 1
            k      = max(1, min(k, len(result.components)))

        return result.reconstruct(k)

    # ── Trend extraction ─────────────────────────────────────────────────────

    def extract_trend(self, x: np.ndarray) -> np.ndarray:
        """Extract trend (first SSA component)."""
        return self.decompose(x).trend

    # ── Cycle detection ──────────────────────────────────────────────────────

    def find_cycles(self, x: np.ndarray, top_k: int = 5) -> List[Dict]:
        """
        Identify dominant periodic components via SSA.

        Pairs of adjacent components (i, i+1) with similar eigenvalues
        often represent oscillatory (cyclic) components.

        Returns list of dicts: {component_pair, eigenvalue, explained_pct, period_estimate}
        """
        result = self.decompose(x)
        cycles = []

        components = result.components
        evals      = result.eigenvalues
        explained  = result.explained_var

        for i in range(0, min(len(components) - 1, top_k * 2), 2):
            c  = components[i]
            # Autocorrelation-based period estimate
            if len(c) < 4:
                continue
            ac  = np.correlate(c - c.mean(), c - c.mean(), mode='full')
            ac  = ac[len(ac) // 2 :]
            ac  = ac / (ac[0] + 1e-12)
            # Find first positive peak after lag 0
            peaks = []
            for j in range(1, len(ac) - 1):
                if ac[j] > ac[j - 1] and ac[j] > ac[j + 1] and ac[j] > 0.1:
                    peaks.append(j)
            period = float(peaks[0]) if peaks else float('nan')

            # Eigenvalue ratio of adjacent pair (close ratio → oscillatory)
            ratio = float(evals[i] / (evals[i + 1] + 1e-12)) if i + 1 < len(evals) else float('nan')

            cycles.append({
                'component':    i,
                'eigenvalue':   round(float(evals[i]), 4),
                'explained_pct': round(float(explained[i] * 100), 2),
                'period_estimate': round(period, 1) if not np.isnan(period) else None,
                'eigenvalue_ratio': round(ratio, 3),
                'is_oscillatory': 0.5 < ratio < 2.0,
            })

        return cycles[:top_k]

    # ── Forecasting (recurrent SSA) ───────────────────────────────────────────

    def forecast(
        self,
        x:          np.ndarray,
        steps:      int = 10,
        n_signal:   int = 5,
    ) -> np.ndarray:
        """
        Recurrent SSA forecast (rSSA).

        Uses the linear recurrence relation implied by the leading eigenvectors
        to extrapolate n `steps` ahead.

        Parameters
        ----------
        x        : time series
        steps    : forecast horizon
        n_signal : number of SSA components to use

        Returns
        -------
        forecast : array of length `steps`
        """
        x  = np.asarray(x, dtype=np.float64)
        N  = len(x)
        L  = self.window or max(2, N // 2)
        L  = min(L, N - 1)
        K  = N - L + 1

        X  = self.embed(x, L)
        U, s, Vt = self._svd(X)
        r  = min(n_signal, len(s))

        # Last column of trajectory matrix (most recent L-window)
        U_r  = U[:, :r]                # L × r
        pi   = U_r[-1, :]              # last row of U_r (L-th component)
        nu2  = float(np.dot(pi, pi))   # nu² = |π|²

        if nu2 >= 1.0:
            # Degenerate case: fall back to last value repeat
            return np.full(steps, x[-1])

        # Linear recurrence coefficients
        P   = U_r[:-1, :]             # (L-1) × r
        coef = P @ pi / (1.0 - nu2)  # length L-1

        # Extrapolate: reconstruct signal then apply recurrence
        signal = self.denoise(x, n_signal=n_signal)
        buf    = list(signal[-L + 1:])

        fcast = np.zeros(steps)
        for i in range(steps):
            next_val  = float(np.dot(coef, buf))
            fcast[i]  = next_val
            buf.append(next_val)
            buf.pop(0)

        return fcast

    # ── Variance / regime monitor ─────────────────────────────────────────────

    def rolling_variance_ratio(
        self,
        x:      np.ndarray,
        window: int = 60,
        k:      int = 2,
    ) -> np.ndarray:
        """
        Rolling ratio: variance of top-K SSA components / total variance.

        High ratio → structured (low noise), Low ratio → noisy (high entropy).
        Sudden drops signal regime changes.
        """
        x   = np.asarray(x, dtype=np.float64)
        N   = len(x)
        out = np.full(N, np.nan)

        for i in range(window, N):
            seg    = x[i - window : i]
            result = self.decompose(seg)
            top_k  = result.explained_var[:k].sum()
            out[i] = float(top_k)

        return out

    def __repr__(self) -> str:
        return (
            f'SSAnalyzer(window={self.window}, '
            f'n_components={self.n_components})'
        )
