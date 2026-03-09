"""
BaseStrategy — Phase 4 Specialized Engines

Abstract base class for all Atlas trading strategies.
Inspired by Microsoft Qlib's BaseStrategy pattern (MIT License).

All strategies inherit from BaseStrategy and implement:
  generate_signals(data) → pd.DataFrame with a 'signal' column (-1 / 0 / 1)

Strategy types:
  Rule-Based   — technical indicator logic (SMA crossover, RSI levels)
  ML           — model predictions (LSTM, XGBoost)
  RL           — reinforcement learning actions (DQN)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class StrategySignal:
    """
    Single signal record produced by a strategy.

    Attributes:
        symbol:     Asset ticker, e.g. "BTC-USD"
        direction:  -1 (short) | 0 (neutral) | 1 (long)
        confidence: 0.0 – 1.0 confidence score (1.0 = maximum conviction)
        metadata:   Optional dict for extra info (indicator values, etc.)
    """
    symbol: str
    direction: int          # -1 / 0 / 1
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.direction not in (-1, 0, 1):
            raise ValueError(f"direction must be -1, 0, or 1 — got {self.direction}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1] — got {self.confidence}")


class BaseStrategy(ABC):
    """
    Abstract base for all Atlas strategies.

    Subclasses implement:
      generate_signals(data) — core signal logic

    Optional overrides:
      fit(data)              — train / calibrate (for ML/RL strategies)
      get_params()           — return hyper-parameter dict

    Example (rule-based)::

        class MySMAStrategy(BaseStrategy):
            def __init__(self, fast=10, slow=30):
                super().__init__(name="sma_crossover")
                self.fast = fast
                self.slow  = slow

            def generate_signals(self, data):
                fast_ma = data["close"].rolling(self.fast).mean()
                slow_ma = data["close"].rolling(self.slow).mean()
                signals = pd.DataFrame(index=data.index)
                signals["signal"] = 0
                signals.loc[fast_ma > slow_ma, "signal"] = 1
                signals.loc[fast_ma < slow_ma, "signal"] = -1
                return signals.dropna()
    """

    def __init__(self, name: str, description: str = ""):
        """
        Args:
            name:        Unique strategy identifier used in StrategyRegistry.
            description: Human-readable description shown in UI / logs.
        """
        self.name = name
        self.description = description
        self._fitted = False

    # ── Core interface ────────────────────────────────────────────────────────

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Compute signals for a DataFrame of OHLCV (or feature) data.

        Args:
            data: DataFrame with at minimum a 'close' column and datetime index.

        Returns:
            DataFrame with same index as ``data`` containing at least:
              'signal' column: int -1 / 0 / 1
        """
        ...

    def fit(self, data: pd.DataFrame, **kwargs) -> "BaseStrategy":
        """
        Optional: train or calibrate the strategy on historical data.

        Rule-based strategies can leave this as a no-op.
        ML/RL strategies must override this.

        Returns self for chaining.
        """
        self._fitted = True
        return self

    # ── Helpers ───────────────────────────────────────────────────────────────

    def get_params(self) -> Dict[str, Any]:
        """Return hyper-parameters as a dict (for logging / serialization)."""
        return {}

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
