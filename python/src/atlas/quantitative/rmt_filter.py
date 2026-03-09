"""
Random Matrix Theory (RMT) Correlation Filter
==============================================
Reference: quant-traderr-lab RMT_Pipeline.py (MIT license)
           Marchenko & Pastur (1967), Bouchaud & Potters (2000)

Uses the Marchenko-Pastur distribution to distinguish signal eigenvalues
from noise eigenvalues in a financial correlation matrix.

Noise eigenvalues: λ ∈ [λ_min, λ_max] of the MP distribution
Signal eigenvalues: λ > λ_max (carry genuine cross-asset information)

MP bounds:
  λ_min = σ²(1 - √(N/T))²
  λ_max = σ²(1 + √(N/T))²
  q = T/N (ratio of observations to assets; need q > 1)

Filtered correlation matrix:
  Rebuild Σ using only signal eigenvectors, redistribute noise variance to
  diagonal to preserve unit-variance structure.

Applications:
  - Cleaner portfolio optimization (Markowitz / Black-Litterman)
  - Better minimum-variance portfolios
  - Pairs trading correlation structure
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MarchenkoPastur:
    """
    Marchenko-Pastur (MP) distribution for noise level estimation.

    Parameters
    ----------
    q     : ratio T/N (obs / assets), must be > 1 for valid MP
    sigma : variance of the noise (usually estimated as 1 for standardized returns)
    """

    def __init__(self, q: float, sigma: float = 1.0):
        if q <= 1:
            logger.warning(
                f'MarchenkoPastur: q={q:.2f} ≤ 1. MP distribution ill-defined. '
                'Need more time observations than assets (T > N).'
            )
        self.q     = q
        self.sigma = sigma

    @property
    def lambda_min(self) -> float:
        """Lower edge of the MP noise bulk."""
        return self.sigma ** 2 * (1.0 - np.sqrt(1.0 / self.q)) ** 2

    @property
    def lambda_max(self) -> float:
        """Upper edge of the MP noise bulk — eigenvalues above this are signal."""
        return self.sigma ** 2 * (1.0 + np.sqrt(1.0 / self.q)) ** 2

    def pdf(self, lam: np.ndarray) -> np.ndarray:
        """
        Marchenko-Pastur probability density function.

        f(λ) = (q/(2πσ²)) · √[(λ_max - λ)(λ - λ_min)] / λ
        """
        lam    = np.asarray(lam, dtype=np.float64)
        l_min  = self.lambda_min
        l_max  = self.lambda_max
        sigma2 = self.sigma ** 2

        term   = np.maximum((l_max - lam) * (lam - l_min), 0.0)
        pdf    = self.q / (2 * np.pi * sigma2) * np.sqrt(term) / (lam + 1e-15)
        pdf    = np.where((lam >= l_min) & (lam <= l_max), pdf, 0.0)
        return pdf

    def fit_sigma(self, eigenvalues: np.ndarray, n_iter: int = 50) -> float:
        """
        Estimate σ² from data eigenvalues by matching MP distribution.
        Uses moment matching: E[λ] under MP = σ².

        Simple estimator: σ² ≈ median eigenvalue (robust to outliers).
        """
        eigs = np.asarray(eigenvalues, dtype=np.float64)
        # Trim obvious outliers (top 10%)
        threshold = np.percentile(eigs, 90)
        noise_eigs = eigs[eigs <= threshold]
        self.sigma = float(np.sqrt(np.mean(noise_eigs)))
        return self.sigma ** 2

    def __repr__(self) -> str:
        return (
            f'MarchenkoPastur(q={self.q:.2f}, σ={self.sigma:.4f}, '
            f'λ_noise=[{self.lambda_min:.4f}, {self.lambda_max:.4f}])'
        )


class RMTFilter:
    """
    Random Matrix Theory correlation filter.

    Removes noise from an empirical correlation/covariance matrix by
    retaining only eigenvalues above the Marchenko-Pastur upper edge.

    Usage
    -----
    flt = RMTFilter(n_assets=50, n_obs=252)
    C_clean = flt.filter(returns_matrix)
    filtered_corr = flt.filtered_correlation
    n_factors = flt.n_signal_factors
    """

    def __init__(
        self,
        n_assets:  int,
        n_obs:     int,
        alpha:     float = 1.0,   # MP scaling (1.0 = standard)
        shrink:    bool  = True,  # Apply Ledoit-Wolf after RMT
    ):
        self.n_assets = n_assets
        self.n_obs    = n_obs
        self.q        = n_obs / n_assets
        self.alpha    = alpha
        self.shrink   = shrink

        self.mp = MarchenkoPastur(q=self.q)

        # Results (populated after filter())
        self.filtered_correlation: Optional[np.ndarray] = None
        self.eigenvalues:          Optional[np.ndarray] = None
        self.n_signal_factors:     int = 0
        self.noise_explained_var:  float = 0.0

    def filter(
        self,
        data: np.ndarray,
        is_returns: bool = True,
    ) -> np.ndarray:
        """
        Filter correlation matrix using RMT.

        Parameters
        ----------
        data       : (T, N) returns or correlation matrix
        is_returns : True if data is a returns matrix; False if already correlation

        Returns
        -------
        C_filtered : (N, N) cleaned correlation matrix
        """
        if is_returns:
            # Standardize returns
            X = np.asarray(data, dtype=np.float64)
            mu = X.mean(axis=0)
            sd = X.std(axis=0) + 1e-9
            Xz = (X - mu) / sd
            C  = Xz.T @ Xz / X.shape[0]  # (N, N) correlation matrix
        else:
            C = np.asarray(data, dtype=np.float64)

        N = C.shape[0]

        # Spectral decomposition
        eigenvalues, eigenvectors = np.linalg.eigh(C)
        eigenvalues = eigenvalues[::-1]     # descending
        eigenvectors = eigenvectors[:, ::-1]

        self.eigenvalues = eigenvalues

        # Fit σ from data
        self.mp.fit_sigma(eigenvalues)
        lam_max = self.mp.lambda_max * self.alpha

        # Identify signal vs noise
        signal_mask = eigenvalues > lam_max
        n_signal    = int(signal_mask.sum())
        self.n_signal_factors = max(n_signal, 1)

        noise_var  = eigenvalues[~signal_mask].mean() if (~signal_mask).any() else 0.0
        total_var  = eigenvalues.sum()
        self.noise_explained_var = float(eigenvalues[~signal_mask].sum() / (total_var + 1e-9))

        logger.info(
            f'RMTFilter: {N} assets, q={self.q:.2f}, '
            f'MP λ_max={lam_max:.4f}, '
            f'signal factors={self.n_signal_factors}/{N} '
            f'({(1 - self.noise_explained_var)*100:.1f}% signal)'
        )

        # Reconstruct: keep signal eigenvalues, replace noise with avg noise
        eigenvalues_filtered = eigenvalues.copy()
        eigenvalues_filtered[~signal_mask] = noise_var  # flatten noise

        # Rebuild correlation matrix
        V  = eigenvectors
        D  = np.diag(eigenvalues_filtered)
        C_reconstructed = V @ D @ V.T

        # Ensure unit diagonal (restore correlation structure)
        d = np.sqrt(np.diag(C_reconstructed))
        d = np.where(d > 0, d, 1.0)
        C_filtered = C_reconstructed / np.outer(d, d)

        # Clip to [-1, 1] for numerical safety
        np.fill_diagonal(C_filtered, 1.0)
        C_filtered = np.clip(C_filtered, -1.0, 1.0)

        # Optional Ledoit-Wolf shrinkage on top of RMT
        if self.shrink:
            C_filtered = self._ledoit_wolf_blend(C, C_filtered, alpha=0.2)

        self.filtered_correlation = C_filtered
        return C_filtered

    @staticmethod
    def _ledoit_wolf_blend(
        C_raw:      np.ndarray,
        C_rmt:      np.ndarray,
        alpha:      float = 0.2,
    ) -> np.ndarray:
        """
        Blend RMT-filtered matrix with identity shrinkage target.
        C_final = (1-α)·C_rmt + α·I
        """
        N = C_rmt.shape[0]
        return (1.0 - alpha) * C_rmt + alpha * np.eye(N)

    def diagnostics(self) -> Dict:
        """Return filtering diagnostics."""
        if self.eigenvalues is None:
            return {}

        return {
            'q_ratio':             round(self.q, 4),
            'mp_lambda_max':       round(float(self.mp.lambda_max), 4),
            'mp_sigma':            round(float(self.mp.sigma), 4),
            'n_assets':            self.n_assets,
            'n_obs':               self.n_obs,
            'n_signal_factors':    self.n_signal_factors,
            'noise_explained_var': round(self.noise_explained_var, 4),
            'top_5_eigenvalues':   [round(float(e), 4) for e in self.eigenvalues[:5]],
        }

    def __repr__(self) -> str:
        return (
            f'RMTFilter(N={self.n_assets}, T={self.n_obs}, q={self.q:.2f}, '
            f'signal={self.n_signal_factors})'
        )
