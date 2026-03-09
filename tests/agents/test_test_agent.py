"""Tests for TestAgent."""

import json
import pytest

from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult
from atlas.core.ai_assistant.agents.test_agent import TestDesignAgent as TestAgent


@pytest.fixture
def agent():
    return TestAgent()


@pytest.fixture
def agent_with_mock():
    design = {
        "functional_risks":  ["rol heredado mal resuelto"],
        "nominal_cases":     [{"name": "test_permiso_valido", "description": "Owner puede acceder"}],
        "edge_cases":        [{"name": "test_rol_inexistente", "description": "Rol vacío"}],
        "error_cases":       [{"name": "test_formato_invalido", "description": "Permiso malformado"}],
        "fixtures_needed":   ["roles_mock"],
        "pytest_starter_code": "import pytest\n\ndef test_permiso_valido():\n    assert True\n",
        "missing_coverage":  ["integración con middleware"],
        "summary":           "Tests completos para módulo de permisos.",
    }
    return TestAgent(llm_client=lambda p: json.dumps(design))


@pytest.fixture
def task():
    return AgentTask(
        objective  = "Testear sistema de permisos RBAC",
        agent_name = "test_agent",
        inputs     = {"code": "def check_permission(user, resource): return user.role in ALLOWED_ROLES[resource]"},
        context    = {"module": "auth"},
    )


class TestTestAgentNominal:

    def test_stub_returns_result(self, agent, task):
        result = agent.safe_run(task)
        assert isinstance(result, AgentResult)

    def test_stub_has_pytest_code(self, agent, task):
        result = agent.safe_run(task)
        code = result.result.get("pytest_starter_code", "")
        assert "def test_" in code

    def test_mock_nominal_cases(self, agent_with_mock, task):
        result = agent_with_mock.safe_run(task)
        assert result.status == "success"
        assert len(result.result["nominal_cases"]) >= 1

    def test_mock_edge_cases(self, agent_with_mock, task):
        result = agent_with_mock.safe_run(task)
        assert len(result.result["edge_cases"]) >= 1

    def test_mock_error_cases(self, agent_with_mock, task):
        result = agent_with_mock.safe_run(task)
        assert len(result.result["error_cases"]) >= 1

    def test_metadata_counts(self, agent_with_mock, task):
        result = agent_with_mock.safe_run(task)
        assert result.metadata["n_nominal"] >= 1
        assert result.metadata["n_edge"] >= 1

    def test_task_id_preserved(self, agent, task):
        result = agent.safe_run(task)
        assert result.task_id == task.task_id


class TestTestAgentEdgeCases:

    def test_no_code_still_runs(self, agent):
        task   = AgentTask(objective="Test auth", agent_name="test_agent", inputs={})
        result = agent.safe_run(task)
        assert isinstance(result, AgentResult)

    def test_agent_name(self):
        assert TestAgent().name == "test_agent"
