"""
MACD Signal Engine
==================
Multi-signal MACD strategy with three independent entry triggers:
  1. Signal-line crossover  (fastest, most common)
  2. Zero-line crossover    (trend confirmation, slower)
  3. Histogram divergence   (early reversal warning)

All three signals are weighted and combined into a confidence score.
Volume and ATR filters prevent trading in quiet/low-momentum markets.

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..base_engine import BaseEngine, EngineType, Signal

logger = logging.getLogger("atlas.engine.macd")


class MACDEngine(BaseEngine):
    """
    MACD-based strategy engine with signal-line, zero-line, and divergence triggers.

    Parameters
    ----------
    fast, slow, signal : Standard MACD parameters (12, 26, 9)
    vol_period         : Volume confirmation lookback
    atr_period         : ATR period for volatility filter
    min_hist_change    : Minimum MACD histogram change to count divergence
    """

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        vol_period: int = 20,
        atr_period: int = 14,
        min_hist_change: float = 0.01,
    ):
        super().__init__(
            name=f"MACD_{fast}_{slow}_{signal}",
            engine_type=EngineType.RULE_BASED,
            config={"fast": fast, "slow": slow, "signal": signal},
        )
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.vol_period = vol_period
        self.atr_period = atr_period
        self.min_hist_change = min_hist_change

    # ── helpers ──────────────────────────────────────────────────────

    def _compute_macd(self, closes: pd.Series):
        ema_fast   = closes.ewm(span=self.fast,   adjust=False).mean()
        ema_slow   = closes.ewm(span=self.slow,   adjust=False).mean()
        macd_line  = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()
        histogram  = macd_line - signal_line
        return macd_line, signal_line, histogram

    @staticmethod
    def _atr(data: pd.DataFrame, period: int) -> pd.Series:
        hi, lo, cl = data["High"], data["Low"], data["Close"].shift(1)
        tr = pd.concat([(data["High"] - data["Low"]).abs(),
                         (data["High"] - cl).abs(),
                         (data["Low"]  - cl).abs()], axis=1).max(axis=1)
        return tr.ewm(com=period - 1, adjust=False).mean()

    # ── main ─────────────────────────────────────────────────────────

    def analyze(self, data: pd.DataFrame, context: Optional[Dict] = None) -> List[Signal]:
        signals: List[Signal] = []
        if not self.validate_data(data):
            return signals

        min_bars = self.slow + self.signal + 10
        if len(data) < min_bars:
            return signals

        closes    = data["Close"]
        symbol    = (context or {}).get("symbol", "UNKNOWN")
        timestamp = data.index[-1]

        macd, sig_line, hist = self._compute_macd(closes)
        atr     = self._atr(data, self.atr_period)
        vol_avg = data["Volume"].rolling(self.vol_period).mean()

        # Current and previous bar values
        m0, m1   = float(macd.iloc[-1]),      float(macd.iloc[-2])
        s0, s1   = float(sig_line.iloc[-1]),  float(sig_line.iloc[-2])
        h0, h1, h2 = float(hist.iloc[-1]),   float(hist.iloc[-2]), float(hist.iloc[-3])
        cur_atr  = float(atr.iloc[-1])
        cur_vol  = float(data["Volume"].iloc[-1])
        avg_vol  = float(vol_avg.iloc[-1])
        cur_price = float(closes.iloc[-1])

        # ATR-based price threshold (skip trades in tiny moves)
        if cur_atr / cur_price < 0.002:
            return signals

        vol_factor = min(1.4, cur_vol / (avg_vol + 1e-10))  # 0 → 1.4

        score_buy, score_sell = 0.0, 0.0
        reasons_buy, reasons_sell = [], []

        # ── Trigger 1: Signal-line crossover ────────────────────────
        # MACD crosses above signal line → BUY
        if m1 <= s1 and m0 > s0:
            strength = min(1.0, abs(m0 - s0) / (cur_atr + 1e-10) * 10)
            score_buy += 0.45 * strength
            reasons_buy.append(f"MACD crossover ↑ (gap={m0-s0:.4f})")

        # MACD crosses below signal line → SELL
        elif m1 >= s1 and m0 < s0:
            strength = min(1.0, abs(m0 - s0) / (cur_atr + 1e-10) * 10)
            score_sell += 0.45 * strength
            reasons_sell.append(f"MACD crossover ↓ (gap={s0-m0:.4f})")

        # ── Trigger 2: Zero-line crossover ──────────────────────────
        if m1 <= 0 and m0 > 0:
            score_buy += 0.30
            reasons_buy.append("MACD zero-line cross ↑")
        elif m1 >= 0 and m0 < 0:
            score_sell += 0.30
            reasons_sell.append("MACD zero-line cross ↓")

        # ── Trigger 3: Histogram momentum (divergence proxy) ─────────
        # Histogram growing from negative → positive momentum shift
        hist_change = h0 - h2
        if hist_change > self.min_hist_change and h0 < 0:
            score_buy += 0.25 * min(1.0, hist_change / (cur_atr + 1e-10))
            reasons_buy.append(f"Hist turning up Δ={hist_change:.4f}")
        elif hist_change < -self.min_hist_change and h0 > 0:
            score_sell += 0.25 * min(1.0, abs(hist_change) / (cur_atr + 1e-10))
            reasons_sell.append(f"Hist turning down Δ={hist_change:.4f}")

        # ── Combine and emit ─────────────────────────────────────────
        if score_buy > 0.30:
            confidence = min(0.92, score_buy * vol_factor * 0.9)
            signals.append(Signal(
                symbol=symbol, action="BUY", confidence=confidence,
                engine_name=self.name, timestamp=timestamp,
                metadata={
                    "reasons": reasons_buy, "macd": round(m0, 4),
                    "signal": round(s0, 4), "histogram": round(h0, 4),
                    "score": round(score_buy, 3), "vol_factor": round(vol_factor, 2),
                },
            ))

        elif score_sell > 0.30:
            confidence = min(0.92, score_sell * vol_factor * 0.9)
            signals.append(Signal(
                symbol=symbol, action="SELL", confidence=confidence,
                engine_name=self.name, timestamp=timestamp,
                metadata={
                    "reasons": reasons_sell, "macd": round(m0, 4),
                    "signal": round(s0, 4), "histogram": round(h0, 4),
                    "score": round(score_sell, 3), "vol_factor": round(vol_factor, 2),
                },
            ))

        return signals
