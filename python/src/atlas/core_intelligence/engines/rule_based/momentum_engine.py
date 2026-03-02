"""
Momentum & Trend Following Engine
===================================
Implements three momentum approaches combined into a single engine:

  1. Time-Series Momentum (TSMOM)
     Buy assets with positive returns over the past N months.
     Classic academic factor (Moskowitz, Ooi, Pedersen 2012).

  2. Dual Moving Average Trend
     Multiple MA alignment (SMA 20, 50, 200) — all aligned = strong trend.
     Confidence scaled by how many MAs agree.

  3. Volume-Price Trend (VPT)
     Cumulative volume weighted by price change direction.
     Rising VPT with price = confirmed trend. Divergence = weakness.

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..base_engine import BaseEngine, EngineType, Signal

logger = logging.getLogger("atlas.engine.momentum")


class MomentumEngine(BaseEngine):
    """
    Multi-approach momentum and trend engine.

    Parameters
    ----------
    tsmom_periods  : list of lookback periods for TSMOM (default [21, 63, 126])
    ma_periods     : SMA periods for alignment check (default [20, 50, 200])
    vpt_period     : VPT signal smoothing (default 14)
    min_score      : Minimum weighted score to generate signal (default 0.30)
    """

    def __init__(
        self,
        tsmom_periods: Optional[List[int]] = None,
        ma_periods: Optional[List[int]] = None,
        vpt_period: int = 14,
        min_score: float = 0.30,
    ):
        self.tsmom_periods = tsmom_periods or [21, 63, 126]
        self.ma_periods    = ma_periods    or [20, 50, 200]
        self.vpt_period    = vpt_period
        self.min_score     = min_score

        super().__init__(
            name="Momentum_MultiApproach",
            engine_type=EngineType.RULE_BASED,
            config={
                "tsmom_periods": self.tsmom_periods,
                "ma_periods": self.ma_periods,
            },
        )

    # ── helpers ──────────────────────────────────────────────────────

    def _tsmom_score(self, closes: pd.Series) -> float:
        """
        Time-Series Momentum score: average sign of returns across periods.
        Returns -1 to +1.
        """
        scores = []
        for p in self.tsmom_periods:
            if len(closes) > p:
                ret = (closes.iloc[-1] - closes.iloc[-p]) / closes.iloc[-p]
                # Risk-adjusted: scale by volatility
                rolling_vol = closes.pct_change().rolling(p).std().iloc[-1]
                if rolling_vol > 0:
                    scores.append(ret / rolling_vol)
        if not scores:
            return 0.0
        avg = float(np.mean(scores))
        return float(np.tanh(avg))  # squash to (-1, 1)

    def _ma_alignment_score(self, closes: pd.Series) -> float:
        """
        Moving average alignment score.
        Returns +1 (fully bullish) to -1 (fully bearish).
        """
        if len(closes) < max(self.ma_periods):
            return 0.0
        price = float(closes.iloc[-1])
        bullish = sum(1 for p in self.ma_periods
                      if price > float(closes.rolling(p).mean().iloc[-1]))
        total   = len(self.ma_periods)
        return (bullish / total) * 2 - 1  # -1 to +1

    def _ma_slope_score(self, closes: pd.Series) -> float:
        """
        Average slope of all MAs (normalized by price).
        Positive slope = upward trend.
        """
        slopes = []
        for p in self.ma_periods:
            if len(closes) > p + 5:
                ma = closes.rolling(p).mean()
                slope = (float(ma.iloc[-1]) - float(ma.iloc[-6])) / float(ma.iloc[-6] + 1e-10)
                slopes.append(slope)
        return float(np.mean(slopes)) if slopes else 0.0

    def _vpt_divergence(self, data: pd.DataFrame) -> float:
        """
        Volume-Price Trend divergence score.
        Returns +1 (confirming trend) to -1 (diverging from trend).
        """
        closes = data["Close"]
        volumes = data["Volume"]
        pct_chg = closes.pct_change()
        vpt = (volumes * pct_chg).cumsum()
        vpt_signal = vpt.rolling(self.vpt_period).mean()

        price_trend = float(closes.iloc[-1]) > float(closes.iloc[-self.vpt_period]) if len(closes) > self.vpt_period else True
        vpt_trend   = float(vpt.iloc[-1]) > float(vpt_signal.iloc[-1])

        if price_trend == vpt_trend:
            return 1.0   # Volume confirms price direction
        return -0.5      # Divergence — weaken signal

    # ── main ─────────────────────────────────────────────────────────

    def analyze(self, data: pd.DataFrame, context: Optional[Dict] = None) -> List[Signal]:
        signals: List[Signal] = []
        if not self.validate_data(data):
            return signals

        min_bars = max(max(self.tsmom_periods), max(self.ma_periods)) + 10
        if len(data) < min_bars:
            return signals

        closes    = data["Close"]
        symbol    = (context or {}).get("symbol", "UNKNOWN")
        timestamp = data.index[-1]

        # ── Component scores ─────────────────────────────────────────
        tsmom   = self._tsmom_score(closes)           # -1 to +1
        ma_aln  = self._ma_alignment_score(closes)    # -1 to +1
        ma_slp  = self._ma_slope_score(closes)        # small float, need to tanh
        ma_slp  = float(np.tanh(ma_slp * 50))        # scale + squash
        vpt_div = self._vpt_divergence(data)          # +1 or -0.5

        # Weighted composite score (weights sum to ~1)
        TSMOM_W, ALIGN_W, SLOPE_W, VPT_W = 0.35, 0.30, 0.20, 0.15
        score = (TSMOM_W * tsmom + ALIGN_W * ma_aln + SLOPE_W * ma_slp) * max(0.5, vpt_div)

        logger.debug(
            "%s: TSMOM=%.2f ALIGN=%.2f SLOPE=%.2f VPT=%.2f → score=%.3f",
            symbol, tsmom, ma_aln, ma_slp, vpt_div, score,
        )

        if abs(score) < self.min_score:
            return signals

        # Confidence: map score → [0.55, 0.90]
        confidence = min(0.92, 0.55 + abs(score) * 0.37)

        ma_values = {f"SMA{p}": round(float(closes.rolling(p).mean().iloc[-1]), 2)
                     for p in self.ma_periods}
        meta = {
            "tsmom_score": round(tsmom, 3),
            "ma_alignment": round(ma_aln, 3),
            "ma_slope": round(ma_slp, 3),
            "vpt_confirm": vpt_div > 0,
            "composite_score": round(score, 3),
            **ma_values,
        }

        if score > 0:
            signals.append(Signal(
                symbol=symbol, action="BUY", confidence=confidence,
                engine_name=self.name, timestamp=timestamp,
                metadata={"reason": "Multi-factor Bullish Momentum", **meta},
            ))
        else:
            signals.append(Signal(
                symbol=symbol, action="SELL", confidence=confidence,
                engine_name=self.name, timestamp=timestamp,
                metadata={"reason": "Multi-factor Bearish Momentum", **meta},
            ))

        return signals
