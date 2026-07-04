"""
Evaluation Module
=================

Tools for evaluating strategy performance and interactive scenarios.
"""

from atlas.evaluation.scenario import ScenarioSession
from atlas.evaluation.challenges import (
    ChallengeEvaluator,
    ChallengeScore,
    ChallengeSpec,
    ChallengeSubmission,
)

__all__ = [
    "ScenarioSession",
    "ChallengeEvaluator",
    "ChallengeScore",
    "ChallengeSpec",
    "ChallengeSubmission",
]
