"""
Wavelet Analysis for Financial Time Series
==========================================
Reference: quant-traderr-lab Wavelet_Pipeline.py (MIT license)

Continuous Wavelet Transform (CWT) with Morlet wavelet for:
  - Time-frequency localization of volatility regimes
  - Multi-scale market cycle detection
  - Non-stationary signal decomposition
  - Regime change detection

Discrete Wavelet Transform (DWT) for:
  - Multi-resolution denoising
  - Trend vs noise separation
  - ARMA residual extraction

The Morlet wavelet:
  ψ(t) = π^(-1/4) · exp(iω₀t) · exp(-t²/2)
  ω₀ = 6 (default — ~6 oscillations per cycle, good for finance)

Scalogram (CWT power spectrum):
  P(s, t) = |CWT(s, t)|²

Scale → Pseudo-Period:
  T ≈ 4πs / (ω₀ + √(2 + ω₀²))

Applications:
  1. Detect dominant market cycles at each point in time
  2. Identify when cycles are strengthening/weakening
  3. Cross-asset wavelet coherence (lead-lag relationships)
  4. Volatility regime transitions
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import pywt
    _PYWT = True
except ImportError:
    _PYWT = False
    logger.debug('WaveletAnalyzer: pywt not installed. DWT unavailable.')


class WaveletAnalyzer:
    """
    Financial time-series wavelet analysis.

    Supports both CWT (continuous) and DWT (discrete) transforms.
    CWT is implemented in pure numpy (no pywt needed) using the Morlet wavelet.
    DWT requires pywt (pip install PyWavelets).

    Parameters
    ----------
    omega0 : Morlet carrier frequency (default 6.0)
    """

    def __init__(self, omega0: float = 6.0):
        self.omega0 = omega0

    # ── CWT (Morlet) ───────────────────────────────────────────────────────

    def morlet_cwt(
        self,
        signal:     np.ndarray,
        scales:     Optional[np.ndarray] = None,
        dt:         float = 1.0,
        n_scales:   int   = 64,
        scale_min:  float = 2.0,
        scale_max:  float = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute Continuous Wavelet Transform using Morlet wavelet.

        Pure numpy implementation — no pywt needed.

        Parameters
        ----------
        signal    : 1D array (price returns or log-prices)
        scales    : custom scales array; if None, auto-generated
        dt        : time step (1 = daily, 1/252 = annual)
        n_scales  : number of scales if auto-generated
        scale_min : minimum scale (period ~ scale × dt)
        scale_max : maximum scale (default: len/4)

        Returns
        -------
        cwt_power : (n_scales, n_time) power spectrum |CWT|²
        scales    : (n_scales,) scale array
        periods   : (n_scales,) pseudo-periods (in dt units)
        """
        x     = np.asarray(signal, dtype=np.float64)
        N     = len(x)
        x     = x - x.mean()  # remove mean

        if scales is None:
            if scale_max is None:
                scale_max = N / 4
            scales = np.geomspace(scale_min, scale_max, n_scales)

        # Pseudo-periods
        # Morlet: T = 4π·s / (ω₀ + √(2 + ω₀²))
        denom   = self.omega0 + np.sqrt(2.0 + self.omega0 ** 2)
        periods = 4.0 * np.pi * scales / denom * dt

        # CWT via convolution in frequency domain
        N_pad  = 2 ** int(np.ceil(np.log2(N)))  # next power of 2
        x_pad  = np.zeros(N_pad)
        x_pad[:N] = x
        X_freq = np.fft.fft(x_pad)
        freqs  = 2.0 * np.pi * np.fft.fftfreq(N_pad, d=dt)

        cwt_coeff = np.empty((len(scales), N), dtype=complex)

        for i, s in enumerate(scales):
            # Normalized Morlet transfer function in frequency domain
            psi_hat  = (np.pi ** -0.25
                        * np.sqrt(2.0 * np.pi * s / dt)
                        * np.exp(-0.5 * (s * freqs - self.omega0) ** 2)
                        * (freqs > 0).astype(float))
            conv     = np.fft.ifft(X_freq * psi_hat)[:N]
            cwt_coeff[i, :] = conv

        cwt_power = np.abs(cwt_coeff) ** 2
        return cwt_power, scales, periods

    def dominant_cycle(
        self,
        signal:   np.ndarray,
        dt:       float = 1.0,
        n_scales: int   = 64,
    ) -> Dict:
        """
        Find dominant market cycle at each time point.

        Returns dict with:
          periods        : (n_time,) dominant period at each step
          avg_period     : average dominant period
          power_spectrum : (n_scales,) time-averaged power (global spectrum)
          scales         : scale array
          periods_axis   : period labels for each scale
        """
        power, scales, period_axis = self.morlet_cwt(signal, dt=dt, n_scales=n_scales)

        # Dominant period at each time step: argmax of power in scale dim
        dom_scale_idx = np.argmax(power, axis=0)
        dom_periods   = period_axis[dom_scale_idx]

        # Global power spectrum (time average)
        global_power  = power.mean(axis=1)

        # Top-3 dominant cycles (global)
        top3_idx      = np.argsort(global_power)[-3:][::-1]
        top3          = [
            {'period': round(float(period_axis[i]), 2), 'power': round(float(global_power[i]), 4)}
            for i in top3_idx
        ]

        return {
            'dominant_periods':   dom_periods,
            'avg_period':         round(float(dom_periods.mean()), 2),
            'global_power':       global_power,
            'top3_cycles':        top3,
            'scales':             scales,
            'period_axis':        period_axis,
            'cwt_power':          power,
        }

    def regime_changes(
        self,
        signal:     np.ndarray,
        dt:         float = 1.0,
        threshold:  float = 2.0,
    ) -> Dict:
        """
        Detect volatility regime changes using wavelet power.

        A regime change is detected when the total wavelet power (summed
        across scales) exceeds threshold standard deviations above its mean.

        Returns dict with regime_change_idx and power_series.
        """
        power, scales, _ = self.morlet_cwt(signal, dt=dt)
        total_power      = power.sum(axis=0)

        m  = total_power.mean()
        s  = total_power.std()
        z  = (total_power - m) / (s + 1e-9)

        change_idx = np.where(z > threshold)[0]

        return {
            'regime_change_idx': change_idx.tolist(),
            'power_series':      total_power,
            'power_zscore':      z,
            'threshold':         threshold,
            'n_changes':         len(change_idx),
        }

    # ── DWT (Discrete) ─────────────────────────────────────────────────────

    def dwt_decompose(
        self,
        signal:   np.ndarray,
        wavelet:  str = 'db4',
        levels:   int = 4,
    ) -> Dict:
        """
        Discrete Wavelet Transform decomposition (requires pywt).

        Decomposes signal into:
          - Trend (approximation at final level)
          - Detail components at each level (noise, cycles, etc.)
          - Reconstructed denoised signal (trend + coarse details)

        Parameters
        ----------
        signal  : 1D price/return series
        wavelet : wavelet family (default 'db4' = Daubechies 4)
        levels  : decomposition levels (4-6 typical for financial data)

        Returns
        -------
        dict with: trend, details, denoised, coefficients
        """
        if not _PYWT:
            return {
                'error': 'pywt not installed. Run: pip install PyWavelets',
                'fallback_trend': self._simple_trend(signal),
            }

        x      = np.asarray(signal, dtype=np.float64)
        coeffs = pywt.wavedec(x, wavelet, level=levels)

        # Soft thresholding for denoising
        sigma_n   = float(np.median(np.abs(coeffs[-1])) / 0.6745)
        threshold = sigma_n * np.sqrt(2 * np.log(len(x)))

        denoised_coeffs = [coeffs[0]]  # keep approximation
        for c in coeffs[1:]:
            denoised_coeffs.append(pywt.threshold(c, threshold, mode='soft'))

        trend    = pywt.waverec([coeffs[0]] + [np.zeros_like(c) for c in coeffs[1:]], wavelet)
        denoised = pywt.waverec(denoised_coeffs, wavelet)

        # Trim to original length (waverec may add 1 sample)
        trend    = trend[:len(x)]
        denoised = denoised[:len(x)]

        details = {
            f'level_{i+1}_detail': coeffs[i + 1]
            for i in range(len(coeffs) - 1)
        }

        return {
            'trend':        trend,
            'denoised':     denoised,
            'noise':        x - denoised,
            'details':      details,
            'levels':       levels,
            'wavelet':      wavelet,
            'sigma_noise':  round(sigma_n, 6),
            'threshold':    round(threshold, 6),
        }

    def _simple_trend(self, signal: np.ndarray, window: int = 20) -> np.ndarray:
        """Simple moving average trend (fallback when pywt unavailable)."""
        x   = np.asarray(signal, dtype=np.float64)
        pad = np.pad(x, window // 2, mode='edge')
        return np.convolve(pad, np.ones(window) / window, mode='valid')[:len(x)]

    # ── Cross-Asset Coherence ───────────────────────────────────────────────

    def wavelet_coherence(
        self,
        x:        np.ndarray,
        y:        np.ndarray,
        dt:       float = 1.0,
        n_scales: int   = 32,
    ) -> Dict:
        """
        Compute wavelet coherence between two signals.

        Coherence R²(s,t) = |<Wxy>|² / (|<Wxx>|·|<Wyy>|)
        where <> denotes smoothing in scale and time.

        High coherence means x and y are strongly co-moving at that
        scale/period, even if raw correlation is low.

        Returns dict with coherence_matrix, mean_coherence, dominant_period.
        """
        Px, scales, periods = self.morlet_cwt(x, dt=dt, n_scales=n_scales)
        Py, _, _            = self.morlet_cwt(y, dt=dt, n_scales=n_scales, scales=scales)

        # Cross-wavelet: Wxy = Wx * conj(Wy)
        # Approximate coherence via smoothed power ratio
        smooth = lambda M: np.apply_along_axis(
            lambda row: np.convolve(row, np.ones(5)/5, mode='same'), axis=1, arr=M
        )

        Px_s  = smooth(Px) + 1e-15
        Py_s  = smooth(Py) + 1e-15
        Pxy_s = smooth(np.sqrt(Px * Py))

        coherence = Pxy_s ** 2 / (Px_s * Py_s)
        coherence = np.clip(coherence, 0, 1)

        mean_coh  = float(coherence.mean())
        dom_idx   = int(np.argmax(coherence.mean(axis=1)))

        return {
            'coherence_matrix':  coherence,
            'mean_coherence':    round(mean_coh, 4),
            'dominant_period':   round(float(periods[dom_idx]), 2),
            'scales':            scales,
            'periods':           periods,
        }

    def __repr__(self) -> str:
        return f'WaveletAnalyzer(ω₀={self.omega0})'
