"""
Enhanced Memory System — Short-term (conversation) + Long-term (persistent)

Architecture:
  - ShortTermMemory: In-memory conversation buffer (last N turns)
  - LongTermMemory: SQLite persistent store + optional vector embeddings
  - MemoryManager: Unified interface for both

Inspired by patterns from system-prompts repos and ARIA's existing memory.
"""

import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    """A single memory entry."""
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)
    category: str = "conversation"  # conversation, fact, preference, project


class ShortTermMemory:
    """
    In-memory conversation buffer.
    Holds the last N turns for context window management.
    """

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._buffer: List[MemoryEntry] = []

    def add(self, role: str, content: str, **metadata):
        """Add a message to short-term memory."""
        entry = MemoryEntry(
            role=role,
            content=content,
            metadata=metadata,
        )
        self._buffer.append(entry)

        # Trim oldest if over limit
        if len(self._buffer) > self.max_turns * 2:
            self._buffer = self._buffer[-self.max_turns * 2:]

    def get_messages(self, limit: Optional[int] = None) -> List[Dict]:
        """Get messages in OpenAI-compatible format."""
        entries = self._buffer[-(limit or self.max_turns * 2):]
        return [{"role": e.role, "content": e.content} for e in entries]

    def get_context_window(self) -> List[Dict]:
        """Get optimized context window for LLM."""
        return self.get_messages(self.max_turns * 2)

    def clear(self):
        """Clear short-term memory."""
        self._buffer.clear()

    def __len__(self):
        return len(self._buffer)


class LongTermMemory:
    """
    SQLite-backed persistent memory store.
    Stores facts, preferences, and important conversation excerpts.
    """

    def __init__(self, db_path: str = "data/atlas_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL DEFAULT 'fact',
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                importance REAL DEFAULT 0.5,
                created_at REAL NOT NULL,
                accessed_at REAL,
                access_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
            CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id);
        """)
        conn.commit()
        conn.close()

    def store_fact(self, content: str, category: str = "fact",
                   importance: float = 0.5, metadata: Dict = None):
        """Store a fact or piece of knowledge."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO memories (category, content, metadata, importance, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (category, content, json.dumps(metadata or {}), importance, time.time())
        )
        conn.commit()
        conn.close()

    def store_conversation(self, session_id: str, role: str, content: str,
                           metadata: Dict = None):
        """Store a conversation message persistently."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO conversations (session_id, role, content, timestamp, metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, role, content, time.time(), json.dumps(metadata or {}))
        )
        conn.commit()
        conn.close()

    def search_facts(self, query: str, category: Optional[str] = None,
                     limit: int = 10) -> List[Dict]:
        """
        Search stored facts by keyword.
        Simple LIKE-based search. For semantic search, use vector_db.
        """
        conn = sqlite3.connect(self.db_path)
        if category:
            cursor = conn.execute(
                """SELECT content, category, importance, metadata
                   FROM memories WHERE category = ? AND content LIKE ?
                   ORDER BY importance DESC LIMIT ?""",
                (category, f"%{query}%", limit)
            )
        else:
            cursor = conn.execute(
                """SELECT content, category, importance, metadata
                   FROM memories WHERE content LIKE ?
                   ORDER BY importance DESC LIMIT ?""",
                (f"%{query}%", limit)
            )

        results = [
            {
                "content": row[0],
                "category": row[1],
                "importance": row[2],
                "metadata": json.loads(row[3]),
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        return results

    def get_recent_conversations(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Get recent conversation messages from a session."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """SELECT role, content, timestamp FROM conversations
               WHERE session_id = ? ORDER BY id DESC LIMIT ?""",
            (session_id, limit)
        )
        results = [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in cursor.fetchall()
        ]
        conn.close()
        return list(reversed(results))

    def get_stats(self) -> Dict:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        facts = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        convos = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        categories = conn.execute(
            "SELECT category, COUNT(*) FROM memories GROUP BY category"
        ).fetchall()
        conn.close()
        return {
            "total_facts": facts,
            "total_conversation_messages": convos,
            "categories": dict(categories),
        }


class MemoryManager:
    """
    Unified memory interface combining short-term and long-term.

    Provides a single API for the AI Layer to:
      - Track conversation context
      - Store and retrieve facts
      - Build context for LLM calls
    """

    def __init__(self, max_turns: int = 20, db_path: str = "data/atlas_memory.db"):
        self.short_term = ShortTermMemory(max_turns=max_turns)
        self.long_term = LongTermMemory(db_path=db_path)
        self.session_id = f"session-{int(time.time())}"

    def add_message(self, role: str, content: str, persist: bool = True, **metadata):
        """
        Add a message to memory.

        Args:
            role: "user", "assistant", or "system"
            content: Message content
            persist: Whether to also store in long-term memory
        """
        self.short_term.add(role, content, **metadata)

        if persist:
            self.long_term.store_conversation(
                self.session_id, role, content, metadata
            )

    def remember(self, fact: str, category: str = "fact", importance: float = 0.5):
        """Store a fact in long-term memory."""
        self.long_term.store_fact(fact, category, importance)

    def recall(self, query: str, category: Optional[str] = None) -> List[Dict]:
        """Search long-term memory for relevant facts."""
        return self.long_term.search_facts(query, category)

    def get_context(self) -> List[Dict]:
        """Get conversation context for LLM calls."""
        return self.short_term.get_context_window()

    def clear_session(self):
        """Clear current session's short-term memory."""
        self.short_term.clear()

    def new_session(self):
        """Start a new session."""
        self.short_term.clear()
        self.session_id = f"session-{int(time.time())}"
