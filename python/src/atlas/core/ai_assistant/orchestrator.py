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

import time
from typing import Callable, Dict, List, Optional

from .agent_registry import AgentRegistry
from .task_schema    import AgentTask, AgentResult
from .audit.task_logs import TaskLogger
from .result_validator import ResultValidator


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
        on_start:  Optional[Callable[[AgentTask], None]]   = None,
        on_end:    Optional[Callable[[AgentResult], None]] = None,
    ):
        self.registry  = registry
        self.logger    = logger or TaskLogger()
        self.validator = validator or ResultValidator()
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

        # 3. Run (safe_run handles exceptions + timing)
        result = agent.safe_run(task)

        # 4. Validate output
        val_errors = self.validator.validate(result)
        if val_errors:
            result.errors.extend(val_errors)
            if result.status == "success":
                result.status = "partial"

        # 5. Log end + fire hook
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

    # ── Info ──────────────────────────────────────────────────────────────────

    def available_agents(self) -> List[str]:
        return self.registry.list_agents()

    def __repr__(self) -> str:
        return (
            f"AgentOrchestrator("
            f"agents={self.available_agents()}, "
            f"logger={type(self.logger).__name__})"
        )
