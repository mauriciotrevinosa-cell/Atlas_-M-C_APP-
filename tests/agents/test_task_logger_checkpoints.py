from atlas.core.ai_assistant.audit.task_logs import TaskLogger
from atlas.core.ai_assistant.task_schema import AgentResult, AgentTask


def test_task_logger_persists_and_loads_checkpoint(tmp_path):
    logger = TaskLogger(log_dir=tmp_path)
    task = AgentTask(
        task_id="task/with unsafe chars",
        agent_name="planner_agent",
        objective="Create a checkpointed plan",
    )
    result = AgentResult(
        task_id=task.task_id,
        status="success",
        summary="Checkpoint created.",
        result={"steps": ["inspect", "implement"]},
        metadata={"agent": "planner_agent", "execution_ms": 12},
    )

    logger.log_start(task)
    logger.log_end(result)

    checkpoint = logger.load_checkpoint(task.task_id)

    assert checkpoint is not None
    assert checkpoint["schema"] == "atlas.agent_checkpoint.v1"
    assert checkpoint["task_id"] == task.task_id
    assert checkpoint["agent_name"] == "planner_agent"
    assert checkpoint["result"]["summary"] == "Checkpoint created."
    assert "checkpointed" in checkpoint["start"]["objective"]


def test_task_logger_lists_checkpoint_manifests(tmp_path):
    logger = TaskLogger(log_dir=tmp_path)
    for idx in range(2):
        task = AgentTask(
            task_id=f"task-{idx}",
            agent_name="reviewer_agent",
            objective=f"Review task {idx}",
        )
        result = AgentResult(
            task_id=task.task_id,
            status="success",
            summary=f"Reviewed {idx}.",
            result={"verdict": "approve"},
            metadata={"agent": "reviewer_agent", "execution_ms": idx + 1},
        )
        logger.log_start(task)
        logger.log_end(result)

    rows = logger.list_checkpoints(n=5)

    assert len(rows) == 2
    assert rows[-1]["task_id"] == "task-1"
    assert rows[-1]["status"] == "success"
    assert rows[-1]["checkpoint_path"].endswith("task-1.json")
