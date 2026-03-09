"""
Fisher Transform & Information-Theoretic Indicators.

Implements:
  · FisherTransform   — Gaussian normalization of price data + signal line
  · InformationRatio  — Rolling information ratio (active return / tracking error)
  · ShannonEntropy    — Rolling price return entropy (market uncertainty)

Mathematical basis (quant-traderr-lab reference):
  Fisher transform:  y = 0.5 × ln((1+x)/(1-x))     where x ∈ (-1, 1)
  Inverse:           x = (e^2y - 1)/(e^2y + 1)
  Signal:            EMA(fisher, signal_period)

The Fisher Transform converts any oscillator to a near-Gaussian distribution,
making extreme values (±2.0) more statistically meaningful for mean-reversion entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


# ── Fisher Transform ───────────────────────────────────────────────────────────

@dataclass
class FisherResult:
    """Output of FisherTransform.compute()."""
    fisher:       np.ndarray        # Fisher Transform values
    signal:       np.ndarray        # EMA signal line
    raw:          np.ndarray        # normalized price [-1, 1]
    extremes:     List[int]         # indices where |fisher| > threshold
    n:            int
    window:       int
    signal_period: int

    def to_dict(self) -> Dict:
        return {
            'fisher':        self.fisher.tolist(),
            'signal':        self.signal.tolist(),
            'raw':           self.raw.tolist(),
            'extremes':      self.extremes,
            'n':             self.n,
            'window':        self.window,
            'signal_period': self.signal_period,
        }


class FisherTransform:
    """
    Fisher Transform Oscillator.

    Parameters
    ----------
    window         : lookback period for price normalization (default 14)
    signal_period  : EMA period for signal line (default 9)
    clip_eps       : epsilon to avoid ln(0) at boundaries (default 0.001)
    extreme_thresh : |fisher| threshold for extreme signal detection (default 2.0)
    """

    def __init__(
        self,
        window:        int   = 14,
        signal_period: int   = 9,
        clip_eps:      float = 0.001,
        extreme_thresh: float = 2.0,
    ):
        self.window         = window
        self.signal_period  = signal_period
        self.clip_eps       = clip_eps
        self.extreme_thresh = extreme_thresh

    # ── Core computation ──────────────────────────────────────────────────────

    def compute(
        self,
        high:  np.ndarray,
        low:   np.ndarray,
        close: Optional[np.ndarray] = None,
    ) -> FisherResult:
        """
        Compute the Fisher Transform.

        Parameters
        ----------
        high  : high prices (or use prices for both high and low)
        low   : low prices
        close : not used (kept for API consistency)

        Returns
        -------
        FisherResult
        """
        H = np.asarray(high,  dtype=np.float64)
        L = np.asarray(low,   dtype=np.float64)
        n = len(H)

        # Step 1: Normalize HL/2 to [-1, 1] within rolling window
        mid   = (H + L) / 2.0
        raw   = np.full(n, 0.0)

        for i in range(self.window - 1, n):
            w_high = H[i - self.window + 1 : i + 1].max()
            w_low  = L[i - self.window + 1 : i + 1].min()
            rang   = w_high - w_low
            if rang < 1e-12:
                raw[i] = 0.0
            else:
                raw[i] = 2.0 * (mid[i] - w_low) / rang - 1.0

        # Clip to avoid atanh singularity
        eps    = self.clip_eps
        x      = np.clip(raw, -1.0 + eps, 1.0 - eps)

        # Step 2: Fisher Transform  y = 0.5 × ln((1+x)/(1-x))  =  atanh(x)
        fisher = np.arctanh(x)  # equivalent to 0.5 * ln((1+x)/(1-x))

        # Step 3: EMA signal line
        signal = self._ema(fisher, self.signal_period)

        # Step 4: Flag extremes
        extremes = [
            i for i in range(n)
            if abs(fisher[i]) >= self.extreme_thresh
        ]

        return FisherResult(
            fisher=fisher,
            signal=signal,
            raw=raw,
            extremes=extremes,
            n=n,
            window=self.window,
            signal_period=self.signal_period,
        )

    def compute_from_prices(self, prices: np.ndarray) -> FisherResult:
        """Convenience: compute Fisher from a single price series (uses prices as both H and L for synthetic HL)."""
        p  = np.asarray(prices, dtype=np.float64)
        # Create synthetic high/low: ±0.5% of price as proxy
        h  = p * 1.005
        l  = p * 0.995
        return self.compute(h, l)

    # ── Signal extraction ─────────────────────────────────────────────────────

    def signal_at(
        self,
        result: FisherResult,
        i:      int = -1,
    ) -> Dict:
        """
        Interpret Fisher signal at index i (default: last).

        Returns dict with: value, signal, crossover, direction, strength
        """
        fisher = result.fisher
        sig    = result.signal
        idx    = i if i >= 0 else len(fisher) + i

        val  = fisher[idx]
        sval = sig[idx]

        # Crossover detection (current vs previous)
        if idx > 0:
            prev_diff = fisher[idx - 1] - sig[idx - 1]
            curr_diff = val - sval
            crossover = (prev_diff * curr_diff < 0)  # sign change
            direction = 'BUY' if curr_diff > 0 and prev_diff <= 0 else \
                        'SELL' if curr_diff < 0 and prev_diff >= 0 else 'HOLD'
        else:
            crossover = False
            direction = 'HOLD'

        return {
            'value':     round(float(val), 4),
            'signal':    round(float(sval), 4),
            'crossover': crossover,
            'direction': direction,
            'extreme':   abs(val) >= self.extreme_thresh,
            'overbought': val >= self.extreme_thresh,
            'oversold':   val <= -self.extreme_thresh,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _ema(x: np.ndarray, period: int) -> np.ndarray:
        """Exponential moving average."""
        k   = 2.0 / (period + 1)
        out = np.copy(x)
        for i in range(1, len(x)):
            out[i] = x[i] * k + out[i - 1] * (1 - k)
        return out

    @staticmethod
    def inverse(y: np.ndarray) -> np.ndarray:
        """Inverse Fisher Transform: maps y → x ∈ (-1, 1)."""
        e2y = np.exp(2.0 * np.asarray(y, dtype=np.float64))
        return (e2y - 1.0) / (e2y + 1.0)

    def __repr__(self) -> str:
        return (
            f'FisherTransform(window={self.window}, '
            f'signal={self.signal_period}, thresh={self.extreme_thresh})'
        )


# ── Shannon Entropy ────────────────────────────────────────────────────────────

class ShannonEntropy:
    """
    Rolling Shannon entropy of price returns.

    High entropy → random/unpredictable market (low edge)
    Low entropy  → structured/trending market (higher edge)

    H(X) = -Σ p_i × log₂(p_i)  over discretized return bins
    """

    def __init__(self, window: int = 60, n_bins: int = 10):
        self.window = window
        self.n_bins = n_bins

    def compute(self, returns: np.ndarray) -> Dict:
        """
        Compute rolling Shannon entropy.

        Returns
        -------
        dict: entropy (array), max_entropy, normalized (array), regime_changes
        """
        r   = np.asarray(returns, dtype=np.float64)
        N   = len(r)
        H   = np.full(N, np.nan)

        for i in range(self.window, N):
            w    = r[i - self.window : i]
            hist, _ = np.histogram(w, bins=self.n_bins)
            p    = hist / hist.sum()
            p    = p[p > 0]
            H[i] = -float(np.sum(p * np.log2(p)))

        max_H   = np.log2(self.n_bins)   # max entropy for n_bins
        H_norm  = H / (max_H + 1e-9)

        # Regime changes: entropy drops
        regime_changes = []
        threshold = 0.1  # 10% entropy drop
        for i in range(1, N):
            if not np.isnan(H_norm[i]) and not np.isnan(H_norm[i - 1]):
                if H_norm[i - 1] - H_norm[i] > threshold:
                    regime_changes.append(i)

        return {
            'entropy':          H.tolist(),
            'entropy_norm':     H_norm.tolist(),
            'max_entropy':      round(max_H, 4),
            'regime_changes':   regime_changes,
            'current_entropy':  round(float(H[~np.isnan(H)][-1]) if not np.all(np.isnan(H)) else 0.0, 4),
            'current_norm':     round(float(H_norm[~np.isnan(H_norm)][-1]) if not np.all(np.isnan(H_norm)) else 0.0, 4),
        }

    def __repr__(self) -> str:
        return f'ShannonEntropy(window={self.window}, bins={self.n_bins})'
