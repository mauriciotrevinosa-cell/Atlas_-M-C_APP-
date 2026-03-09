"""
BaseAgent — abstract base class for all Atlas agents.

Every agent must:
  1. Declare a unique `name` and `version`
  2. Implement `run(task: AgentTask) -> AgentResult`
  3. Optionally override `validate_input()` and `validate_output()`

Design principles:
  - Agents are stateless between calls
  - Each agent owns exactly one domain
  - Agents never call each other directly (use the orchestrator)
  - Agents never touch production or merge code autonomously
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from atlas.core.ai_assistant.task_schema import AgentTask, AgentResult


class BaseAgent(ABC):
    """Abstract base for all Atlas agents."""

    name:    str = "base_agent"
    version: str = "v1"

    # ── Required interface ────────────────────────────────────────────────────

    @abstractmethod
    def run(self, task: AgentTask) -> AgentResult:
        """Execute the agent task and return a structured result."""

    # ── Optional hooks ────────────────────────────────────────────────────────

    def validate_input(self, task: AgentTask) -> List[str]:
        """
        Validate input before running.
        Return list of error strings (empty = valid).
        Override in subclasses for agent-specific validation.
        """
        errors = []
        if not task.objective or not task.objective.strip():
            errors.append("objective cannot be empty")
        return errors

    def validate_output(self, result: AgentResult) -> List[str]:
        """
        Validate output after running.
        Return list of error strings (empty = valid).
        Override in subclasses for agent-specific validation.
        """
        return []

    # ── Safe runner (wraps run with timing + error handling) ─────────────────

    def safe_run(self, task: AgentTask) -> AgentResult:
        """
        Wraps run() with:
          - input validation
          - timing measurement
          - error catching
          - output validation
        """
        t0 = time.perf_counter()

        # 1. Validate input
        input_errors = self.validate_input(task)
        if input_errors:
            return AgentResult.error_result(
                task_id=task.task_id,
                error=f"Input validation failed: {'; '.join(input_errors)}",
                agent=self.name,
            )

        # 2. Run
        try:
            result = self.run(task)
        except Exception as exc:
            return AgentResult.error_result(
                task_id=task.task_id,
                error=f"Agent raised exception: {exc}",
                agent=self.name,
            )

        # 3. Inject timing metadata
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        result.metadata.setdefault("agent",        self.name)
        result.metadata.setdefault("version",      self.version)
        result.metadata.setdefault("execution_ms", elapsed_ms)

        # 4. Validate output
        output_errors = self.validate_output(result)
        if output_errors:
            result.errors.extend(output_errors)
            result.status = "partial"

        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, version={self.version!r})"

    @property
    def info(self) -> Dict[str, str]:
        return {"name": self.name, "version": self.version}
