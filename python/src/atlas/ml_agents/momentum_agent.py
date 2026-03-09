"""
Momentum Agent — Swarm Committee Member
=========================================
Specialized agent for trend and momentum analysis.
Covers: price momentum, RSI, MACD, trend strength, sector rotation.

Signals produced:
  - Price momentum (1m, 3m, 6m, 12m)
  - RSI momentum state
  - MACD signal alignment
  - ADX trend strength
  - Bollinger Band position
  - 52-week relative position
  - Momentum composite score → verdict

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.ml_agents.momentum_agent")


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class MomentumReport:
    """Output structure from the Momentum Agent."""
    symbol: str
    mom_1m: float = 0.0      # 21-bar return
    mom_3m: float = 0.0      # 63-bar return
    mom_6m: float = 0.0      # 126-bar return
    mom_12m: float = 0.0     # 252-bar return
    rsi_14: float = 50.0     # RSI(14)
    rsi_state: str = "NEUTRAL"  # OVERBOUGHT / NEUTRAL / OVERSOLD
    macd_signal: str = "FLAT"   # BULLISH / BEARISH / FLAT
    macd_histogram: float = 0.0
    adx: float = 20.0        # Average Directional Index
    trend_strength: str = "WEAK"  # STRONG / MODERATE / WEAK
    bb_position: float = 0.5  # 0 = lower band, 1 = upper band
    week52_position: float = 0.5  # 0 = 52-week low, 1 = 52-week high
    momentum_score: float = 0.5   # 0–1 composite
    verdict: str = "HOLD"
    reasoning: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "momentum": {
                "1m": round(self.mom_1m, 4),
                "3m": round(self.mom_3m, 4),
                "6m": round(self.mom_6m, 4),
                "12m": round(self.mom_12m, 4),
            },
            "rsi_14": round(self.rsi_14, 2),
            "rsi_state": self.rsi_state,
            "macd_signal": self.macd_signal,
            "macd_histogram": round(self.macd_histogram, 6),
            "adx": round(self.adx, 2),
            "trend_strength": self.trend_strength,
            "bb_position": round(self.bb_position, 3),
            "week52_position": round(self.week52_position, 3),
            "momentum_score": round(self.momentum_score, 3),
            "verdict": self.verdict,
            "reasoning": self.reasoning,
        }


# ══════════════════════════════════════════════════════════════════════════════
#  MomentumAgent
# ══════════════════════════════════════════════════════════════════════════════

class MomentumAgent:
    """
    Swarm committee member: Momentum Specialist.

    Uses pure numpy/pandas indicator calculations (no TA-Lib dependency).

    Usage:
        agent = MomentumAgent()
        report = agent.analyse("TSLA", ohlcv_df)
        print(report.to_dict())
    """

    def __init__(self):
        logger.info("MomentumAgent initialised")

    # ── Public API ────────────────────────────────────────────────────────────

    def analyse(self, symbol: str, ohlcv: pd.DataFrame) -> MomentumReport:
        """
        Full momentum analysis.

        Parameters
        ----------
        symbol : Ticker
        ohlcv  : DataFrame with Open/High/Low/Close/Volume columns

        Returns MomentumReport.
        """
        report = MomentumReport(symbol=symbol)

        if ohlcv is None or len(ohlcv) < 20:
            report.reasoning.append("Insufficient data — all metrics defaulted")
            return report

        try:
            closes = self._closes(ohlcv)
            highs  = self._col(ohlcv, "high")
            lows   = self._col(ohlcv, "low")

            # Price momentum
            report.mom_1m  = self._momentum(closes, 21)
            report.mom_3m  = self._momentum(closes, 63)
            report.mom_6m  = self._momentum(closes, 126)
            report.mom_12m = self._momentum(closes, 252)

            # Oscillators
            report.rsi_14     = self._rsi(closes, 14)
            report.rsi_state  = self._rsi_state(report.rsi_14)

            macd_line, signal_line, hist = self._macd(closes)
            report.macd_histogram = hist
            report.macd_signal    = self._macd_signal(hist, macd_line, signal_line)

            # Trend
            report.adx            = self._adx(highs, lows, closes, 14)
            report.trend_strength = self._trend_strength(report.adx)

            # Band position
            report.bb_position    = self._bb_position(closes, 20)
            report.week52_position = self._week52_position(closes)

            # Composite
            report.momentum_score = self._composite(report)
            report.verdict        = self._verdict(report)
            report.reasoning      = self._build_reasoning(report)
            report.metadata       = {
                "n_bars": len(closes),
                "last_close": float(closes.iloc[-1]),
                "macd_line": round(macd_line, 6),
                "signal_line": round(signal_line, 6),
            }

        except Exception as exc:
            logger.exception("MomentumAgent.analyse failed for %s: %s", symbol, exc)
            report.reasoning.append(f"Analysis error: {exc}")

        return report

    # ── Indicator calculations ────────────────────────────────────────────────

    @staticmethod
    def _col(df: pd.DataFrame, name: str) -> pd.Series:
        for c in df.columns:
            if c.lower() == name:
                return df[c].astype(float)
        return df.iloc[:, 0].astype(float)

    def _closes(self, df: pd.DataFrame) -> pd.Series:
        return self._col(df, "close")

    @staticmethod
    def _momentum(closes: pd.Series, period: int) -> float:
        if len(closes) <= period:
            return 0.0
        return float((closes.iloc[-1] / closes.iloc[-period - 1]) - 1)

    @staticmethod
    def _ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False).mean()

    def _rsi(self, closes: pd.Series, period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        delta  = closes.diff().dropna()
        gain   = delta.clip(lower=0)
        loss   = (-delta).clip(lower=0)
        avg_g  = gain.ewm(com=period - 1, adjust=False).mean()
        avg_l  = loss.ewm(com=period - 1, adjust=False).mean()
        rs     = avg_g / avg_l.replace(0, np.nan)
        rsi    = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1])

    @staticmethod
    def _rsi_state(rsi: float) -> str:
        if rsi >= 70:
            return "OVERBOUGHT"
        elif rsi <= 30:
            return "OVERSOLD"
        return "NEUTRAL"

    def _macd(
        self, closes: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ):
        if len(closes) < slow + signal:
            return 0.0, 0.0, 0.0
        ema_fast    = self._ema(closes, fast)
        ema_slow    = self._ema(closes, slow)
        macd_line   = ema_fast - ema_slow
        signal_line = self._ema(macd_line, signal)
        histogram   = macd_line - signal_line
        return (
            float(macd_line.iloc[-1]),
            float(signal_line.iloc[-1]),
            float(histogram.iloc[-1]),
        )

    @staticmethod
    def _macd_signal(hist: float, macd: float, signal: float) -> str:
        if macd > signal and hist > 0:
            return "BULLISH"
        elif macd < signal and hist < 0:
            return "BEARISH"
        return "FLAT"

    def _adx(
        self,
        highs: pd.Series,
        lows: pd.Series,
        closes: pd.Series,
        period: int = 14,
    ) -> float:
        if len(closes) < period + 1:
            return 20.0
        try:
            h = highs.values.astype(float)
            l = lows.values.astype(float)
            c = closes.values.astype(float)

            plus_dm  = np.maximum(np.diff(h), 0)
            minus_dm = np.maximum(-np.diff(l), 0)
            # When both positive, pick the larger
            mask = plus_dm > minus_dm
            minus_dm[mask] = 0
            plus_dm[~mask] = 0

            # True Range
            tr = np.maximum(
                h[1:] - l[1:],
                np.maximum(np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1]))
            )

            def _smooth(arr, n):
                res = np.zeros_like(arr)
                res[n - 1] = arr[:n].sum()
                for i in range(n, len(arr)):
                    res[i] = res[i - 1] - res[i - 1] / n + arr[i]
                return res

            atr      = _smooth(tr, period)
            s_plus   = _smooth(plus_dm, period)
            s_minus  = _smooth(minus_dm, period)

            with np.errstate(divide="ignore", invalid="ignore"):
                di_plus  = 100 * np.where(atr > 0, s_plus  / atr, 0)
                di_minus = 100 * np.where(atr > 0, s_minus / atr, 0)
                dx_denom = di_plus + di_minus
                dx       = 100 * np.where(dx_denom > 0, np.abs(di_plus - di_minus) / dx_denom, 0)

            if len(dx) < period:
                return 20.0
            adx_vals = pd.Series(dx).ewm(span=period, adjust=False).mean()
            return float(adx_vals.iloc[-1])
        except Exception:
            return 20.0

    @staticmethod
    def _trend_strength(adx: float) -> str:
        if adx >= 40:
            return "STRONG"
        elif adx >= 25:
            return "MODERATE"
        return "WEAK"

    @staticmethod
    def _bb_position(closes: pd.Series, period: int = 20) -> float:
        """0 = at lower band, 0.5 = at middle, 1 = at upper band."""
        if len(closes) < period:
            return 0.5
        window = closes.tail(period)
        mid    = window.mean()
        std    = window.std()
        if std == 0:
            return 0.5
        upper = mid + 2 * std
        lower = mid - 2 * std
        last  = float(closes.iloc[-1])
        band_range = upper - lower
        if band_range == 0:
            return 0.5
        return float(max(0.0, min(1.0, (last - lower) / band_range)))

    @staticmethod
    def _week52_position(closes: pd.Series) -> float:
        """Position within 52-week high/low range."""
        window = closes.tail(252)
        hi  = float(window.max())
        lo  = float(window.min())
        rng = hi - lo
        if rng == 0:
            return 0.5
        return float((closes.iloc[-1] - lo) / rng)

    # ── Composite scoring ─────────────────────────────────────────────────────

    @staticmethod
    def _composite(r: MomentumReport) -> float:
        """
        Composite momentum score 0–1.
        Components: price momentum (40%), RSI (20%), MACD (20%), trend (20%)
        """
        def clamp(v):
            return max(0.0, min(1.0, v))

        # Price momentum composite (normalised across periods)
        mom_vals = [r.mom_1m, r.mom_3m, r.mom_6m, r.mom_12m]
        mom_avg  = float(np.mean(mom_vals))
        mom_score = clamp(0.5 + mom_avg * 2.0)   # map ±25% → 0–1

        # RSI score: oversold=bullish, overbought=bearish from entry perspective
        rsi_score = clamp(1 - (r.rsi_14 / 100)) if r.rsi_14 > 50 else clamp(r.rsi_14 / 50 * 0.7 + 0.3)

        # MACD score
        macd_score = {"BULLISH": 0.8, "FLAT": 0.5, "BEARISH": 0.2}.get(r.macd_signal, 0.5)

        # Trend strength
        trend_score = {"STRONG": 0.85, "MODERATE": 0.60, "WEAK": 0.35}.get(r.trend_strength, 0.5)

        return round(
            0.40 * mom_score +
            0.20 * rsi_score +
            0.20 * macd_score +
            0.20 * trend_score,
            3,
        )

    @staticmethod
    def _verdict(r: MomentumReport) -> str:
        if r.momentum_score >= 0.70:
            return "BUY"
        elif r.momentum_score >= 0.50:
            return "HOLD"
        elif r.momentum_score >= 0.30:
            return "REDUCE"
        return "SELL"

    def _build_reasoning(self, r: MomentumReport) -> List[str]:
        lines = []
        lines.append(
            f"Momentum → 1M:{r.mom_1m:.1%}  3M:{r.mom_3m:.1%}  "
            f"6M:{r.mom_6m:.1%}  12M:{r.mom_12m:.1%}"
        )
        lines.append(f"RSI(14): {r.rsi_14:.1f}  →  {r.rsi_state}")
        lines.append(f"MACD Signal: {r.macd_signal}  (histogram={r.macd_histogram:.4f})")
        lines.append(f"ADX: {r.adx:.1f}  →  Trend: {r.trend_strength}")
        lines.append(f"Bollinger Position: {r.bb_position:.1%}  |  52W Position: {r.week52_position:.1%}")
        lines.append(f"Composite Momentum Score: {r.momentum_score:.3f}  →  Verdict: {r.verdict}")
        return lines
