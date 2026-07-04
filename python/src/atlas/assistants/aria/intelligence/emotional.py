"""
ARIA Emotional Intelligence Module
==================================
Assesses market sentiment and user emotional state.
Adjusts communication tone accordingly.

Features:
- Market mood classification (EUPHORIA → PANIC spectrum)
- User mood detection from recent messages
- Tone guidance generation
- Context-aware communication adjustment

This module uses simple keyword and metric-based analysis
(no additional LLM calls required).

Usage:
    ei = EmotionalIntelligence()
    market_mood = ei.assess_market_mood(market_data)
    user_mood = ei.assess_user_mood(recent_messages)
    tone = ei.get_tone_adjustment(market_mood, user_mood)
    print(f"Recommend: {tone.recommendation}")

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

logger = logging.getLogger("atlas.aria.intelligence.emotional")


# ── Enumerations ──────────────────────────────────────────────────────────────

class MarketMood(str, Enum):
    """Market sentiment state."""
    EUPHORIA = "euphoria"      # Extreme optimism (20% gain, VIX < 10)
    OPTIMISM = "optimism"      # Positive sentiment (5% gain, VIX < 15)
    NEUTRAL = "neutral"        # Balanced (±3%, VIX 15-20)
    ANXIETY = "anxiety"        # Worry, uncertainty (5% loss, VIX 20-25)
    FEAR = "fear"              # Significant fear (10% loss, VIX > 25)
    PANIC = "panic"            # Extreme panic (>15% loss, VIX > 40)


class UserMood(str, Enum):
    """User emotional state."""
    ENTHUSIASTIC = "enthusiastic"  # Excited, bullish
    CONFIDENT = "confident"        # Assured, taking action
    CURIOUS = "curious"            # Inquisitive, exploring
    WORRIED = "worried"            # Anxious, concerned
    FRUSTRATED = "frustrated"      # Upset, negative
    NEUTRAL = "neutral"            # Matter-of-fact


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class ToneGuidance:
    """Guidance for tone adjustment."""
    market_mood: MarketMood
    user_mood: UserMood
    recommendation: str
    cautions: List[str]
    encouragements: List[str]
    communication_style: str
    risk_emphasis: str  # "high", "medium", "low"
    optimism_level: float  # 0-1 scale

    def get_system_prompt_addition(self) -> str:
        """Generate system prompt text based on tone guidance."""
        lines = [
            "## Emotional Context",
            f"Market Mood: {self.market_mood.value}",
            f"User Mood: {self.user_mood.value}",
            "",
            f"Communication Style: {self.communication_style}",
            "",
        ]

        if self.cautions:
            lines.append("Cautions:")
            for caution in self.cautions:
                lines.append(f"  - {caution}")
            lines.append("")

        if self.encouragements:
            lines.append("Encouragements:")
            for enc in self.encouragements:
                lines.append(f"  - {enc}")
            lines.append("")

        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  EmotionalIntelligence
# ══════════════════════════════════════════════════════════════════════════════

class EmotionalIntelligence:
    """
    Assesses emotional context and adjusts communication accordingly.

    Uses simple keyword-based and metric-based analysis:
    - Market mood from price action, VIX, breadth
    - User mood from message sentiment keywords
    - Generates contextual tone guidance
    """

    def __init__(self):
        """Initialize emotional intelligence module."""
        # Market sentiment keywords
        self.bullish_terms = {
            "buy", "strong", "bullish", "optimistic", "green", "rally", "surge",
            "breakout", "momentum", "hot", "explosive", "gain", "profit", "win"
        }

        self.bearish_terms = {
            "sell", "weak", "bearish", "pessimistic", "red", "crash", "plunge",
            "collapse", "breakdown", "stall", "loss", "risk", "caution", "fear"
        }

        # User sentiment keywords
        self.positive_keywords = {
            "excited", "enthusiastic", "confident", "bullish", "optimistic",
            "great", "excellent", "winning", "perfect", "amazing", "love"
        }

        self.negative_keywords = {
            "worried", "frustrated", "angry", "upset", "bearish", "pessimistic",
            "terrible", "awful", "hate", "lost", "fail", "wrong"
        }

        self.uncertain_keywords = {
            "confused", "unsure", "uncertain", "question", "help", "understand",
            "what", "how", "why", "maybe", "perhaps"
        }

        logger.info("EmotionalIntelligence module initialized")

    # ── Market Assessment ─────────────────────────────────────────────────────

    def assess_market_mood(self, data: Dict[str, Any]) -> MarketMood:
        """
        Assess overall market mood from data.

        Args:
            data: Market data dict with keys like vix, price_change, breadth

        Returns:
            MarketMood enum
        """
        try:
            # Extract key metrics
            vix = data.get("vix", 20.0)
            price_change = data.get("price_change_percent", 0.0)  # -100 to +100
            breadth = data.get("advance_decline_ratio", 0.5)  # 0-1, >0.5 is bullish
            momentum = data.get("momentum", 0.0)  # -1 to 1

            # Calculate mood score
            mood_score = 0.0

            # VIX contribution (inverse - high VIX = negative)
            if vix < 10:
                mood_score += 1.0
            elif vix < 15:
                mood_score += 0.5
            elif vix < 20:
                mood_score += 0.0
            elif vix < 25:
                mood_score -= 0.3
            elif vix < 40:
                mood_score -= 0.6
            else:
                mood_score -= 1.0

            # Price change contribution
            if price_change > 20:
                mood_score += 1.0
            elif price_change > 10:
                mood_score += 0.6
            elif price_change > 5:
                mood_score += 0.3
            elif price_change > 0:
                mood_score += 0.1
            elif price_change > -5:
                mood_score -= 0.1
            elif price_change > -10:
                mood_score -= 0.4
            elif price_change > -15:
                mood_score -= 0.7
            else:
                mood_score -= 1.0

            # Breadth contribution
            if breadth > 0.7:
                mood_score += 0.3
            elif breadth < 0.3:
                mood_score -= 0.3

            # Momentum contribution
            mood_score += momentum * 0.4

            # Classify mood based on score
            if mood_score > 0.6:
                return MarketMood.EUPHORIA
            elif mood_score > 0.3:
                return MarketMood.OPTIMISM
            elif mood_score > -0.3:
                return MarketMood.NEUTRAL
            elif mood_score > -0.6:
                return MarketMood.ANXIETY
            elif mood_score > -0.8:
                return MarketMood.FEAR
            else:
                return MarketMood.PANIC

        except Exception as e:
            logger.warning(f"Error assessing market mood: {e}")
            return MarketMood.NEUTRAL

    # ── User Assessment ──────────────────────────────────────────────────────

    def assess_user_mood(self, recent_messages: List[str]) -> UserMood:
        """
        Assess user mood from recent messages.

        Args:
            recent_messages: List of recent user queries/statements

        Returns:
            UserMood enum
        """
        if not recent_messages:
            return UserMood.NEUTRAL

        try:
            # Combine messages
            combined_text = " ".join(recent_messages).lower()

            # Count sentiment signals
            positive_count = sum(1 for term in self.positive_keywords if term in combined_text)
            negative_count = sum(1 for term in self.negative_keywords if term in combined_text)
            uncertain_count = sum(1 for term in self.uncertain_keywords if term in combined_text)

            bullish_count = sum(1 for term in self.bullish_terms if term in combined_text)
            bearish_count = sum(1 for term in self.bearish_terms if term in combined_text)

            # Determine mood
            if positive_count > negative_count and bullish_count > bearish_count:
                return UserMood.ENTHUSIASTIC
            elif positive_count > negative_count and uncertain_count == 0:
                return UserMood.CONFIDENT
            elif uncertain_count >= 2 or uncertain_count > positive_count:
                return UserMood.CURIOUS
            elif negative_count > positive_count and bearish_count > bullish_count:
                return UserMood.FRUSTRATED
            elif negative_count > positive_count:
                return UserMood.WORRIED
            else:
                return UserMood.NEUTRAL

        except Exception as e:
            logger.warning(f"Error assessing user mood: {e}")
            return UserMood.NEUTRAL

    # ── Tone Adjustment ──────────────────────────────────────────────────────

    def get_tone_adjustment(
        self,
        market_mood: MarketMood,
        user_mood: UserMood,
    ) -> ToneGuidance:
        """
        Generate tone guidance based on market and user mood.

        Args:
            market_mood: Current market sentiment
            user_mood: Current user emotional state

        Returns:
            ToneGuidance with recommendations
        """
        # Initialize guidance components
        recommendation = ""
        cautions = []
        encouragements = []
        communication_style = ""
        risk_emphasis = "medium"
        optimism_level = 0.5

        # ── Market Mood Effects ───────────────────────────────────────────────

        if market_mood == MarketMood.EUPHORIA:
            cautions.append("Market euphoria detected - remind user that excess can precede reversals")
            cautions.append("Emphasize position sizing and risk management")
            risk_emphasis = "high"
            optimism_level = 0.3
            communication_style = "Measured, cautionary tone. Temper enthusiasm."

        elif market_mood == MarketMood.OPTIMISM:
            encouragements.append("Market shows positive momentum - can discuss constructive ideas")
            optimism_level = 0.7
            communication_style = "Professional, balanced. Can be moderately positive."

        elif market_mood == MarketMood.NEUTRAL:
            communication_style = "Neutral, analytical. Focus on facts and probability."
            optimism_level = 0.5

        elif market_mood == MarketMood.ANXIETY:
            cautions.append("Market showing signs of stress - increased volatility likely")
            cautions.append("Emphasize hedging and risk reduction")
            risk_emphasis = "high"
            communication_style = "Measured, reassuring. Acknowledge uncertainty."

        elif market_mood == MarketMood.FEAR:
            cautions.append("Market in fear - this is not the time for aggressive positioning")
            cautions.append("Suggest defensive strategies and capital preservation")
            cautions.append("Many investors at emotional extremes - stay disciplined")
            risk_emphasis = "high"
            optimism_level = 0.2
            communication_style = "Calm, steadying. Acknowledge fear, but provide perspective."

        elif market_mood == MarketMood.PANIC:
            cautions.append("MARKET PANIC - Extreme volatility and forced liquidations likely")
            cautions.append("This is a time for caution, not aggression")
            cautions.append("Focus on preservation of capital and avoiding forced sales")
            encouragements.append("Historically, panic creates long-term opportunities for prepared investors")
            risk_emphasis = "high"
            optimism_level = 0.1
            communication_style = "Calm, thoughtful, historical perspective. Stabilizing tone."

        # ── User Mood Effects ────────────────────────────────────────────────

        if user_mood == UserMood.ENTHUSIASTIC:
            encouragements.append("User is engaged and excited - channel into structured analysis")
            encouragements.append("This is a good time for research and strategy development")
            optimism_level = min(1.0, optimism_level + 0.2)

        elif user_mood == UserMood.CONFIDENT:
            encouragements.append("User is confident - provide quality analysis to support good decisions")
            optimism_level = min(1.0, optimism_level + 0.15)

        elif user_mood == UserMood.CURIOUS:
            encouragements.append("User is asking questions - provide thorough, educational responses")
            communication_style = "Detailed, educational. Take time to explain concepts."

        elif user_mood == UserMood.WORRIED:
            cautions.append("User is worried - avoid aggressive recommendations")
            cautions.append("Focus on risk management and downside scenarios")
            communication_style = "Reassuring, methodical. Address concerns directly."
            risk_emphasis = "high"

        elif user_mood == UserMood.FRUSTRATED:
            cautions.append("User appears frustrated - be especially careful with recommendations")
            cautions.append("Acknowledge challenges and provide honest assessment")
            communication_style = "Empathetic, straightforward. Validate concerns."

        elif user_mood == UserMood.NEUTRAL:
            communication_style = "Professional, balanced. Data-driven recommendations."

        # ── Generate Recommendation ───────────────────────────────────────────

        mood_summary = f"{market_mood.value} market / {user_mood.value} user"
        recommendation = self._generate_recommendation(market_mood, user_mood)

        return ToneGuidance(
            market_mood=market_mood,
            user_mood=user_mood,
            recommendation=recommendation,
            cautions=cautions,
            encouragements=encouragements,
            communication_style=communication_style,
            risk_emphasis=risk_emphasis,
            optimism_level=optimism_level,
        )

    def _generate_recommendation(
        self,
        market_mood: MarketMood,
        user_mood: UserMood,
    ) -> str:
        """Generate personalized recommendation based on moods."""
        recommendations = {
            (MarketMood.EUPHORIA, UserMood.ENTHUSIASTIC): "Cap position sizes and take profits",
            (MarketMood.EUPHORIA, UserMood.CONFIDENT): "Reduce new risk taking",
            (MarketMood.EUPHORIA, UserMood.CURIOUS): "Study mean reversion patterns",
            (MarketMood.OPTIMISM, UserMood.ENTHUSIASTIC): "Can increase positions in quality names",
            (MarketMood.OPTIMISM, UserMood.CURIOUS): "Good time to research new opportunities",
            (MarketMood.PANIC, UserMood.WORRIED): "Focus on cash and stability, avoid decisions",
            (MarketMood.PANIC, UserMood.FRUSTRATED): "Step back and reassess strategy",
            (MarketMood.FEAR, UserMood.WORRIED): "Maintain defensive posture, be patient",
        }

        # Try exact match first
        key = (market_mood, user_mood)
        if key in recommendations:
            return recommendations[key]

        # Fall back to market-mood-only recommendations
        market_only = {
            MarketMood.EUPHORIA: "Reduce risk, take profits, prepare for correction",
            MarketMood.OPTIMISM: "Good environment for constructive investing",
            MarketMood.NEUTRAL: "Stay disciplined, follow your plan",
            MarketMood.ANXIETY: "Hedge exposed positions, increase scrutiny",
            MarketMood.FEAR: "Opportunities emerge from fear - stay prepared",
            MarketMood.PANIC: "Capital preservation is paramount - avoid forced decisions",
        }

        return market_only.get(market_mood, "Maintain discipline and follow your plan")

    # ── Utilities ─────────────────────────────────────────────────────────────

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text.

        Returns:
            Dict with bullish, bearish, uncertain scores (0-1)
        """
        text_lower = text.lower()

        bullish = sum(1 for term in self.bullish_terms if term in text_lower)
        bearish = sum(1 for term in self.bearish_terms if term in text_lower)
        uncertain = sum(1 for term in self.uncertain_keywords if term in text_lower)

        total = max(1, bullish + bearish + uncertain)

        return {
            "bullish": bullish / total,
            "bearish": bearish / total,
            "uncertain": uncertain / total,
        }

    def get_market_mood_explanation(self, mood: MarketMood) -> str:
        """Get human-readable explanation of market mood."""
        explanations = {
            MarketMood.EUPHORIA: (
                "Market is experiencing extreme euphoria. Prices have surged significantly, "
                "VIX is very low, and sentiment is extremely bullish. This is historically "
                "unsustainable and often precedes corrections."
            ),
            MarketMood.OPTIMISM: (
                "Market sentiment is positive with solid gains. Investors are confident "
                "but not complacent. Volatility is manageable. Good environment for growth."
            ),
            MarketMood.NEUTRAL: (
                "Market is balanced between buyers and sellers. Prices are stable with "
                "normal volatility. Sentiment is neither extremely bullish nor bearish."
            ),
            MarketMood.ANXIETY: (
                "Market is showing signs of stress and concern. Prices have declined "
                "modestly and volatility is elevated. Investors are becoming more cautious."
            ),
            MarketMood.FEAR: (
                "Market is gripped by fear. Significant declines and elevated volatility. "
                "Forced selling and panic are evident. Investors are extremely cautious."
            ),
            MarketMood.PANIC: (
                "Market is in panic mode. Severe selloffs, extremely elevated volatility, "
                "and widespread fear. This is an extreme state that typically doesn't last long "
                "but can cause significant damage if you're caught unprepared."
            ),
        }

        return explanations.get(mood, "Market mood unclear")
