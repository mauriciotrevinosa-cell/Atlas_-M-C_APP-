"""Tests for RepoScoutAgent."""

import json
from types import SimpleNamespace

import pytest

from atlas.core.ai_assistant.agents.repo_scout_agent import RepoScoutAgent
from atlas.core.ai_assistant.task_schema import AgentResult, AgentTask


@pytest.fixture
def scout_payload():
    return {
        "solution_categories": ["agent orchestration", "context retrieval"],
        "repeated_patterns": ["small specialist agents", "JSON contracts"],
        "copy_conceptually": ["agent registry", "tool allowlists"],
        "avoid_copying": ["vendor-specific framework lock-in"],
        "adoption_risks": ["license review required"],
        "proposal_for_atlas": ["Keep Atlas agents behind the existing registry"],
        "references": [{"name": "LangGraph", "reason": "workflow graph pattern"}],
        "summary": "Scout found reusable orchestration patterns.",
    }


@pytest.fixture
def task():
    return AgentTask(
        task_id="scout-1",
        objective="Research agent orchestration patterns for Atlas",
        agent_name="repo_scout_agent",
        context={
            "criteria": ["Python compatible", "permissive license"],
            "constraints": ["No runtime downloads"],
        },
        inputs={},
    )


class TestRepoScoutNominal:
    def test_no_llm_returns_stub_partial(self, task):
        result = RepoScoutAgent().safe_run(task)

        assert isinstance(result, AgentResult)
        assert result.status == "partial"
        assert result.task_id == task.task_id
        assert "solution_categories" in result.result
        assert "stub" in result.summary.lower()

    def test_callable_llm_success(self, task, scout_payload):
        agent = RepoScoutAgent(llm_client=lambda prompt: json.dumps(scout_payload))
        result = agent.safe_run(task)

        assert result.status == "success"
        assert result.result["repeated_patterns"] == scout_payload["repeated_patterns"]
        assert result.result["references"][0]["name"] == "LangGraph"

    def test_model_router_generate_success(self, task, scout_payload):
        class Router:
            def generate(self, prompt, agent_name, risk_level):
                assert agent_name == "repo_scout_agent"
                assert risk_level == task.risk_level
                return SimpleNamespace(text=json.dumps(scout_payload))

        result = RepoScoutAgent(llm_client=Router()).safe_run(task)

        assert result.status == "success"
        assert result.result["proposal_for_atlas"]

    def test_criteria_can_come_from_inputs(self, scout_payload):
        captured = {}

        def llm(prompt):
            captured["prompt"] = prompt
            return json.dumps(scout_payload)

        task = AgentTask(
            objective="Research vector databases",
            agent_name="repo_scout_agent",
            inputs={"criteria": "local first, simple persistence"},
        )

        result = RepoScoutAgent(llm_client=llm).safe_run(task)

        assert result.status == "success"
        assert "local first" in captured["prompt"]


class TestRepoScoutParsing:
    def test_markdown_json_fence_parsed(self, task, scout_payload):
        agent = RepoScoutAgent(llm_client=lambda prompt: f"```json\n{json.dumps(scout_payload)}\n```")

        result = agent.safe_run(task)

        assert result.status == "success"
        assert result.result["summary"] == scout_payload["summary"]

    def test_embedded_json_parsed(self, task, scout_payload):
        agent = RepoScoutAgent(llm_client=lambda prompt: f"Notes before {json.dumps(scout_payload)} after")

        result = agent.safe_run(task)

        assert result.status == "success"
        assert "agent orchestration" in result.result["solution_categories"]

    def test_garbage_json_degrades_to_stub(self, task):
        result = RepoScoutAgent(llm_client=lambda prompt: "not json").safe_run(task)

        assert result.status == "partial"
        assert result.errors
        assert "proposal_for_atlas" in result.result

    def test_generate_exception_degrades_to_stub(self, task):
        class FailingRouter:
            def generate(self, prompt, agent_name, risk_level):
                raise RuntimeError("provider down")

        result = RepoScoutAgent(llm_client=FailingRouter()).safe_run(task)

        assert result.status == "partial"
        assert result.errors
        assert result.metadata["agent"] == "repo_scout_agent"

    def test_empty_objective_is_validation_error(self):
        task = AgentTask(objective="", agent_name="repo_scout_agent")

        result = RepoScoutAgent().safe_run(task)

        assert result.status == "error"
        assert "objective cannot be empty" in result.errors[0]

    def test_agent_identity(self):
        agent = RepoScoutAgent()

        assert agent.name == "repo_scout_agent"
        assert agent.version == "v1"
