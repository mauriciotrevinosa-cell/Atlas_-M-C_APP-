"""
ARIA Session Manager - Session state and working memory management.

Manages ARIA's working memory within a session: active context,
running calculations, tool results, and conversation summarization.

Copyright (c) 2026 M&C. All rights reserved.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

logger = logging.getLogger("atlas.aria.memory.session_manager")


@dataclass
class SessionState:
    """Current session state for ARIA."""
    session_id: str
    active_tickers: List[str] = field(default_factory=list)
    """Tickers currently being analyzed"""

    current_analysis: Dict[str, Any] = field(default_factory=dict)
    """Current analysis context (what ARIA is working on)"""

    last_tool_results: Dict[str, Any] = field(default_factory=dict)
    """Results from last tool executions"""

    conversation_summary: Optional[str] = None
    """Summary of conversation history for context window management"""

    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    """Session start timestamp"""

    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    """Last update timestamp"""

    context_window_used: int = 0
    """Estimated tokens used in LLM context window"""

    max_conversation_turns: int = 20
    """Max conversation turns to keep before summarization"""

    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "SessionState":
        """Create from dict."""
        return cls(**data)


class SessionManager:
    """
    Manages ARIA's session state and working memory.

    Tracks:
    - Active tickers and analysis context
    - Running tool executions and their results
    - Conversation context with automatic summarization
    - Session lifecycle

    Example::

        mgr = SessionManager()
        session = mgr.start_session()

        mgr.update_context("active_tickers", ["AAPL", "MSFT"])
        mgr.update_context("current_analysis", {
            "type": "valuation",
            "status": "in_progress"
        })

        mgr.add_tool_result("market_data", {"price": 150.25})
        summary = mgr.get_session_summary()
    """

    def __init__(self, persist_dir: str = "data/aria_sessions",
                 max_turns: int = 20):
        """
        Initialize session manager.

        Args:
            persist_dir: Directory for session persistence
            max_turns: Max conversation turns before summarization
        """
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.max_turns = max_turns
        self.current_session: Optional[SessionState] = None
        self.conversation_history: List[Dict] = []
        logger.info("Initialized SessionManager")

    def start_session(self) -> SessionState:
        """
        Start a new session.

        Returns:
            Initial SessionState
        """
        session_id = str(uuid4())
        self.current_session = SessionState(
            session_id=session_id,
            max_conversation_turns=self.max_turns,
        )
        self.conversation_history = []
        self._persist_session()
        logger.info(f"Started session {session_id}")
        return self.current_session

    def load_session(self, session_id: str) -> Optional[SessionState]:
        """
        Load a previous session by ID.

        Args:
            session_id: Session ID to load

        Returns:
            SessionState if found, None otherwise
        """
        session_file = self.persist_dir / f"{session_id}.json"

        if not session_file.exists():
            logger.warning(f"Session not found: {session_id}")
            return None

        try:
            with open(session_file, "r") as f:
                data = json.load(f)

            self.current_session = SessionState.from_dict(data)
            logger.info(f"Loaded session {session_id}")
            return self.current_session
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def update_context(self, key: str, value: Any) -> None:
        """
        Update current session context.

        Args:
            key: Context key (e.g., "active_tickers", "current_analysis")
            value: Value to set
        """
        if not self.current_session:
            logger.warning("No active session")
            return

        # Handle different context types
        if key == "active_tickers":
            if isinstance(value, list):
                self.current_session.active_tickers = value
            else:
                self.current_session.active_tickers = [value]

        elif key == "current_analysis":
            if isinstance(value, dict):
                self.current_session.current_analysis.update(value)
            else:
                self.current_session.current_analysis = {"data": value}

        else:
            # Generic context storage
            if not hasattr(self.current_session, "custom_context"):
                self.current_session.custom_context = {}
            self.current_session.custom_context[key] = value

        self.current_session.updated_at = datetime.utcnow().isoformat()
        self._persist_session()
        logger.debug(f"Updated context: {key}")

    def add_conversation_turn(self, role: str, content: str) -> None:
        """
        Add conversation message to session history.

        Automatically triggers summarization if too many turns.

        Args:
            role: "user" or "assistant"
            content: Message content
        """
        if not self.current_session:
            logger.warning("No active session")
            return

        self.conversation_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "role": role,
            "content": content,
        })

        # Summarize if too many turns
        if len(self.conversation_history) > self.max_turns:
            self._summarize_conversation()

        logger.debug(f"Added {role} message to conversation")

    def add_tool_result(self, tool_name: str, result: Any) -> None:
        """
        Store result from tool execution.

        Args:
            tool_name: Name of tool that was executed
            result: Result data
        """
        if not self.current_session:
            logger.warning("No active session")
            return

        self.current_session.last_tool_results[tool_name] = {
            "timestamp": datetime.utcnow().isoformat(),
            "result": result,
        }

        self.current_session.updated_at = datetime.utcnow().isoformat()
        self._persist_session()
        logger.debug(f"Stored result from tool: {tool_name}")

    def get_session_summary(self) -> str:
        """
        Get formatted summary of session for LLM context injection.

        Returns:
            Formatted session context string
        """
        if not self.current_session:
            return "No active session"

        lines = [
            "## Current Session Context:",
            f"Session ID: {self.current_session.session_id}",
            f"Started: {self.current_session.started_at}",
        ]

        if self.current_session.active_tickers:
            lines.append(f"Active Tickers: {', '.join(self.current_session.active_tickers)}")

        if self.current_session.current_analysis:
            lines.append("Current Analysis:")
            for key, value in self.current_session.current_analysis.items():
                lines.append(f"  - {key}: {value}")

        if self.current_session.last_tool_results:
            lines.append("Latest Tool Results:")
            for tool, data in self.current_session.last_tool_results.items():
                timestamp = data.get("timestamp", "")
                result_preview = str(data.get("result", ""))[:100]
                lines.append(f"  - {tool} ({timestamp}): {result_preview}...")

        if self.current_session.conversation_summary:
            lines.append(f"Conversation Summary: {self.current_session.conversation_summary}")

        return "\n".join(lines)

    def get_conversation_context(self) -> List[Dict]:
        """
        Get conversation history in LLM-ready format.

        Returns:
            List of conversation messages
        """
        return self.conversation_history.copy()

    def get_info(self) -> Dict:
        """Get session information."""
        if not self.current_session:
            return {"status": "no_active_session"}

        return {
            "session_id": self.current_session.session_id,
            "started_at": self.current_session.started_at,
            "updated_at": self.current_session.updated_at,
            "active_tickers": self.current_session.active_tickers,
            "conversation_turns": len(self.conversation_history),
            "has_analysis": bool(self.current_session.current_analysis),
            "tool_results_count": len(self.current_session.last_tool_results),
        }

    def clear_session(self) -> None:
        """Clear current session and history."""
        if self.current_session:
            logger.info(f"Cleared session {self.current_session.session_id}")

        self.current_session = None
        self.conversation_history = []

    def _summarize_conversation(self) -> None:
        """
        Summarize conversation history to manage context window.

        Keeps recent turns, summarizes older ones into a single entry.
        """
        if len(self.conversation_history) <= self.max_turns:
            return

        num_to_summarize = len(self.conversation_history) - (self.max_turns // 2)

        # Get messages to summarize
        to_summarize = self.conversation_history[:num_to_summarize]
        self.conversation_history = self.conversation_history[num_to_summarize:]

        # Create summary
        summary_text = self._create_summary(to_summarize)

        if self.current_session:
            self.current_session.conversation_summary = summary_text
            self.current_session.updated_at = datetime.utcnow().isoformat()
            self._persist_session()

        logger.info(f"Summarized {len(to_summarize)} conversation turns")

    @staticmethod
    def _create_summary(messages: List[Dict]) -> str:
        """
        Create summary of conversation messages.

        Args:
            messages: List of message dicts

        Returns:
            Summary string
        """
        if not messages:
            return ""

        # Extract key topics from messages
        topics = set()
        for msg in messages:
            content = msg.get("content", "").lower()

            # Simple keyword extraction
            if "stock" in content or "price" in content:
                topics.add("stock analysis")
            if "analysis" in content:
                topics.add("analysis")
            if "market" in content or "dow" in content or "spy" in content:
                topics.add("market data")
            if "tool" in content or "data" in content:
                topics.add("data retrieval")

        user_msgs = [m for m in messages if m.get("role") == "user"]
        assistant_msgs = [m for m in messages if m.get("role") == "assistant"]

        summary = f"Earlier conversation ({len(messages)} messages): "
        if topics:
            summary += f"Discussed {', '.join(sorted(topics))}. "

        summary += f"{len(user_msgs)} user messages, {len(assistant_msgs)} assistant responses."

        return summary

    def _persist_session(self) -> None:
        """Save current session to disk."""
        if not self.current_session:
            return

        try:
            session_file = self.persist_dir / f"{self.current_session.session_id}.json"
            with open(session_file, "w") as f:
                json.dump(self.current_session.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist session: {e}")

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count for text (rough approximation).

        Uses simple heuristic: ~4 chars per token.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4
