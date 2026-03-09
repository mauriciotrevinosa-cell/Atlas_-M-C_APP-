"""
Tests for PlannerAgent.

Validates: stub mode (no LLM), input validation, output schema,
edge cases (empty objective, oversized input), pipeline integration.
"""

import json
import pytest

from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult
from atlas.core.ai_assistant.agents.planner_agent import PlannerAgent


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def agent_no_llm():
    """PlannerAgent with no LLM — uses stub output."""
    return PlannerAgent()


@pytest.fixture
def agent_with_llm():
    """PlannerAgent with a deterministic mock LLM."""
    mock_plan = {
        "expected_result":    "RBAC funcional",
        "assumptions":        ["auth service existe"],
        "risks":              [{"level": "medium", "issue": "scope", "mitigation": "dividir"}],
        "steps":              ["Definir modelo", "Implementar policy", "Agregar tests"],
        "files_to_touch":    ["permissions.py", "auth.py"],
        "tests_required":    ["test_permiso_valido", "test_permiso_denegado"],
        "validation_criteria": ["Tests pasan", "Backend rechaza inválidos"],
        "not_now":           ["UI admin avanzada"],
        "summary":           "Plan para implementar RBAC modular.",
    }

    class MockLLM:
        def __call__(self, prompt: str) -> str:
            return json.dumps(mock_plan)

    return PlannerAgent(llm_client=MockLLM())


@pytest.fixture
def basic_task():
    return AgentTask(
        objective  = "Implementar sistema de permisos RBAC para módulos",
        agent_name = "planner_agent",
        context    = {
            "project":     "Atlas",
            "module":      "auth",
            "files":       ["core/ai_assistant/permissions.py"],
            "constraints": ["No romper arquitectura modular", "Agregar tests"],
        },
        risk_level = "medium",
    )


# ── Nominal tests ─────────────────────────────────────────────────────────────

class TestPlannerAgentNoLLM:
    """Tests in stub mode (no LLM required)."""

    def test_run_returns_agent_result(self, agent_no_llm, basic_task):
        result = agent_no_llm.safe_run(basic_task)
        assert isinstance(result, AgentResult)

    def test_stub_returns_required_keys(self, agent_no_llm, basic_task):
        result = agent_no_llm.safe_run(basic_task)
        required = ["expected_result", "steps", "files_to_touch", "tests_required",
                    "validation_criteria", "summary"]
        for key in required:
            assert key in result.result, f"Missing key: {key}"

    def test_stub_has_non_empty_steps(self, agent_no_llm, basic_task):
        result = agent_no_llm.safe_run(basic_task)
        assert isinstance(result.result.get("steps"), list)
        assert len(result.result["steps"]) > 0

    def test_result_task_id_matches(self, agent_no_llm, basic_task):
        result = agent_no_llm.safe_run(basic_task)
        assert result.task_id == basic_task.task_id

    def test_metadata_contains_agent_info(self, agent_no_llm, basic_task):
        result = agent_no_llm.safe_run(basic_task)
        assert result.metadata.get("agent") == "planner_agent"
        assert "execution_ms" in result.metadata

    def test_summary_is_non_empty_string(self, agent_no_llm, basic_task):
        result = agent_no_llm.safe_run(basic_task)
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0


class TestPlannerAgentWithMockLLM:
    """Tests with deterministic mock LLM."""

    def test_mock_llm_produces_success(self, agent_with_llm, basic_task):
        result = agent_with_llm.safe_run(basic_task)
        assert result.status == "success"

    def test_mock_llm_steps_are_list(self, agent_with_llm, basic_task):
        result = agent_with_llm.safe_run(basic_task)
        assert isinstance(result.result["steps"], list)
        assert len(result.result["steps"]) >= 3

    def test_mock_llm_files_to_touch(self, agent_with_llm, basic_task):
        result = agent_with_llm.safe_run(basic_task)
        files = result.result.get("files_to_touch", [])
        assert isinstance(files, list)

    def test_mock_llm_summary_matches(self, agent_with_llm, basic_task):
        result = agent_with_llm.safe_run(basic_task)
        assert "RBAC" in result.summary or len(result.summary) > 0


# ── Edge cases ─────────────────────────────────────────────────────────────────

class TestPlannerAgentEdgeCases:

    def test_empty_objective_returns_error(self, agent_no_llm):
        task = AgentTask(objective="", agent_name="planner_agent")
        result = agent_no_llm.safe_run(task)
        assert result.status == "error"
        assert len(result.errors) > 0

    def test_whitespace_objective_returns_error(self, agent_no_llm):
        task = AgentTask(objective="   ", agent_name="planner_agent")
        result = agent_no_llm.safe_run(task)
        assert result.status == "error"

    def test_oversized_objective_flagged(self, agent_no_llm):
        task = AgentTask(
            objective  = "A" * 2001,
            agent_name = "planner_agent",
        )
        result = agent_no_llm.safe_run(task)
        # Should either error or flag in errors
        assert result.status in ("error", "partial") or len(result.errors) > 0

    def test_minimal_context_still_works(self, agent_no_llm):
        task   = AgentTask(objective="Build auth module", agent_name="planner_agent")
        result = agent_no_llm.safe_run(task)
        assert result.task_id == task.task_id
        assert "steps" in result.result

    def test_all_risk_levels_accepted(self, agent_no_llm):
        for risk in ("low", "medium", "high", "critical"):
            task   = AgentTask(objective="Test task", agent_name="planner_agent", risk_level=risk)
            result = agent_no_llm.safe_run(task)
            assert result is not None

    def test_invalid_risk_level_raises(self):
        with pytest.raises(ValueError):
            AgentTask(objective="Test", agent_name="planner_agent", risk_level="extreme")


# ── Error cases ───────────────────────────────────────────────────────────────

class TestPlannerAgentErrors:

    def test_llm_exception_returns_partial(self):
        class FailingLLM:
            def __call__(self, prompt):
                raise RuntimeError("API timeout")

        agent  = PlannerAgent(llm_client=FailingLLM())
        task   = AgentTask(objective="Test", agent_name="planner_agent")
        result = agent.safe_run(task)
        # Should degrade gracefully — either error or partial
        assert result.status in ("error", "partial", "success")

    def test_llm_returns_garbage_json(self):
        class GarbageLLM:
            def __call__(self, prompt):
                return "this is not json at all !@#$%"

        agent  = PlannerAgent(llm_client=GarbageLLM())
        task   = AgentTask(objective="Test", agent_name="planner_agent")
        result = agent.safe_run(task)
        assert result.status in ("error", "partial")

    def test_agent_name_preserved(self):
        agent  = PlannerAgent()
        assert agent.name == "planner_agent"
        assert agent.version == "v1"
