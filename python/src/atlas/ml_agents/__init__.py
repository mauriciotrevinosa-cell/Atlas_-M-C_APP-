"""
ML Agents — Swarm Committee + ML Bridge
=========================================
Two parallel systems for autonomous trading intelligence:

1. SWARM COMMITTEE (Multi-Agent System):
   SwarmCoordinator — ARIA as CEO orchestrating specialized agents
   RiskAgent        — Capital preservation, VaR, drawdown, stress tests
   MomentumAgent    — Trend analysis, RSI, MACD, ADX, price momentum
   OptionsAgent     — IV surface, options flow, gamma walls, max pain

   Usage:
       from atlas.ml_agents import SwarmCoordinator
       coordinator = SwarmCoordinator()
       decision = coordinator.decide("AAPL", ohlcv_df)
       print(decision.summary())

2. ML SIGNAL BRIDGE (AutoTrader integration):
   MLSignalAdapter  — wraps an MLEngine, uses FeaturePipeline, returns Decision
   MLAgentBridge    — factory with pre-configured XGBoost, RF, and LSTM adapters
   make_ml_sources  — convenience to get source tuples for auto_trader.register_source()

   Usage:
       from atlas.ml_agents import MLAgentBridge
       bridge = MLAgentBridge()
       bridge.train_all(ohlcv_df)

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.ml_agents")


# ── Lazy imports so missing optional deps never crash the module ───────────────

def _import_ml_suite():
    try:
        from atlas.core_intelligence.engines.ml.ml_suite import (
            XGBoostEngine, RandomForestEngine, LSTMEngine, FeaturePipeline,
        )
        return XGBoostEngine, RandomForestEngine, LSTMEngine, FeaturePipeline
    except ImportError as e:
        logger.warning("ml_suite import failed (install xgboost/torch/sklearn): %s", e)
        return None, None, None, None


def _import_decision():
    try:
        from atlas.auto_trader.auto_trader import Decision
        return Decision
    except ImportError:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  MLSignalAdapter
# ══════════════════════════════════════════════════════════════════════════════

class MLSignalAdapter:
    """
    Wraps an MLEngine and adapts it to the AutoTrader decision-source protocol.

    When called as a callback (symbol, features_dict, portfolio_state) it:
      1. Pulls the 'ohlcv' DataFrame from features_dict
      2. Lower-cases column names for FeaturePipeline compatibility
      3. Builds features and runs predict_proba
      4. Maps prediction probabilities → 'buy' | 'sell' | 'hold'
      5. Returns a Decision object

    Gracefully falls back to HOLD (confidence=0.50) when:
      - ohlcv is missing / too short
      - model is not yet trained
      - any prediction error occurs
    """

    def __init__(self, engine, source_name: str, lookback: int = 20):
        self.engine      = engine
        self.source_name = source_name
        self.lookback    = lookback
        _, _, _, FeaturePipeline = _import_ml_suite()
        self.pipeline = FeaturePipeline(lookback=lookback) if FeaturePipeline else None

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
        """Lower-case OHLCV column names for FeaturePipeline."""
        return df.rename(columns={c: c.lower() for c in df.columns})

    def _hold(self, symbol: str, reason: str):
        Decision = _import_decision()
        if Decision is None:
            return None
        return Decision(
            source=self.source_name, action="hold",
            symbol=symbol, confidence=0.50, reasoning=reason,
        )

    # ── main callback ─────────────────────────────────────────────────────────

    def __call__(
        self,
        symbol: str,
        features: Dict[str, Any],
        portfolio_state: Dict[str, Any],
    ):
        """AutoTrader decision source: (symbol, features, state) → Decision."""
        Decision = _import_decision()
        if Decision is None:
            return self._hold(symbol, "auto_trader module unavailable")
        if self.pipeline is None:
            return self._hold(symbol, "FeaturePipeline unavailable")

        ohlcv: Optional[pd.DataFrame] = features.get("ohlcv")
        if ohlcv is None or len(ohlcv) < self.lookback + 10:
            return self._hold(symbol, "Insufficient OHLCV data")

        try:
            df   = self._normalize_cols(ohlcv)
            feat = self.pipeline.build_features(df)
            if len(feat) < 2:
                return self._hold(symbol, "Too few feature rows")

            X = feat.values[-1:].astype(float)

            if not self.engine.is_trained:
                return self._hold(symbol, "Model not yet trained")

            proba = self.engine.predict_proba(X)   # shape (1, n_classes)
            pred  = self.engine.predict(X)[0]

            if proba.shape[1] >= 2:
                up_prob   = float(proba[0, 1])
                down_prob = float(proba[0, 0])
                confidence = max(up_prob, down_prob)
            else:
                up_prob = down_prob = 0.50
                confidence = 0.50

            if pred == 1 and up_prob >= 0.55:
                action = "buy"
            elif pred == 0 and down_prob >= 0.55:
                action = "sell"
            else:
                action = "hold"

            return Decision(
                source=self.source_name,
                action=action,
                symbol=symbol,
                confidence=round(confidence, 3),
                reasoning=f"{self.source_name}: P(↑)={up_prob:.1%}  P(↓)={down_prob:.1%}",
                metadata={"proba": proba.tolist(), "pred_class": int(pred)},
            )

        except Exception as exc:
            logger.warning("%s prediction failed for %s: %s", self.source_name, symbol, exc)
            return self._hold(symbol, f"Prediction error: {exc}")

    # ── training ──────────────────────────────────────────────────────────────

    def train(
        self,
        ohlcv: pd.DataFrame,
        label_method: str = "direction",
    ) -> Dict[str, float]:
        """Train the wrapped engine on an OHLCV DataFrame."""
        if self.pipeline is None:
            return {"error": "FeaturePipeline not available"}
        df = self._normalize_cols(ohlcv)
        X, y, _ = self.pipeline.prepare(df, label_method)
        if len(X) < 40:
            return {"error": f"Need ≥40 feature rows, got {len(X)}"}
        return self.engine.train(X, y)


# ══════════════════════════════════════════════════════════════════════════════
#  MLAgentBridge
# ══════════════════════════════════════════════════════════════════════════════

class MLAgentBridge:
    """
    Factory that creates pre-configured MLSignalAdapters for all three ML models.

    Models are untrained at construction time; call train_all() before they
    produce actionable signals (until then they return neutral HOLDs).

    Usage:
        bridge = MLAgentBridge()
        bridge.train_all(ohlcv_df)

        trader = AutoTrader(...)
        for name, callback, weight in bridge.get_sources():
            trader.register_source(name, callback, weight)
    """

    DEFAULT_WEIGHTS: Dict[str, float] = {
        "ml_xgboost": 0.25,
        "ml_rf":      0.15,
        "ml_lstm":    0.20,
    }

    def __init__(self, lookback: int = 20):
        XGBoostEngine, RandomForestEngine, LSTMEngine, _ = _import_ml_suite()

        self.adapters: Dict[str, MLSignalAdapter] = {}
        self.weights  = dict(self.DEFAULT_WEIGHTS)

        if XGBoostEngine:
            self.adapters["ml_xgboost"] = MLSignalAdapter(
                XGBoostEngine(), "ml_xgboost", lookback
            )
        if RandomForestEngine:
            self.adapters["ml_rf"] = MLSignalAdapter(
                RandomForestEngine(), "ml_rf", lookback
            )
        if LSTMEngine:
            self.adapters["ml_lstm"] = MLSignalAdapter(
                LSTMEngine(sequence_length=lookback, epochs=30), "ml_lstm", lookback
            )

        if not self.adapters:
            logger.warning("No ML engines loaded — check optional dependencies.")

    # ── public API ────────────────────────────────────────────────────────────

    def train_all(
        self,
        ohlcv: pd.DataFrame,
        label_method: str = "direction",
    ) -> Dict[str, Dict[str, float]]:
        """
        Train all three ML engines on the provided OHLCV DataFrame.

        Parameters
        ----------
        ohlcv : DataFrame with Open/High/Low/Close/Volume columns (any case)
        label_method : 'direction' (binary up/down) | 'triple' (−1/0/+1)

        Returns dict of per-engine training metrics.
        """
        results: Dict[str, Dict] = {}
        for name, adapter in self.adapters.items():
            logger.info("Training %s ...", name)
            try:
                metrics = adapter.train(ohlcv, label_method)
                results[name] = metrics
                logger.info("%s complete: %s", name, metrics)
            except Exception as exc:
                logger.warning("%s training failed: %s", name, exc)
                results[name] = {"error": str(exc)}
        return results

    def get_sources(self) -> List[Tuple[str, Callable, float]]:
        """Return (name, callback, weight) tuples for AutoTrader.register_source."""
        return [
            (name, adapter, self.weights.get(name, 0.15))
            for name, adapter in self.adapters.items()
        ]

    def get_status(self) -> Dict[str, Dict]:
        """Return per-engine training status."""
        return {
            name: {
                "trained":    adapter.engine.is_trained,
                "model_type": type(adapter.engine).__name__,
            }
            for name, adapter in self.adapters.items()
        }


# ── Convenience helper ─────────────────────────────────────────────────────────

def make_ml_sources(lookback: int = 20) -> List[Tuple[str, Callable, float]]:
    """
    Create a fresh MLAgentBridge and return (name, callback, weight) tuples.

    Models are untrained — they return neutral HOLDs until bridge.train_all()
    is called. Register them first, then train when data is available.
    """
    return MLAgentBridge(lookback=lookback).get_sources()


# ── Swarm Exports ──────────────────────────────────────────────────────────────

try:
    from .swarm_coordinator import SwarmCoordinator, SwarmDecision, AgentVote
    from .risk_agent        import RiskAgent, RiskReport
    from .momentum_agent    import MomentumAgent, MomentumReport
    from .options_agent     import OptionsAgent, OptionsReport

    __all__ = [
        # Swarm committee
        "SwarmCoordinator", "SwarmDecision", "AgentVote",
        "RiskAgent",        "RiskReport",
        "MomentumAgent",    "MomentumReport",
        "OptionsAgent",     "OptionsReport",
        # ML bridge
        "MLSignalAdapter", "MLAgentBridge", "make_ml_sources",
    ]

except ImportError as _e:
    logger.warning("Swarm agents import failed (numpy/pandas may be missing): %s", _e)
    __all__ = ["MLSignalAdapter", "MLAgentBridge", "make_ml_sources"]
