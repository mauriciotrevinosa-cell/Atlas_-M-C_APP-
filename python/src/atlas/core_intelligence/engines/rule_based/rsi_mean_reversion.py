"""
RSI Mean Reversion Engine
==========================
Buys extreme oversold conditions and sells extreme overbought conditions.
Confirmation layers: Bollinger Bands, Volume, and ADX filter.

Strategy Logic:
  BUY  when RSI < 30 AND price near/below BB lower AND volume above avg
  SELL when RSI > 70 AND price near/above BB upper AND volume above avg
  Filtered by: ADX < 25 (avoids trending markets where MR fails)

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from ..base_engine import BaseEngine, EngineType, Signal

logger = logging.getLogger("atlas.engine.rsi_mr")


class RSIMeanReversionEngine(BaseEngine):
    """
    RSI Mean-Reversion strategy with multi-factor confirmation.

    Parameters
    ----------
    rsi_period    : RSI lookback window (default 14)
    rsi_oversold  : RSI threshold to trigger BUY (default 30)
    rsi_overbought: RSI threshold to trigger SELL (default 70)
    bb_period     : Bollinger Band period (default 20)
    bb_std        : Bollinger Band std multiplier (default 2.0)
    vol_period    : Volume comparison period (default 20)
    adx_period    : ADX filter period (default 14)
    adx_max       : Max ADX to allow trade (avoids trending mkts, default 30)
    """

    def __init__(
        self,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        bb_period: int = 20,
        bb_std: float = 2.0,
        vol_period: int = 20,
        adx_period: int = 14,
        adx_max: float = 30.0,
    ):
        super().__init__(
            name=f"RSI_MR_{rsi_period}",
            engine_type=EngineType.RULE_BASED,
            config={
                "rsi_period": rsi_period, "rsi_oversold": rsi_oversold,
                "rsi_overbought": rsi_overbought, "bb_period": bb_period,
                "bb_std": bb_std, "adx_max": adx_max,
            },
        )
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.vol_period = vol_period
        self.adx_period = adx_period
        self.adx_max = adx_max

    # ── indicator helpers ─────────────────────────────────────────────

    @staticmethod
    def _rsi(closes: pd.Series, period: int) -> pd.Series:
        delta = closes.diff()
        gain = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
        loss = (-delta.clip(upper=0)).ewm(com=period - 1, adjust=False).mean()
        rs = gain / (loss + 1e-10)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _bollinger(closes: pd.Series, period: int, n_std: float):
        mid = closes.rolling(period).mean()
        std = closes.rolling(period).std()
        return mid - n_std * std, mid, mid + n_std * std

    @staticmethod
    def _adx(data: pd.DataFrame, period: int) -> pd.Series:
        hi, lo, cl = data["High"], data["Low"], data["Close"]
        prev_cl = cl.shift(1)
        tr = pd.concat([
            (hi - lo).abs(),
            (hi - prev_cl).abs(),
            (lo - prev_cl).abs(),
        ], axis=1).max(axis=1)

        dm_plus  = (hi - hi.shift(1)).clip(lower=0)
        dm_minus = (lo.shift(1) - lo).clip(lower=0)
        dm_plus  = dm_plus.where(dm_plus > dm_minus, 0)
        dm_minus = dm_minus.where(dm_minus > dm_plus, 0)

        atr   = tr.ewm(com=period - 1, adjust=False).mean()
        di_p  = 100 * dm_plus.ewm(com=period - 1, adjust=False).mean() / (atr + 1e-10)
        di_n  = 100 * dm_minus.ewm(com=period - 1, adjust=False).mean() / (atr + 1e-10)
        dx    = (100 * (di_p - di_n).abs() / (di_p + di_n + 1e-10))
        return dx.ewm(com=period - 1, adjust=False).mean()

    # ── main signal method ────────────────────────────────────────────

    def analyze(self, data: pd.DataFrame, context: Optional[Dict] = None) -> List[Signal]:
        signals: List[Signal] = []
        if not self.validate_data(data):
            return signals

        min_bars = max(self.rsi_period, self.bb_period, self.adx_period) + 5
        if len(data) < min_bars:
            return signals

        closes = data["Close"]
        symbol = (context or {}).get("symbol", "UNKNOWN")
        timestamp = data.index[-1]

        rsi     = self._rsi(closes, self.rsi_period)
        bb_lo, bb_mid, bb_hi = self._bollinger(closes, self.bb_period, self.bb_std)
        adx_val = self._adx(data, self.adx_period)
        vol_avg = data["Volume"].rolling(self.vol_period).mean()

        cur_rsi    = float(rsi.iloc[-1])
        cur_close  = float(closes.iloc[-1])
        cur_bb_lo  = float(bb_lo.iloc[-1])
        cur_bb_hi  = float(bb_hi.iloc[-1])
        cur_bb_mid = float(bb_mid.iloc[-1])
        cur_adx    = float(adx_val.iloc[-1])
        cur_vol    = float(data["Volume"].iloc[-1])
        avg_vol    = float(vol_avg.iloc[-1])

        # ADX filter: skip if strongly trending
        if cur_adx > self.adx_max:
            logger.debug("%s: ADX=%.1f > %.1f, skipping MR signal", symbol, cur_adx, self.adx_max)
            return signals

        vol_ok = cur_vol > avg_vol * 0.8  # mild volume confirmation

        # ── BUY signal ───────────────────────────────────────────────
        if cur_rsi < self.rsi_oversold and cur_close <= cur_bb_lo * 1.01:
            # Confidence: how extreme the oversold is + price position
            rsi_extreme   = (self.rsi_oversold - cur_rsi) / self.rsi_oversold
            price_extreme = max(0, (cur_bb_lo - cur_close) / (cur_bb_mid - cur_bb_lo + 1e-10))
            confidence    = min(0.9, 0.55 + rsi_extreme * 0.25 + price_extreme * 0.10 + (0.05 if vol_ok else 0))
            signals.append(Signal(
                symbol=symbol, action="BUY", confidence=confidence,
                engine_name=self.name, timestamp=timestamp,
                metadata={
                    "reason": "RSI Oversold + BB Lower Touch",
                    "rsi": round(cur_rsi, 1), "bb_lo": round(cur_bb_lo, 2),
                    "adx": round(cur_adx, 1), "vol_above_avg": vol_ok,
                },
            ))

        # ── SELL signal ──────────────────────────────────────────────
        elif cur_rsi > self.rsi_overbought and cur_close >= cur_bb_hi * 0.99:
            rsi_extreme   = (cur_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
            price_extreme = max(0, (cur_close - cur_bb_hi) / (cur_bb_hi - cur_bb_mid + 1e-10))
            confidence    = min(0.9, 0.55 + rsi_extreme * 0.25 + price_extreme * 0.10 + (0.05 if vol_ok else 0))
            signals.append(Signal(
                symbol=symbol, action="SELL", confidence=confidence,
                engine_name=self.name, timestamp=timestamp,
                metadata={
                    "reason": "RSI Overbought + BB Upper Touch",
                    "rsi": round(cur_rsi, 1), "bb_hi": round(cur_bb_hi, 2),
                    "adx": round(cur_adx, 1), "vol_above_avg": vol_ok,
                },
            ))

        return signals
