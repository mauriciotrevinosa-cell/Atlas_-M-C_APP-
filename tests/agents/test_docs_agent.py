"""Tests for DocsAgent."""

import json
import pytest

from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult
from atlas.core.ai_assistant.agents.docs_agent import DocsAgent, DOC_TYPES


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def agent():
    return DocsAgent()


@pytest.fixture
def agent_with_mock():
    doc = {
        "document_type": "module_spec",
        "title":         "Auth Module Spec",
        "content":       "# Auth Module\n\n## Purpose\nHandles RBAC.\n\n## API\n...",
        "metadata":      {"generated_at": "2026-01-01T00:00:00", "version": "1.0"},
        "summary":       "Module spec for Auth.",
    }
    return DocsAgent(llm_client=lambda p: json.dumps(doc))


@pytest.fixture
def adr_task():
    return AgentTask(
        objective  = "Adopt FastAPI over Flask for REST endpoints",
        agent_name = "docs_agent",
        inputs     = {"document_type": "adr"},
        context    = {
            "module":             "api_gateway",
            "change_description": "Switch web framework",
            "files_changed":      ["api/server.py", "requirements.txt"],
        },
    )


@pytest.fixture
def module_spec_task():
    return AgentTask(
        objective  = "Document the Auth module",
        agent_name = "docs_agent",
        inputs     = {"document_type": "module_spec"},
        context    = {"module": "auth"},
    )


@pytest.fixture
def changelog_task():
    return AgentTask(
        objective  = "Add RBAC system",
        agent_name = "docs_agent",
        inputs     = {"document_type": "changelog"},
        context    = {"module": "auth"},
    )


# ── Nominal tests ─────────────────────────────────────────────────────────────

class TestDocsAgentNominal:

    def test_returns_agent_result(self, agent, module_spec_task):
        result = agent.safe_run(module_spec_task)
        assert isinstance(result, AgentResult)

    def test_stub_adr_has_status_section(self, agent, adr_task):
        result = agent.safe_run(adr_task)
        content = result.result.get("content", "")
        assert "Status" in content or "ADR" in content

    def test_stub_adr_has_context_section(self, agent, adr_task):
        result = agent.safe_run(adr_task)
        content = result.result.get("content", "")
        assert "Context" in content

    def test_stub_adr_has_decision_section(self, agent, adr_task):
        result = agent.safe_run(adr_task)
        content = result.result.get("content", "")
        assert "Decision" in content

    def test_stub_changelog_has_added(self, agent, changelog_task):
        result = agent.safe_run(changelog_task)
        content = result.result.get("content", "")
        assert "Added" in content

    def test_stub_module_spec_has_purpose(self, agent, module_spec_task):
        result = agent.safe_run(module_spec_task)
        content = result.result.get("content", "")
        assert "Propósito" in content or "Purpose" in content or "#" in content

    def test_result_has_document_type(self, agent, module_spec_task):
        result = agent.safe_run(module_spec_task)
        assert "document_type" in result.result

    def test_result_has_title(self, agent, module_spec_task):
        result = agent.safe_run(module_spec_task)
        assert "title" in result.result

    def test_result_has_content(self, agent, module_spec_task):
        result = agent.safe_run(module_spec_task)
        assert "content" in result.result
        assert len(result.result["content"]) > 0

    def test_task_id_preserved(self, agent, module_spec_task):
        result = agent.safe_run(module_spec_task)
        assert result.task_id == module_spec_task.task_id

    def test_metadata_has_word_count(self, agent, module_spec_task):
        result = agent.safe_run(module_spec_task)
        assert "word_count" in result.metadata
        assert result.metadata["word_count"] > 0

    def test_mock_llm_returns_success(self, agent_with_mock, module_spec_task):
        result = agent_with_mock.safe_run(module_spec_task)
        assert result.status == "success"

    def test_mock_llm_summary_present(self, agent_with_mock, module_spec_task):
        result = agent_with_mock.safe_run(module_spec_task)
        assert len(result.summary) > 0


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestDocsAgentEdgeCases:

    def test_unknown_doc_type_defaults_to_module_spec(self, agent):
        task = AgentTask(
            objective  = "Generate docs",
            agent_name = "docs_agent",
            inputs     = {"document_type": "unknown_type"},
        )
        result = agent.safe_run(task)
        assert result.result.get("document_type") == "module_spec"

    def test_no_inputs_uses_module_spec(self, agent):
        task = AgentTask(
            objective  = "Generate docs",
            agent_name = "docs_agent",
            inputs     = {},
        )
        result = agent.safe_run(task)
        assert isinstance(result, AgentResult)
        assert "content" in result.result

    def test_readme_doc_type(self, agent):
        task = AgentTask(
            objective  = "Write README",
            agent_name = "docs_agent",
            inputs     = {"document_type": "readme"},
            context    = {"module": "atlas"},
        )
        result = agent.safe_run(task)
        assert isinstance(result, AgentResult)
        assert result.result.get("document_type") == "readme"

    def test_api_doc_type(self, agent):
        task = AgentTask(
            objective  = "Document API",
            agent_name = "docs_agent",
            inputs     = {"document_type": "api_doc"},
            context    = {"module": "api"},
        )
        result = agent.safe_run(task)
        assert isinstance(result, AgentResult)

    def test_agent_name(self):
        assert DocsAgent().name == "docs_agent"

    def test_agent_version(self):
        assert DocsAgent().version == "v1"

    def test_all_doc_types_produce_content(self, agent):
        for doc_type in DOC_TYPES:
            task = AgentTask(
                objective  = f"Test {doc_type}",
                agent_name = "docs_agent",
                inputs     = {"document_type": doc_type},
                context    = {"module": "test_module"},
            )
            result = agent.safe_run(task)
            assert "content" in result.result, f"No content for doc_type={doc_type}"
            assert len(result.result["content"]) > 0
