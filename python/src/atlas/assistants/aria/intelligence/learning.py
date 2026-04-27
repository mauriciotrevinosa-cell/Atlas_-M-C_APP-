"""
ARIA User Learning and Adaptation Engine
========================================
Learns user preferences, expertise level, and trading patterns.
Adapts ARIA's behavior to personalize responses and communication style.

Features:
- User profile building (assets, risk tolerance, expertise)
- Interaction tracking and pattern detection
- Dynamic personalization context generation
- JSON persistence for state preservation
- Tool preference learning

Usage:
    engine = UserLearningEngine()
    engine.track_interaction("What's VIX?", response, feedback)
    context = engine.get_personalization_context()

    # In system prompt:
    # "{personalization_context}"
    # Adapts tone, technical level, and tool suggestions

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("atlas.aria.intelligence.learning")


# ── Enumerations ──────────────────────────────────────────────────────────────

class RiskTolerance(str, Enum):
    """User risk tolerance level."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ExpertiseLevel(str, Enum):
    """User expertise level."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TimeFrame(str, Enum):
    """Preferred trading timeframe."""
    INTRADAY = "intraday"
    SHORT_TERM = "short_term"
    MEDIUM_TERM = "medium_term"
    LONG_TERM = "long_term"


class MarketSegment(str, Enum):
    """Market segments user focuses on."""
    EQUITIES = "equities"
    OPTIONS = "options"
    FIXED_INCOME = "fixed_income"
    COMMODITIES = "commodities"
    CRYPTO = "crypto"
    FOREX = "forex"


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class UserProfile:
    """User profile - updated through interactions."""
    user_id: str
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)

    # Preferences
    preferred_assets: List[str] = field(default_factory=list)  # e.g., ["AAPL", "NVDA"]
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    preferred_timeframes: List[TimeFrame] = field(default_factory=list)
    market_segments: List[MarketSegment] = field(default_factory=list)

    # Expertise
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    technical_languages_preferred: List[str] = field(default_factory=list)  # e.g., ["Python"]

    # Interaction patterns
    interaction_count: int = 0
    favorite_tools: Dict[str, int] = field(default_factory=dict)  # tool_name -> usage_count
    frequent_queries: List[str] = field(default_factory=list)
    average_query_complexity: float = 0.0  # 0-1 scale

    # Communication preferences
    prefers_technical_language: bool = False
    prefers_detailed_explanations: bool = True
    prefers_visual_aids: bool = True

    # Market interests
    favorite_assets: List[str] = field(default_factory=list)
    watched_assets: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> UserProfile:
        """Deserialize from dictionary."""
        # Convert enums
        if isinstance(data.get("risk_tolerance"), str):
            data["risk_tolerance"] = RiskTolerance(data["risk_tolerance"])
        if isinstance(data.get("expertise_level"), str):
            data["expertise_level"] = ExpertiseLevel(data["expertise_level"])

        # Convert lists of enums
        if data.get("preferred_timeframes"):
            data["preferred_timeframes"] = [
                TimeFrame(tf) if isinstance(tf, str) else tf
                for tf in data["preferred_timeframes"]
            ]
        if data.get("market_segments"):
            data["market_segments"] = [
                MarketSegment(ms) if isinstance(ms, str) else ms
                for ms in data["market_segments"]
            ]

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Interaction:
    """Record of user interaction."""
    timestamp: float
    query: str
    response: str
    tools_used: List[str] = field(default_factory=list)
    feedback: Optional[str] = None  # "positive", "negative", "neutral"
    complexity: float = 0.5  # 0-1


# ══════════════════════════════════════════════════════════════════════════════
#  UserLearningEngine
# ══════════════════════════════════════════════════════════════════════════════

class UserLearningEngine:
    """
    Learns from user interactions and adapts ARIA's behavior.

    Features:
    - Tracks interaction patterns
    - Updates user profile dynamically
    - Learns preferred tools and assets
    - Adjusts communication style
    - Persists state to JSON
    """

    def __init__(
        self,
        user_id: str = "default_user",
        profile_path: Optional[Path] = None,
    ):
        """
        Initialize learning engine.

        Args:
            user_id: User identifier
            profile_path: Path to save/load profiles (default: data/aria_user_profile.json)
        """
        self.user_id = user_id
        self.profile_path = profile_path or Path("data/aria_user_profile.json")
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create profile
        self.profile = self._load_profile()

        # Recent interactions (for pattern detection)
        self.recent_interactions: List[Interaction] = []

        # Complexity scoring keywords
        self.complexity_indicators = {
            "easy": ["what", "is", "simple", "basic", "explain"],
            "medium": ["analyze", "calculate", "compare", "technical"],
            "hard": ["optimize", "algorithm", "derivative", "stochastic", "framework"],
        }

        logger.info(f"UserLearningEngine initialized for user {user_id}")

    # ── Main API ──────────────────────────────────────────────────────────────

    def track_interaction(
        self,
        query: str,
        response: str,
        feedback: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
    ) -> None:
        """
        Track a user interaction to learn from it.

        Args:
            query: User's question
            response: ARIA's response
            feedback: Optional feedback ("positive", "negative", "neutral")
            tools_used: List of tools ARIA used
        """
        try:
            # Calculate complexity
            complexity = self._estimate_complexity(query)

            # Create interaction record
            interaction = Interaction(
                timestamp=time.time(),
                query=query,
                response=response,
                tools_used=tools_used or [],
                feedback=feedback,
                complexity=complexity,
            )

            self.recent_interactions.append(interaction)

            # Keep only recent interactions for memory
            if len(self.recent_interactions) > 100:
                self.recent_interactions = self.recent_interactions[-100:]

            # Update profile from interaction
            self._update_profile_from_interaction(interaction)

            # Save profile
            self._save_profile()

            logger.debug(f"Tracked interaction (complexity: {complexity:.2f})")

        except Exception as e:
            logger.warning(f"Error tracking interaction: {e}")

    def get_personalization_context(self) -> str:
        """
        Generate personalization context to inject into system prompt.

        Returns:
            String describing user preferences and style guidance
        """
        context_lines = []

        # Expertise level guidance
        context_lines.append("## User Profile Context\n")
        context_lines.append(f"User Expertise: {self.profile.expertise_level.value}")

        if self.profile.expertise_level == ExpertiseLevel.BEGINNER:
            context_lines.append(
                "Provide detailed explanations, avoid jargon, use analogies. "
                "Prioritize education and clarity."
            )
        elif self.profile.expertise_level == ExpertiseLevel.INTERMEDIATE:
            context_lines.append(
                "Use professional terminology but explain complex concepts. "
                "Balance depth with clarity."
            )
        elif self.profile.expertise_level in (ExpertiseLevel.ADVANCED, ExpertiseLevel.EXPERT):
            context_lines.append(
                "Use technical language freely. Can discuss advanced concepts, "
                "quantitative methods, and edge cases."
            )

        # Risk tolerance
        context_lines.append(f"\nRisk Tolerance: {self.profile.risk_tolerance.value}")
        if self.profile.risk_tolerance == RiskTolerance.CONSERVATIVE:
            context_lines.append(
                "Emphasize capital preservation and downside risk. "
                "Recommend hedging and defensive strategies."
            )
        elif self.profile.risk_tolerance == RiskTolerance.AGGRESSIVE:
            context_lines.append(
                "Can discuss leveraged strategies and concentrated positions. "
                "Focus on growth and return maximization."
            )

        # Preferred assets
        if self.profile.preferred_assets:
            assets_str = ", ".join(self.profile.preferred_assets[:5])
            context_lines.append(f"\nUser commonly analyzes: {assets_str}")

        # Tools preference
        if self.profile.favorite_tools:
            top_tools = sorted(
                self.profile.favorite_tools.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            tools_str = ", ".join(name for name, _ in top_tools)
            context_lines.append(f"User's favorite tools: {tools_str}")

        # Communication style
        context_lines.append("\n## Communication Style")
        if self.profile.prefers_detailed_explanations:
            context_lines.append("Provide thorough explanations with supporting reasoning.")
        else:
            context_lines.append("Keep responses concise and focused on key points.")

        if self.profile.prefers_technical_language:
            context_lines.append("Use technical terminology; assume financial background.")

        return "\n".join(context_lines)

    def suggest_next_action(self) -> Optional[str]:
        """
        Based on learning, suggest what ARIA should offer next.

        Returns:
            Suggested next action or None
        """
        if not self.recent_interactions:
            return None

        try:
            recent_query = self.recent_interactions[-1].query.lower()

            # Pattern-based suggestions
            if "risk" in recent_query:
                if "hedge" not in recent_query:
                    return "Would you like to discuss hedging strategies?"

            if "opportunity" in recent_query:
                if "entry" not in recent_query:
                    return "Should I analyze entry points for the opportunities identified?"

            if "analysis" in recent_query:
                if "forecast" not in recent_query:
                    return "Would you like me to forecast potential outcomes?"

            return None

        except Exception as e:
            logger.warning(f"Error suggesting action: {e}")
            return None

    # ── Profile Updates ───────────────────────────────────────────────────────

    def _update_profile_from_interaction(self, interaction: Interaction) -> None:
        """Update profile based on interaction."""
        # Update interaction count
        self.profile.interaction_count += 1

        # Update average complexity
        n = self.profile.interaction_count
        self.profile.average_query_complexity = (
            ((self.profile.average_query_complexity * (n - 1)) + interaction.complexity) / n
        )

        # Track tool usage
        for tool in interaction.tools_used:
            self.profile.favorite_tools[tool] = self.profile.favorite_tools.get(tool, 0) + 1

        # Extract assets from query
        self._extract_assets_from_query(interaction.query)

        # Estimate expertise level
        self._update_expertise_level(interaction)

        # Update last interaction time
        self.profile.last_updated = time.time()

    def _estimate_complexity(self, query: str) -> float:
        """Estimate query complexity (0-1)."""
        query_lower = query.lower()
        score = 0.3  # base

        # Count complexity indicators
        for level, keywords in self.complexity_indicators.items():
            for keyword in keywords:
                if keyword in query_lower:
                    if level == "easy":
                        score = min(1.0, score + 0.0)
                    elif level == "medium":
                        score = min(1.0, score + 0.2)
                    elif level == "hard":
                        score = min(1.0, score + 0.3)

        # Query length as indicator
        words = len(query_lower.split())
        if words > 20:
            score = min(1.0, score + 0.15)

        return score

    def _extract_assets_from_query(self, query: str) -> None:
        """Extract asset symbols from query and update profile."""
        # Simple pattern: look for known stock symbols (A-Z in uppercase)
        import re
        symbols = re.findall(r'\b([A-Z]{1,5})\b', query)

        for symbol in symbols:
            # Only track if looks like a real symbol (common tickers)
            if symbol not in ("I", "A", "THE", "AND", "OR", "IF", "IS"):
                if symbol not in self.profile.preferred_assets:
                    self.profile.preferred_assets.append(symbol)
                if symbol not in self.profile.watched_assets:
                    self.profile.watched_assets.append(symbol)

        # Keep only most relevant
        if len(self.profile.preferred_assets) > 20:
            self.profile.preferred_assets = self.profile.preferred_assets[-20:]

    def _update_expertise_level(self, interaction: Interaction) -> None:
        """Estimate expertise level from interaction patterns."""
        query_lower = interaction.query.lower()

        # Expertise indicators
        advanced_terms = {
            "greeks", "stochastic", "correlation", "covariance", "volatility surface",
            "implied volatility", "optimization", "algorithm", "monte carlo",
            "quantitative", "regression", "derivatives", "hedge ratio", "correlation decay"
        }

        beginner_terms = {
            "simple", "basic", "what is", "explain", "how do", "can you teach",
            "new", "start", "beginner", "learning"
        }

        advanced_count = sum(1 for term in advanced_terms if term in query_lower)
        beginner_count = sum(1 for term in beginner_terms if term in query_lower)

        # Update based on patterns
        if advanced_count >= 2:
            self.profile.expertise_level = ExpertiseLevel.ADVANCED
        elif advanced_count == 1:
            if self.profile.expertise_level in (ExpertiseLevel.BEGINNER, ExpertiseLevel.INTERMEDIATE):
                self.profile.expertise_level = ExpertiseLevel.INTERMEDIATE
        elif beginner_count >= 2:
            if self.profile.expertise_level == ExpertiseLevel.EXPERT:
                self.profile.expertise_level = ExpertiseLevel.ADVANCED
            else:
                self.profile.expertise_level = ExpertiseLevel.BEGINNER

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_profile(self) -> UserProfile:
        """Load user profile from disk, or create new one."""
        try:
            if self.profile_path.exists():
                with open(self.profile_path, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded profile for user {self.user_id}")
                    return UserProfile.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load profile: {e}")

        # Create new profile
        logger.info(f"Creating new profile for user {self.user_id}")
        return UserProfile(user_id=self.user_id)

    def _save_profile(self) -> None:
        """Save user profile to disk."""
        try:
            data = self.profile.to_dict()
            with open(self.profile_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            logger.debug(f"Profile saved to {self.profile_path}")
        except Exception as e:
            logger.warning(f"Failed to save profile: {e}")

    # ── Utilities ─────────────────────────────────────────────────────────────

    def get_profile_summary(self) -> Dict[str, Any]:
        """Get human-readable profile summary."""
        favorite_tools = sorted(
            self.profile.favorite_tools.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        return {
            "user_id": self.user_id,
            "interaction_count": self.profile.interaction_count,
            "expertise": self.profile.expertise_level.value,
            "risk_tolerance": self.profile.risk_tolerance.value,
            "avg_query_complexity": round(self.profile.average_query_complexity, 2),
            "favorite_assets": self.profile.preferred_assets[:5],
            "favorite_tools": [name for name, _ in favorite_tools],
        }

    def reset_profile(self) -> None:
        """Reset profile to defaults (useful for testing)."""
        self.profile = UserProfile(user_id=self.user_id)
        self._save_profile()
        logger.info("Profile reset to defaults")
