"""
Entropy-Based Market Features
==============================
Information-theory metrics applied to market data.

Metrics
-------
ShannonEntropyRolling   — Rolling window Shannon entropy of returns
TransferEntropy         — Directed information flow A → B (Schreiber 2000)
InformationRatio        — Signal-to-noise: IC × sqrt(breadth)
MarketEntropyAnalyzer   — Unified analyzer returning all metrics

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.entropy")


# ── Rolling Shannon Entropy ────────────────────────────────────────────────────

def rolling_shannon_entropy(
    returns: pd.Series,
    window: int = 20,
    n_bins: int = 8,
) -> pd.Series:
    """
    Rolling Shannon entropy of returns distribution.

    High entropy → unpredictable / noisy market.
    Low entropy  → structured / directional moves.

    Returns pd.Series of entropy values (bits, same index as input).
    """
    def _h(arr: np.ndarray) -> float:
        arr = arr[np.isfinite(arr)]
        if len(arr) < 3:
            return np.nan
        counts, _ = np.histogram(arr, bins=n_bins)
        total = counts.sum()
        if total == 0:
            return np.nan
        p = counts / total
        p = p[p > 0]
        return float(-np.sum(p * np.log2(p)))

    return returns.rolling(window).apply(_h, raw=True)


# ── Transfer Entropy ──────────────────────────────────────────────────────────

def transfer_entropy(
    source: Union[pd.Series, np.ndarray],
    target: Union[pd.Series, np.ndarray],
    lag: int = 1,
    n_bins: int = 5,
) -> float:
    """
    Transfer Entropy from source → target (Schreiber 2000).

    Measures directed information flow. TE(X→Y) > 0 means X carries
    information about future Y beyond Y's own past.

    Parameters
    ----------
    source, target : return series (must be same length)
    lag            : prediction lag (default 1)
    n_bins         : number of bins for discretisation

    Returns scalar TE in bits.
    """
    s = np.asarray(source, dtype=float)
    t = np.asarray(target, dtype=float)

    # Align lengths
    n = min(len(s), len(t))
    s, t = s[:n], t[:n]

    # Remove NaNs
    mask = np.isfinite(s) & np.isfinite(t)
    s, t = s[mask], t[mask]
    n = len(s)
    if n < lag + 5:
        return 0.0

    # Discretise via quantile bins
    def _digitise(x: np.ndarray) -> np.ndarray:
        edges = np.percentile(x, np.linspace(0, 100, n_bins + 1))
        edges = np.unique(edges)
        return np.digitize(x, edges[1:-1])

    s_d   = _digitise(s)
    t_d   = _digitise(t)
    t_fut = t_d[lag:]
    t_now = t_d[:-lag]
    s_now = s_d[:-lag]

    def _p(*arrays: np.ndarray) -> Dict[tuple, float]:
        """Joint probability distribution from co-occurring values."""
        keys = list(zip(*[a for a in arrays]))
        counts: Dict[tuple, int] = {}
        for k in keys:
            counts[k] = counts.get(k, 0) + 1
        total = len(keys)
        return {k: v / total for k, v in counts.items()}

    # p(t_fut, t_now, s_now)
    p_joint   = _p(t_fut, t_now, s_now)
    # p(t_fut, t_now)
    p_tn_tf   = _p(t_fut, t_now)
    # p(t_now, s_now)
    p_tn_sn   = _p(t_now, s_now)
    # p(t_now)
    p_tn      = _p(t_now,)

    te = 0.0
    for (tf, tn, sn), p_all in p_joint.items():
        p_tf_tn  = p_tn_tf.get((tf, tn), 1e-12)
        p_tn_s   = p_tn_sn.get((tn, sn), 1e-12)
        p_t      = p_tn.get((tn,), 1e-12)

        # TE = Σ p(t+1,t,s) * log[ p(t+1|t,s) / p(t+1|t) ]
        # = Σ p * log[ p(t+1,t,s) * p(t) / (p(t+1,t) * p(t,s)) ]
        if p_all > 0 and p_tf_tn > 0 and p_tn_s > 0 and p_t > 0:
            ratio = (p_all * p_t) / (p_tf_tn * p_tn_s)
            if ratio > 0:
                te += p_all * np.log2(ratio)

    return round(float(max(0.0, te)), 5)


# ── Information Ratio Proxy ────────────────────────────────────────────────────

def information_ratio(
    signal: Union[pd.Series, np.ndarray],
    forward_returns: Union[pd.Series, np.ndarray],
) -> float:
    """
    Information Coefficient (IC) = Spearman rank correlation between
    signal and forward returns.  Proxy for Information Ratio.

    Returns IC ∈ [-1, 1]. |IC| > 0.05 is considered meaningful.
    """
    sig = np.asarray(signal, dtype=float)
    fwd = np.asarray(forward_returns, dtype=float)

    n = min(len(sig), len(fwd))
    sig, fwd = sig[:n], fwd[:n]
    mask = np.isfinite(sig) & np.isfinite(fwd)
    sig, fwd = sig[mask], fwd[mask]

    if len(sig) < 5:
        return 0.0

    # Spearman rank correlation
    rank_s = np.argsort(np.argsort(sig)).astype(float)
    rank_f = np.argsort(np.argsort(fwd)).astype(float)
    n_r    = len(rank_s)

    cov = float(np.cov(rank_s, rank_f)[0, 1])
    std = float(np.std(rank_s, ddof=1) * np.std(rank_f, ddof=1))

    ic = cov / (std + 1e-10)
    return round(float(np.clip(ic, -1.0, 1.0)), 4)


# ── Entropy Regime Classification ─────────────────────────────────────────────

def entropy_regime(entropy_value: float, max_bits: float = 3.32) -> str:
    """
    Classify market state from Shannon entropy value.
    max_bits = log2(10) ≈ 3.32 for 10-bin histogram.
    """
    pct = entropy_value / (max_bits + 1e-10)
    if pct < 0.30:
        return "STRUCTURED"     # Very low entropy — directional pattern
    elif pct < 0.55:
        return "MODERATE"       # Some structure remains
    elif pct < 0.75:
        return "NOISY"          # Near-random
    else:
        return "CHAOTIC"        # Maximum entropy — no predictable structure


# ══════════════════════════════════════════════════════════════════════════════
#  MarketEntropyAnalyzer — unified interface
# ══════════════════════════════════════════════════════════════════════════════

class MarketEntropyAnalyzer:
    """
    Compute a full entropy profile for a single asset or an asset pair.

    Usage
    -----
    analyzer = MarketEntropyAnalyzer(window=20)

    # Single asset
    profile = analyzer.analyze(prices_series)

    # Cross-asset information flow
    te = analyzer.transfer_entropy(source_returns, target_returns)
    """

    def __init__(self, window: int = 20, n_bins: int = 8):
        self.window = window
        self.n_bins = n_bins

    def analyze(self, prices: Union[pd.Series, np.ndarray]) -> Dict[str, float]:
        """
        Compute current entropy metrics for a price series.

        Returns
        -------
        dict with:
            current_entropy  : latest rolling Shannon entropy
            entropy_mean     : rolling mean entropy
            entropy_std      : rolling std (entropy volatility)
            entropy_regime   : 'STRUCTURED' | 'MODERATE' | 'NOISY' | 'CHAOTIC'
            entropy_pct      : 0-1 percentile of current entropy (vs window)
            predictability   : 1 - normalised_entropy
        """
        arr = np.asarray(prices, dtype=float)
        if len(arr) < self.window + 2:
            return self._empty()

        series = pd.Series(arr)
        rets   = series.pct_change().dropna()
        ent_s  = rolling_shannon_entropy(rets, window=self.window, n_bins=self.n_bins).dropna()

        if len(ent_s) == 0:
            return self._empty()

        cur_ent = float(ent_s.iloc[-1])
        max_ent = float(np.log2(self.n_bins))   # theoretical maximum
        pct     = round(float(np.clip(cur_ent / (max_ent + 1e-10), 0, 1)), 3)

        return {
            "current_entropy": round(cur_ent, 4),
            "entropy_mean":    round(float(ent_s.mean()), 4),
            "entropy_std":     round(float(ent_s.std()), 4),
            "entropy_regime":  entropy_regime(cur_ent, max_ent),
            "entropy_pct":     pct,
            "predictability":  round(1.0 - pct, 3),
        }

    def transfer_entropy(
        self,
        source: Union[pd.Series, np.ndarray],
        target: Union[pd.Series, np.ndarray],
        lag: int = 1,
    ) -> float:
        """Directed information flow: source → target."""
        return transfer_entropy(source, target, lag=lag, n_bins=self.n_bins)

    @staticmethod
    def _empty() -> Dict[str, float]:
        return {
            "current_entropy": 0.0,
            "entropy_mean":    0.0,
            "entropy_std":     0.0,
            "entropy_regime":  "UNKNOWN",
            "entropy_pct":     0.5,
            "predictability":  0.5,
        }
