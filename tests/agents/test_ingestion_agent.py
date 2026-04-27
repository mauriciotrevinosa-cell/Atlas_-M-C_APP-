"""Tests for IngestionAgent."""

import json
from types import SimpleNamespace

import pytest

from atlas.core.ai_assistant.agents.ingestion_agent import IngestionAgent
from atlas.core.ai_assistant.task_schema import AgentResult, AgentTask


@pytest.fixture
def ingestion_payload():
    return {
        "executive_summary": "Atlas RBAC document explains backend-first permission checks.",
        "key_concepts": ["RBAC", "backend validation"],
        "entities": [{"type": "role", "name": "Owner"}],
        "relations": [{"from": "Owner", "to": "Project", "relation": "controls"}],
        "actionable_data": ["Move permission checks to server routes"],
        "ambiguities": ["Worker role boundaries need confirmation"],
        "knowledge_pack": {
            "domain": "atlas_auth",
            "version": "v1",
            "facts": [{"subject": "RBAC", "predicate": "validated_at", "object": "backend"}],
        },
        "summary": "Ingestion completed for Atlas RBAC.",
    }


@pytest.fixture
def task():
    return AgentTask(
        task_id="ingest-1",
        objective="Ingest Atlas auth design notes",
        agent_name="ingestion_agent",
        inputs={
            "source": "Roles: Client, Worker, Owner. Permissions must be checked by backend APIs.",
            "source_type": "text",
        },
    )


class TestIngestionNominal:
    def test_no_llm_returns_stub_partial(self, task):
        result = IngestionAgent().safe_run(task)

        assert isinstance(result, AgentResult)
        assert result.status == "partial"
        assert result.task_id == task.task_id
        assert "knowledge_pack" in result.result
        assert result.result["knowledge_pack"]["task_id"] == task.task_id

    def test_callable_llm_success(self, task, ingestion_payload):
        agent = IngestionAgent(llm_client=lambda prompt: json.dumps(ingestion_payload))

        result = agent.safe_run(task)

        assert result.status == "success"
        assert result.result["key_concepts"] == ["RBAC", "backend validation"]
        assert result.metadata["n_facts"] == 1

    def test_model_router_generate_success(self, task, ingestion_payload):
        class Router:
            def generate(self, prompt, agent_name, risk_level):
                assert agent_name == "ingestion_agent"
                assert risk_level == task.risk_level
                return SimpleNamespace(text=json.dumps(ingestion_payload))

        result = IngestionAgent(llm_client=Router()).safe_run(task)

        assert result.status == "success"
        assert result.result["executive_summary"].startswith("Atlas RBAC")

    def test_objective_used_when_source_missing(self, ingestion_payload):
        captured = {}

        def llm(prompt):
            captured["prompt"] = prompt
            return json.dumps(ingestion_payload)

        task = AgentTask(objective="Raw objective text to ingest", agent_name="ingestion_agent")

        result = IngestionAgent(llm_client=llm).safe_run(task)

        assert result.status == "success"
        assert "Raw objective text to ingest" in captured["prompt"]


class TestIngestionNormalization:
    def test_missing_pack_fields_are_added(self, task):
        payload = {
            "executive_summary": "Summary",
            "key_concepts": ["concept"],
            "entities": [],
            "relations": [],
            "actionable_data": [],
            "ambiguities": [],
            "knowledge_pack": {},
            "summary": "Done",
        }

        result = IngestionAgent(llm_client=lambda prompt: json.dumps(payload)).safe_run(task)
        pack = result.result["knowledge_pack"]

        assert result.status == "success"
        assert pack["domain"] == "atlas_general"
        assert pack["version"] == "v1"
        assert pack["task_id"] == task.task_id
        assert "ingested_at" in pack

    def test_missing_knowledge_pack_is_normalized(self, task):
        payload = {
            "executive_summary": "Summary",
            "key_concepts": [],
            "entities": [],
            "relations": [],
            "actionable_data": [],
            "ambiguities": [],
            "summary": "Done",
        }

        result = IngestionAgent(llm_client=lambda prompt: json.dumps(payload)).safe_run(task)

        assert result.status == "success"
        assert result.result["knowledge_pack"]["facts"] == []


class TestIngestionParsing:
    def test_markdown_json_fence_parsed(self, task, ingestion_payload):
        agent = IngestionAgent(llm_client=lambda prompt: f"```json\n{json.dumps(ingestion_payload)}\n```")

        result = agent.safe_run(task)

        assert result.status == "success"
        assert result.result["summary"] == ingestion_payload["summary"]

    def test_embedded_json_parsed(self, task, ingestion_payload):
        agent = IngestionAgent(llm_client=lambda prompt: f"Result follows: {json.dumps(ingestion_payload)}")

        result = agent.safe_run(task)

        assert result.status == "success"
        assert result.result["actionable_data"]

    def test_garbage_json_degrades_to_stub(self, task):
        result = IngestionAgent(llm_client=lambda prompt: "not json").safe_run(task)

        assert result.status == "partial"
        assert result.errors
        assert result.result["knowledge_pack"]["domain"] == "atlas_general"

    def test_generate_exception_degrades_to_stub(self, task):
        class FailingRouter:
            def generate(self, prompt, agent_name, risk_level):
                raise RuntimeError("provider unavailable")

        result = IngestionAgent(llm_client=FailingRouter()).safe_run(task)

        assert result.status == "partial"
        assert result.errors
        assert result.metadata["agent"] == "ingestion_agent"

    def test_empty_objective_is_validation_error(self):
        task = AgentTask(objective="", agent_name="ingestion_agent", inputs={"source": "content"})

        result = IngestionAgent().safe_run(task)

        assert result.status == "error"

    def test_agent_identity(self):
        agent = IngestionAgent()

        assert agent.name == "ingestion_agent"
        assert agent.version == "v1"
