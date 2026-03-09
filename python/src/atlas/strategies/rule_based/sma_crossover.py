"""
SMACrossoverStrategy — Rule-Based Engine

Classic dual-SMA crossover:
  signal =  1 when fast SMA crosses above slow SMA (bullish)
  signal = -1 when fast SMA crosses below slow SMA (bearish)
  signal =  0 otherwise (neutral / no position)

Registered as "sma_crossover" in StrategyRegistry.
"""

from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from atlas.strategies.base import BaseStrategy
from atlas.strategies.registry import StrategyRegistry


class SMACrossoverStrategy(BaseStrategy):
    """
    Dual Simple Moving Average crossover strategy.

    Args:
        fast: Period for the fast (short) SMA.  Default: 10
        slow: Period for the slow (long)  SMA.  Default: 30

    Signals are generated only after the slow SMA has enough data
    (i.e. after the first ``slow`` bars). Earlier rows are dropped.
    """

    def __init__(self, fast: int = 10, slow: int = 30):
        super().__init__(
            name="sma_crossover",
            description=f"Dual SMA crossover (fast={fast}, slow={slow})",
        )
        if fast >= slow:
            raise ValueError(
                f"fast ({fast}) must be strictly less than slow ({slow})."
            )
        self.fast = fast
        self.slow = slow

    # ── Core logic ────────────────────────────────────────────────────────────

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Args:
            data: OHLCV DataFrame with a 'close' column and datetime index.

        Returns:
            DataFrame with columns:
              'fast_ma'  — fast SMA values
              'slow_ma'  — slow SMA values
              'signal'   — int -1 / 0 / 1
        """
        close = data["close"]

        fast_ma = close.rolling(self.fast).mean()
        slow_ma = close.rolling(self.slow).mean()

        signals = pd.DataFrame(index=data.index)
        signals["fast_ma"] = fast_ma
        signals["slow_ma"] = slow_ma

        # Crossover logic: compare current vs previous bar
        signals["signal"] = 0
        signals.loc[fast_ma > slow_ma, "signal"] = 1
        signals.loc[fast_ma < slow_ma, "signal"] = -1

        # Drop NaN rows (warm-up period before slow SMA is available)
        return signals.dropna()

    def get_params(self) -> Dict[str, Any]:
        return {"fast": self.fast, "slow": self.slow}


# ── Auto-register ─────────────────────────────────────────────────────────────
StrategyRegistry.register("sma_crossover", SMACrossoverStrategy)
