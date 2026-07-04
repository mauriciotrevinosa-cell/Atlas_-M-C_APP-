from atlas.assistants.aria.tools.operations_workflow import AtlasOperationsWorkflowTool


def test_aria_operations_proposal_requires_review(monkeypatch, tmp_path):
    from atlas.operations import api
    from atlas.operations.store import OperationsStore

    temporary_store = OperationsStore(tmp_path / "aria-operations.db")
    monkeypatch.setattr(api, "store", temporary_store)

    result = AtlasOperationsWorkflowTool().execute(
        action="propose",
        objective="Review SPY risk",
        symbol="SPY",
        timeframe="6mo",
    )

    assert result["success"] is True
    assert result["requires_human_review"] is True
    assert result["workflow"]["status"] == "draft"
    assert temporary_store.get_workflow(result["workflow"]["workflow_id"]) is not None
