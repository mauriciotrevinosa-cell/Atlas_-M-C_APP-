"""Tests for ReviewerAgent."""

import json
import pytest

from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult
from atlas.core.ai_assistant.agents.reviewer_agent import ReviewerAgent


@pytest.fixture
def agent_no_llm():
    return ReviewerAgent()


@pytest.fixture
def agent_approve():
    review = {
        "verdict":           "approve",
        "summary":           "Código limpio, bien estructurado y testeable.",
        "critical_findings": [],
        "important_findings": [],
        "minor_findings":    [{"issue": "Nombre poco claro", "suggestion": "renombrar a validate_permission"}],
        "good_parts":        ["Separación clara de capas", "Código legible"],
        "merge_recommendation": "merge",
        "concrete_fixes":    [],
    }
    return ReviewerAgent(llm_client=lambda p: json.dumps(review))


@pytest.fixture
def agent_reject():
    review = {
        "verdict":           "changes_requested",
        "summary":           "Hay vulnerabilidades críticas de seguridad.",
        "critical_findings": [{"issue": "Permisos validados en frontend", "why_it_matters": "Bypasseable", "line_hint": "L42"}],
        "important_findings": [],
        "minor_findings":    [],
        "good_parts":        [],
        "merge_recommendation": "do_not_merge_yet",
        "concrete_fixes":    ["Mover validación al backend"],
    }
    return ReviewerAgent(llm_client=lambda p: json.dumps(review))


@pytest.fixture
def code_task():
    return AgentTask(
        objective  = "Revisar implementación de permisos",
        agent_name = "reviewer_agent",
        inputs     = {"code": "def check_perm(user, action): return user.role == 'admin'"},
        context    = {"project": "Atlas", "module": "auth"},
    )


@pytest.fixture
def diff_task():
    return AgentTask(
        objective  = "Revisar diff de auth",
        agent_name = "reviewer_agent",
        inputs     = {"diff": "+def new_check(): pass\n-def old_check(): pass"},
        context    = {"project": "Atlas"},
    )


# ── Nominal ───────────────────────────────────────────────────────────────────

class TestReviewerNominal:

    def test_stub_returns_result(self, agent_no_llm, code_task):
        result = agent_no_llm.safe_run(code_task)
        assert isinstance(result, AgentResult)

    def test_stub_has_verdict(self, agent_no_llm, code_task):
        result = agent_no_llm.safe_run(code_task)
        assert "verdict" in result.result

    def test_stub_has_merge_rec(self, agent_no_llm, code_task):
        result = agent_no_llm.safe_run(code_task)
        assert "merge_recommendation" in result.result

    def test_approve_verdict(self, agent_approve, code_task):
        result = agent_approve.safe_run(code_task)
        assert result.result["verdict"] == "approve"
        assert result.result["merge_recommendation"] == "merge"
        assert result.status == "success"

    def test_reject_verdict(self, agent_reject, code_task):
        result = agent_reject.safe_run(code_task)
        assert result.result["verdict"] == "changes_requested"
        assert result.result["merge_recommendation"] == "do_not_merge_yet"
        assert len(result.result["critical_findings"]) > 0

    def test_diff_input_accepted(self, agent_no_llm, diff_task):
        result = agent_no_llm.safe_run(diff_task)
        assert isinstance(result, AgentResult)
        assert result.task_id == diff_task.task_id

    def test_metadata_contains_verdict(self, agent_approve, code_task):
        result = agent_approve.safe_run(code_task)
        assert result.metadata.get("verdict") in ("approve", "changes_requested", "reject", "needs_more_info")


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestReviewerEdgeCases:

    def test_empty_code_and_objective_fails(self, agent_no_llm):
        task = AgentTask(
            objective  = "",
            agent_name = "reviewer_agent",
            inputs     = {},
        )
        result = agent_no_llm.safe_run(task)
        assert result.status == "error"

    def test_objective_used_when_no_code(self, agent_no_llm):
        task = AgentTask(
            objective  = "Review this function",
            agent_name = "reviewer_agent",
            inputs     = {},
        )
        result = agent_no_llm.safe_run(task)
        assert isinstance(result, AgentResult)

    def test_invalid_verdict_normalized(self):
        """Garbage verdict from LLM is normalized to 'needs_more_info'."""
        bad_review = {
            "verdict": "maybe_kinda_ok",
            "summary": "Unclear.",
            "critical_findings": [],
            "important_findings": [],
            "minor_findings": [],
            "good_parts": [],
            "merge_recommendation": "whatever",
            "concrete_fixes": [],
        }
        agent  = ReviewerAgent(llm_client=lambda p: json.dumps(bad_review))
        task   = AgentTask(objective="X", agent_name="reviewer_agent", inputs={"code": "x=1"})
        result = agent.safe_run(task)
        assert result.result["verdict"] in ReviewerAgent.VALID_VERDICTS
        assert result.result["merge_recommendation"] in ReviewerAgent.VALID_MERGE_RECS


# ── Error cases ───────────────────────────────────────────────────────────────

class TestReviewerErrors:

    def test_llm_garbage_json_degrades(self):
        agent  = ReviewerAgent(llm_client=lambda p: "not json")
        task   = AgentTask(objective="Review", agent_name="reviewer_agent", inputs={"code": "x=1"})
        result = agent.safe_run(task)
        assert result.status in ("error", "partial")

    def test_agent_name_is_reviewer(self):
        assert ReviewerAgent().name == "reviewer_agent"
