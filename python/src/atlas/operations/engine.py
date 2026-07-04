from __future__ import annotations

from typing import Any, Callable, Dict
from uuid import uuid4

from .models import WorkflowDefinition, utc_now
from .store import OperationsStore

StepHandler = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


class StepRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[str, StepHandler] = {}

    def register(self, name: str, handler: StepHandler) -> None:
        self._handlers[name] = handler

    def names(self) -> set[str]:
        return set(self._handlers)

    def execute(self, name: str, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._handlers:
            raise KeyError(f"Unknown operations handler: {name}")
        return self._handlers[name](inputs, context)


class OperationsEngine:
    def __init__(self, store: OperationsStore, registry: StepRegistry) -> None:
        self.store = store
        self.registry = registry

    def run(self, workflow: WorkflowDefinition, inputs: Dict[str, Any]) -> Dict[str, Any]:
        validation_errors = workflow.validate(self.registry.names())
        if validation_errors:
            raise ValueError("; ".join(validation_errors))

        run = {
            "run_id": str(uuid4()),
            "workflow_id": workflow.workflow_id,
            "workflow_version": workflow.version,
            "status": "running",
            "inputs": dict(inputs),
            "steps": [],
            "started_at": utc_now(),
            "completed_at": None,
        }
        self.store.save_run(run)
        context: Dict[str, Any] = {"inputs": dict(inputs), "steps": {}}

        for step in workflow.steps:
            if not step.enabled:
                step_run = {
                    "step_id": step.step_id, "name": step.name, "handler": step.handler,
                    "status": "skipped", "data": None, "source": "atlas.operations",
                    "mode": "MANUAL", "updated_at": utc_now(), "error": None,
                }
                run["steps"].append(step_run)
                context["steps"][step.step_id] = step_run
                continue
            try:
                payload = {**inputs, **step.config}
                data = self.registry.execute(step.handler, payload, context)
                step_run = {
                    "step_id": step.step_id, "name": step.name, "handler": step.handler,
                    "status": "live", "data": data, "source": step.handler,
                    "mode": "MANUAL", "updated_at": utc_now(), "error": None,
                }
            except Exception as exc:
                step_run = {
                    "step_id": step.step_id, "name": step.name, "handler": step.handler,
                    "status": "unavailable", "data": None, "source": step.handler,
                    "mode": "MANUAL", "updated_at": utc_now(), "error": str(exc),
                }
            run["steps"].append(step_run)
            context["steps"][step.step_id] = step_run
            self.store.save_run(run)
            if step_run["error"] and not step.continue_on_error:
                run["status"] = "failed"
                break

        if run["status"] == "running":
            run["status"] = "completed"
        run["completed_at"] = utc_now()
        self.store.save_run(run)
        return run
