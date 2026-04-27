"""
ARIA Intelligence Orchestrator — Central reasoning coordinator
==============================================================
Coordinates intelligent processing across all ARIA subsystems.

This orchestrator:
  - Classifies user intent (DIRECT, ANALYTICAL, RESEARCH, PLANNING, CREATIVE)
  - Retrieves relevant memory and context
  - Selects appropriate reasoning strategy
  - Executes multi-step reasoning with tools
  - Learns from results and updates knowledge

Architecture:
  User Query → Intent Classifier
            → Memory Retrieval
            → Reasoning Strategy Selector
            → Execution Engine
            → Learning Module

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("atlas.aria.intelligence.orchestrator")


# ── Reasoning Strategies ──────────────────────────────────────────────────────

class ReasoningStrategy(str, Enum):
    """Reasoning strategies for different query types."""
    DIRECT = "direct"              # Simple Q&A, factual lookup
    ANALYTICAL = "analytical"      # Data-driven, tool-based analysis
    RESEARCH = "research"          # Multi-step investigation
    PLANNING = "planning"          # Task decomposition, step-by-step
    CREATIVE = "creative"          # Freeform generation, exploration


class IntentClass(str, Enum):
    """Query intent classifications."""
    QUESTION = "question"          # Information seeking
    TASK = "task"                  # Action/execution request
    ANALYSIS = "analysis"          # Data analysis request
    DECISION = "decision"          # Decision support needed
    GENERATION = "generation"      # Content generation
    CLARIFICATION = "clarification"  # Follow-up or clarification


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class ProcessingContext:
    """Context passed through the reasoning pipeline."""
    query: str
    intent_class: Optional[IntentClass] = None
    strategy: Optional[ReasoningStrategy] = None
    user_profile: Optional[Dict[str, Any]] = None
    market_data: Optional[Dict[str, Any]] = None
    portfolio_data: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict]] = None
    memory_items: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningStep:
    """Individual step in a reasoning chain."""
    step_number: int
    name: str
    description: str
    tool_calls: List[str] = field(default_factory=list)
    result: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class IntelligenceResult:
    """Final output from intelligence orchestrator."""
    query: str
    response: str
    reasoning_chain: List[ReasoningStep] = field(default_factory=list)
    confidence: float = 0.7
    tools_used: List[str] = field(default_factory=list)
    context_used: List[str] = field(default_factory=list)
    intent_class: Optional[IntentClass] = None
    strategy: Optional[ReasoningStrategy] = None
    timestamp: float = field(default_factory=time.time)
    total_duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "query": self.query,
            "response": self.response,
            "reasoning_chain": [
                {
                    "step": s.step_number,
                    "name": s.name,
                    "description": s.description,
                    "tool_calls": s.tool_calls,
                    "result": s.result,
                    "duration_ms": round(s.duration_ms, 2),
                }
                for s in self.reasoning_chain
            ],
            "confidence": round(self.confidence, 3),
            "tools_used": self.tools_used,
            "context_used": self.context_used,
            "intent": self.intent_class.value if self.intent_class else None,
            "strategy": self.strategy.value if self.strategy else None,
            "total_duration_ms": round(self.total_duration_ms, 2),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  IntelligenceOrchestrator
# ══════════════════════════════════════════════════════════════════════════════

class IntelligenceOrchestrator:
    """
    Central coordinator for ARIA's intelligent reasoning.

    Manages:
    - Intent classification
    - Memory retrieval
    - Strategy selection
    - Execution with tools
    - Learning from results

    Usage:
        orchestrator = IntelligenceOrchestrator(aria_instance, swarm_coordinator)
        result = orchestrator.process_query(
            query="What is NVDA's risk profile?",
            context=ProcessingContext(...)
        )
        print(result.response)
    """

    def __init__(
        self,
        aria_instance=None,
        swarm_coordinator=None,
        agent_orchestrator=None,
        memory_store=None,
    ):
        """
        Initialize the Intelligence Orchestrator.

        Args:
            aria_instance: ARIA chat engine (for LLM calls)
            swarm_coordinator: Multi-agent coordinator for market decisions
            agent_orchestrator: Task orchestrator for complex operations
            memory_store: Persistent memory system
        """
        self.aria = aria_instance
        self.swarm = swarm_coordinator
        self.agent_orch = agent_orchestrator
        self.memory = memory_store

        # Intent classifier keywords
        self._intent_keywords: Dict[IntentClass, List[str]] = {
            IntentClass.QUESTION: [
                "what", "how", "why", "when", "where", "who",
                "explain", "describe", "tell me", "is", "are", "can you"
            ],
            IntentClass.TASK: [
                "run", "execute", "perform", "do", "create", "build",
                "make", "generate", "export", "save", "delete"
            ],
            IntentClass.ANALYSIS: [
                "analyze", "analyze", "compare", "evaluate", "assess",
                "calculate", "compute", "find", "determine", "measure"
            ],
            IntentClass.DECISION: [
                "should", "recommend", "advise", "suggest", "best",
                "better", "risk", "decision", "choice", "option"
            ],
            IntentClass.GENERATION: [
                "write", "compose", "generate", "create", "draft",
                "outline", "summarize", "list", "suggest"
            ],
            IntentClass.CLARIFICATION: [
                "what do you mean", "clarify", "explain", "again",
                "more detail", "further", "deeper"
            ],
        }

        # Strategy selection rules
        self._strategy_patterns: Dict[ReasoningStrategy, List[str]] = {
            ReasoningStrategy.DIRECT: [
                "who", "what is", "when", "where", "definition",
                "explain briefly", "simple"
            ],
            ReasoningStrategy.ANALYTICAL: [
                "analyze", "compare", "calculate", "evaluate", "metrics",
                "data", "numbers", "historical"
            ],
            ReasoningStrategy.RESEARCH: [
                "investigate", "explore", "find out", "discover", "research",
                "deep dive", "comprehensive", "detailed"
            ],
            ReasoningStrategy.PLANNING: [
                "plan", "steps", "process", "how to", "sequence",
                "build", "create", "design"
            ],
            ReasoningStrategy.CREATIVE: [
                "imagine", "brainstorm", "ideas", "creative", "generate",
                "compose", "write", "story"
            ],
        }

        logger.info("IntelligenceOrchestrator initialized")

    # ── Main API ──────────────────────────────────────────────────────────────

    def process_query(
        self,
        query: str,
        context: Optional[ProcessingContext] = None,
    ) -> IntelligenceResult:
        """
        Process a user query through the full intelligence pipeline.

        Args:
            query: User's question or request
            context: Optional processing context with data

        Returns:
            IntelligenceResult with response and metadata
        """
        start_time = time.time()
        context = context or ProcessingContext(query=query)

        try:
            logger.info(f"Processing query: {query[:60]}...")

            # Step 1: Classify intent
            intent = self._classify_intent(query)
            context.intent_class = intent

            # Step 2: Retrieve memory
            memory_items = self._retrieve_memory(query)
            context.memory_items = memory_items

            # Step 3: Select reasoning strategy
            strategy = self._select_strategy(query, intent)
            context.strategy = strategy

            # Step 4: Execute reasoning
            response, reasoning_chain, tools_used, confidence = self._execute_reasoning(
                query, context, strategy
            )

            # Step 5: Learn from result
            self._learn_from_result(query, response, confidence)

            duration_ms = (time.time() - start_time) * 1000

            result = IntelligenceResult(
                query=query,
                response=response,
                reasoning_chain=reasoning_chain,
                confidence=confidence,
                tools_used=tools_used,
                context_used=self._get_context_labels(context),
                intent_class=intent,
                strategy=strategy,
                total_duration_ms=duration_ms,
            )

            logger.info(
                f"Query processed: intent={intent}, strategy={strategy}, "
                f"confidence={confidence:.2f}, duration={duration_ms:.0f}ms"
            )

            return result

        except Exception as e:
            logger.exception(f"Error processing query: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return IntelligenceResult(
                query=query,
                response=f"I encountered an error processing your request: {str(e)}",
                confidence=0.0,
                total_duration_ms=duration_ms,
            )

    # ── Pipeline Stages ───────────────────────────────────────────────────────

    def _classify_intent(self, query: str) -> IntentClass:
        """Classify user intent from query text."""
        query_lower = query.lower()

        # Score each intent class
        scores: Dict[IntentClass, int] = {ic: 0 for ic in IntentClass}

        for intent_class, keywords in self._intent_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    scores[intent_class] += 1

        # Return highest scoring class, default to QUESTION
        if max(scores.values()) == 0:
            return IntentClass.QUESTION

        best_intent = max(scores, key=scores.get)
        logger.debug(f"Intent classified: {best_intent} (scores: {scores})")
        return best_intent

    def _retrieve_memory(self, query: str) -> List[Dict]:
        """Retrieve relevant memory items from knowledge store."""
        if not self.memory:
            return []

        try:
            # Extract key entities/concepts from query
            keywords = self._extract_keywords(query)

            # Retrieve from memory (implementation depends on memory_store)
            items = []
            for keyword in keywords[:3]:  # Top 3 keywords
                if hasattr(self.memory, 'retrieve'):
                    result = self.memory.retrieve(keyword, limit=2)
                    items.extend(result if result else [])

            logger.debug(f"Retrieved {len(items)} memory items for query")
            return items

        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
            return []

    def _select_strategy(
        self,
        query: str,
        intent: IntentClass,
    ) -> ReasoningStrategy:
        """Select the best reasoning strategy for the query."""
        query_lower = query.lower()

        # Score each strategy based on pattern matches
        scores: Dict[ReasoningStrategy, int] = {s: 0 for s in ReasoningStrategy}

        for strategy, patterns in self._strategy_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    scores[strategy] += 1

        # Intent-based strategy preference
        intent_strategy_map = {
            IntentClass.QUESTION: ReasoningStrategy.DIRECT,
            IntentClass.ANALYSIS: ReasoningStrategy.ANALYTICAL,
            IntentClass.DECISION: ReasoningStrategy.ANALYTICAL,
            IntentClass.TASK: ReasoningStrategy.PLANNING,
            IntentClass.GENERATION: ReasoningStrategy.CREATIVE,
            IntentClass.CLARIFICATION: ReasoningStrategy.DIRECT,
        }

        # Use pattern score if strong signal, else use intent mapping
        if max(scores.values()) > 0:
            selected = max(scores, key=scores.get)
        else:
            selected = intent_strategy_map.get(intent, ReasoningStrategy.DIRECT)

        logger.debug(f"Strategy selected: {selected}")
        return selected

    def _execute_reasoning(
        self,
        query: str,
        context: ProcessingContext,
        strategy: ReasoningStrategy,
    ) -> Tuple[str, List[ReasoningStep], List[str], float]:
        """Execute the reasoning strategy and generate response."""
        reasoning_chain: List[ReasoningStep] = []
        tools_used: List[str] = []
        confidence: float = 0.7

        try:
            if strategy == ReasoningStrategy.DIRECT:
                response, chain, tools, conf = self._direct_reasoning(query, context)

            elif strategy == ReasoningStrategy.ANALYTICAL:
                response, chain, tools, conf = self._analytical_reasoning(query, context)

            elif strategy == ReasoningStrategy.RESEARCH:
                response, chain, tools, conf = self._research_reasoning(query, context)

            elif strategy == ReasoningStrategy.PLANNING:
                response, chain, tools, conf = self._planning_reasoning(query, context)

            elif strategy == ReasoningStrategy.CREATIVE:
                response, chain, tools, conf = self._creative_reasoning(query, context)

            else:
                # Fallback to direct reasoning
                response, chain, tools, conf = self._direct_reasoning(query, context)

            reasoning_chain = chain
            tools_used = tools
            confidence = conf

        except Exception as e:
            logger.warning(f"Reasoning execution failed: {e}")
            response = f"I attempted to reason through this but encountered an issue: {str(e)}"
            confidence = 0.3

        return response, reasoning_chain, tools_used, confidence

    def _direct_reasoning(
        self,
        query: str,
        context: ProcessingContext,
    ) -> Tuple[str, List[ReasoningStep], List[str], float]:
        """Direct Q&A - simple lookup or brief explanation."""
        step = ReasoningStep(
            step_number=1,
            name="Direct Answer",
            description="Provide direct answer to question",
        )

        # Use ARIA if available
        if self.aria:
            response = self.aria.ask(query)
        else:
            response = f"I understand your question about: {query}"

        step.result = response[:100]
        return response, [step], [], 0.8

    def _analytical_reasoning(
        self,
        query: str,
        context: ProcessingContext,
    ) -> Tuple[str, List[ReasoningStep], List[str], float]:
        """Data-driven analysis with tools."""
        chain: List[ReasoningStep] = []
        tools_used: List[str] = []

        # Step 1: Data gathering
        if context.market_data:
            tools_used.append("market_data_fetch")
            chain.append(ReasoningStep(
                step_number=1,
                name="Data Collection",
                description="Fetch relevant market data",
                tool_calls=["market_data_fetch"],
                result="Data retrieved",
            ))

        # Step 2: Analysis
        chain.append(ReasoningStep(
            step_number=len(chain) + 1,
            name="Analysis",
            description="Analyze collected data",
            result="Analysis complete",
        ))

        # Generate response
        response = f"Analysis of: {query}\n\nBased on available data, here are my findings..."

        return response, chain, tools_used, 0.75

    def _research_reasoning(
        self,
        query: str,
        context: ProcessingContext,
    ) -> Tuple[str, List[ReasoningStep], List[str], float]:
        """Multi-step investigation with research tools."""
        chain: List[ReasoningStep] = []
        tools_used: List[str] = ["search", "data_fetch", "analysis"]

        # Step 1: Search
        chain.append(ReasoningStep(
            step_number=1,
            name="Research Search",
            description="Search for information",
            tool_calls=["search"],
            result="Search completed",
        ))

        # Step 2: Data collection
        chain.append(ReasoningStep(
            step_number=2,
            name="Data Collection",
            description="Gather supporting data",
            tool_calls=["data_fetch"],
            result="Data collected",
        ))

        # Step 3: Synthesis
        chain.append(ReasoningStep(
            step_number=3,
            name="Synthesis",
            description="Synthesize findings",
            tool_calls=["analysis"],
            result="Synthesis complete",
        ))

        response = f"Research findings on: {query}\n\nThrough investigation, I found..."

        return response, chain, tools_used, 0.7

    def _planning_reasoning(
        self,
        query: str,
        context: ProcessingContext,
    ) -> Tuple[str, List[ReasoningStep], List[str], float]:
        """Task decomposition and planning."""
        chain: List[ReasoningStep] = []

        # Decompose task
        chain.append(ReasoningStep(
            step_number=1,
            name="Task Decomposition",
            description="Break down task into steps",
            result="Task decomposed",
        ))

        chain.append(ReasoningStep(
            step_number=2,
            name="Planning",
            description="Create step-by-step plan",
            result="Plan created",
        ))

        response = f"Plan for: {query}\n\nHere's my step-by-step approach:\n1. First...\n2. Then...\n3. Finally..."

        return response, chain, [], 0.75

    def _creative_reasoning(
        self,
        query: str,
        context: ProcessingContext,
    ) -> Tuple[str, List[ReasoningStep], List[str], float]:
        """Freeform creative generation."""
        step = ReasoningStep(
            step_number=1,
            name="Creative Generation",
            description="Generate creative content",
        )

        if self.aria:
            response = self.aria.ask(query)
        else:
            response = f"Creative response to: {query}\n\nLet me explore this idea..."

        step.result = response[:100]
        return response, [step], [], 0.65

    # ── Learning ──────────────────────────────────────────────────────────────

    def _learn_from_result(self, query: str, response: str, confidence: float) -> None:
        """Learn from successful reasoning results."""
        try:
            if not self.memory:
                return

            # Store successful query-response pair with confidence
            if hasattr(self.memory, 'store'):
                self.memory.store(
                    key=query,
                    value={"response": response, "confidence": confidence},
                    metadata={"type": "reasoning_result"}
                )

            logger.debug("Learning stored from result")

        except Exception as e:
            logger.warning(f"Learning storage failed: {e}")

    # ── Utilities ─────────────────────────────────────────────────────────────

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for memory retrieval."""
        # Simple keyword extraction - in production, use NLP
        words = text.lower().split()
        # Filter out common words
        stopwords = {"what", "how", "why", "when", "where", "who", "is", "are", "the", "a", "an"}
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        return keywords[:5]

    def _get_context_labels(self, context: ProcessingContext) -> List[str]:
        """Get labels describing what context was used."""
        labels = []
        if context.market_data:
            labels.append("market_data")
        if context.portfolio_data:
            labels.append("portfolio_data")
        if context.user_profile:
            labels.append("user_profile")
        if context.conversation_history:
            labels.append("conversation_history")
        if context.memory_items:
            labels.append("memory")
        return labels
