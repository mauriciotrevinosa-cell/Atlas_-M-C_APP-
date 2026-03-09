"""
ARIA Tools Setup
================
Factory helpers for wiring available tools into an ARIA instance.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas.assistants.aria.core.chat import ARIA

logger = logging.getLogger("atlas.aria.tools.setup")


def register_all_tools(aria: "ARIA") -> int:
    """
    Register all recovered ARIA tools into the given ARIA instance.

    Returns:
        Number of tools successfully registered.
    """
    registered = 0

    def _register(tool_factory, label: str) -> None:
        nonlocal registered
        try:
            aria.register_tool(tool_factory())
            registered += 1
            logger.info("Registered: %s", label)
        except Exception as exc:
            logger.warning("Could not register %s: %s", label, exc)

    # Education
    from atlas.assistants.aria.tools.explain_concept import ExplainConceptTool

    _register(ExplainConceptTool, "ExplainConceptTool")

    # Analysis tools
    from atlas.assistants.aria.tools.explain_signal import ExplainSignalTool
    from atlas.assistants.aria.tools.get_market_state import GetMarketStateTool
    from atlas.assistants.aria.tools.analyze_risk import AnalyzeRiskTool
    from atlas.assistants.aria.tools.run_backtest import RunBacktestTool

    _register(ExplainSignalTool, "ExplainSignalTool")
    _register(GetMarketStateTool, "GetMarketStateTool")
    _register(AnalyzeRiskTool, "AnalyzeRiskTool")
    _register(RunBacktestTool, "RunBacktestTool")

    logger.info("ARIA tool registration complete: %d tool(s) registered.", registered)
    return registered


def create_aria_with_tools(
    model: str = "llama3.1:8b",
    host: str = "http://localhost:11434",
    temperature: float = 0.7,
) -> "ARIA":
    """
    Create a fully initialized ARIA instance with tools pre-registered.
    """
    from atlas.assistants.aria.core.chat import ARIA

    aria = ARIA(model=model, host=host, temperature=temperature)
    n = register_all_tools(aria)
    aria._safe_print(f"{n} tool(s) registered and ready.")
    return aria

