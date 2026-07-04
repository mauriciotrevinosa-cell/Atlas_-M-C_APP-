"""
AgentOrchestrator — dispatches tasks to agents, handles audit logging.

The orchestrator is the ONLY entry point for running agents.
It enforces:
  - Agent registration check
  - Input validation
  - Audit trail (start/end)
  - Risk gate (blocks critical tasks without explicit approval)
  - Result validation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .agent_registry import AgentRegistry
from .task_schema    import AgentTask, AgentResult
from .audit.task_logs import TaskLogger
from .permissions import PermissionChecker, get_checker
from .result_validator import ResultValidator


@dataclass
class PipelineRunReport:
    """Summary for a multi-agent pipeline run."""

    total: int
    succeeded: int
    partial: int
    failed: int
    stopped_on_error: bool
    agents: List[str] = field(default_factory=list)
    task_ids: List[str] = field(default_factory=list)
    results: List[AgentResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.failed == 0 and not self.stopped_on_error

    def to_dict(self) -> Dict:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "partial": self.partial,
            "failed": self.failed,
            "stopped_on_error": self.stopped_on_error,
            "ok": self.ok,
            "agents": self.agents,
            "task_ids": self.task_ids,
            "results": [result.to_dict() for result in self.results],
        }


class AgentOrchestrator:
    """
    Central dispatcher for all agent tasks.

    Usage:
        orch   = AgentOrchestrator(registry, logger)
        result = orch.execute(task)
    """

    def __init__(
        self,
        registry:  AgentRegistry,
        logger:    Optional[TaskLogger]    = None,
        validator: Optional[ResultValidator] = None,
        permission_checker: Optional[PermissionChecker] = None,
        on_start:  Optional[Callable[[AgentTask], None]]   = None,
        on_end:    Optional[Callable[[AgentResult], None]] = None,
    ):
        self.registry  = registry
        self.logger    = logger or TaskLogger()
        self.validator = validator or ResultValidator()
        self.permissions = permission_checker or get_checker()
        self._on_start = on_start
        self._on_end   = on_end

    # ── Execute ───────────────────────────────────────────────────────────────

    def execute(self, task: AgentTask) -> AgentResult:
        """
        Full pipeline:
          1. Validate task
          2. Get agent from registry
          3. Log start
          4. Run agent (via safe_run for error handling + timing)
          5. Validate result
          6. Log end
          7. Return result
        """
        # 1. Check agent exists
        if not self.registry.has(task.agent_name):
            result = AgentResult.error_result(
                task_id=task.task_id,
                error=f"No agent registered for '{task.agent_name}'. "
                      f"Available: {self.registry.list_agents()}",
                agent=task.agent_name,
            )
            self.logger.log_end(result)
            return result

        agent = self.registry.get(task.agent_name)

        # 2. Log start + fire hook
        self.logger.log_start(task)
        if self._on_start:
            try:
                self._on_start(task)
            except Exception:
                pass

        # 3. Gateway preflight
        decision = self.permissions.preflight(task)
        if not decision.allowed:
            result = AgentResult.error_result(
                task_id=task.task_id,
                error=f"Gateway preflight denied task: {decision.reason}",
                agent=task.agent_name,
            )
            result.metadata["gateway_preflight"] = decision.to_dict()
            self.logger.log_end(result)
            if self._on_end:
                try:
                    self._on_end(result)
                except Exception:
                    pass
            return result

        # 4. Run (safe_run handles exceptions + timing)
        result = agent.safe_run(task)
        result.metadata.setdefault("gateway_preflight", decision.to_dict())

        # 5. Validate output
        val_errors = self.validator.validate(result)
        if val_errors:
            result.errors.extend(val_errors)
            if result.status == "success":
                result.status = "partial"

        # 6. Log end + fire hook
        self.logger.log_end(result)
        if self._on_end:
            try:
                self._on_end(result)
            except Exception:
                pass

        return result

    # ── Multi-step pipelines ──────────────────────────────────────────────────

    def pipeline(
        self,
        tasks:      List[AgentTask],
        stop_on_error: bool = True,
    ) -> List[AgentResult]:
        """
        Run a sequence of tasks in order.
        If stop_on_error=True, halt pipeline on first error result.
        """
        results = []
        for task in tasks:
            result = self.execute(task)
            results.append(result)
            if stop_on_error and result.status == "error":
                break
        return results

    def pipeline_report(
        self,
        tasks: List[AgentTask],
        stop_on_error: bool = True,
    ) -> PipelineRunReport:
        """Run a pipeline and return an auditable summary."""
        results = self.pipeline(tasks, stop_on_error=stop_on_error)
        return PipelineRunReport(
            total=len(results),
            succeeded=sum(1 for result in results if result.status == "success"),
            partial=sum(1 for result in results if result.status == "partial"),
            failed=sum(1 for result in results if result.status == "error"),
            stopped_on_error=stop_on_error and len(results) < len(tasks),
            agents=[task.agent_name for task in tasks[:len(results)]],
            task_ids=[result.task_id for result in results],
            results=results,
        )

    # ── Info ──────────────────────────────────────────────────────────────────

    def available_agents(self) -> List[str]:
        return self.registry.list_agents()

    def __repr__(self) -> str:
        return (
            f"AgentOrchestrator("
            f"agents={self.available_agents()}, "
            f"logger={type(self.logger).__name__})"
        )
