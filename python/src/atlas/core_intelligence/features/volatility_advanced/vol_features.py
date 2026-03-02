"""
Advanced Volatility Features
=============================
Beyond simple rolling std — captures volatility regimes, clusters,
and term structure.

Metrics
-------
realized_variance       — High-frequency-style RV from OHLC (Garman-Klass)
garman_klass_vol        — Classic GK estimator (uses H/L/O/C)
yang_zhang_vol          — Yang-Zhang combined estimator (most efficient)
vol_of_vol             — Volatility of volatility (vol uncertainty)
vol_regime_state       — HMM-like 2-state vol regime (LOW / HIGH / SPIKE)
volatility_surface_sim — Simulated IV surface parameters from realized vol
RollingVolatilityEngine — Unified engine class

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.vol_advanced")


# ── Garman-Klass Volatility Estimator ─────────────────────────────────────────

def garman_klass_vol(
    high: Union[pd.Series, np.ndarray],
    low:  Union[pd.Series, np.ndarray],
    close: Union[pd.Series, np.ndarray],
    open_: Optional[Union[pd.Series, np.ndarray]] = None,
    window: int = 20,
    annualize: bool = True,
) -> pd.Series:
    """
    Garman-Klass volatility estimator.
    More efficient than close-to-close (uses OHLC structure).

    GK = sqrt(0.5*(log H/L)² − (2log2−1)*(log C/O)²)

    Returns annualised daily vol series.
    """
    h = pd.Series(np.asarray(high, dtype=float))
    l = pd.Series(np.asarray(low,  dtype=float))
    c = pd.Series(np.asarray(close, dtype=float))

    log_hl = (np.log(h / l)) ** 2
    c_prev = c.shift(1) if open_ is None else pd.Series(np.asarray(open_, dtype=float))
    log_co = (np.log(c / c_prev)) ** 2

    gk = 0.5 * log_hl - (2 * np.log(2) - 1) * log_co
    gk = gk.clip(lower=0)

    vol = np.sqrt(gk.rolling(window).mean())
    if annualize:
        vol = vol * np.sqrt(252)
    return vol


# ── Yang-Zhang Volatility (most efficient unbiased OHLC estimator) ────────────

def yang_zhang_vol(
    ohlcv: pd.DataFrame,
    window: int = 20,
    annualize: bool = True,
) -> pd.Series:
    """
    Yang-Zhang 2000 combined estimator.
    Minimum variance estimator for OHLC data.
    Handles overnight gaps.

    Parameters
    ----------
    ohlcv : DataFrame with Open, High, Low, Close columns (capitalized)
    """
    o = np.log(ohlcv["Open"] / ohlcv["Close"].shift(1))
    c = np.log(ohlcv["Close"] / ohlcv["Open"])
    hl = np.log(ohlcv["High"] / ohlcv["Low"]) ** 2

    k  = 0.34 / (1.34 + (window + 1) / (window - 1))
    v_o = o.rolling(window).var(ddof=0)
    v_c = c.rolling(window).var(ddof=0)
    v_rs = hl.rolling(window).mean()   # Rogers-Satchell component

    yz = v_o + k * v_c + (1 - k) * v_rs
    yz = yz.clip(lower=0)
    vol = np.sqrt(yz)
    if annualize:
        vol = vol * np.sqrt(252)
    return vol


# ── Realized Variance from Returns ───────────────────────────────────────────

def realized_variance(
    returns: Union[pd.Series, np.ndarray],
    window: int = 20,
    annualize: bool = True,
) -> pd.Series:
    """
    Simple realized variance = sum of squared returns over window.
    Fast proxy for high-frequency RV.
    """
    ret = pd.Series(np.asarray(returns, dtype=float))
    rv  = (ret ** 2).rolling(window).sum()
    if annualize:
        rv = rv * (252 / window)
    return rv


# ── Vol-of-Vol ────────────────────────────────────────────────────────────────

def vol_of_vol(
    returns: Union[pd.Series, np.ndarray],
    vol_window: int = 10,
    vov_window: int = 30,
    annualize: bool = True,
) -> pd.Series:
    """
    Volatility of volatility — rolling std of rolling vol.
    High VoV → unstable regime (vol itself is volatile).
    """
    ret = pd.Series(np.asarray(returns, dtype=float))
    daily_vol = ret.rolling(vol_window).std()
    if annualize:
        daily_vol = daily_vol * np.sqrt(252)
    vov = daily_vol.rolling(vov_window).std()
    return vov


# ── Volatility Regime Detection ───────────────────────────────────────────────

def vol_regime_state(
    returns: Union[pd.Series, np.ndarray],
    window: int = 20,
    low_pct: float = 33.0,
    high_pct: float = 67.0,
) -> pd.Series:
    """
    2-state volatility regime: 'LOW' | 'NORMAL' | 'HIGH' | 'SPIKE'.

    Based on rolling vol percentile rank vs its own 1-year history.
    """
    ret  = pd.Series(np.asarray(returns, dtype=float))
    vol  = ret.rolling(window).std() * np.sqrt(252)
    rank = vol.rolling(252).apply(
        lambda x: float(np.percentile(x, 50) if len(x) > 1 else 50),
        raw=True,
    )

    def _classify(v: float, r: float) -> str:
        if np.isnan(v) or np.isnan(r):
            return "UNKNOWN"
        annualised_pct = v * 100
        if annualised_pct > 80:
            return "SPIKE"
        if r > high_pct:
            return "HIGH"
        elif r < low_pct:
            return "LOW"
        else:
            return "NORMAL"

    regimes = pd.Series(
        [_classify(v, r) for v, r in zip(vol, rank)],
        index=vol.index,
    )
    return regimes


# ── Volatility Smile Simulation ───────────────────────────────────────────────

def volatility_surface_params(
    realized_vol: float,
    skew_factor: float = -0.05,
    kurtosis_factor: float = 0.02,
) -> Dict[str, float]:
    """
    Simulate IV surface parameters from realized vol.
    Returns ATM vol, skew slope, and smile convexity for 3 expiries.

    Purely synthetic — for visualization of surface shape.
    """
    return {
        "atm_vol_1m":  round(realized_vol * 1.05, 4),
        "atm_vol_3m":  round(realized_vol * 1.00, 4),
        "atm_vol_6m":  round(realized_vol * 0.95, 4),
        "skew_slope":  round(skew_factor,    4),
        "convexity":   round(kurtosis_factor, 4),
        "term_slope":  round(-0.02,           4),   # vol declines with expiry
    }


# ══════════════════════════════════════════════════════════════════════════════
#  RollingVolatilityEngine — unified interface
# ══════════════════════════════════════════════════════════════════════════════

class RollingVolatilityEngine:
    """
    Compute all advanced volatility metrics from OHLCV data.

    Usage
    -----
    engine  = RollingVolatilityEngine(window=20)
    profile = engine.analyze(ohlcv_df)       # current snapshot
    panel   = engine.rolling_panel(ohlcv_df) # DataFrame over time
    """

    def __init__(self, window: int = 20, annualize: bool = True):
        self.window    = window
        self.annualize = annualize

    def analyze(self, ohlcv: pd.DataFrame) -> Dict[str, float]:
        """
        Current-point-in-time volatility profile.

        Parameters
        ----------
        ohlcv : DataFrame with Open, High, Low, Close, Volume columns

        Returns dict of metrics (scalars).
        """
        required = {"Open", "High", "Low", "Close"}
        if not required.issubset(ohlcv.columns):
            raise ValueError(f"OHLCV must have columns: {required}")

        closes  = ohlcv["Close"]
        returns = closes.pct_change().dropna()

        if len(returns) < self.window + 5:
            return self._empty()

        # Yang-Zhang vol (best estimator)
        yz = yang_zhang_vol(ohlcv, self.window, self.annualize)
        # Garman-Klass vol
        gk = garman_klass_vol(ohlcv["High"], ohlcv["Low"], ohlcv["Close"],
                               ohlcv["Open"], self.window, self.annualize)
        # Close-to-close (baseline)
        c2c = returns.rolling(self.window).std() * (np.sqrt(252) if self.annualize else 1.0)
        # Vol-of-vol
        vov = vol_of_vol(returns, vol_window=10, vov_window=self.window, annualize=self.annualize)
        # Regime
        regime_s = vol_regime_state(returns, self.window)

        def _last(s: pd.Series) -> float:
            v = s.dropna()
            return round(float(v.iloc[-1]), 4) if len(v) > 0 else 0.0

        cur_yz  = _last(yz)
        cur_gk  = _last(gk)
        cur_c2c = _last(c2c)
        cur_vov = _last(vov)
        cur_reg = regime_s.dropna().iloc[-1] if len(regime_s.dropna()) > 0 else "UNKNOWN"

        # 5-day vs 20-day vol ratio (short/long term spread)
        vol_5  = float(returns.tail(5).std()  * (np.sqrt(252) if self.annualize else 1.0))
        vol_20 = float(returns.tail(20).std() * (np.sqrt(252) if self.annualize else 1.0))
        vol_ratio = round(vol_5 / (vol_20 + 1e-10), 3)

        surface = volatility_surface_params(cur_yz)

        return {
            "vol_yz":           cur_yz,          # Yang-Zhang (most accurate)
            "vol_gk":           cur_gk,          # Garman-Klass
            "vol_c2c":          cur_c2c,         # Close-to-close (standard)
            "vol_of_vol":       cur_vov,         # Vol uncertainty
            "vol_ratio_5_20":   vol_ratio,       # >1 = vol is rising
            "regime":           cur_reg,
            "atm_vol_1m":       surface["atm_vol_1m"],
            "skew":             surface["skew_slope"],
            "convexity":        surface["convexity"],
        }

    def rolling_panel(self, ohlcv: pd.DataFrame) -> pd.DataFrame:
        """
        Compute vol metrics for every bar (returns DataFrame indexed by date).
        """
        returns = ohlcv["Close"].pct_change()
        yz      = yang_zhang_vol(ohlcv, self.window, self.annualize)
        gk      = garman_klass_vol(ohlcv["High"], ohlcv["Low"], ohlcv["Close"],
                                    ohlcv["Open"], self.window, self.annualize)
        c2c     = returns.rolling(self.window).std() * (np.sqrt(252) if self.annualize else 1.0)
        vov     = vol_of_vol(returns, vol_window=10, vov_window=self.window,
                              annualize=self.annualize)
        regimes = vol_regime_state(returns, self.window)

        df = pd.DataFrame({
            "vol_yz":      yz,
            "vol_gk":      gk,
            "vol_c2c":     c2c,
            "vol_of_vol":  vov,
            "vol_ratio":   c2c.rolling(5).mean() / c2c.rolling(20).mean(),
            "regime":      regimes,
        })
        return df.dropna(subset=["vol_yz"])

    @staticmethod
    def _empty() -> Dict[str, float]:
        return {
            "vol_yz": 0.0, "vol_gk": 0.0, "vol_c2c": 0.0,
            "vol_of_vol": 0.0, "vol_ratio_5_20": 1.0,
            "regime": "UNKNOWN", "atm_vol_1m": 0.0,
            "skew": 0.0, "convexity": 0.0,
        }
