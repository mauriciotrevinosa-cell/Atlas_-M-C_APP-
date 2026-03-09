"""
Atlas AI Layer - modular routing/memory/providers package.

Some branches include a higher-level ``layer.py`` facade (``AILayer``),
while others expose only the building blocks. Keep import-time behavior
compatible across both layouts.
"""

try:
    from .layer import AILayer  # type: ignore

    __all__ = ["AILayer"]
except Exception:
    from .prompt_store import PromptStore
    from .query_router import QueryRouter, RouteResult

    __all__ = ["PromptStore", "QueryRouter", "RouteResult"]
