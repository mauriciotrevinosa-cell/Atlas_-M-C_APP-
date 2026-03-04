"""
Research report model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResearchStage(str, Enum):
    IDEA = "idea"
    DATA = "data"
    MODEL = "model"
    BACKTEST = "backtest"
    VALIDATION = "validation"
    DEPLOYMENT = "deployment"


@dataclass(slots=True)
class ResearchReport:
    run_id: str
    generated_at_utc: str
    stage: ResearchStage
    idea_name: str
    symbols: list[str]
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "generated_at_utc": self.generated_at_utc,
            "stage": self.stage.value,
            "idea_name": self.idea_name,
            "symbols": self.symbols,
            "metrics": self.metrics,
            "artifacts": self.artifacts,
        }

