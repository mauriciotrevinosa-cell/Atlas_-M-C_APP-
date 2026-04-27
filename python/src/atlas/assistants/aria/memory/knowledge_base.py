"""
ARIA Knowledge Base - Long-term knowledge storage with semantic search.

Stores market insights, analysis results, user preferences, and other
long-term knowledge with TTL support and automatic summarization.

Copyright (c) 2026 M&C. All rights reserved.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("atlas.aria.memory.knowledge_base")


class KnowledgeCategory(Enum):
    """Categories for knowledge entries."""
    MARKET_INSIGHT = "market_insight"
    ANALYSIS_RESULT = "analysis_result"
    USER_PREFERENCE = "user_preference"
    STRATEGY_RESULT = "strategy_result"
    TOOL_OUTPUT = "tool_output"
    GENERAL = "general"


@dataclass
class KnowledgeEntry:
    """Single entry in knowledge base."""
    id: str
    content: str
    category: str
    source: str
    metadata: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    """ISO timestamp when entry expires (optional TTL)"""

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if not self.expires_at:
            return False
        return datetime.fromisoformat(self.expires_at) < datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "source": self.source,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "KnowledgeEntry":
        """Create from dict (JSON deserialization)."""
        return cls(**data)


class KnowledgeBase:
    """
    Long-term knowledge store for ARIA.

    Features:
    - Semantic search via vector memory
    - Category-based organization
    - TTL support (entries can expire)
    - Automatic summarization of long entries
    - JSON persistence
    - Metadata filtering

    Example::

        kb = KnowledgeBase(vector_memory=vector_mem)

        # Add market insight (expires after 24 hours)
        kb.add_knowledge(
            "Fed raised rates by 25bps to combat inflation",
            category=KnowledgeCategory.MARKET_INSIGHT,
            source="market_analysis",
            metadata={"ticker": "SPY", "event": "FOMC"},
            ttl_hours=24
        )

        # Search
        results = kb.search_knowledge("Federal Reserve interest rates")
        for entry in results:
            print(f"[{entry.category}] {entry.content}")
    """

    def __init__(self, vector_memory=None, persist_path: str = "data/aria_knowledge.json"):
        """
        Initialize knowledge base.

        Args:
            vector_memory: Optional VectorMemory for semantic search
            persist_path: Path for JSON persistence
        """
        self.vector_memory = vector_memory
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: Dict[str, KnowledgeEntry] = {}
        self._load_from_disk()
        logger.info(f"Initialized KnowledgeBase with {len(self.entries)} entries")

    def add_knowledge(
        self,
        content: str,
        category: KnowledgeCategory = KnowledgeCategory.GENERAL,
        source: str = "unknown",
        metadata: Optional[Dict] = None,
        ttl_hours: Optional[int] = None,
    ) -> str:
        """
        Add knowledge entry to base.

        Automatically summarizes long content and indexes in vector memory.

        Args:
            content: Knowledge content
            category: Knowledge category
            source: Source of knowledge (e.g., "user_input", "market_analysis")
            metadata: Optional metadata for filtering
            ttl_hours: Time-to-live in hours (None = permanent)

        Returns:
            Entry ID
        """
        entry_id = str(uuid4())

        # Summarize if too long
        processed_content = self._summarize_if_needed(content)

        expires_at = None
        if ttl_hours:
            expires_at = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()

        entry = KnowledgeEntry(
            id=entry_id,
            content=processed_content,
            category=category.value,
            source=source,
            metadata=metadata or {},
            expires_at=expires_at,
        )

        self.entries[entry_id] = entry

        # Index in vector memory if available
        if self.vector_memory:
            try:
                self.vector_memory.add(
                    text=processed_content,
                    metadata={
                        "entry_id": entry_id,
                        "category": category.value,
                        "source": source,
                        **metadata
                    },
                    embedding=None
                )
            except Exception as e:
                logger.error(f"Failed to index knowledge in vector memory: {e}")

        self._persist()
        logger.debug(f"Added knowledge entry {entry_id} ({category.value})")

        return entry_id

    def search_knowledge(
        self,
        query: str,
        category: Optional[KnowledgeCategory] = None,
        top_k: int = 5,
    ) -> List[KnowledgeEntry]:
        """
        Search knowledge base.

        Uses vector memory for semantic search if available,
        falls back to category filtering.

        Args:
            query: Search query
            category: Optional category filter
            top_k: Max results to return

        Returns:
            List of relevant KnowledgeEntry objects
        """
        results = []

        # Remove expired entries
        expired_ids = [
            entry_id for entry_id, entry in self.entries.items()
            if entry.is_expired()
        ]
        for entry_id in expired_ids:
            del self.entries[entry_id]
            logger.debug(f"Removed expired entry {entry_id}")

        if self.vector_memory:
            # Semantic search via vector memory
            try:
                metadata_filter = {}
                if category:
                    metadata_filter["category"] = category.value

                matches = self.vector_memory.search(
                    query=query,
                    top_k=top_k * 2,  # Get more to filter
                    metadata_filter=metadata_filter if metadata_filter else None
                )

                # Extract entry IDs from matches and get full entries
                seen_ids = set()
                for entry_text, score in matches:
                    # Find entry by content
                    for entry_id, entry in self.entries.items():
                        if entry_id not in seen_ids and entry.content == entry_text:
                            if not entry.is_expired():
                                results.append(entry)
                                seen_ids.add(entry_id)
                                break

                return results[:top_k]

            except Exception as e:
                logger.error(f"Vector search failed, falling back to category filter: {e}")

        # Fallback: category filtering only
        candidates = self.entries.values()

        if category:
            candidates = [e for e in candidates if e.category == category.value]

        # Return non-expired entries
        non_expired = [e for e in candidates if not e.is_expired()]
        return non_expired[:top_k]

    def get_by_category(self, category: KnowledgeCategory) -> List[KnowledgeEntry]:
        """Get all non-expired entries in a category."""
        entries = [
            e for e in self.entries.values()
            if e.category == category.value and not e.is_expired()
        ]
        return entries

    def delete_entry(self, entry_id: str) -> bool:
        """Delete knowledge entry by ID."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._persist()
            logger.debug(f"Deleted knowledge entry {entry_id}")
            return True
        return False

    def clear_category(self, category: KnowledgeCategory) -> int:
        """Delete all entries in a category."""
        ids_to_delete = [
            entry_id for entry_id, entry in self.entries.items()
            if entry.category == category.value
        ]

        for entry_id in ids_to_delete:
            del self.entries[entry_id]

        self._persist()
        logger.info(f"Cleared {len(ids_to_delete)} entries in category {category.value}")
        return len(ids_to_delete)

    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        expired_ids = [
            entry_id for entry_id, entry in self.entries.items()
            if entry.is_expired()
        ]

        for entry_id in expired_ids:
            del self.entries[entry_id]

        if expired_ids:
            self._persist()
            logger.info(f"Cleaned up {len(expired_ids)} expired entries")

        return len(expired_ids)

    def get_info(self) -> Dict:
        """Get knowledge base statistics."""
        non_expired = [e for e in self.entries.values() if not e.is_expired()]

        category_counts = {}
        for entry in non_expired:
            cat = entry.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        return {
            "total_entries": len(self.entries),
            "non_expired_entries": len(non_expired),
            "by_category": category_counts,
            "vector_indexed": self.vector_memory is not None,
        }

    def _summarize_if_needed(self, content: str, max_length: int = 500) -> str:
        """
        Summarize content if it exceeds max length.

        Simple summarization: keep first max_length chars + ellipsis.

        Args:
            content: Content to summarize
            max_length: Max length before summarization

        Returns:
            Original or summarized content
        """
        if len(content) <= max_length:
            return content

        # Simple truncation with context preservation
        summarized = content[:max_length].rsplit(" ", 1)[0] + "..."
        logger.debug(f"Summarized knowledge: {len(content)} -> {len(summarized)} chars")
        return summarized

    def _persist(self) -> None:
        """Save entries to disk."""
        try:
            data = {
                entry_id: entry.to_dict()
                for entry_id, entry in self.entries.items()
            }
            with open(self.persist_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist knowledge base: {e}")

    def _load_from_disk(self) -> None:
        """Load entries from disk."""
        if not self.persist_path.exists():
            return

        try:
            with open(self.persist_path, "r") as f:
                data = json.load(f)

            for entry_id, entry_data in data.items():
                self.entries[entry_id] = KnowledgeEntry.from_dict(entry_data)

            logger.info(f"Loaded {len(self.entries)} knowledge entries from disk")
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
