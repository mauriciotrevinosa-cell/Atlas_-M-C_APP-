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


class TestTestAgentParsingAndErrors:

    def test_markdown_json_fence_parsed(self, task):
        design = {
            "functional_risks": ["auth bypass"],
            "nominal_cases": [{"name": "test_valid_permission"}],
            "edge_cases": [{"name": "test_empty_role"}],
            "error_cases": [{"name": "test_bad_permission"}],
            "fixtures_needed": ["user_factory"],
            "pytest_starter_code": "def test_valid_permission():\n    assert True\n",
            "missing_coverage": [],
            "summary": "Designed tests.",
        }
        agent = TestAgent(llm_client=lambda p: f"```json\n{json.dumps(design)}\n```")

        result = agent.safe_run(task)

        assert result.status == "success"
        assert result.result["functional_risks"] == ["auth bypass"]

    def test_embedded_json_parsed(self, task):
        design = {
            "functional_risks": [],
            "nominal_cases": [{"name": "test_happy_path"}],
            "edge_cases": [],
            "error_cases": [],
            "fixtures_needed": [],
            "pytest_starter_code": "def test_happy_path():\n    assert True\n",
            "missing_coverage": [],
            "summary": "Designed.",
        }
        agent = TestAgent(llm_client=lambda p: f"LLM notes before {json.dumps(design)}")

        result = agent.safe_run(task)

        assert result.status == "success"
        assert result.metadata["n_nominal"] == 1

    def test_garbage_json_returns_error(self, task):
        agent = TestAgent(llm_client=lambda p: "not json")

        result = agent.safe_run(task)

        assert result.status == "error"
        assert result.errors
        assert "raw_response" in result.result

    def test_missing_keys_mark_result_partial(self, task):
        agent = TestAgent(llm_client=lambda p: json.dumps({"summary": "too small"}))

        result = agent.safe_run(task)

        assert result.status == "partial"
        assert any("Missing test keys" in err for err in result.errors)

    def test_pytest_starter_without_tests_is_partial(self, task):
        design = {
            "functional_risks": [],
            "nominal_cases": [],
            "edge_cases": [],
            "error_cases": [],
            "fixtures_needed": [],
            "pytest_starter_code": "print('no tests here')",
            "missing_coverage": [],
            "summary": "Designed.",
        }
        agent = TestAgent(llm_client=lambda p: json.dumps(design))

        result = agent.safe_run(task)

        assert result.status == "partial"
        assert any("no test functions" in err for err in result.errors)

    def test_generate_exception_degrades_to_stub(self, task):
        class FailingRouter:
            def generate(self, prompt, agent_name, risk_level, model_prefs):
                raise RuntimeError("timeout")

        result = TestAgent(llm_client=FailingRouter()).safe_run(task)

        assert result.status == "success"
        assert "pytest_starter_code" in result.result
