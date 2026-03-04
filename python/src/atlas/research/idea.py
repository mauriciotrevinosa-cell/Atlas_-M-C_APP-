"""
Research idea schema.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HypothesisType(str, Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY = "volatility"
    FLOW = "flow"


@dataclass(slots=True)
class ResearchIdea:
    name: str
    hypothesis: str
    symbols: list[str]
    lookback_days: int = 252
    hypothesis_type: HypothesisType = HypothesisType.MOMENTUM
    parameters: dict[str, Any] = field(default_factory=dict)

