"""
Orchestration Engine
=====================
Routes data through the full Atlas pipeline:
Data → Features → Engines → Signals → Risk → Decision

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("atlas.orchestration")


class PipelineStep:
    """A single step in the orchestration pipeline."""

    def __init__(self, name: str, handler: callable, required: bool = True):
        self.name = name
        self.handler = handler
        self.required = required

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        start = time.time()
        try:
            result = self.handler(context)
            elapsed = time.time() - start
            logger.info("Step '%s' completed in %.3fs", self.name, elapsed)
            return {"status": "ok", "result": result, "elapsed": elapsed}
        except Exception as e:
            elapsed = time.time() - start
            logger.error("Step '%s' failed: %s", self.name, e)
            if self.required:
                raise
            return {"status": "error", "error": str(e), "elapsed": elapsed}


class Orchestrator:
    """
    Central orchestrator that runs the full analysis pipeline.

    Pipeline:
    1. Data fetch
    2. Feature extraction
    3. Market state detection
    4. Engine signal generation
    5. Signal composition
    6. Discrepancy analysis
    7. Risk assessment
    8. Final decision
    """

    def __init__(self):
        self._steps: List[PipelineStep] = []
        self._engines: Dict[str, Any] = {}

    def register_step(self, name: str, handler: callable, required: bool = True):
        """Register a pipeline step."""
        self._steps.append(PipelineStep(name, handler, required))
        logger.info("Registered pipeline step: %s (required=%s)", name, required)

    def register_engine(self, name: str, engine: Any):
        """Register a trading engine."""
        self._engines[name] = engine
        logger.info("Registered engine: %s", name)

    def run(self, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute full pipeline.

        Args:
            initial_context: Starting data (symbol, timeframe, etc.)

        Returns:
            Final context with all results
        """
        context = dict(initial_context)
        context["_pipeline_start"] = time.time()
        context["_step_results"] = {}

        for step in self._steps:
            logger.info("Running step: %s", step.name)
            step_result = step.execute(context)
            context["_step_results"][step.name] = step_result

            if step_result["status"] == "ok" and step_result.get("result"):
                context.update(step_result["result"])

        context["_pipeline_elapsed"] = time.time() - context["_pipeline_start"]
        return context

    def get_registered_engines(self) -> List[str]:
        return list(self._engines.keys())

    def get_pipeline_summary(self) -> List[Dict[str, Any]]:
        return [
            {"name": s.name, "required": s.required}
            for s in self._steps
        ]
