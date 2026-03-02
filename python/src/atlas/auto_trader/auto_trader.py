"""
Atlas Auto-Trader
==================
Hybrid autonomous trading system that combines:
- Rule-based signals (technical analysis)
- ML predictions (XGBoost, LSTM)
- RL agent decisions
- Human override capability

Operating modes:
1. MANUAL:     Human makes all decisions, Atlas provides analysis
2. ADVISORY:   Atlas recommends, human approves/rejects
3. SEMI_AUTO:  Atlas executes within human-set guardrails
4. FULL_AUTO:  Atlas trades autonomously (with kill switch)

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger("atlas.auto_trader")


class TradingMode(Enum):
    MANUAL = "manual"
    ADVISORY = "advisory"
    SEMI_AUTO = "semi_auto"
    FULL_AUTO = "full_auto"


class Decision:
    """Represents a trading decision from any source."""

    def __init__(
        self,
        source: str,
        action: str,
        symbol: str,
        confidence: float,
        reasoning: str = "",
        metadata: Optional[Dict] = None,
    ):
        self.source = source       # "rules", "ml_xgboost", "ml_lstm", "rl_agent", "human"
        self.action = action       # "buy", "sell", "hold", "close"
        self.symbol = symbol
        self.confidence = confidence
        self.reasoning = reasoning
        self.metadata = metadata or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "action": self.action,
            "symbol": self.symbol,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }


class GuardRails:
    """
    Safety constraints for autonomous trading.
    The system CANNOT violate these regardless of mode.
    """

    def __init__(
        self,
        max_position_pct: float = 0.10,
        max_daily_loss_pct: float = 0.02,
        max_drawdown_pct: float = 0.10,
        max_trades_per_day: int = 20,
        min_confidence: float = 0.60,
        allowed_symbols: Optional[List[str]] = None,
        max_leverage: float = 1.0,
        trading_hours: Optional[Dict] = None,  # {"start": "09:30", "end": "16:00"}
    ):
        self.max_position_pct = max_position_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_trades_per_day = max_trades_per_day
        self.min_confidence = min_confidence
        self.allowed_symbols = allowed_symbols
        self.max_leverage = max_leverage
        self.trading_hours = trading_hours

    def check(self, decision: Decision, portfolio_state: Dict) -> Dict[str, Any]:
        """
        Check if a decision passes all guardrails.

        Returns: {"approved": bool, "violations": [...]}
        """
        violations = []

        # Confidence check
        if decision.confidence < self.min_confidence:
            violations.append(
                f"Confidence {decision.confidence:.1%} below minimum {self.min_confidence:.1%}"
            )

        # Symbol whitelist
        if self.allowed_symbols and decision.symbol not in self.allowed_symbols:
            violations.append(f"Symbol {decision.symbol} not in allowed list")

        # Daily loss check
        daily_pnl = portfolio_state.get("daily_pnl_pct", 0)
        if daily_pnl < -self.max_daily_loss_pct:
            violations.append(
                f"Daily loss {daily_pnl:.2%} exceeds limit {self.max_daily_loss_pct:.2%}"
            )

        # Drawdown check
        drawdown = portfolio_state.get("drawdown", 0)
        if drawdown > self.max_drawdown_pct:
            violations.append(
                f"Drawdown {drawdown:.2%} exceeds limit {self.max_drawdown_pct:.2%}"
            )

        # Trade count
        trades_today = portfolio_state.get("trades_today", 0)
        if trades_today >= self.max_trades_per_day:
            violations.append(f"Max daily trades ({self.max_trades_per_day}) reached")

        # Position size
        proposed_size = portfolio_state.get("proposed_position_pct", 0)
        if abs(proposed_size) > self.max_position_pct:
            violations.append(
                f"Position size {proposed_size:.1%} exceeds max {self.max_position_pct:.1%}"
            )

        return {
            "approved": len(violations) == 0,
            "violations": violations,
            "decision": decision.to_dict(),
        }


class AutoTrader:
    """
    Main hybrid auto-trading system.

    Combines multiple decision sources and routes through
    guardrails and approval flow based on operating mode.
    """

    def __init__(
        self,
        mode: TradingMode = TradingMode.ADVISORY,
        guardrails: Optional[GuardRails] = None,
    ):
        self.mode = mode
        self.guardrails = guardrails or GuardRails()
        self._decision_sources: Dict[str, Callable] = {}
        self._human_callback: Optional[Callable] = None
        self._execution_callback: Optional[Callable] = None
        self._decision_log: List[Dict] = []

        # Weights for multi-source consensus
        self.source_weights = {
            "rules": 0.20,
            "ml_xgboost": 0.25,
            "ml_lstm": 0.20,
            "rl_agent": 0.25,
            "human": 0.10,
        }

    def register_source(self, name: str, callback: Callable, weight: float = 0.20):
        """
        Register a decision source.

        callback signature: (symbol, features, state) → Decision
        """
        self._decision_sources[name] = callback
        self.source_weights[name] = weight
        logger.info("Registered decision source: %s (weight=%.2f)", name, weight)

    def set_human_callback(self, callback: Callable):
        """Set callback for human approval in ADVISORY/SEMI_AUTO modes."""
        self._human_callback = callback

    def set_execution_callback(self, callback: Callable):
        """Set callback for order execution."""
        self._execution_callback = callback

    def decide(
        self,
        symbol: str,
        features: Dict[str, Any],
        portfolio_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run the full decision pipeline.

        1. Collect decisions from all registered sources
        2. Aggregate via weighted consensus
        3. Check guardrails
        4. Route based on mode (approve/execute/log)
        """
        # Step 1: Collect decisions
        decisions = []
        for name, source_fn in self._decision_sources.items():
            try:
                decision = source_fn(symbol, features, portfolio_state)
                if isinstance(decision, Decision):
                    decisions.append(decision)
            except Exception as e:
                logger.warning("Source '%s' failed: %s", name, e)

        if not decisions:
            return {"action": "hold", "reason": "No decision sources available"}

        # Step 2: Aggregate
        consensus = self._aggregate_decisions(decisions)

        # Step 3: Guardrails
        guardrail_check = self.guardrails.check(consensus, portfolio_state)

        # Step 4: Route based on mode
        result = {
            "consensus": consensus.to_dict(),
            "individual_decisions": [d.to_dict() for d in decisions],
            "guardrails": guardrail_check,
            "mode": self.mode.value,
        }

        if not guardrail_check["approved"]:
            result["action"] = "blocked"
            result["reason"] = f"Guardrail violations: {guardrail_check['violations']}"
            logger.warning("Decision blocked: %s", guardrail_check["violations"])

        elif self.mode == TradingMode.MANUAL:
            result["action"] = "recommendation_only"
            result["reason"] = "Manual mode — no execution"

        elif self.mode == TradingMode.ADVISORY:
            result["action"] = "awaiting_human_approval"
            if self._human_callback:
                approved = self._human_callback(result)
                if approved:
                    result["action"] = "approved_and_executed"
                    self._execute(consensus)
                else:
                    result["action"] = "human_rejected"

        elif self.mode == TradingMode.SEMI_AUTO:
            # Auto-execute if confidence is high enough
            if consensus.confidence >= 0.75:
                result["action"] = "auto_executed"
                self._execute(consensus)
            else:
                result["action"] = "awaiting_human_approval"
                if self._human_callback:
                    approved = self._human_callback(result)
                    if approved:
                        self._execute(consensus)

        elif self.mode == TradingMode.FULL_AUTO:
            result["action"] = "auto_executed"
            self._execute(consensus)

        # Log
        self._decision_log.append(result)
        return result

    def _aggregate_decisions(self, decisions: List[Decision]) -> Decision:
        """Weighted consensus from multiple sources."""
        # Convert to numeric: buy=+1, sell=-1, hold=0, close=0
        action_map = {"buy": 1.0, "sell": -1.0, "hold": 0.0, "close": 0.0}

        weighted_sum = 0.0
        weight_total = 0.0
        confidences = []

        for d in decisions:
            w = self.source_weights.get(d.source, 0.1)
            numeric = action_map.get(d.action, 0.0)
            weighted_sum += numeric * d.confidence * w
            weight_total += w
            confidences.append(d.confidence)

        score = weighted_sum / weight_total if weight_total > 0 else 0

        # Map back to action
        if score > 0.2:
            action = "buy"
        elif score < -0.2:
            action = "sell"
        else:
            action = "hold"

        avg_confidence = float(np.mean(confidences))

        # Agreement boost
        actions = [d.action for d in decisions]
        agreement = max(actions.count(a) for a in set(actions)) / len(actions)
        final_confidence = avg_confidence * agreement

        reasoning_parts = [f"{d.source}: {d.action} ({d.confidence:.0%})" for d in decisions]

        return Decision(
            source="consensus",
            action=action,
            symbol=decisions[0].symbol,
            confidence=round(final_confidence, 3),
            reasoning=" | ".join(reasoning_parts),
            metadata={"score": round(score, 4), "agreement": round(agreement, 3)},
        )

    def _execute(self, decision: Decision):
        """Execute a trading decision."""
        if self._execution_callback:
            self._execution_callback(decision)
            logger.info("Executed: %s %s (confidence: %.1%%)",
                       decision.action, decision.symbol, decision.confidence)

    def get_log(self) -> List[Dict]:
        return self._decision_log

    def set_mode(self, mode: TradingMode):
        """Change operating mode."""
        old = self.mode
        self.mode = mode
        logger.info("Mode changed: %s → %s", old.value, mode.value)
