"""
Atlas — Quant Research Pipeline
==================================
End-to-end research workflow: Idea → Data → Model → Backtest → Validate → Deploy.

Modules:
    pipeline     — QuantResearchPipeline (orchestrates the full workflow)
    idea         — ResearchIdea (structured research hypothesis)
    validator    — StatisticalValidator (significance tests, multiple-testing correction)
    report       — ResearchReport (output artifacts)

Usage:
    from atlas.research import QuantResearchPipeline, ResearchIdea

    pipeline = QuantResearchPipeline()
    idea = ResearchIdea(
        name="Gap Continuation Momentum",
        hypothesis="Stocks that gap up >1% at open continue higher 60% of the time",
        symbols=["SPY", "QQQ"],
        lookback_days=252,
    )
    report = pipeline.run(idea)

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

from .pipeline import QuantResearchPipeline, PipelineConfig
from .idea import ResearchIdea, HypothesisType
from .validator import StatisticalValidator, ValidationResult
from .report import ResearchReport, ResearchStage

__all__ = [
    "QuantResearchPipeline",
    "PipelineConfig",
    "ResearchIdea",
    "HypothesisType",
    "StatisticalValidator",
    "ValidationResult",
    "ResearchReport",
    "ResearchStage",
]
