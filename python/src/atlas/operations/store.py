from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from .models import WorkflowDefinition, utc_now


class OperationsStore:
    """SQLite source of truth for workflow definitions and execution history."""

    def __init__(self, path: str | Path = Path("data") / "operations.db") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS operation_workflows (
                    workflow_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    definition_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operation_runs (
                    run_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    workflow_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    inputs_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT
                );
                """
            )

    def save_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        workflow.updated_at = utc_now()
        payload = json.dumps(workflow.to_dict(), default=str)
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO operation_workflows
                   (workflow_id, version, name, definition_json, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(workflow_id) DO UPDATE SET
                     version=excluded.version, name=excluded.name,
                     definition_json=excluded.definition_json,
                     updated_at=excluded.updated_at""",
                (workflow.workflow_id, workflow.version, workflow.name, payload, workflow.updated_at),
            )
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT definition_json FROM operation_workflows WHERE workflow_id = ?",
                (workflow_id,),
            ).fetchone()
        return WorkflowDefinition.from_dict(json.loads(row[0])) if row else None

    def list_workflows(self) -> List[WorkflowDefinition]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT definition_json FROM operation_workflows ORDER BY updated_at DESC"
            ).fetchall()
        return [WorkflowDefinition.from_dict(json.loads(row[0])) for row in rows]

    def save_run(self, run: Dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO operation_runs
                   (run_id, workflow_id, workflow_version, status, inputs_json,
                    result_json, started_at, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run["run_id"], run["workflow_id"], run["workflow_version"],
                    run["status"], json.dumps(run.get("inputs", {}), default=str),
                    json.dumps(run, default=str), run["started_at"], run.get("completed_at"),
                ),
            )

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT result_json FROM operation_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None
