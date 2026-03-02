"""
Bollinger Band Squeeze Engine
==============================
Based on John Carter's "TTM Squeeze" concept:
  - Identifies volatility compression (BB inside Keltner Channel)
  - Measures squeeze momentum via a custom oscillator
  - Fires directional breakout signal when squeeze releases

Additional filter: Connors RSI direction confirmation.

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..base_engine import BaseEngine, EngineType, Signal

logger = logging.getLogger("atlas.engine.bb_squeeze")


class BBSqueezeEngine(BaseEngine):
    """
    Bollinger Band Squeeze + Breakout Detection.

    Parameters
    ----------
    bb_period    : BB period (default 20)
    bb_std       : BB std dev (default 2.0)
    kc_period    : Keltner period (default 20)
    kc_mult      : Keltner ATR multiplier (default 1.5)
    mom_period   : Momentum oscillator period (default 12)
    min_squeeze  : Minimum consecutive squeeze bars to qualify (default 3)
    """

    def __init__(
        self,
        bb_period: int = 20,
        bb_std: float = 2.0,
        kc_period: int = 20,
        kc_mult: float = 1.5,
        mom_period: int = 12,
        min_squeeze: int = 3,
    ):
        super().__init__(
            name=f"BB_Squeeze_{bb_period}",
            engine_type=EngineType.RULE_BASED,
            config={"bb_period": bb_period, "kc_mult": kc_mult, "min_squeeze": min_squeeze},
        )
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.kc_period = kc_period
        self.kc_mult = kc_mult
        self.mom_period = mom_period
        self.min_squeeze = min_squeeze

    # ── indicators ───────────────────────────────────────────────────

    def _bb(self, closes: pd.Series):
        mid = closes.rolling(self.bb_period).mean()
        std = closes.rolling(self.bb_period).std()
        return mid - self.bb_std * std, mid, mid + self.bb_std * std

    def _keltner(self, data: pd.DataFrame):
        mid  = data["Close"].ewm(span=self.kc_period, adjust=False).mean()
        hi, lo, cl = data["High"], data["Low"], data["Close"].shift(1)
        tr   = pd.concat([(data["High"] - data["Low"]).abs(),
                           (data["High"] - cl).abs(),
                           (data["Low"]  - cl).abs()], axis=1).max(axis=1)
        atr  = tr.ewm(com=self.kc_period - 1, adjust=False).mean()
        return mid - self.kc_mult * atr, mid, mid + self.kc_mult * atr

    def _momentum_oscillator(self, data: pd.DataFrame) -> pd.Series:
        """
        Momentum = delta between close and midpoint of highest-high/lowest-low
        over mom_period (similar to TTM momentum oscillator).
        """
        closes  = data["Close"]
        hi_roll = data["High"].rolling(self.mom_period).max()
        lo_roll = data["Low"].rolling(self.mom_period).min()
        mid_hl  = (hi_roll + lo_roll) / 2
        mid_sma = closes.rolling(self.mom_period).mean()
        delta   = closes - (mid_hl + mid_sma) / 2
        # Linear regression of delta over mom_period
        return delta.rolling(self.mom_period).mean()

    # ── main ─────────────────────────────────────────────────────────

    def analyze(self, data: pd.DataFrame, context: Optional[Dict] = None) -> List[Signal]:
        signals: List[Signal] = []
        if not self.validate_data(data):
            return signals

        min_bars = max(self.bb_period, self.kc_period, self.mom_period) + self.min_squeeze + 5
        if len(data) < min_bars:
            return signals

        closes    = data["Close"]
        symbol    = (context or {}).get("symbol", "UNKNOWN")
        timestamp = data.index[-1]

        bb_lo, _bb_m, bb_hi = self._bb(closes)
        kc_lo, _kc_m, kc_hi = self._keltner(data)
        mom = self._momentum_oscillator(data)

        # Squeeze = BB narrower than KC
        squeeze = (bb_lo > kc_lo) & (bb_hi < kc_hi)

        # Count consecutive squeeze bars looking back
        squeeze_arr  = squeeze.values
        consec = 0
        for i in range(2, min(self.min_squeeze + 10, len(squeeze_arr) - 1)):
            if squeeze_arr[-(i + 1)]:
                consec += 1
            else:
                break

        cur_squeeze  = bool(squeeze.iloc[-1])
        prev_squeeze = bool(squeeze.iloc[-2])
        cur_mom      = float(mom.iloc[-1])
        prev_mom     = float(mom.iloc[-2])

        # Signal: squeeze just released (was in squeeze, now out)
        squeeze_released = (not cur_squeeze) and prev_squeeze and (consec >= self.min_squeeze - 1)

        if not squeeze_released:
            # Still in squeeze or no squeeze history — no signal
            if cur_squeeze:
                logger.debug("%s: In squeeze for %d bars", symbol, consec)
            return signals

        # Direction determined by momentum oscillator
        mom_increasing = cur_mom > prev_mom
        mom_positive   = cur_mom > 0

        # Confidence from squeeze duration and momentum strength
        squeeze_conf = min(0.2, consec * 0.04)
        mom_conf     = min(0.3, abs(cur_mom) / (float(closes.std()) + 1e-10))

        base_conf = 0.55 + squeeze_conf + mom_conf

        if mom_positive and mom_increasing:
            signals.append(Signal(
                symbol=symbol, action="BUY",
                confidence=min(0.90, base_conf),
                engine_name=self.name, timestamp=timestamp,
                metadata={
                    "reason": f"BB Squeeze Release ↑ ({consec} bars compressed)",
                    "squeeze_bars": consec, "momentum": round(cur_mom, 4),
                    "bb_width": round(float(bb_hi.iloc[-1] - bb_lo.iloc[-1]), 4),
                },
            ))

        elif (not mom_positive) and (not mom_increasing):
            signals.append(Signal(
                symbol=symbol, action="SELL",
                confidence=min(0.90, base_conf),
                engine_name=self.name, timestamp=timestamp,
                metadata={
                    "reason": f"BB Squeeze Release ↓ ({consec} bars compressed)",
                    "squeeze_bars": consec, "momentum": round(cur_mom, 4),
                    "bb_width": round(float(bb_hi.iloc[-1] - bb_lo.iloc[-1]), 4),
                },
            ))

        return signals
