"""
Atlas AI Assistant System
=========================
Own agent system (n8n-style) with structured contracts and audit trail.

Sprint 1 agents (production-ready):
  PlannerAgent         — goal → executable plan
  ReviewerAgent        — code → structured review + merge recommendation
  TestAgent            — code → pytest test design
  ContextCuratorAgent  — context → filtered compact context

Sprint 2 agents (production-ready):
  CodeBuilderAgent     — task → clean code proposal
  RepoScoutAgent       — problem → research + pattern analysis
  IngestionAgent       — document → structured knowledge pack

Infrastructure:
  AgentRegistry        — central agent catalog
  AgentOrchestrator    — task dispatcher + audit
  ModelRouter          — provider/model selection
  PromptStore          — template loader
  TaskLogger           — immutable audit trail
  ResultValidator      — output contract checker

Usage:
    from atlas.core.ai_assistant import build_system

    orch  = build_system()
    task  = AgentTask(objective="Implement RBAC", agent_name="planner_agent")
    result = orch.execute(task)
"""

from .agent_registry   import AgentRegistry, get_registry
from .orchestrator     import AgentOrchestrator
from .task_schema      import AgentTask, AgentResult
from .result_validator import ResultValidator
from .agents import (
    PlannerAgent, ReviewerAgent, TestAgent, ContextCuratorAgent,
    CodeBuilderAgent, RepoScoutAgent, IngestionAgent, DocsAgent,
)


def build_system(
    llm_client=None,
    log_dir=None,
    ollama_url: str = "http://localhost:11434",
    claude_key: str = None,
    openai_key: str = None,
    gemini_key: str = None,
) -> AgentOrchestrator:
    """
    Factory: build and return a fully configured AgentOrchestrator.

    If llm_client is None, uses ModelRouter with available providers.
    Agents run in stub mode if no providers are configured.

    Parameters
    ----------
    llm_client : optional pre-built ModelRouter or callable LLM
    log_dir    : path for audit logs (default: logs/agents/)
    ollama_url : Ollama server URL
    claude_key : Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
    openai_key : OpenAI API key (falls back to OPENAI_API_KEY env var)
    gemini_key : Gemini API key (falls back to GEMINI_API_KEY env var)

    Returns
    -------
    AgentOrchestrator ready to execute tasks
    """
    from atlas.services.llm.model_router import ModelRouter
    from atlas.services.llm.prompt_store import PromptStore
    from atlas.core.ai_assistant.audit.task_logs import TaskLogger

    # Build LLM client
    if llm_client is None:
        llm_client = ModelRouter(
            ollama_url = ollama_url,
            claude_key = claude_key,
            openai_key = openai_key,
            gemini_key = gemini_key,
        )

    prompt_store = PromptStore()

    # Build agents
    registry = AgentRegistry()
    registry.register_many([
        PlannerAgent(llm_client=llm_client, prompt_store=prompt_store),
        ReviewerAgent(llm_client=llm_client, prompt_store=prompt_store),
        TestAgent(llm_client=llm_client, prompt_store=prompt_store),
        ContextCuratorAgent(llm_client=llm_client, prompt_store=prompt_store),
        CodeBuilderAgent(llm_client=llm_client, prompt_store=prompt_store),
        RepoScoutAgent(llm_client=llm_client, prompt_store=prompt_store),
        IngestionAgent(llm_client=llm_client, prompt_store=prompt_store),
        DocsAgent(llm_client=llm_client, prompt_store=prompt_store),
    ])

    logger    = TaskLogger(log_dir=log_dir)
    validator = ResultValidator()

    return AgentOrchestrator(
        registry  = registry,
        logger    = logger,
        validator = validator,
    )


__all__ = [
    "AgentRegistry", "get_registry",
    "AgentOrchestrator",
    "AgentTask", "AgentResult",
    "ResultValidator",
    "PlannerAgent", "ReviewerAgent", "TestAgent", "ContextCuratorAgent",
    "CodeBuilderAgent", "RepoScoutAgent", "IngestionAgent", "DocsAgent",
    "build_system",
]
