"""
ARIA Memory Retrieval - Enhanced RAG with semantic search and deduplication.

Combines conversation history, semantic search, and knowledge base lookups
for context-aware LLM interaction.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

logger = logging.getLogger("atlas.aria.memory.retrieval")


@dataclass
class RetrievalContext:
    """
    Structured context from memory for LLM injection.

    Combines multiple memory sources with relevance scoring and formatting.
    """
    conversation_history: List[Dict] = field(default_factory=list)
    """Recent conversation messages"""

    semantic_matches: List[Tuple[str, float]] = field(default_factory=list)
    """(text, similarity_score) tuples from vector search"""

    knowledge_snippets: List[Tuple[str, str]] = field(default_factory=list)
    """(content, category) tuples from knowledge base"""

    relevance_scores: Dict[str, float] = field(default_factory=dict)
    """Relevance scores for each source"""

    deduplication_count: int = 0
    """Number of duplicates removed"""

    def format_for_llm(self) -> str:
        """
        Format context as a structured string for LLM system prompt injection.

        Returns:
            Formatted context string ready for LLM consumption
        """
        sections = []

        if self.conversation_history:
            sections.append("## Recent Conversation History:")
            for msg in self.conversation_history:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                sections.append(f"[{role}]: {content}")

        if self.semantic_matches:
            sections.append("\n## Semantically Related Information:")
            for text, score in self.semantic_matches:
                sections.append(f"- {text[:200]}... (relevance: {score:.2%})")

        if self.knowledge_snippets:
            sections.append("\n## Knowledge Base Entries:")
            for content, category in self.knowledge_snippets:
                sections.append(f"[{category}] {content[:150]}...")

        if self.deduplication_count > 0:
            sections.append(
                f"\n[Note: {self.deduplication_count} duplicate entries merged]"
            )

        return "\n".join(sections)

    def get_summary(self) -> str:
        """Get brief summary of retrieved context."""
        parts = []

        if self.conversation_history:
            parts.append(f"{len(self.conversation_history)} conversation turns")

        if self.semantic_matches:
            avg_score = sum(s for _, s in self.semantic_matches) / len(self.semantic_matches)
            parts.append(f"{len(self.semantic_matches)} semantic matches (avg relevance: {avg_score:.2%})")

        if self.knowledge_snippets:
            parts.append(f"{len(self.knowledge_snippets)} knowledge entries")

        return " | ".join(parts) if parts else "No context retrieved"


class MemoryRetrieval:
    """
    Enhanced memory retrieval with RAG capabilities.

    Combines:
    - Conversation history (recent context)
    - Vector semantic search (knowledge recall)
    - Knowledge base lookup (structured insights)
    - Deduplication and relevance ranking

    Example::

        retrieval = MemoryRetrieval(conversation_memory, vector_memory, knowledge_base)
        context = retrieval.get_context("What's the outlook for Apple stock?")
        print(context.format_for_llm())
    """

    def __init__(self, conversation_memory=None, vector_memory=None,
                 knowledge_base=None):
        """
        Initialize memory retrieval system.

        Args:
            conversation_memory: ConversationMemory instance
            vector_memory: VectorMemory instance
            knowledge_base: KnowledgeBase instance
        """
        self.conversation_memory = conversation_memory
        self.vector_memory = vector_memory
        self.knowledge_base = knowledge_base
        logger.info("Initialized MemoryRetrieval")

    def get_context(self, query: str, max_items: int = 5) -> RetrievalContext:
        """
        Retrieve context from all memory sources.

        Combines and deduplicates results, ranks by relevance.

        Args:
            query: Query text for semantic search
            max_items: Maximum items to retrieve per source

        Returns:
            RetrievalContext with formatted context ready for LLM
        """
        context = RetrievalContext()

        # Get recent conversation history
        if self.conversation_memory:
            try:
                recent = self.conversation_memory.get_recent(limit=max_items)
                context.conversation_history = recent
                context.relevance_scores["conversation"] = 1.0
                logger.debug(f"Retrieved {len(recent)} conversation turns")
            except Exception as e:
                logger.error(f"Failed to get conversation history: {e}")

        # Get semantic matches from vector memory
        if self.vector_memory:
            try:
                matches = self.vector_memory.search(query, top_k=max_items)
                for entry, score in matches:
                    context.semantic_matches.append((entry.text, score))

                if matches:
                    avg_score = sum(s for _, s in matches) / len(matches)
                    context.relevance_scores["semantic"] = avg_score
                    logger.debug(f"Retrieved {len(matches)} semantic matches")
            except Exception as e:
                logger.error(f"Failed to search vector memory: {e}")

        # Get knowledge base entries
        if self.knowledge_base:
            try:
                knowledge = self.knowledge_base.search_knowledge(query, top_k=max_items)
                for entry in knowledge:
                    context.knowledge_snippets.append((entry.content, entry.category))

                if knowledge:
                    context.relevance_scores["knowledge"] = 0.8
                    logger.debug(f"Retrieved {len(knowledge)} knowledge entries")
            except Exception as e:
                logger.error(f"Failed to search knowledge base: {e}")

        # Deduplicate similar content
        context.deduplication_count = self._deduplicate_context(context)

        logger.info(f"Retrieved context: {context.get_summary()}")
        return context

    @staticmethod
    def _deduplicate_context(context: RetrievalContext) -> int:
        """
        Remove duplicate/near-duplicate content across sources.

        Simple deduplication: if texts are very similar (>95% overlap),
        keep only the highest relevance one.

        Args:
            context: RetrievalContext to deduplicate in-place

        Returns:
            Number of duplicates removed
        """
        removed = 0

        # Extract all text pieces
        all_texts: List[Tuple[str, str, int]] = []

        for i, msg in enumerate(context.conversation_history):
            text = msg.get("content", "")
            if text:
                all_texts.append((text, "conversation", i))

        for i, (text, _) in enumerate(context.semantic_matches):
            all_texts.append((text, "semantic", i))

        for i, (text, _) in enumerate(context.knowledge_snippets):
            all_texts.append((text, "knowledge", i))

        # Simple deduplication: check for substring containment
        indices_to_remove = set()
        for i in range(len(all_texts)):
            for j in range(i + 1, len(all_texts)):
                text_i = all_texts[i][0].lower()
                text_j = all_texts[j][0].lower()

                # If one is substring of other (>80% overlap), mark for removal
                if len(text_i) > 20 and len(text_j) > 20:
                    overlap = len(set(text_i) & set(text_j)) / max(len(set(text_i)), len(set(text_j)))
                    if overlap > 0.8:
                        # Keep the shorter one (more specific)
                        if len(text_i) > len(text_j):
                            indices_to_remove.add(i)
                        else:
                            indices_to_remove.add(j)

        # Remove duplicates from sources
        # (This is a simplified version - in production, you'd track original indices)
        original_semantic = context.semantic_matches
        original_knowledge = context.knowledge_snippets

        context.semantic_matches = [
            (text, score) for text, score in original_semantic
            if text not in [t for t, _, _ in [all_texts[i] for i in indices_to_remove if all_texts[i][1] == "semantic"]]
        ]

        context.knowledge_snippets = [
            (text, cat) for text, cat in original_knowledge
            if text not in [t for t, _, _ in [all_texts[i] for i in indices_to_remove if all_texts[i][1] == "knowledge"]]
        ]

        removed = len(original_semantic) - len(context.semantic_matches)
        removed += len(original_knowledge) - len(context.knowledge_snippets)

        if removed > 0:
            logger.debug(f"Deduplicated {removed} items")

        return removed

    def get_context_summary(self, query: str) -> str:
        """
        Get a one-line summary of available context for a query.

        Args:
            query: Query text

        Returns:
            Summary string
        """
        context = self.get_context(query)
        return context.get_summary()

    def inject_into_system_prompt(self, query: str, system_prompt: str) -> str:
        """
        Inject retrieved context into LLM system prompt.

        Args:
            query: User query
            system_prompt: Base system prompt

        Returns:
            Enhanced system prompt with context
        """
        context = self.get_context(query)
        context_str = context.format_for_llm()

        if not context_str.strip():
            return system_prompt

        enhanced = f"""{system_prompt}

---

RETRIEVED CONTEXT:
{context_str}
"""
        return enhanced

    def get_info(self) -> Dict:
        """Get retrieval system info."""
        return {
            "conversation_memory": "available" if self.conversation_memory else "unavailable",
            "vector_memory": "available" if self.vector_memory else "unavailable",
            "knowledge_base": "available" if self.knowledge_base else "unavailable",
            "has_conversation_data": bool(self.conversation_memory and self.conversation_memory.get_recent(limit=1)),
        }
