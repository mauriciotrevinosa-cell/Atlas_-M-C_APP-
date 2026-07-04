from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from atlas.orchestration.router import PipelineRouter

from .engine import OperationsEngine, StepRegistry
from .handlers import register_builtin_handlers
from .models import StepDefinition, WorkflowDefinition
from .store import OperationsStore

router = APIRouter(prefix="/api/operations", tags=["operations"])
store = OperationsStore()
registry = StepRegistry()


def _market_analysis(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    symbol = str(inputs.get("symbol") or "").strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    timeframe = str(inputs.get("timeframe") or "3mo")
    result = PipelineRouter().quick_analysis(symbol, timeframe)
    if result.get("errors") and not result.get("indicators"):
        raise RuntimeError("; ".join(result["errors"]))
    return result


registry.register("atlas.market.quick_analysis", _market_analysis)
register_builtin_handlers(registry)
engine = OperationsEngine(store, registry)


def _ensure_default_workflow() -> None:
    current = store.get_workflow("symbol-due-diligence-v1")
    if current and current.version > 1:
        return
    if current and {step.handler for step in current.steps} != {"atlas.market.quick_analysis"}:
        return
    store.save_workflow(WorkflowDefinition(
        workflow_id="symbol-due-diligence-v1",
        name="Symbol due diligence",
        description="Editable first vertical slice: real market analysis with provenance.",
        status="ready",
        version=2,
        steps=[
            StepDefinition(
                step_id="market-analysis",
                name="Market state, indicators, and risk",
                handler="atlas.market.quick_analysis",
            ),
            StepDefinition(
                step_id="signal-summary",
                name="Derived signal summary",
                handler="atlas.signals.snapshot",
                config={"source_step_id": "market-analysis"},
            ),
        ],
    ))


_ensure_default_workflow()


@router.get("/handlers")
def list_handlers() -> Dict[str, Any]:
    return {"handlers": sorted(registry.names())}


@router.get("/workflows")
def list_workflows() -> Dict[str, Any]:
    items = [workflow.to_dict() for workflow in store.list_workflows()]
    return {"items": items, "total": len(items)}


@router.post("/workflows")
def create_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
    workflow = WorkflowDefinition.from_dict(payload)
    errors = workflow.validate(registry.names())
    if errors:
        raise HTTPException(422, detail=errors)
    return store.save_workflow(workflow).to_dict()


@router.patch("/workflows/{workflow_id}")
def update_workflow(workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    current = store.get_workflow(workflow_id)
    if current is None:
        raise HTTPException(404, "Workflow not found")
    merged = current.to_dict()
    merged.update(payload)
    merged["workflow_id"] = workflow_id
    merged["version"] = current.version + 1
    workflow = WorkflowDefinition.from_dict(merged)
    errors = workflow.validate(registry.names())
    if errors:
        raise HTTPException(422, detail=errors)
    return store.save_workflow(workflow).to_dict()


@router.post("/workflows/{workflow_id}/runs")
def run_workflow(workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    workflow = store.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(404, "Workflow not found")
    try:
        return engine.run(workflow, dict(payload.get("inputs") or payload))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> Dict[str, Any]:
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run
