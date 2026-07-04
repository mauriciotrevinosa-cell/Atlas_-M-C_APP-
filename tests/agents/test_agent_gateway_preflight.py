from __future__ import annotations

from atlas.core.ai_assistant.agent_registry import AgentRegistry
from atlas.core.ai_assistant.agents.base import BaseAgent
from atlas.core.ai_assistant.audit.task_logs import TaskLogger
from atlas.core.ai_assistant.orchestrator import AgentOrchestrator
from atlas.core.ai_assistant.task_schema import AgentResult, AgentTask


class DummyAgent(BaseAgent):
    name = "dummy_agent"
    version = "v1"

    def run(self, task: AgentTask) -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            status="success",
            summary="Dummy completed.",
            result={"ran": True},
        )


def _orchestrator(tmp_path):
    registry = AgentRegistry()
    registry.register(DummyAgent())
    return AgentOrchestrator(registry=registry, logger=TaskLogger(log_dir=tmp_path))


def test_gateway_denies_globally_blocked_tool(tmp_path):
    orch = _orchestrator(tmp_path)
    task = AgentTask(
        objective="Try unsafe deployment",
        agent_name="dummy_agent",
        allowed_tools=["deploy_production"],
    )

    result = orch.execute(task)

    assert result.status == "error"
    assert "Gateway preflight denied" in result.summary
    assert result.metadata["gateway_preflight"]["allowed"] is False
    assert result.metadata["gateway_preflight"]["denied_tools"] == ["deploy_production"]


def test_gateway_denies_live_mode(tmp_path):
    orch = _orchestrator(tmp_path)
    task = AgentTask(
        objective="Execute live trading order",
        agent_name="dummy_agent",
        context={"mode": "live"},
    )

    result = orch.execute(task)

    assert result.status == "error"
    assert result.metadata["gateway_preflight"]["mode"] == "live"
    assert "live or production" in result.errors[0]


def test_gateway_denies_critical_without_human_approval(tmp_path):
    orch = _orchestrator(tmp_path)
    task = AgentTask(
        objective="Critical task",
        agent_name="dummy_agent",
        risk_level="critical",
    )

    result = orch.execute(task)

    assert result.status == "error"
    assert result.metadata["gateway_preflight"]["requires_approval"] is True


def test_gateway_allows_paper_mode_and_audits_preflight(tmp_path):
    orch = _orchestrator(tmp_path)
    task = AgentTask(
        objective="Read sandbox context",
        agent_name="dummy_agent",
        context={"mode": "paper", "human_approved": True},
        allowed_tools=["read_file"],
    )

    result = orch.execute(task)

    assert result.status == "success"
    assert result.result == {"ran": True}
    assert result.metadata["gateway_preflight"]["allowed"] is True
    assert result.metadata["gateway_preflight"]["mode"] == "paper"
    assert orch.logger.load_checkpoint(task.task_id)["result"]["status"] == "success"
