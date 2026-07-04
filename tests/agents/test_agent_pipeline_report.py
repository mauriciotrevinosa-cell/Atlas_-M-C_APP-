from __future__ import annotations

from atlas.core.ai_assistant.agent_registry import AgentRegistry
from atlas.core.ai_assistant.agents.base import BaseAgent
from atlas.core.ai_assistant.audit.task_logs import TaskLogger
from atlas.core.ai_assistant.orchestrator import AgentOrchestrator, PipelineRunReport
from atlas.core.ai_assistant.task_schema import AgentResult, AgentTask


class PipelineAgent(BaseAgent):
    name = "pipeline_agent"
    version = "v1"

    def run(self, task: AgentTask) -> AgentResult:
        if task.inputs.get("fail"):
            return AgentResult.error_result(task.task_id, "requested failure", self.name)
        return AgentResult(
            task_id=task.task_id,
            status="success",
            summary="Pipeline step completed.",
            result={"objective": task.objective},
        )


def _orchestrator(tmp_path):
    registry = AgentRegistry()
    registry.register(PipelineAgent())
    return AgentOrchestrator(registry=registry, logger=TaskLogger(log_dir=tmp_path))


def test_pipeline_report_summarizes_success(tmp_path):
    orch = _orchestrator(tmp_path)
    tasks = [
        AgentTask(objective="Step 1", agent_name="pipeline_agent"),
        AgentTask(objective="Step 2", agent_name="pipeline_agent"),
    ]

    report = orch.pipeline_report(tasks)

    assert isinstance(report, PipelineRunReport)
    assert report.ok is True
    assert report.succeeded == 2
    assert report.failed == 0
    assert report.to_dict()["agents"] == ["pipeline_agent", "pipeline_agent"]


def test_pipeline_report_marks_stop_on_error(tmp_path):
    orch = _orchestrator(tmp_path)
    tasks = [
        AgentTask(objective="Step 1", agent_name="pipeline_agent"),
        AgentTask(objective="Step fail", agent_name="pipeline_agent", inputs={"fail": True}),
        AgentTask(objective="Step skipped", agent_name="pipeline_agent"),
    ]

    report = orch.pipeline_report(tasks, stop_on_error=True)

    assert report.ok is False
    assert report.total == 2
    assert report.failed == 1
    assert report.stopped_on_error is True
