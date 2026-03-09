"""
TaskLogger — append-only audit trail for all agent runs.

Logs to:
  - In-memory buffer (always)
  - JSONL file on disk (optional, default: logs/agents/<agent>/<date>.jsonl)

Every run is immutable once logged. Never modify or delete logs.
"""

from __future__ import annotations

import json
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque, Dict, List, Optional

from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


class TaskLogger:
    """
    Audit logger for agent tasks.

    Usage:
        logger = TaskLogger(log_dir="logs/agents")
        logger.log_start(task)
        logger.log_end(result)
        history = logger.recent(n=10)
    """

    def __init__(
        self,
        log_dir:    Optional[Path] = None,
        max_memory: int            = 1000,
        enabled:    bool           = True,
    ):
        self._dir      = Path(log_dir) if log_dir else self._default_dir()
        self._buffer:  Deque[Dict] = deque(maxlen=max_memory)
        self._enabled  = enabled
        self._starts:  Dict[str, Dict] = {}   # task_id → start record

    # ── Logging ───────────────────────────────────────────────────────────────

    def log_start(self, task: AgentTask) -> None:
        """Record task start. Called before agent.run()."""
        if not self._enabled:
            return
        record = {
            "event":      "START",
            "task_id":    task.task_id,
            "agent_name": task.agent_name,
            "objective":  task.objective[:200],
            "risk_level": task.risk_level,
            "timestamp":  self._now(),
        }
        self._starts[task.task_id] = record
        self._buffer.append(record)
        self._write(task.agent_name, record)

    def log_end(self, result: AgentResult) -> None:
        """Record task end. Called after agent.run()."""
        if not self._enabled:
            return
        start = self._starts.pop(result.task_id, {})
        record = {
            "event":        "END",
            "task_id":      result.task_id,
            "agent_name":   result.metadata.get("agent", "unknown"),
            "status":       result.status,
            "summary":      result.summary[:200],
            "errors":       result.errors,
            "execution_ms": result.metadata.get("execution_ms", 0),
            "model_used":   result.metadata.get("model_used", ""),
            "timestamp":    self._now(),
        }
        self._buffer.append(record)
        self._write(record["agent_name"], record)

    # ── Query ─────────────────────────────────────────────────────────────────

    def recent(self, n: int = 20) -> List[Dict]:
        """Return the n most recent log records (newest last)."""
        buf = list(self._buffer)
        return buf[-n:]

    def by_agent(self, agent_name: str, n: int = 50) -> List[Dict]:
        """Return recent records for a specific agent."""
        records = [r for r in self._buffer if r.get("agent_name") == agent_name]
        return records[-n:]

    def by_task(self, task_id: str) -> List[Dict]:
        """Return all records for a specific task_id."""
        return [r for r in self._buffer if r.get("task_id") == task_id]

    def stats(self) -> Dict:
        """Return summary statistics."""
        ends = [r for r in self._buffer if r["event"] == "END"]
        if not ends:
            return {"total_runs": 0}
        success = sum(1 for r in ends if r.get("status") == "success")
        errors  = sum(1 for r in ends if r.get("status") == "error")
        avg_ms  = sum(r.get("execution_ms", 0) for r in ends) / len(ends)
        return {
            "total_runs":   len(ends),
            "success":      success,
            "errors":       errors,
            "avg_ms":       round(avg_ms, 1),
            "agents_used":  list({r.get("agent_name") for r in ends}),
        }

    # ── Disk ──────────────────────────────────────────────────────────────────

    def _write(self, agent_name: str, record: Dict) -> None:
        """Append record to agent-specific JSONL file."""
        try:
            today    = datetime.now().strftime("%Y-%m-%d")
            path     = self._dir / agent_name / f"{today}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # Disk errors never crash the agent

    @staticmethod
    def _default_dir() -> Path:
        return Path("logs") / "agents"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def __repr__(self) -> str:
        return (
            f"TaskLogger(records={len(self._buffer)}, "
            f"dir={self._dir})"
        )
