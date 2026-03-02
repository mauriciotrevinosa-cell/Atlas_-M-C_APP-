"""
Multi-Strategy Consensus Engine
================================
Runs ALL available rule-based engines and aggregates their signals
into a single weighted consensus signal.

Architecture:
  SMACrossover  → weight 0.15 (simple baseline)
  RSIMeanRevert → weight 0.25 (contrarian)
  MACDEngine    → weight 0.25 (trend-momentum)
  BBSqueeze     → weight 0.20 (volatility breakout)
  Momentum      → weight 0.15 (time-series + MA alignment)

Agreement multiplier: if N engines agree, confidence boosted.
Conflict detection: opposing signals reduce final confidence.

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..base_engine import BaseEngine, EngineType, Signal
from .sma_crossover       import SMACrossoverEngine
from .rsi_mean_reversion  import RSIMeanReversionEngine
from .macd_engine         import MACDEngine
from .bb_squeeze          import BBSqueezeEngine
from .momentum_engine     import MomentumEngine

logger = logging.getLogger("atlas.engine.multi_strategy")


class MultiStrategyEngine(BaseEngine):
    """
    Consensus engine that combines all rule-based strategies.

    Parameters
    ----------
    weights : dict mapping strategy name to weight (optional)
    min_confidence : Minimum confidence to emit a signal (default 0.50)
    require_agreement : N engines must agree for full-strength signal (default 2)
    """

    DEFAULT_WEIGHTS = {
        "sma": 0.15,
        "rsi_mr": 0.25,
        "macd": 0.25,
        "bb_squeeze": 0.20,
        "momentum": 0.15,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        min_confidence: float = 0.45,
        require_agreement: int = 2,
    ):
        super().__init__(
            name="MultiStrategy_Consensus",
            engine_type=EngineType.RULE_BASED,
            config={"weights": weights or self.DEFAULT_WEIGHTS},
        )
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)
        self.min_confidence = min_confidence
        self.require_agreement = require_agreement

        # Initialize sub-engines
        self._engines: Dict[str, Tuple[BaseEngine, float]] = {
            "sma":       (SMACrossoverEngine(fast_period=20, slow_period=50), self.weights.get("sma", 0.15)),
            "rsi_mr":    (RSIMeanReversionEngine(), self.weights.get("rsi_mr", 0.25)),
            "macd":      (MACDEngine(), self.weights.get("macd", 0.25)),
            "bb_squeeze": (BBSqueezeEngine(), self.weights.get("bb_squeeze", 0.20)),
            "momentum":  (MomentumEngine(), self.weights.get("momentum", 0.15)),
        }
        logger.info("MultiStrategy Engine initialized with %d sub-engines", len(self._engines))

    def analyze(self, data: pd.DataFrame, context: Optional[Dict] = None) -> List[Signal]:
        """Run all engines, aggregate into one consensus signal."""
        if not self.validate_data(data):
            return []

        symbol    = (context or {}).get("symbol", "UNKNOWN")
        timestamp = data.index[-1]

        # Collect signals from all engines
        all_signals: List[Tuple[str, Signal, float]] = []   # (key, signal, weight)
        engine_results: Dict[str, Optional[str]] = {}

        for key, (engine, weight) in self._engines.items():
            try:
                sigs = engine.analyze(data, context)
                if sigs:
                    sig = sigs[0]  # Take first signal per engine
                    all_signals.append((key, sig, weight))
                    engine_results[key] = sig.action
                else:
                    engine_results[key] = "HOLD"
            except Exception as exc:
                logger.warning("Engine %s failed: %s", key, exc)
                engine_results[key] = "HOLD"

        # ── Consensus calculation ────────────────────────────────────
        buy_weight  = sum(w for _, s, w in all_signals if s.action == "BUY")
        sell_weight = sum(w for _, s, w in all_signals if s.action == "SELL")
        hold_weight = sum(w for _, s, w in all_signals if s.action == "HOLD")

        # Count agreements
        buy_count  = sum(1 for _, s, _ in all_signals if s.action == "BUY")
        sell_count = sum(1 for _, s, _ in all_signals if s.action == "SELL")

        net_score = buy_weight - sell_weight  # positive = bullish, negative = bearish

        # Agreement multiplier
        max_agreement = max(buy_count, sell_count)
        agreement_mult = min(1.25, 1.0 + (max_agreement - 1) * 0.1)

        # Weighted average confidence
        if all_signals:
            avg_conf = float(np.average(
                [s.confidence for _, s, _ in all_signals],
                weights=[w for _, _, w in all_signals],
            ))
        else:
            avg_conf = 0.0

        # Final confidence = avg_conf * agreement_mult * |net_score boost|
        score_boost = min(1.15, 1.0 + abs(net_score) * 0.3)
        final_conf  = min(0.93, avg_conf * agreement_mult * score_boost)

        # Build metadata
        meta = {
            "engines": engine_results,
            "buy_weight": round(buy_weight, 3),
            "sell_weight": round(sell_weight, 3),
            "net_score": round(net_score, 3),
            "agreement": max_agreement,
            "signals_count": len(all_signals),
            "individual_signals": [
                {
                    "engine": k,
                    "action": s.action,
                    "confidence": round(s.confidence, 3),
                    "weight": round(w, 3),
                    "reasons": s.metadata.get("reason", s.metadata.get("reasons", "")),
                }
                for k, s, w in all_signals
            ],
        }

        # Only fire if enough engines agree and confidence is high enough
        if max_agreement < self.require_agreement or final_conf < self.min_confidence:
            return []

        if net_score > 0.05 and buy_count >= self.require_agreement:
            return [Signal(
                symbol=symbol, action="BUY", confidence=final_conf,
                engine_name=self.name, timestamp=timestamp,
                metadata={"reason": f"Consensus BUY ({buy_count}/{len(self._engines)} agree)", **meta},
            )]

        if net_score < -0.05 and sell_count >= self.require_agreement:
            return [Signal(
                symbol=symbol, action="SELL", confidence=final_conf,
                engine_name=self.name, timestamp=timestamp,
                metadata={"reason": f"Consensus SELL ({sell_count}/{len(self._engines)} agree)", **meta},
            )]

        return []

    def get_individual_signals(self, data: pd.DataFrame, context: Optional[Dict] = None) -> Dict[str, List[Signal]]:
        """Return raw signals from each engine (useful for UI display)."""
        result = {}
        for key, (engine, _) in self._engines.items():
            try:
                result[key] = engine.analyze(data, context)
            except Exception as e:
                result[key] = []
        return result

    def get_engine_names(self) -> List[str]:
        return list(self._engines.keys())
