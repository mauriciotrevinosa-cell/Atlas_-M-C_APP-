"""
AgentRuns — aggregate statistics and history across all agent executions.

Complements TaskLogger (per-run JSONL) with in-memory aggregated metrics.
Used by: monitoring dashboard, evaluation, model comparison.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, Dict, List, Optional


@dataclass
class RunRecord:
    """Immutable record of a single agent execution."""
    task_id:      str
    agent_name:   str
    status:       str        # success | error | partial
    execution_ms: int
    model_used:   str
    timestamp:    str
    error_count:  int = 0
    summary:      str = ""

    @property
    def ok(self) -> bool:
        return self.status == "success"


class AgentRunStore:
    """
    In-memory store for agent run history and aggregate metrics.

    Features:
    - Per-agent success rate
    - Average latency per agent
    - Model usage breakdown
    - Recent failures (for debugging)
    - Per-task run lookup
    """

    def __init__(self, max_history: int = 5000):
        self._runs:     Deque[RunRecord]          = deque(maxlen=max_history)
        self._by_agent: Dict[str, List[RunRecord]] = defaultdict(list)
        self._by_task:  Dict[str, RunRecord]       = {}

    # ── Recording ─────────────────────────────────────────────────────────────

    def record(self, run: RunRecord) -> None:
        """Add a run record."""
        self._runs.append(run)
        self._by_agent[run.agent_name].append(run)
        self._by_task[run.task_id] = run

    def record_from_result(self, result, task) -> None:
        """Convenience: create RunRecord from AgentResult + AgentTask."""
        run = RunRecord(
            task_id      = result.task_id,
            agent_name   = result.metadata.get("agent", task.agent_name),
            status       = result.status,
            execution_ms = result.metadata.get("execution_ms", 0),
            model_used   = result.metadata.get("model_used", ""),
            timestamp    = datetime.now(timezone.utc).isoformat(),
            error_count  = len(result.errors),
            summary      = result.summary[:100],
        )
        self.record(run)

    # ── Queries ───────────────────────────────────────────────────────────────

    def by_agent(self, agent_name: str) -> List[RunRecord]:
        return list(self._by_agent.get(agent_name, []))

    def by_task(self, task_id: str) -> Optional[RunRecord]:
        return self._by_task.get(task_id)

    def recent(self, n: int = 20) -> List[RunRecord]:
        return list(self._runs)[-n:]

    def recent_failures(self, n: int = 10) -> List[RunRecord]:
        failures = [r for r in self._runs if not r.ok]
        return failures[-n:]

    # ── Aggregate stats ───────────────────────────────────────────────────────

    def agent_stats(self, agent_name: str) -> Dict:
        """Per-agent performance summary."""
        runs = self._by_agent.get(agent_name, [])
        if not runs:
            return {"agent": agent_name, "total_runs": 0}

        success  = sum(1 for r in runs if r.ok)
        errors   = sum(1 for r in runs if r.status == "error")
        avg_ms   = sum(r.execution_ms for r in runs) / len(runs)
        model_counts: Dict[str, int] = defaultdict(int)
        for r in runs:
            if r.model_used:
                model_counts[r.model_used] += 1

        return {
            "agent":        agent_name,
            "total_runs":   len(runs),
            "success":      success,
            "errors":       errors,
            "success_rate": round(success / len(runs), 3),
            "avg_ms":       round(avg_ms, 1),
            "models_used":  dict(model_counts),
        }

    def global_stats(self) -> Dict:
        """Cross-agent summary."""
        runs = list(self._runs)
        if not runs:
            return {"total_runs": 0}

        by_agent: Dict[str, Dict] = {}
        for agent_name in self._by_agent:
            by_agent[agent_name] = self.agent_stats(agent_name)

        success = sum(1 for r in runs if r.ok)
        return {
            "total_runs":    len(runs),
            "success":       success,
            "errors":        sum(1 for r in runs if r.status == "error"),
            "success_rate":  round(success / len(runs), 3),
            "agents_active": list(self._by_agent.keys()),
            "per_agent":     by_agent,
        }

    def compare_models(self) -> Dict[str, Dict]:
        """Compare success rate + latency across all models used."""
        model_runs: Dict[str, List[RunRecord]] = defaultdict(list)
        for r in self._runs:
            if r.model_used:
                model_runs[r.model_used].append(r)

        result = {}
        for model, runs in model_runs.items():
            success = sum(1 for r in runs if r.ok)
            result[model] = {
                "total_runs":   len(runs),
                "success_rate": round(success / len(runs), 3),
                "avg_ms":       round(sum(r.execution_ms for r in runs) / len(runs), 1),
            }
        return result

    def __len__(self) -> int:
        return len(self._runs)

    def __repr__(self) -> str:
        return f"AgentRunStore(runs={len(self._runs)}, agents={list(self._by_agent.keys())})"
