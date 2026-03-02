"""
Chaos & Nonlinear Market Features  —  Fase 3.5
===============================================
Quantifies market complexity, persistence, and fractal structure using
information theory and dynamical-systems tools.

Metrics
-------
hurst_exponent      H ∈ (0,1): >0.5 trending, <0.5 mean-reverting, 0.5 random
dfa_exponent        DFA α: long-range correlation exponent (similar to Hurst)
fractal_dimension   Higuchi FD ∈ [1,2]: 1=smooth trend, 2=chaotic noise
lyapunov_proxy      Rate of trajectory divergence (positive → unstable/chaotic)
shannon_entropy     Information entropy of return distribution (bits)
approx_entropy      Template-matching regularity: low = predictable
permutation_entropy Ordinal-pattern entropy in [0,1]: 0 = perfectly ordered

All pure-numpy — no scipy required.

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.chaos")


# ── Hurst Exponent (R/S Analysis) ─────────────────────────────────────────────

def hurst_exponent(prices: Union[pd.Series, np.ndarray], max_lag: int = 20) -> float:
    """
    Rescaled Range (R/S) Hurst exponent.

    Returns
    -------
    H ∈ [0.01, 0.99]
      H > 0.55 → persistent / trending
      H < 0.45 → anti-persistent / mean-reverting
      H ≈ 0.50 → random walk (efficient market)
    """
    ts = np.asarray(prices, dtype=float)
    n  = len(ts)
    if n < max_lag * 2:
        return 0.5

    lags = range(2, min(max_lag, n // 2))
    rs_vals: List[float] = []

    for lag in lags:
        n_blocks = n // lag
        if n_blocks < 2:
            continue
        block_rs: List[float] = []
        for b in range(n_blocks):
            blk = ts[b * lag:(b + 1) * lag]
            m   = blk.mean()
            dev = np.cumsum(blk - m)
            R   = dev.max() - dev.min()
            S   = blk.std(ddof=1)
            if S > 0:
                block_rs.append(R / S)
        if block_rs:
            rs_vals.append(float(np.mean(block_rs)))

    if len(rs_vals) < 2:
        return 0.5

    log_lags = np.log(np.arange(2, 2 + len(rs_vals), dtype=float))
    log_rs   = np.log(np.array(rs_vals, dtype=float))
    H        = float(np.polyfit(log_lags, log_rs, 1)[0])
    return round(float(np.clip(H, 0.01, 0.99)), 4)


# ── Detrended Fluctuation Analysis ────────────────────────────────────────────

def dfa_exponent(prices: Union[pd.Series, np.ndarray],
                 scales: Optional[List[int]] = None) -> float:
    """
    DFA scaling exponent α.  Interpretation same as Hurst.

    Returns α ∈ [0.01, 1.50].
    """
    ts = np.asarray(prices, dtype=float)
    n  = len(ts)
    if n < 20:
        return 0.5

    integrated = np.cumsum(ts - ts.mean())

    if scales is None:
        scales = [max(4, int(n * r)) for r in [0.05, 0.10, 0.20, 0.30, 0.40]]

    flucts: List[float] = []
    valid:  List[int]   = []

    for s in sorted(set(scales)):
        if s < 4 or s > n // 2:
            continue
        n_blk = n // s
        F2: List[float] = []
        for b in range(n_blk):
            blk = integrated[b * s:(b + 1) * s]
            x   = np.arange(len(blk), dtype=float)
            c   = np.polyfit(x, blk, 1)
            res = blk - np.polyval(c, x)
            F2.append(float(np.mean(res ** 2)))
        if F2:
            flucts.append(float(np.sqrt(np.mean(F2))))
            valid.append(s)

    if len(valid) < 2:
        return 0.5

    alpha = float(np.polyfit(np.log(valid), np.log(flucts), 1)[0])
    return round(float(np.clip(alpha, 0.01, 1.50)), 4)


# ── Higuchi Fractal Dimension ──────────────────────────────────────────────────

def fractal_dimension(prices: Union[pd.Series, np.ndarray], kmax: int = 8) -> float:
    """
    Higuchi Fractal Dimension D ∈ [1.0, 2.0].
      D ≈ 1.0 → smooth trend
      D ≈ 1.5 → Brownian motion
      D ≈ 2.0 → chaotic / maximally rough
    """
    ts = np.asarray(prices, dtype=float)
    n  = len(ts)
    if n < kmax * 2:
        return 1.5

    Lk: List[float] = []
    for k in range(1, kmax + 1):
        Lm: List[float] = []
        for m in range(1, k + 1):
            idx = np.arange(m - 1, n, k)
            if len(idx) < 2:
                continue
            N_mk   = (n - m) // k
            length = np.sum(np.abs(np.diff(ts[idx])))
            if N_mk > 0 and k > 0:
                Lmk = length * (n - 1) / (N_mk * k)
                Lm.append(Lmk)
        if Lm:
            Lk.append(float(np.mean(Lm)))

    if len(Lk) < 2:
        return 1.5

    log_k = np.log(np.arange(1, len(Lk) + 1, dtype=float))
    log_L = np.log(np.array(Lk, dtype=float))
    D = -float(np.polyfit(log_k, log_L, 1)[0])
    return round(float(np.clip(D, 1.0, 2.0)), 4)


# ── Shannon Entropy ────────────────────────────────────────────────────────────

def shannon_entropy(returns: Union[pd.Series, np.ndarray], n_bins: int = 10) -> float:
    """
    Shannon entropy of the return distribution (bits).
    Higher → more uniform / unpredictable.  Max = log2(n_bins) ≈ 3.32 for n_bins=10.
    """
    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 5:
        return 0.0

    counts, _ = np.histogram(arr, bins=n_bins)
    total = counts.sum()
    if total == 0:
        return 0.0

    probs = counts / total
    probs = probs[probs > 0]
    H = -float(np.sum(probs * np.log2(probs)))
    return round(H, 4)


# ── Approximate Entropy ────────────────────────────────────────────────────────

def approx_entropy(returns: Union[pd.Series, np.ndarray],
                   m: int = 2, r_factor: float = 0.2) -> float:
    """
    Approximate Entropy (ApEn).
    Low → regular / predictable.  High → complex / irregular.
    Clipped to [0.0, 2.5].

    Note: O(n²) — use a short series (≤200 bars) for speed.
    """
    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    n   = len(arr)
    if n < m + 2:
        return 0.0

    r = r_factor * float(arr.std())
    if r == 0:
        return 0.0

    def _phi(m_: int) -> float:
        count = 0.0
        denom = n - m_
        if denom <= 0:
            return 0.0
        for i in range(denom):
            tmpl = arr[i:i + m_]
            matches = sum(
                1 for j in range(denom)
                if np.max(np.abs(arr[j:j + m_] - tmpl)) <= r
            )
            if matches > 0:
                count += math.log(matches / denom)
        return count / denom

    try:
        apen = _phi(m) - _phi(m + 1)
    except Exception:
        apen = 0.0

    return round(float(np.clip(apen, 0.0, 2.5)), 4)


# ── Permutation Entropy ────────────────────────────────────────────────────────

def permutation_entropy(returns: Union[pd.Series, np.ndarray],
                        order: int = 3, delay: int = 1) -> float:
    """
    Permutation Entropy (Bandt & Pompe 2002).
    Maps the time series to ordinal patterns, computes normalised Shannon entropy.

    Returns H ∈ [0, 1]:
      0 → perfectly ordered (100% predictable)
      1 → maximally disordered
    Very fast O(n) — works on large windows.
    """
    arr = np.asarray(returns, dtype=float)
    arr = arr[np.isfinite(arr)]
    n   = len(arr)
    if n < order * delay + 1:
        return 0.5

    H_max = math.log(math.factorial(order))

    patterns: Dict[tuple, int] = {}
    for i in range(n - (order - 1) * delay):
        window  = arr[i:i + order * delay:delay]
        pattern = tuple(int(x) for x in np.argsort(window))
        patterns[pattern] = patterns.get(pattern, 0) + 1

    counts = np.array(list(patterns.values()), dtype=float)
    probs  = counts / counts.sum()
    H_raw  = -float(np.sum(probs * np.log(probs + 1e-12)))

    if H_max == 0:
        return 0.5

    return round(float(np.clip(H_raw / H_max, 0.0, 1.0)), 4)


# ── Lyapunov Proxy ─────────────────────────────────────────────────────────────

def lyapunov_proxy(prices: Union[pd.Series, np.ndarray],
                   embedding_dim: int = 3, lag: int = 1) -> float:
    """
    Approximate Largest Lyapunov Exponent via nearest-neighbour divergence.

    Positive → trajectories diverge (chaotic / unstable).
    Negative → trajectories converge (stable attractor).
    Zero     → neutral.
    """
    ts = np.asarray(prices, dtype=float)
    if len(ts) < embedding_dim * lag + 20:
        return 0.0

    std = ts.std()
    if std == 0:
        return 0.0
    ts_n = (ts - ts.mean()) / std

    # Build delay-embedding matrix
    n_pts = len(ts_n) - (embedding_dim - 1) * lag
    E = np.array(
        [ts_n[i:i + embedding_dim * lag:lag] for i in range(n_pts)],
        dtype=float,
    )

    sample_size = min(40, n_pts - 2)
    divergences: List[float] = []

    rng = np.random.default_rng(42)
    indices = rng.choice(n_pts - 1, size=sample_size, replace=False)

    for i in indices:
        dists = np.linalg.norm(E - E[i], axis=1)
        # Exclude temporal neighbours
        lo, hi = max(0, i - 5), min(n_pts, i + 6)
        dists[lo:hi] = np.inf
        j = int(np.argmin(dists))
        if dists[j] == np.inf or i + 1 >= n_pts or j + 1 >= n_pts:
            continue
        d0 = max(dists[j], 1e-10)
        d1 = float(np.linalg.norm(E[i + 1] - E[j + 1]))
        if d1 > 0:
            divergences.append(math.log(d1 / d0))

    if not divergences:
        return 0.0

    return round(float(np.mean(divergences)), 4)


# ══════════════════════════════════════════════════════════════════════════════
#  ChaosFeatureExtractor — unified high-level interface
# ══════════════════════════════════════════════════════════════════════════════

class ChaosFeatureExtractor:
    """
    Compute all chaos / nonlinear features from a price (or return) series.

    Usage
    -----
    extractor = ChaosFeatureExtractor(lookback=126)
    features  = extractor.compute(prices_series)
    label     = extractor.regime_label(features)

    rolling_df = extractor.rolling(prices_series, window=63)
    """

    def __init__(self, lookback: int = 126, rolling_window: int = 63):
        self.lookback        = lookback
        self.rolling_window  = rolling_window

    # ── compute ───────────────────────────────────────────────────────────────

    def compute(self, prices: Union[pd.Series, np.ndarray]) -> Dict[str, float]:
        """
        Compute all chaos metrics on the most recent `lookback` bars.

        Returns dict of metric_name → float value.
        """
        arr = np.asarray(prices, dtype=float)[-self.lookback:]
        if len(arr) < 20:
            return self._empty()

        ret = np.diff(np.log(np.maximum(arr, 1e-10)))

        result: Dict[str, float] = {}

        # Price-based
        for name, fn, args in [
            ("hurst",       hurst_exponent,   (arr,)),
            ("dfa_alpha",   dfa_exponent,     (arr,)),
            ("fractal_dim", fractal_dimension, (arr,)),
            ("lyapunov",    lyapunov_proxy,   (arr,)),
        ]:
            try:
                result[name] = fn(*args)       # type: ignore[operator]
            except Exception:
                result[name] = self._empty()[name]

        # Return-based
        for name, fn, args in [
            ("shannon_ent", shannon_entropy,    (ret,)),
            ("approx_ent",  approx_entropy,     (ret,)),
            ("perm_ent",    permutation_entropy, (ret,)),
        ]:
            try:
                result[name] = fn(*args)       # type: ignore[operator]
            except Exception:
                result[name] = self._empty()[name]

        # Derived boolean signals
        H   = result.get("hurst",    0.5)
        pe  = result.get("perm_ent", 0.5)
        lya = result.get("lyapunov", 0.0)

        result["is_trending"]       = int(H > 0.55)
        result["is_mean_reverting"] = int(H < 0.45)
        result["is_chaotic"]        = int(lya > 0.10)
        result["predictability"]    = round(1.0 - pe, 3)

        return result

    # ── rolling ───────────────────────────────────────────────────────────────

    def rolling(self, prices: pd.Series, window: Optional[int] = None) -> pd.DataFrame:
        """
        Compute chaos features on a rolling basis.
        Returns a DataFrame indexed by price dates (after warm-up).
        """
        w = window or self.rolling_window
        rows: List[Dict] = []
        for i in range(w, len(prices)):
            feat = self.compute(prices.iloc[i - w:i])
            feat["_date"] = prices.index[i]
            rows.append(feat)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows).set_index("_date")
        df.index.name = "date"
        return df

    # ── regime label ──────────────────────────────────────────────────────────

    def regime_label(self, features: Dict[str, float]) -> str:
        """Map chaos features to a descriptive market-regime label."""
        H   = features.get("hurst",    0.5)
        pe  = features.get("perm_ent", 0.5)
        lya = features.get("lyapunov", 0.0)

        if H > 0.65 and pe < 0.55:
            return "STRONGLY_TRENDING"
        elif H > 0.55:
            return "TRENDING"
        elif H < 0.35 and pe < 0.45:
            return "STRONGLY_MEAN_REVERTING"
        elif H < 0.45:
            return "MEAN_REVERTING"
        elif lya > 0.20:
            return "CHAOTIC"
        else:
            return "RANDOM_WALK"

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _empty() -> Dict[str, float]:
        return {
            "hurst":         0.5,
            "dfa_alpha":     0.5,
            "fractal_dim":   1.5,
            "lyapunov":      0.0,
            "shannon_ent":   2.5,
            "approx_ent":    0.5,
            "perm_ent":      0.5,
            "is_trending":   0,
            "is_mean_reverting": 0,
            "is_chaotic":    0,
            "predictability": 0.5,
        }
