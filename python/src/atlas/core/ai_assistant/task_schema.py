"""
Task & Result schemas — common data contracts for all Atlas agents.

Every agent receives an AgentTask and returns an AgentResult.
This file is the single source of truth for that interface.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Risk levels ────────────────────────────────────────────────────────────────
RISK_LEVELS = ("low", "medium", "high", "critical")


# ── Input contract ─────────────────────────────────────────────────────────────
@dataclass
class AgentTask:
    """
    Universal input envelope for all Atlas agents.

    Attributes
    ----------
    task_id       : unique identifier (auto-generated if not provided)
    agent_name    : target agent (e.g. 'planner_agent')
    objective     : human-readable goal string
    context       : structured dict — project, module, files, constraints, etc.
    inputs        : agent-specific payload (e.g. code diff, URL, document)
    risk_level    : 'low' | 'medium' | 'high' | 'critical'
    allowed_tools : explicit whitelist of tools this task may use
    model_prefs   : optional model preference hints
    """

    objective:     str
    agent_name:    str                         = "planner_agent"
    task_id:       str                         = field(default_factory=lambda: str(uuid.uuid4()))
    context:       Dict[str, Any]              = field(default_factory=dict)
    inputs:        Dict[str, Any]              = field(default_factory=dict)
    risk_level:    str                         = "low"
    allowed_tools: List[str]                   = field(default_factory=list)
    model_prefs:   Dict[str, str]              = field(default_factory=dict)

    def __post_init__(self):
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"risk_level must be one of {RISK_LEVELS}")

    def to_dict(self) -> Dict:
        return {
            "task_id":       self.task_id,
            "agent_name":    self.agent_name,
            "objective":     self.objective,
            "context":       self.context,
            "inputs":        self.inputs,
            "risk_level":    self.risk_level,
            "allowed_tools": self.allowed_tools,
            "model_prefs":   self.model_prefs,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "AgentTask":
        return cls(
            task_id=d.get("task_id", str(uuid.uuid4())),
            agent_name=d.get("agent_name", "planner_agent"),
            objective=d["objective"],
            context=d.get("context", {}),
            inputs=d.get("inputs", {}),
            risk_level=d.get("risk_level", "low"),
            allowed_tools=d.get("allowed_tools", []),
            model_prefs=d.get("model_prefs", {}),
        )


# ── Output contract ────────────────────────────────────────────────────────────
@dataclass
class AgentResult:
    """
    Universal output envelope for all Atlas agents.

    Attributes
    ----------
    task_id    : mirrors the input task_id
    status     : 'success' | 'error' | 'partial'
    summary    : 1–2 sentence human-readable summary
    result     : structured agent-specific payload
    errors     : list of error strings (empty on success)
    metadata   : execution info (model_used, execution_ms, agent, version)
    """

    task_id:   str
    status:    str
    summary:   str
    result:    Dict[str, Any]                  = field(default_factory=dict)
    errors:    List[str]                       = field(default_factory=list)
    metadata:  Dict[str, Any]                  = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in ("success", "error", "partial"):
            raise ValueError("status must be 'success', 'error', or 'partial'")

    @property
    def ok(self) -> bool:
        return self.status == "success"

    def to_dict(self) -> Dict:
        return {
            "task_id":  self.task_id,
            "status":   self.status,
            "summary":  self.summary,
            "result":   self.result,
            "errors":   self.errors,
            "metadata": self.metadata,
        }

    @classmethod
    def error_result(cls, task_id: str, error: str, agent: str = "") -> "AgentResult":
        """Factory for error results."""
        return cls(
            task_id=task_id,
            status="error",
            summary=f"Agent failed: {error}",
            result={},
            errors=[error],
            metadata={"agent": agent},
        )
