"""
ARIA Multi-Agent Coordination System
====================================
Manages a team of specialized agents that collaborate on complex tasks.

Architecture:
  - AgentTeam coordinates multiple agents
  - Built-in agent types: Research, Analysis, Execution, Validation
  - Each agent has specialized role, tools, and personality
  - Supports parallel execution with consensus merging
  - Confidence weighting for combining agent opinions

Usage:
    team = AgentTeam()
    result = team.delegate("Analyze NVDA's earnings impact")
    consensus = team.consensus("What's the best entry point?")

Copyright (c) 2026 M&C. All rights reserved.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("atlas.aria.intelligence.multi_agent")


# ── Agent Types and Roles ─────────────────────────────────────────────────────

class AgentRole(str, Enum):
    """Specialized agent roles."""
    RESEARCH = "research"          # Investigates and gathers information
    ANALYSIS = "analysis"          # Analyzes data and identifies patterns
    EXECUTION = "execution"        # Plans and executes actions
    VALIDATION = "validation"      # Validates results and identifies issues
    SYNTHESIS = "synthesis"        # Combines insights into coherent views


class AgentExpertise(str, Enum):
    """Domain expertise areas."""
    TRADING = "trading"
    RISK_MANAGEMENT = "risk_management"
    TECHNICAL_ANALYSIS = "technical_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    PORTFOLIO_MANAGEMENT = "portfolio_management"
    MARKET_MICROSTRUCTURE = "market_microstructure"


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class AgentResponse:
    """Response from an individual agent."""
    agent_id: str
    agent_name: str
    role: AgentRole
    response: str
    confidence: float
    reasoning: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "role": self.role.value,
            "response": self.response,
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning,
            "tools_used": self.tools_used,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class ConsensusResult:
    """Consensus from multiple agents."""
    task: str
    agents_consulted: int
    consensus_view: str
    confidence: float
    disagreement_level: float  # 0 = full agreement, 1 = full disagreement
    agent_responses: List[AgentResponse] = field(default_factory=list)
    conflicting_views: List[str] = field(default_factory=list)
    recommended_action: Optional[str] = None
    caveats: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "task": self.task,
            "agents": self.agents_consulted,
            "consensus": self.consensus_view,
            "confidence": round(self.confidence, 3),
            "disagreement": round(self.disagreement_level, 3),
            "responses": [r.to_dict() for r in self.agent_responses],
            "conflicts": self.conflicting_views,
            "action": self.recommended_action,
            "caveats": self.caveats,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class DelegationResult:
    """Result from delegating task to best agent."""
    task: str
    selected_agent: str
    selected_role: AgentRole
    response: str
    confidence: float
    reason_for_selection: str
    duration_ms: float = 0.0

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "task": self.task,
            "selected_agent": self.selected_agent,
            "role": self.selected_role.value,
            "response": self.response,
            "confidence": round(self.confidence, 3),
            "selection_reason": self.reason_for_selection,
            "duration_ms": round(self.duration_ms, 2),
        }


# ══════════════════════════════════════════════════════════════════════════════
#  Specialized Agents
# ══════════════════════════════════════════════════════════════════════════════

class SpecializedAgent:
    """Base class for specialized agents."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: AgentRole,
        system_prompt_suffix: str,
        available_tools: List[str],
        llm_interface=None,
    ):
        """
        Initialize a specialized agent.

        Args:
            agent_id: Unique identifier
            name: Human-readable name
            role: Agent's primary role
            system_prompt_suffix: Role-specific system prompt addition
            available_tools: List of tool names agent can use
            llm_interface: Interface to LLM (e.g., ARIA instance)
        """
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.system_prompt_suffix = system_prompt_suffix
        self.available_tools = available_tools
        self.llm = llm_interface
        self.request_count = 0
        self.total_confidence = 0.0

    def process_task(self, task: str, context: Optional[Dict] = None) -> AgentResponse:
        """
        Process a task as this agent.

        Args:
            task: Task description
            context: Optional context data

        Returns:
            AgentResponse with result and metadata
        """
        start_time = time.time()
        self.request_count += 1

        try:
            # Construct prompt with agent personality
            prompt = self._build_prompt(task, context)

            # Call LLM (or use fallback)
            if self.llm and hasattr(self.llm, 'ask'):
                response_text = self.llm.ask(prompt)
            else:
                response_text = f"{self.name}'s analysis: {task}"

            # Parse confidence from response (heuristic)
            confidence = self._estimate_confidence(response_text)
            self.total_confidence += confidence

            # Extract reasoning
            reasoning = self._extract_reasoning(response_text)

            duration_ms = (time.time() - start_time) * 1000

            return AgentResponse(
                agent_id=self.agent_id,
                agent_name=self.name,
                role=self.role,
                response=response_text,
                confidence=confidence,
                reasoning=reasoning,
                tools_used=self._identify_tools_used(response_text),
                duration_ms=duration_ms,
            )

        except Exception as e:
            logger.warning(f"Agent {self.name} failed: {e}")
            duration_ms = (time.time() - start_time) * 1000
            return AgentResponse(
                agent_id=self.agent_id,
                agent_name=self.name,
                role=self.role,
                response=f"Error: {str(e)}",
                confidence=0.0,
                reasoning=["Processing error"],
                duration_ms=duration_ms,
            )

    def get_average_confidence(self) -> float:
        """Get agent's average confidence across requests."""
        if self.request_count == 0:
            return 0.5
        return self.total_confidence / self.request_count

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_prompt(self, task: str, context: Optional[Dict]) -> str:
        """Build task prompt with agent personality."""
        base_prompt = f"""You are {self.name}, a {self.role.value} specialist.

Your Role: {self.system_prompt_suffix}

Available Tools: {', '.join(self.available_tools)}

Task: {task}
"""
        if context:
            base_prompt += f"\nContext: {context}\n"

        return base_prompt

    def _estimate_confidence(self, response: str) -> float:
        """Estimate confidence from response text."""
        # Simple heuristic: count confidence keywords
        confidence_words = ["confident", "certain", "high", "strong", "clear", "definitely"]
        uncertainty_words = ["may", "might", "could", "possibly", "uncertain", "unclear"]

        conf_count = sum(1 for word in confidence_words if word in response.lower())
        unc_count = sum(1 for word in uncertainty_words if word in response.lower())

        # Base confidence
        base_conf = 0.7
        adjustment = (conf_count - unc_count) * 0.05
        return max(0.0, min(1.0, base_conf + adjustment))

    def _extract_reasoning(self, response: str) -> List[str]:
        """Extract key reasoning points from response."""
        # Simple extraction: split by sentences containing "because", "since", "due to"
        sentences = response.split(". ")
        reasoning = []

        for sentence in sentences:
            if any(word in sentence.lower() for word in ["because", "since", "due", "reason"]):
                reasoning.append(sentence.strip()[:100])

        return reasoning[:3] if reasoning else [response[:100]]

    def _identify_tools_used(self, response: str) -> List[str]:
        """Identify which tools were used in the response."""
        tools_used = []
        for tool in self.available_tools:
            if tool.lower() in response.lower():
                tools_used.append(tool)
        return tools_used


# ══════════════════════════════════════════════════════════════════════════════
#  AgentTeam
# ══════════════════════════════════════════════════════════════════════════════

class AgentTeam:
    """
    Manages a team of specialized agents that collaborate on tasks.

    Features:
    - Delegate tasks to most appropriate agent
    - Run consensus across multiple agents
    - Parallel execution support
    - Confidence-weighted result merging
    """

    def __init__(self, llm_interface=None):
        """
        Initialize agent team.

        Args:
            llm_interface: Shared LLM interface (e.g., ARIA instance)
        """
        self.llm = llm_interface
        self.agents: Dict[str, SpecializedAgent] = {}
        self._setup_agents()

    def _setup_agents(self) -> None:
        """Create and register built-in agent types."""
        agents_config = [
            {
                "id": "research_specialist",
                "name": "Research Specialist",
                "role": AgentRole.RESEARCH,
                "suffix": "Your expertise is finding and synthesizing information. "
                         "You excel at research, investigation, and literature review.",
                "tools": ["web_search", "data_fetch", "memory_retrieve"],
            },
            {
                "id": "data_analyst",
                "name": "Data Analyst",
                "role": AgentRole.ANALYSIS,
                "suffix": "Your expertise is analyzing data and identifying patterns. "
                         "You excel at statistical analysis, visualization, and insights.",
                "tools": ["statistical_analysis", "visualization", "correlation", "regression"],
            },
            {
                "id": "execution_specialist",
                "name": "Execution Specialist",
                "role": AgentRole.EXECUTION,
                "suffix": "Your expertise is planning and executing complex operations. "
                         "You excel at task decomposition, planning, and implementation.",
                "tools": ["task_planning", "workflow_execution", "scheduling", "logging"],
            },
            {
                "id": "validation_expert",
                "name": "Validation Expert",
                "role": AgentRole.VALIDATION,
                "suffix": "Your expertise is validating results and identifying issues. "
                         "You excel at quality checks, error detection, and risk assessment.",
                "tools": ["validation_check", "error_detection", "risk_assessment"],
            },
            {
                "id": "synthesis_strategist",
                "name": "Synthesis Strategist",
                "role": AgentRole.SYNTHESIS,
                "suffix": "Your expertise is combining insights into coherent strategies. "
                         "You excel at synthesis, big-picture thinking, and strategy formulation.",
                "tools": ["pattern_detection", "integration", "strategy_formulation"],
            },
        ]

        for config in agents_config:
            agent = SpecializedAgent(
                agent_id=config["id"],
                name=config["name"],
                role=config["role"],
                system_prompt_suffix=config["suffix"],
                available_tools=config["tools"],
                llm_interface=self.llm,
            )
            self.agents[config["id"]] = agent

        logger.info(f"Initialized agent team with {len(self.agents)} agents")

    # ── Public API ────────────────────────────────────────────────────────────

    def delegate(
        self,
        task: str,
        context: Optional[Dict] = None,
        preferred_role: Optional[AgentRole] = None,
    ) -> DelegationResult:
        """
        Delegate task to the most appropriate agent.

        Args:
            task: Task description
            context: Optional context data
            preferred_role: Optional preferred agent role

        Returns:
            DelegationResult with selected agent and response
        """
        start_time = time.time()

        # Select best agent
        selected_agent_id = self._select_best_agent(task, preferred_role)
        selected_agent = self.agents[selected_agent_id]

        logger.info(f"Delegating task to {selected_agent.name}")

        # Execute task
        response = selected_agent.process_task(task, context)

        duration_ms = (time.time() - start_time) * 1000

        return DelegationResult(
            task=task,
            selected_agent=selected_agent.name,
            selected_role=selected_agent.role,
            response=response.response,
            confidence=response.confidence,
            reason_for_selection=self._explain_selection(selected_agent_id, task),
            duration_ms=duration_ms,
        )

    def consensus(
        self,
        task: str,
        context: Optional[Dict] = None,
        agents_to_consult: Optional[List[str]] = None,
        parallel: bool = True,
    ) -> ConsensusResult:
        """
        Run task through multiple agents and merge results.

        Args:
            task: Task description
            context: Optional context data
            agents_to_consult: Specific agent IDs to use (default: all)
            parallel: Use parallel execution (default: True)

        Returns:
            ConsensusResult with merged opinions and metadata
        """
        start_time = time.time()

        # Determine which agents to consult
        if agents_to_consult is None:
            agents_to_consult = list(self.agents.keys())
        else:
            agents_to_consult = [a for a in agents_to_consult if a in self.agents]

        logger.info(f"Running consensus across {len(agents_to_consult)} agents")

        # Execute in parallel or serial
        if parallel and len(agents_to_consult) > 1:
            responses = self._parallel_execution(task, context, agents_to_consult)
        else:
            responses = self._serial_execution(task, context, agents_to_consult)

        # Merge results
        consensus_view, disagreement = self._merge_responses(responses)

        # Calculate consensus confidence
        avg_confidence = (
            sum(r.confidence for r in responses) / len(responses)
            if responses else 0.5
        )

        # Identify conflicting views
        conflicting_views = self._identify_conflicts(responses)

        # Caveats
        caveats = []
        if disagreement > 0.5:
            caveats.append("Agents showed significant disagreement - consider multiple perspectives")
        if avg_confidence < 0.6:
            caveats.append("Low overall confidence - more investigation may be needed")

        duration_ms = (time.time() - start_time) * 1000

        return ConsensusResult(
            task=task,
            agents_consulted=len(responses),
            consensus_view=consensus_view,
            confidence=avg_confidence,
            disagreement_level=disagreement,
            agent_responses=responses,
            conflicting_views=conflicting_views,
            caveats=caveats,
            duration_ms=duration_ms,
        )

    # ── Execution Methods ─────────────────────────────────────────────────────

    def _parallel_execution(
        self,
        task: str,
        context: Optional[Dict],
        agent_ids: List[str],
    ) -> List[AgentResponse]:
        """Execute task across agents in parallel."""
        responses = []

        with ThreadPoolExecutor(max_workers=min(len(agent_ids), 4)) as executor:
            futures = {
                executor.submit(
                    self.agents[agent_id].process_task, task, context
                ): agent_id
                for agent_id in agent_ids
            }

            for future in as_completed(futures):
                try:
                    response = future.result()
                    responses.append(response)
                except Exception as e:
                    logger.warning(f"Agent execution failed: {e}")

        return responses

    def _serial_execution(
        self,
        task: str,
        context: Optional[Dict],
        agent_ids: List[str],
    ) -> List[AgentResponse]:
        """Execute task across agents serially."""
        responses = []

        for agent_id in agent_ids:
            try:
                response = self.agents[agent_id].process_task(task, context)
                responses.append(response)
            except Exception as e:
                logger.warning(f"Agent {agent_id} failed: {e}")

        return responses

    # ── Result Merging ────────────────────────────────────────────────────────

    def _merge_responses(self, responses: List[AgentResponse]) -> tuple[str, float]:
        """
        Merge multiple agent responses into consensus view.

        Returns:
            (consensus_text, disagreement_level)
        """
        if not responses:
            return "No agent responses available", 1.0

        # Weighted merge by confidence
        consensus_parts = []
        for response in responses:
            if response.confidence > 0.5:  # Only use confident responses
                consensus_parts.append(response.response[:50])

        if consensus_parts:
            consensus_view = " | ".join(consensus_parts)
        else:
            # Fall back to highest confidence response
            best = max(responses, key=lambda r: r.confidence)
            consensus_view = best.response

        # Calculate disagreement
        if len(responses) > 1:
            confidences = [r.confidence for r in responses]
            disagreement = max(confidences) - min(confidences)
        else:
            disagreement = 0.0

        return consensus_view, min(disagreement, 1.0)

    def _identify_conflicts(self, responses: List[AgentResponse]) -> List[str]:
        """Identify conflicting views among agents."""
        conflicts = []

        # Look for opposing sentiment words
        negative_words = {"no", "not", "avoid", "negative", "risk", "caution"}
        positive_words = {"yes", "positive", "buy", "strong", "bullish"}

        has_negative = any(any(w in r.response.lower() for w in negative_words) for r in responses)
        has_positive = any(any(w in r.response.lower() for w in positive_words) for r in responses)

        if has_negative and has_positive:
            conflicts.append("Some agents are bullish while others are bearish")

        return conflicts

    # ── Selection Logic ───────────────────────────────────────────────────────

    def _select_best_agent(
        self,
        task: str,
        preferred_role: Optional[AgentRole],
    ) -> str:
        """Select the best agent for a task."""
        task_lower = task.lower()

        # Role preference based on task keywords
        role_keywords = {
            AgentRole.RESEARCH: ["research", "investigate", "find", "discover", "search"],
            AgentRole.ANALYSIS: ["analyze", "examine", "evaluate", "assess", "metrics"],
            AgentRole.EXECUTION: ["execute", "implement", "plan", "do", "build"],
            AgentRole.VALIDATION: ["validate", "check", "verify", "risk", "error"],
            AgentRole.SYNTHESIS: ["synthesize", "combine", "integrate", "strategy", "overview"],
        }

        # If preferred role given, use it
        if preferred_role:
            for agent_id, agent in self.agents.items():
                if agent.role == preferred_role:
                    return agent_id

        # Score agents based on task keywords
        best_score = 0
        best_agent_id = list(self.agents.keys())[0]

        for agent_id, agent in self.agents.items():
            score = 0

            # Keywords matching
            for keyword in role_keywords.get(agent.role, []):
                if keyword in task_lower:
                    score += 2

            # Average confidence
            score += agent.get_average_confidence()

            if score > best_score:
                best_score = score
                best_agent_id = agent_id

        return best_agent_id

    def _explain_selection(self, agent_id: str, task: str) -> str:
        """Explain why this agent was selected."""
        agent = self.agents[agent_id]
        return f"Selected {agent.name} ({agent.role.value}) for this task"

    # ── Team Info ─────────────────────────────────────────────────────────────

    def list_agents(self) -> List[Dict[str, str]]:
        """List all agents and their roles."""
        return [
            {"id": agent_id, "name": agent.name, "role": agent.role.value}
            for agent_id, agent in self.agents.items()
        ]

    def get_agent_stats(self) -> Dict[str, Dict]:
        """Get performance stats for all agents."""
        return {
            agent_id: {
                "name": agent.name,
                "requests": agent.request_count,
                "avg_confidence": round(agent.get_average_confidence(), 3),
            }
            for agent_id, agent in self.agents.items()
        }
