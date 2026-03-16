from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class AgentTask:
    task_id: str
    agent_name: str
    objective: str
    context: Dict[str, Any]
    inputs: Dict[str, Any]
    risk_level: str = "low"


@dataclass
class AgentResult:
    task_id: str
    status: str
    summary: str
    result: Dict[str, Any]
    errors: list[str]
    metadata: Dict[str, Any]


class BaseAgent(ABC):
    name: str = "base_agent"
    version: str = "v1"

    @abstractmethod
    def run(self, task: AgentTask) -> AgentResult:
        pass
