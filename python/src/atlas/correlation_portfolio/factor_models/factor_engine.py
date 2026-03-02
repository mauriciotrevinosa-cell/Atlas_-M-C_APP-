"""
Atlas Factor Engine — Alpha158 inspired (qlib-style)
=====================================================
Computes 50+ quantitative alpha factors from OHLCV data.
Inspired by Microsoft qlib's Alpha158 / Alpha360 feature pipelines.

Factor groups:
  MOMENTUM  — price return over multiple windows
  VOLUME    — volume-price relationship and anomalies
  VOLATILITY— realized vol, ATR, range normalisation
  QUALITY   — Sharpe-like ratio, consistency measures
  TECHNICAL — RSI, MACD, BB width, EMA crossovers
  MICRO     — intraday range, close position, gap fill

Usage:
    from atlas.correlation_portfolio.factor_models.factor_engine import FactorEngine
    engine = FactorEngine()
    factors = engine.compute(df)   # df: OHLCV with CAPITALIZED columns
    scores  = engine.score(df)     # normalized factor scores dict
"""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FactorEngine:
    """
    Computes quantitative alpha factors from OHLCV price data.

    Accepts DataFrames with either capitalized (Open/High/Low/Close/Volume)
    or lowercase (open/high/low/close/volume) column names.
    """

    # Factor group definitions: name → list of factor function names
    GROUPS = {
        "MOMENTUM":   ["mom1","mom5","mom10","mom20","mom60","roc5","roc20",
                       "ema_ratio","price_accel","reg_slope20"],
        "VOLUME":     ["vol_ratio5","vol_ratio20","vol_surge","dollar_vol",
                       "vwap_dev","vol_momentum","volume_zscore","pvt","obv_roc"],
        "VOLATILITY": ["atr14","realized_vol5","realized_vol20","hl_range",
                       "vol_regime","parkinson_vol","garman_klass"],
        "QUALITY":    ["sharpe_ratio20","sharpe_ratio60","calmar_proxy",
                       "consistency20","up_capture","sortino_proxy"],
        "TECHNICAL":  ["rsi14","macd_hist","bb_width","ema_cross","cci20",
                       "stoch_k","williams_r","adx_proxy"],
        "MICRO":      ["close_pos","gap_fill","intraday_range",
                       "tail_ratio","open_drive","body_ratio"],
    }

    def __init__(self, min_periods: int = 5):
        self.min_periods = min_periods

    # ─── Public API ───────────────────────────────────────────────────────

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute all factor values.

        Returns a DataFrame where each column is one factor,
        indexed the same as the input (tail row = most recent).
        """
        d = self._normalise(df)
        if len(d) < self.min_periods:
            return pd.DataFrame()

        result = {}
        for group, names in self.GROUPS.items():
            for name in names:
                try:
                    fn = getattr(self, f"_f_{name}", None)
                    if fn:
                        val = fn(d)
                        if val is not None:
                            result[f"{group}/{name}"] = val
                except Exception as e:
                    logger.debug("Factor %s failed: %s", name, e)

        return pd.DataFrame(result, index=d.index)

    def score(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Return the LATEST row of factor values, normalised to [-1, 1].
        Used by the /api/factors/{ticker} endpoint.
        """
        factors_df = self.compute(df)
        if factors_df.empty:
            return {}

        latest = factors_df.iloc[-1]
        # Rolling z-score normalise across the factor window
        scores = {}
        for col in factors_df.columns:
            series = factors_df[col].dropna()
            if len(series) < 3:
                continue
            mu, sd = series.mean(), series.std()
            if sd < 1e-9:
                continue
            z = (latest[col] - mu) / sd
            # Clip to [-3,3] then scale to [-1,1]
            scores[col] = float(np.clip(z / 3, -1, 1))
        return scores

    def group_scores(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Return average score per factor group (for radar/dashboard display).
        """
        scores = self.score(df)
        groups: Dict[str, list] = {}
        for key, val in scores.items():
            grp = key.split("/")[0]
            groups.setdefault(grp, []).append(val)
        return {g: float(np.mean(v)) for g, v in groups.items() if v}

    def top_factors(self, df: pd.DataFrame, n: int = 10) -> list:
        """Return top-N strongest (absolute) factor signals."""
        scores = self.score(df)
        ranked = sorted(scores.items(), key=lambda x: abs(x[1]), reverse=True)
        return [{"factor": k, "score": round(v, 4)} for k, v in ranked[:n]]

    # ─── Internal normalisation ───────────────────────────────────────────

    def _normalise(self, df: pd.DataFrame) -> pd.DataFrame:
        """Accept capitalized or lowercase OHLCV columns."""
        col_map = {}
        for orig in df.columns:
            lo = orig.lower()
            if lo in ("open","high","low","close","volume"):
                col_map[orig] = lo
        d = df.rename(columns=col_map).copy()
        required = ["open","high","low","close","volume"]
        missing = [c for c in required if c not in d.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")
        for c in required:
            d[c] = pd.to_numeric(d[c], errors="coerce")
        return d.dropna(subset=["close"])

    # ─── MOMENTUM factors ─────────────────────────────────────────────────

    def _f_mom1(self, d): return d["close"].pct_change(1)
    def _f_mom5(self, d): return d["close"].pct_change(5)
    def _f_mom10(self, d): return d["close"].pct_change(10)
    def _f_mom20(self, d): return d["close"].pct_change(20)
    def _f_mom60(self, d): return d["close"].pct_change(60)

    def _f_roc5(self, d):
        """Rate of change 5-day, smoothed."""
        roc = d["close"].pct_change(5)
        return roc.rolling(3).mean()

    def _f_roc20(self, d):
        return d["close"].pct_change(20).rolling(5).mean()

    def _f_ema_ratio(self, d):
        """Short EMA / Long EMA — above 1 = bullish."""
        ema12 = d["close"].ewm(span=12).mean()
        ema26 = d["close"].ewm(span=26).mean()
        return (ema12 / ema26 - 1)

    def _f_price_accel(self, d):
        """Acceleration = mom5 - mom5_lagged: is momentum speeding up?"""
        m5 = d["close"].pct_change(5)
        return m5 - m5.shift(5)

    def _f_reg_slope20(self, d):
        """Linear regression slope of close over 20 bars (normalised)."""
        def slope(s):
            if s.isna().any(): return np.nan
            x = np.arange(len(s))
            return np.polyfit(x, s.values, 1)[0] / (s.mean() + 1e-9)
        return d["close"].rolling(20).apply(slope, raw=False)

    # ─── VOLUME factors ───────────────────────────────────────────────────

    def _f_vol_ratio5(self, d):
        """Volume vs 5-day average — surge detection."""
        return d["volume"] / d["volume"].rolling(5).mean()

    def _f_vol_ratio20(self, d):
        return d["volume"] / d["volume"].rolling(20).mean()

    def _f_vol_surge(self, d):
        """Z-score of volume over 20-day window."""
        v = d["volume"]
        return (v - v.rolling(20).mean()) / (v.rolling(20).std() + 1e-9)

    def _f_dollar_vol(self, d):
        """Log(price × volume) — liquidity proxy."""
        dv = d["close"] * d["volume"]
        return np.log(dv + 1).pct_change(5)

    def _f_vwap_dev(self, d):
        """Close deviation from rolling VWAP."""
        vwap = (d["close"] * d["volume"]).rolling(10).sum() / d["volume"].rolling(10).sum()
        return (d["close"] / vwap - 1)

    def _f_vol_momentum(self, d):
        """Rate of change in volume itself."""
        return d["volume"].pct_change(10)

    def _f_volume_zscore(self, d):
        v = d["volume"]
        return (v - v.rolling(60).mean()) / (v.rolling(60).std() + 1e-9)

    def _f_pvt(self, d):
        """Price-Volume Trend."""
        pvt = (d["close"].pct_change() * d["volume"]).cumsum()
        return pvt.pct_change(5)

    def _f_obv_roc(self, d):
        """On-Balance Volume rate of change."""
        sign = np.sign(d["close"].diff())
        obv  = (sign * d["volume"]).cumsum()
        return obv.pct_change(10)

    # ─── VOLATILITY factors ───────────────────────────────────────────────

    def _f_atr14(self, d):
        """Average True Range / Close — normalised ATR."""
        hl  = d["high"] - d["low"]
        hpc = (d["high"] - d["close"].shift()).abs()
        lpc = (d["low"]  - d["close"].shift()).abs()
        tr  = pd.concat([hl, hpc, lpc], axis=1).max(axis=1)
        return (tr.rolling(14).mean() / d["close"])

    def _f_realized_vol5(self, d):
        """5-day realized volatility (std of log returns)."""
        lr = np.log(d["close"] / d["close"].shift())
        return lr.rolling(5).std()

    def _f_realized_vol20(self, d):
        lr = np.log(d["close"] / d["close"].shift())
        return lr.rolling(20).std()

    def _f_hl_range(self, d):
        """High-Low range / close — daily range normalised."""
        return (d["high"] - d["low"]) / d["close"]

    def _f_vol_regime(self, d):
        """Is current vol above its own 60-day average?"""
        rv = np.log(d["close"]/d["close"].shift()).rolling(20).std()
        return rv / rv.rolling(60).mean()

    def _f_parkinson_vol(self, d):
        """Parkinson historical volatility (uses high/low)."""
        factor = 1.0 / (4.0 * math.log(2))
        ln_hl  = np.log(d["high"] / d["low"])
        return np.sqrt(factor * (ln_hl**2).rolling(20).mean())

    def _f_garman_klass(self, d):
        """Garman-Klass volatility estimator."""
        u = np.log(d["high"] / d["close"].shift())
        d_ = np.log(d["low"]  / d["close"].shift())
        c  = np.log(d["close"] / d["close"].shift())
        gk = (0.5*(u-d_)**2 - (2*math.log(2)-1)*c**2)
        return np.sqrt(gk.rolling(20).mean())

    # ─── QUALITY factors ──────────────────────────────────────────────────

    def _f_sharpe_ratio20(self, d):
        """Rolling 20-day Sharpe (excess return / vol)."""
        r = d["close"].pct_change()
        return r.rolling(20).mean() / (r.rolling(20).std() + 1e-9) * math.sqrt(252)

    def _f_sharpe_ratio60(self, d):
        r = d["close"].pct_change()
        return r.rolling(60).mean() / (r.rolling(60).std() + 1e-9) * math.sqrt(252)

    def _f_calmar_proxy(self, d):
        """Annualised return / MaxDrawdown (20-day window)."""
        r  = d["close"].pct_change()
        ret_20  = r.rolling(20).sum() * (252/20)
        cum     = d["close"] / d["close"].rolling(20).max()
        mdd     = (1 - cum.rolling(20).min()).clip(lower=1e-6)
        return ret_20 / mdd

    def _f_consistency20(self, d):
        """Fraction of up-days in last 20 days."""
        return (d["close"].diff() > 0).rolling(20).mean()

    def _f_up_capture(self, d):
        """Average gain on up-days / average loss on down-days."""
        r   = d["close"].pct_change()
        ups = r.where(r > 0).rolling(20).mean()
        dns = r.where(r < 0).rolling(20).mean().abs()
        return ups / (dns + 1e-9)

    def _f_sortino_proxy(self, d):
        """Sortino ratio proxy (20-day)."""
        r    = d["close"].pct_change()
        ret  = r.rolling(20).mean()
        down = r.where(r < 0).rolling(20).std()
        return ret / (down + 1e-9) * math.sqrt(252)

    # ─── TECHNICAL factors ────────────────────────────────────────────────

    def _f_rsi14(self, d):
        """RSI(14), normalised to [-1, 1]."""
        delta = d["close"].diff()
        gain  = delta.where(delta>0, 0.0).rolling(14).mean()
        loss  = (-delta.where(delta<0, 0.0)).rolling(14).mean()
        rs    = gain / (loss + 1e-9)
        rsi   = 100 - 100/(1+rs)
        return (rsi - 50) / 50    # normalise: 0=neutral, +1=overbought, -1=oversold

    def _f_macd_hist(self, d):
        """MACD histogram, normalised by close."""
        ema12 = d["close"].ewm(span=12).mean()
        ema26 = d["close"].ewm(span=26).mean()
        macd  = ema12 - ema26
        sig   = macd.ewm(span=9).mean()
        return (macd - sig) / (d["close"] + 1e-9)

    def _f_bb_width(self, d):
        """Bollinger Band width / middle — measures volatility expansion."""
        mid = d["close"].rolling(20).mean()
        sd  = d["close"].rolling(20).std()
        return 2*sd / (mid + 1e-9)

    def _f_ema_cross(self, d):
        """EMA 5 / EMA 20 cross signal."""
        e5  = d["close"].ewm(span=5).mean()
        e20 = d["close"].ewm(span=20).mean()
        return (e5 - e20) / (d["close"] + 1e-9)

    def _f_cci20(self, d):
        """Commodity Channel Index, normalised."""
        tp   = (d["high"] + d["low"] + d["close"]) / 3
        sma  = tp.rolling(20).mean()
        mad  = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
        cci  = (tp - sma) / (0.015 * mad + 1e-9)
        return cci / 200   # typical range ±100 → ±0.5

    def _f_stoch_k(self, d):
        """Stochastic %K, normalised to [-1, 1]."""
        lo14 = d["low"].rolling(14).min()
        hi14 = d["high"].rolling(14).max()
        k    = (d["close"] - lo14) / (hi14 - lo14 + 1e-9)
        return k*2 - 1   # [0,1] → [-1,1]

    def _f_williams_r(self, d):
        """Williams %R, normalised to [-1, 1]."""
        lo14 = d["low"].rolling(14).min()
        hi14 = d["high"].rolling(14).max()
        wr   = (hi14 - d["close"]) / (hi14 - lo14 + 1e-9)
        return 1 - wr*2  # invert: +1=overbought, -1=oversold

    def _f_adx_proxy(self, d):
        """Simplified ADX proxy — trend strength [0, 1]."""
        hl   = (d["high"] - d["low"]).rolling(14).mean()
        rng  = d["close"].rolling(14).apply(lambda x: x.max()-x.min(), raw=True)
        return (rng / (hl*14 + 1e-9)).clip(0,1)

    # ─── MICRO / microstructure factors ──────────────────────────────────

    def _f_close_pos(self, d):
        """Where close falls within the daily range: 0=bottom, 1=top."""
        lo, hi = d["low"], d["high"]
        pos = (d["close"] - lo) / (hi - lo + 1e-9)
        return pos.rolling(5).mean() * 2 - 1   # → [-1,1]

    def _f_gap_fill(self, d):
        """Overnight gap: today's open vs yesterday's close."""
        return (d["open"] / d["close"].shift() - 1)

    def _f_intraday_range(self, d):
        """Normalised intraday range: (H-L)/O."""
        return (d["high"] - d["low"]) / (d["open"] + 1e-9)

    def _f_tail_ratio(self, d):
        """Upper vs lower wick ratio — buying pressure proxy."""
        body  = (d["close"] - d["open"]).abs()
        upper = d["high"] - d[["open","close"]].max(axis=1)
        lower = d[["open","close"]].min(axis=1) - d["low"]
        return (upper - lower) / (body + upper + lower + 1e-9)

    def _f_open_drive(self, d):
        """How far price moves from open by close."""
        return (d["close"] - d["open"]) / (d["open"] + 1e-9)

    def _f_body_ratio(self, d):
        """Body size as fraction of total daily range."""
        body  = (d["close"] - d["open"]).abs()
        total = (d["high"] - d["low"]) + 1e-9
        return body / total


# ── Module-level convenience ─────────────────────────────────────────────────

_engine = FactorEngine()


def compute_factors(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all factors from OHLCV DataFrame."""
    return _engine.compute(df)


def get_scores(df: pd.DataFrame) -> Dict[str, float]:
    """Return normalised latest factor scores."""
    return _engine.score(df)


def get_group_scores(df: pd.DataFrame) -> Dict[str, float]:
    """Return per-group average score for radar display."""
    return _engine.group_scores(df)


def get_top_factors(df: pd.DataFrame, n: int = 10) -> list:
    """Return top-N strongest factor signals."""
    return _engine.top_factors(df, n)


if __name__ == "__main__":
    import yfinance as yf
    ticker = "AAPL"
    df = yf.download(ticker, period="2y", auto_adjust=True)
    df.columns = [c.capitalize() for c in df.columns]
    engine = FactorEngine()
    scores = engine.score(df)
    print(f"\n=== {ticker} Factor Scores (latest bar) ===")
    for k, v in sorted(scores.items(), key=lambda x: abs(x[1]), reverse=True)[:20]:
        bar = "█" * int(abs(v)*20)
        sign = "+" if v > 0 else "-"
        print(f"  {sign}{bar:<20} {k:<30} {v:+.4f}")
    print(f"\nGroup averages:")
    for g, s in engine.group_scores(df).items():
        print(f"  {g:<12} {s:+.4f}")
