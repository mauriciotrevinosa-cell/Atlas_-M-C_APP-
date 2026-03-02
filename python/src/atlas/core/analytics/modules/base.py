"""
Base interfaces for analysis modules executed by the simulation runner.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from atlas.core.analytics.artifacts import Artifact


@dataclass(frozen=True)
class SimulationTickContext:
    tick: int
    started_at: datetime
    timestamp: datetime
    tick_interval_seconds: float
    demo_mode: bool = True
    inputs: dict[str, Any] = field(default_factory=dict)


class ArtifactPublisher(Protocol):
    def __call__(self, artifact: Artifact) -> Artifact:
        ...


class AnalysisModule(ABC):
    module_id: str
    title: str
    description: str

    @abstractmethod
    def on_tick(self, context: SimulationTickContext, publish: ArtifactPublisher) -> None:
        """
        Execute one simulation tick and publish any resulting artifacts.
        """
