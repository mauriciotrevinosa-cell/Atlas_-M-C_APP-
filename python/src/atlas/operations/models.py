from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StepDefinition:
    name: str
    handler: str
    step_id: str = field(default_factory=lambda: str(uuid4()))
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    continue_on_error: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepDefinition":
        return cls(
            step_id=data.get("step_id") or str(uuid4()),
            name=str(data.get("name") or data.get("handler") or "Unnamed step"),
            handler=str(data["handler"]),
            enabled=bool(data.get("enabled", True)),
            config=dict(data.get("config") or {}),
            continue_on_error=bool(data.get("continue_on_error", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowDefinition:
    name: str
    steps: List[StepDefinition]
    workflow_id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    version: int = 1
    status: str = "draft"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        steps = [
            step if isinstance(step, StepDefinition) else StepDefinition.from_dict(step)
            for step in data.get("steps", [])
        ]
        return cls(
            workflow_id=data.get("workflow_id") or str(uuid4()),
            name=str(data.get("name") or "Untitled workflow"),
            description=str(data.get("description") or ""),
            version=int(data.get("version", 1)),
            status=str(data.get("status") or "draft"),
            steps=steps,
            created_at=data.get("created_at") or utc_now(),
            updated_at=data.get("updated_at") or utc_now(),
        )

    def validate(self, available_handlers: set[str] | None = None) -> List[str]:
        errors: List[str] = []
        if not self.name.strip():
            errors.append("Workflow name is required")
        if not self.steps:
            errors.append("At least one step is required")
        ids = [step.step_id for step in self.steps]
        if len(ids) != len(set(ids)):
            errors.append("Step IDs must be unique")
        if available_handlers is not None:
            for step in self.steps:
                if step.handler not in available_handlers:
                    errors.append(f"Unknown handler: {step.handler}")
        return errors

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["steps"] = [step.to_dict() for step in self.steps]
        return data
