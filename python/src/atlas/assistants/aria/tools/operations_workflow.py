from __future__ import annotations

from typing import Any, Dict

from atlas.assistants.aria.tools.base import Tool


class AtlasOperationsWorkflowTool(Tool):
    """Let ARIA inspect, propose, and run the same workflows used by the manual UI."""

    def __init__(self):
        super().__init__(
            name="atlas_operations_workflow",
            description=(
                "List Atlas operations workflows, propose an editable draft, or run an existing "
                "workflow. Proposals never execute automatically and runs use the shared audited engine."
            ),
            category="operations",
        )
        self.add_parameter("action", "string", "One of: list, propose, run.")
        self.add_parameter("objective", "string", "Human objective for a draft proposal.", required=False, default="")
        self.add_parameter("workflow_id", "string", "Workflow ID for run.", required=False, default="")
        self.add_parameter("symbol", "string", "Market symbol input.", required=False, default="SPY")
        self.add_parameter("timeframe", "string", "Market timeframe input.", required=False, default="3mo")

    def execute(
        self,
        action: str,
        objective: str = "",
        workflow_id: str = "",
        symbol: str = "SPY",
        timeframe: str = "3mo",
    ) -> Dict[str, Any]:
        from atlas.operations.api import engine, registry, store
        from atlas.operations.models import StepDefinition, WorkflowDefinition

        action = action.strip().lower()
        if action == "list":
            return {
                "success": True,
                "workflows": [item.to_dict() for item in store.list_workflows()],
                "handlers": sorted(registry.names()),
            }
        if action == "propose":
            if not objective.strip():
                return {"success": False, "error": "objective is required"}
            workflow = WorkflowDefinition(
                name=objective.strip()[:120],
                description=(
                    "ARIA-proposed draft. Review and edit this workflow in the manual workspace "
                    "before running it."
                ),
                status="draft",
                steps=[
                    StepDefinition(
                        step_id="market-analysis",
                        name="Market state, indicators, and risk",
                        handler="atlas.market.quick_analysis",
                        config={"symbol": symbol.upper(), "timeframe": timeframe},
                    ),
                    StepDefinition(
                        step_id="signal-summary",
                        name="Derived signal summary",
                        handler="atlas.signals.snapshot",
                        config={"source_step_id": "market-analysis"},
                    ),
                ],
            )
            store.save_workflow(workflow)
            return {"success": True, "requires_human_review": True, "workflow": workflow.to_dict()}
        if action == "run":
            workflow = store.get_workflow(workflow_id)
            if workflow is None:
                return {"success": False, "error": "Workflow not found"}
            return {
                "success": True,
                "run": engine.run(workflow, {"symbol": symbol.upper(), "timeframe": timeframe}),
            }
        return {"success": False, "error": "action must be list, propose, or run"}
