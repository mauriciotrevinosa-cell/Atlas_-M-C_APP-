from __future__ import annotations

from atlas.operations import (
    OperationsEngine,
    OperationsStore,
    StepDefinition,
    StepRegistry,
    WorkflowDefinition,
)


def test_manual_workflow_is_editable_persisted_and_auditable(tmp_path):
    store = OperationsStore(tmp_path / "operations.db")
    registry = StepRegistry()
    registry.register("test.double", lambda inputs, context: {"value": inputs["value"] * 2})
    workflow = WorkflowDefinition(
        name="Test workflow",
        steps=[StepDefinition(name="Double", handler="test.double")],
    )
    store.save_workflow(workflow)

    run = OperationsEngine(store, registry).run(workflow, {"value": 4})

    assert run["status"] == "completed"
    assert run["steps"][0]["data"] == {"value": 8}
    assert run["steps"][0]["source"] == "test.double"
    assert store.get_workflow(workflow.workflow_id).name == "Test workflow"
    assert store.get_run(run["run_id"])["status"] == "completed"


def test_workflow_stops_and_records_handler_failure(tmp_path):
    store = OperationsStore(tmp_path / "operations.db")
    registry = StepRegistry()

    def fail(inputs, context):
        raise RuntimeError("source offline")

    registry.register("test.fail", fail)
    workflow = WorkflowDefinition(
        name="Failure workflow",
        steps=[StepDefinition(name="Fail", handler="test.fail")],
    )

    run = OperationsEngine(store, registry).run(workflow, {})

    assert run["status"] == "failed"
    assert run["steps"][0]["status"] == "unavailable"
    assert run["steps"][0]["error"] == "source offline"
