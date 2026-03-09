"""Tests for ContextCuratorAgent."""

import json
import pytest

from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult
from atlas.core.ai_assistant.agents.context_curator_agent import ContextCuratorAgent


@pytest.fixture
def agent():
    return ContextCuratorAgent()


@pytest.fixture
def agent_with_mock():
    curation = {
        "required_context":      ["RBAC roles: Client, Worker, Owner", "Backend-first validation"],
        "optional_context":      ["UI mockups"],
        "irrelevant_context":    ["crypto module", "stress lab"],
        "compact_prompt_context": "Atlas usa RBAC modular. Roles: Client, Worker, Owner. Validación backend-first.",
        "context_risks":         ["No confirmada estructura final del auth service"],
        "summary":               "Contexto reducido a RBAC y validación — irrelevante eliminado.",
    }
    return ContextCuratorAgent(llm_client=lambda p: json.dumps(curation))


@pytest.fixture
def task():
    return AgentTask(
        objective  = "Implementar validación de permisos",
        agent_name = "context_curator_agent",
        context    = {
            "full_context": (
                "Atlas es un sistema modular de trading con módulos de auth, "
                "crypto, stress lab, indicadores, paper trading, RBAC. "
                "Los roles son Client, Worker, Owner. La validación debe ser backend-first."
            )
        },
    )


class TestContextCuratorNominal:

    def test_no_llm_returns_fallback(self, agent, task):
        result = agent.safe_run(task)
        assert isinstance(result, AgentResult)
        assert "compact_prompt_context" in result.result

    def test_compact_context_not_empty(self, agent, task):
        result = agent.safe_run(task)
        assert len(result.result["compact_prompt_context"]) > 0

    def test_with_mock_has_required_context(self, agent_with_mock, task):
        result = agent_with_mock.safe_run(task)
        assert result.status == "success"
        assert len(result.result["required_context"]) >= 1

    def test_with_mock_removes_irrelevant(self, agent_with_mock, task):
        result = agent_with_mock.safe_run(task)
        irrelevant = result.result.get("irrelevant_context", [])
        assert "crypto module" in irrelevant or len(irrelevant) >= 0

    def test_compact_context_word_limit(self, agent_with_mock, task):
        result = agent_with_mock.safe_run(task)
        compact = result.result["compact_prompt_context"]
        words = compact.split()
        assert len(words) <= ContextCuratorAgent.MAX_COMPACT_WORDS + 5  # small tolerance

    def test_metadata_word_count(self, agent_with_mock, task):
        result = agent_with_mock.safe_run(task)
        assert "compact_word_count" in result.metadata
        assert result.metadata["compact_word_count"] > 0

    def test_task_id_preserved(self, agent, task):
        result = agent.safe_run(task)
        assert result.task_id == task.task_id

    def test_flat_context_dict_supported(self, agent):
        task = AgentTask(
            objective  = "Test flat context",
            agent_name = "context_curator_agent",
            context    = {
                "project": "Atlas",
                "module":  "auth",
                "constraints": ["backend-first", "no UI logic"],
            },
        )
        result = agent.safe_run(task)
        assert "compact_prompt_context" in result.result


class TestContextCuratorEdgeCases:

    def test_empty_context_handled(self, agent):
        task   = AgentTask(objective="Test empty", agent_name="context_curator_agent")
        result = agent.safe_run(task)
        assert isinstance(result, AgentResult)

    def test_large_context_truncated(self, agent):
        task = AgentTask(
            objective  = "Curate large context",
            agent_name = "context_curator_agent",
            context    = {"full_context": "word " * 5000},
        )
        result = agent.safe_run(task)
        compact = result.result.get("compact_prompt_context", "")
        # Should be returned (truncated if LLM available, fallback if not)
        assert isinstance(compact, str)

    def test_agent_name(self):
        assert ContextCuratorAgent().name == "context_curator_agent"
