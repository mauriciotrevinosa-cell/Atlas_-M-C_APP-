"""
ARIA tool wrapper for the Atlas agent orchestration system.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from atlas.assistants.aria.tools.base import Tool
from atlas.core.ai_assistant.task_schema import AgentTask


class AtlasAgentTaskTool(Tool):
    """
    Run a structured Atlas agent task and return the structured result.
    """

    def __init__(self, orchestrator=None):
        super().__init__(
            name="atlas_agent_task",
            description="Run a structured Atlas agent task for planning, research, ingestion, documentation, or code proposals.",
            category="agents",
        )
        self._orchestrator = orchestrator
        self.add_parameter("agent_name", "string", "Agent to run, such as planner_agent or repo_scout_agent.")
        self.add_parameter("objective", "string", "Primary objective for the selected agent.")
        self.add_parameter(
            "risk_level",
            "string",
            "Risk level: low, medium, high, or critical.",
            required=False,
            default="low",
        )
        self.add_parameter(
            "context",
            "object",
            "Optional structured context dictionary for the agent.",
            required=False,
            default={},
        )
        self.add_parameter(
            "inputs",
            "object",
            "Optional structured input payload for the agent.",
            required=False,
            default={},
        )

    def _get_orchestrator(self):
        if self._orchestrator is None:
            from atlas.core.ai_assistant import build_system

            self._orchestrator = build_system()
        return self._orchestrator

    def execute(
        self,
        agent_name: str,
        objective: str,
        risk_level: str = "low",
        context: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            orchestrator = self._get_orchestrator()
            task = AgentTask(
                objective=objective,
                agent_name=agent_name,
                risk_level=risk_level,
                context=context or {},
                inputs=inputs or {},
            )
            result = orchestrator.execute(task)
            return {
                "success": result.ok,
                "status": result.status,
                "summary": result.summary,
                "result": result.result,
                "errors": result.errors,
                "metadata": result.metadata,
            }
        except Exception as exc:
            return {
                "success": False,
                "status": "error",
                "summary": f"Agent execution failed: {exc}",
                "errors": [str(exc)],
            }
