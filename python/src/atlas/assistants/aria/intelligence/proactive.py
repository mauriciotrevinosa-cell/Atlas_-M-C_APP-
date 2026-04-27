"""
ARIA Proactive Suggestion Engine
=================================
Analyzes market conditions and user context to generate proactive suggestions.

Features:
- Rule-based trigger detection
- Multiple suggestion types (risk alerts, opportunities, rebalancing, etc.)
- Configurable thresholds and cooldown periods
- Priority-weighted suggestion ranking
- Suggestion metadata for filtering and sorting

Usage:
    engine = ProactiveEngine()
    suggestions = engine.analyze_context(
        market_data=current_prices,
        portfolio=portfolio,
        recent_queries=chat_history
    )
    for suggestion in suggestions:
        print(f"[{suggestion.priority}] {suggestion.message}")

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("atlas.aria.intelligence.proactive")


# ── Suggestion Types ──────────────────────────────────────────────────────────

class SuggestionType(str, Enum):
    """Types of proactive suggestions."""
    RISK_ALERT = "risk_alert"              # Risk threshold exceeded
    OPPORTUNITY = "opportunity"            # Trading opportunity detected
    REBALANCE = "rebalance"               # Portfolio rebalancing needed
    NEWS_IMPACT = "news_impact"           # Important news detected
    ANOMALY = "anomaly"                   # Unusual market behavior
    PATTERN_DETECTED = "pattern_detected" # Technical pattern found
    PERFORMANCE = "performance"           # Portfolio performance update
    CORRELATION_CHANGE = "correlation_change"  # Correlation breakdown


class Priority(int, Enum):
    """Suggestion priority levels."""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    INFO = 1


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class Suggestion:
    """Proactive suggestion for user."""
    type: SuggestionType
    priority: Priority
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    suggested_action: Optional[str] = None
    confidence: float = 0.7
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "type": self.type.value,
            "priority": self.priority.value,
            "message": self.message,
            "data": self.data,
            "suggested_action": self.suggested_action,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
        }


@dataclass
class ContextAnalysis:
    """Analysis results from context examination."""
    market_health: str  # "healthy", "warning", "critical"
    portfolio_health: str  # "strong", "caution", "weak"
    risk_level: float  # 0-1
    opportunity_count: int
    alert_count: int
    metrics: Dict[str, float] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
#  ProactiveEngine
# ══════════════════════════════════════════════════════════════════════════════

class ProactiveEngine:
    """
    Generates proactive suggestions based on market and portfolio analysis.

    Configuration:
    - Thresholds for various triggers
    - Cooldown periods to prevent suggestion spam
    - Priority assignment logic
    - Suggestion filtering rules
    """

    # Default thresholds
    DEFAULT_THRESHOLDS = {
        "var_critical": 0.20,        # Value at risk critical threshold
        "var_warning": 0.15,         # Value at risk warning threshold
        "drawdown_critical": 0.25,   # Portfolio drawdown critical
        "drawdown_warning": 0.15,    # Portfolio drawdown warning
        "vix_alert": 25.0,          # VIX alert threshold
        "correlation_change_min": 0.20,  # Min correlation change to flag
        "volume_anomaly_factor": 2.0,    # Volume spike factor (2x = anomaly)
        "momentum_extreme": 0.8,    # Momentum extreme threshold
        "rsi_overbought": 70.0,     # RSI overbought
        "rsi_oversold": 30.0,       # RSI oversold
    }

    # Cooldown periods (seconds) to prevent suggestion spam
    DEFAULT_COOLDOWNS = {
        SuggestionType.RISK_ALERT: 300,      # 5 min
        SuggestionType.OPPORTUNITY: 600,     # 10 min
        SuggestionType.REBALANCE: 3600,      # 1 hour
        SuggestionType.NEWS_IMPACT: 300,     # 5 min
        SuggestionType.ANOMALY: 600,         # 10 min
        SuggestionType.PATTERN_DETECTED: 600,  # 10 min
        SuggestionType.PERFORMANCE: 900,     # 15 min
        SuggestionType.CORRELATION_CHANGE: 1800,  # 30 min
    }

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        cooldowns: Optional[Dict[SuggestionType, int]] = None,
    ):
        """
        Initialize proactive engine.

        Args:
            thresholds: Custom threshold values
            cooldowns: Custom cooldown periods (in seconds)
        """
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.cooldowns = {**self.DEFAULT_COOLDOWNS, **(cooldowns or {})}

        # Last suggestion timestamp by type (for cooldown)
        self.last_suggestion: Dict[SuggestionType, float] = {}

        # Suggestion history
        self.suggestion_history: List[Suggestion] = []

        logger.info("ProactiveEngine initialized with custom config")

    # ── Main API ──────────────────────────────────────────────────────────────

    def analyze_context(
        self,
        market_data: Optional[Dict[str, Any]] = None,
        portfolio: Optional[Dict[str, Any]] = None,
        recent_queries: Optional[List[str]] = None,
    ) -> List[Suggestion]:
        """
        Analyze market and portfolio context to generate suggestions.

        Args:
            market_data: Current market data (prices, indicators, etc.)
            portfolio: Current portfolio state (positions, weights, etc.)
            recent_queries: Recent user queries for context

        Returns:
            List of Suggestion objects, sorted by priority
        """
        suggestions: List[Suggestion] = []

        try:
            logger.info("Analyzing context for proactive suggestions")

            # Analyze market
            if market_data:
                market_suggestions = self._analyze_market(market_data)
                suggestions.extend(market_suggestions)

            # Analyze portfolio
            if portfolio:
                portfolio_suggestions = self._analyze_portfolio(portfolio, market_data)
                suggestions.extend(portfolio_suggestions)

            # Analyze user behavior
            if recent_queries:
                behavior_suggestions = self._analyze_user_behavior(recent_queries)
                suggestions.extend(behavior_suggestions)

            # Filter by cooldown
            suggestions = self._apply_cooldowns(suggestions)

            # Sort by priority
            suggestions.sort(key=lambda s: (s.priority.value, s.timestamp), reverse=True)

            # Store in history
            self.suggestion_history.extend(suggestions)

            logger.info(f"Generated {len(suggestions)} suggestions")
            return suggestions

        except Exception as e:
            logger.exception(f"Error analyzing context: {e}")
            return []

    # ── Market Analysis ───────────────────────────────────────────────────────

    def _analyze_market(self, market_data: Dict[str, Any]) -> List[Suggestion]:
        """Analyze market conditions for alerts and opportunities."""
        suggestions: List[Suggestion] = []

        try:
            # VIX analysis
            vix = market_data.get("vix")
            if vix and vix > self.thresholds["vix_alert"]:
                suggestions.append(Suggestion(
                    type=SuggestionType.RISK_ALERT,
                    priority=Priority.HIGH if vix > 30 else Priority.MEDIUM,
                    message=f"Market volatility elevated (VIX: {vix:.1f}). Consider defensive positioning.",
                    data={"vix": vix},
                    suggested_action="Review portfolio hedges and risk exposure",
                    confidence=0.85,
                ))

            # Momentum analysis
            momentum = market_data.get("market_momentum")
            if momentum:
                if momentum > self.thresholds["momentum_extreme"]:
                    suggestions.append(Suggestion(
                        type=SuggestionType.OPPORTUNITY,
                        priority=Priority.MEDIUM,
                        message="Strong market momentum detected. Consider increasing exposure to trending positions.",
                        data={"momentum": momentum},
                        suggested_action="Review trend-following strategies",
                        confidence=0.70,
                    ))
                elif momentum < -self.thresholds["momentum_extreme"]:
                    suggestions.append(Suggestion(
                        type=SuggestionType.RISK_ALERT,
                        priority=Priority.MEDIUM,
                        message="Negative market momentum detected. Risk management may be prudent.",
                        data={"momentum": momentum},
                        suggested_action="Review risk positions and hedges",
                        confidence=0.70,
                    ))

            # Volume anomaly
            volume_anomaly = market_data.get("volume_anomaly")
            if volume_anomaly and volume_anomaly > self.thresholds["volume_anomaly_factor"]:
                suggestions.append(Suggestion(
                    type=SuggestionType.ANOMALY,
                    priority=Priority.MEDIUM,
                    message=f"Unusual trading volume detected ({volume_anomaly:.1f}x normal). May indicate significant move ahead.",
                    data={"volume_anomaly": volume_anomaly},
                    suggested_action="Monitor for breakouts or reversals",
                    confidence=0.65,
                ))

            # Correlation breakdown
            correlation_change = market_data.get("correlation_change")
            if correlation_change and abs(correlation_change) > self.thresholds["correlation_change_min"]:
                suggestions.append(Suggestion(
                    type=SuggestionType.CORRELATION_CHANGE,
                    priority=Priority.HIGH,
                    message=f"Asset correlations shifting ({correlation_change:+.2f}). Portfolio diversification may be affected.",
                    data={"correlation_change": correlation_change},
                    suggested_action="Rebalance portfolio to restore diversification",
                    confidence=0.80,
                ))

        except Exception as e:
            logger.warning(f"Market analysis error: {e}")

        return suggestions

    # ── Portfolio Analysis ────────────────────────────────────────────────────

    def _analyze_portfolio(
        self,
        portfolio: Dict[str, Any],
        market_data: Optional[Dict[str, Any]] = None,
    ) -> List[Suggestion]:
        """Analyze portfolio for risk and rebalancing needs."""
        suggestions: List[Suggestion] = []

        try:
            # Value at Risk
            var = portfolio.get("var")
            if var:
                if var > self.thresholds["var_critical"]:
                    suggestions.append(Suggestion(
                        type=SuggestionType.RISK_ALERT,
                        priority=Priority.CRITICAL,
                        message=f"Portfolio VaR critically high ({var:.1%}). Immediate risk reduction recommended.",
                        data={"var": var},
                        suggested_action="Reduce position sizes or hedge with derivatives",
                        confidence=0.90,
                    ))
                elif var > self.thresholds["var_warning"]:
                    suggestions.append(Suggestion(
                        type=SuggestionType.RISK_ALERT,
                        priority=Priority.HIGH,
                        message=f"Portfolio VaR elevated ({var:.1%}). Consider taking some risk off the table.",
                        data={"var": var},
                        suggested_action="Review largest positions for trim candidates",
                        confidence=0.85,
                    ))

            # Drawdown
            drawdown = portfolio.get("drawdown", 0)
            if drawdown < -self.thresholds["drawdown_critical"]:
                suggestions.append(Suggestion(
                    type=SuggestionType.RISK_ALERT,
                    priority=Priority.CRITICAL,
                    message=f"Portfolio drawdown severe ({drawdown:.1%}). Consider rebalancing and reviewing strategy.",
                    data={"drawdown": drawdown},
                    suggested_action="Halt new trades, review strategy alignment",
                    confidence=0.95,
                ))
            elif drawdown < -self.thresholds["drawdown_warning"]:
                suggestions.append(Suggestion(
                    type=SuggestionType.RISK_ALERT,
                    priority=Priority.HIGH,
                    message=f"Portfolio drawdown notable ({drawdown:.1%}). Defensive positioning warranted.",
                    data={"drawdown": drawdown},
                    suggested_action="Increase cash allocation temporarily",
                    confidence=0.80,
                ))

            # Allocation drift
            allocation_drift = portfolio.get("allocation_drift")
            if allocation_drift and allocation_drift > 0.10:  # 10% drift
                suggestions.append(Suggestion(
                    type=SuggestionType.REBALANCE,
                    priority=Priority.MEDIUM,
                    message=f"Portfolio allocation drifted {allocation_drift:.1%}. Rebalancing may restore desired risk profile.",
                    data={"drift": allocation_drift},
                    suggested_action="Rebalance to target weights",
                    confidence=0.75,
                ))

            # Concentration risk
            largest_position = portfolio.get("largest_position_weight", 0)
            if largest_position > 0.20:  # 20% limit
                suggestions.append(Suggestion(
                    type=SuggestionType.RISK_ALERT,
                    priority=Priority.MEDIUM,
                    message=f"Portfolio concentration high ({largest_position:.1%} in largest position). Consider trimming.",
                    data={"concentration": largest_position},
                    suggested_action="Reduce position sizes to improve diversification",
                    confidence=0.70,
                ))

        except Exception as e:
            logger.warning(f"Portfolio analysis error: {e}")

        return suggestions

    # ── User Behavior Analysis ────────────────────────────────────────────────

    def _analyze_user_behavior(self, recent_queries: List[str]) -> List[Suggestion]:
        """Analyze user behavior patterns for insights."""
        suggestions: List[Suggestion] = []

        try:
            if not recent_queries:
                return suggestions

            # Frequency analysis
            query_text = " ".join(recent_queries).lower()

            # Risk-focused queries
            risk_keywords = ["risk", "loss", "var", "hedge", "exposure", "drawdown"]
            risk_count = sum(1 for kw in risk_keywords if kw in query_text)

            if risk_count > 3:
                suggestions.append(Suggestion(
                    type=SuggestionType.RISK_ALERT,
                    priority=Priority.MEDIUM,
                    message="You've been asking about risk management frequently. Consider running a risk audit.",
                    data={"risk_query_count": risk_count},
                    suggested_action="Run comprehensive risk analysis on portfolio",
                    confidence=0.65,
                ))

            # Opportunity-focused queries
            opp_keywords = ["opportunity", "buy", "undervalued", "entry", "bullish"]
            opp_count = sum(1 for kw in opp_keywords if kw in query_text)

            if opp_count > 3:
                suggestions.append(Suggestion(
                    type=SuggestionType.OPPORTUNITY,
                    priority=Priority.LOW,
                    message="You're exploring opportunities actively. Here are some candidates worth analyzing.",
                    data={"opportunity_query_count": opp_count},
                    suggested_action="Review screened opportunities for your criteria",
                    confidence=0.60,
                ))

        except Exception as e:
            logger.warning(f"User behavior analysis error: {e}")

        return suggestions

    # ── Cooldown Management ───────────────────────────────────────────────────

    def _apply_cooldowns(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Filter suggestions based on cooldown periods."""
        current_time = time.time()
        filtered = []

        for suggestion in suggestions:
            # Check if suggestion type is on cooldown
            last_time = self.last_suggestion.get(suggestion.type, 0)
            cooldown = self.cooldowns.get(suggestion.type, 0)

            if current_time - last_time >= cooldown:
                filtered.append(suggestion)
                self.last_suggestion[suggestion.type] = current_time
            else:
                logger.debug(
                    f"Suggestion type {suggestion.type} on cooldown "
                    f"({cooldown - (current_time - last_time):.0f}s remaining)"
                )

        return filtered

    # ── Utilities ─────────────────────────────────────────────────────────────

    def get_suggestion_summary(self) -> Dict[str, Any]:
        """Get summary of recent suggestions."""
        if not self.suggestion_history:
            return {
                "total_suggestions": 0,
                "by_type": {},
                "by_priority": {},
            }

        # Count by type
        by_type: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}

        for suggestion in self.suggestion_history[-100:]:  # Last 100
            type_val = suggestion.type.value
            priority_val = suggestion.priority.name
            by_type[type_val] = by_type.get(type_val, 0) + 1
            by_priority[priority_val] = by_priority.get(priority_val, 0) + 1

        return {
            "total_suggestions": len(self.suggestion_history),
            "recent_suggestions": len(self.suggestion_history[-100:]),
            "by_type": by_type,
            "by_priority": by_priority,
        }

    def clear_cooldowns(self) -> None:
        """Reset all cooldowns (useful for testing)."""
        self.last_suggestion = {}
        logger.info("All cooldowns cleared")

    def update_threshold(self, threshold_name: str, value: float) -> None:
        """Update a threshold value dynamically."""
        if threshold_name in self.thresholds:
            old_value = self.thresholds[threshold_name]
            self.thresholds[threshold_name] = value
            logger.info(f"Threshold {threshold_name}: {old_value} → {value}")
        else:
            logger.warning(f"Unknown threshold: {threshold_name}")
