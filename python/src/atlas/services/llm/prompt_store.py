"""
PromptStore — loads and caches prompt templates from markdown files.

Templates use {PLACEHOLDER} syntax for simple string formatting.
Files live in: python/src/atlas/core/ai_assistant/prompts/
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional


# Default prompts directory (relative to this file)
_DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent.parent / "core" / "ai_assistant" / "prompts"


class PromptStore:
    """
    Loads prompt templates from .md files with caching.

    Usage:
        store   = PromptStore()
        prompt  = store.render("planner", OBJETIVO="...", CONTEXTO="...", RESTRICCIONES="...")
    """

    def __init__(self, prompts_dir: Optional[Path] = None):
        self._dir   = Path(prompts_dir or _DEFAULT_PROMPTS_DIR)
        self._cache: Dict[str, str] = {}

    # ── Load ──────────────────────────────────────────────────────────────────

    def load(self, name: str) -> str:
        """
        Load a prompt template by name (without extension).
        Tries .md then .txt. Caches results.

        Raises FileNotFoundError if not found.
        """
        if name in self._cache:
            return self._cache[name]

        for ext in (".md", ".txt"):
            path = self._dir / f"{name}{ext}"
            if path.exists():
                text = path.read_text(encoding="utf-8")
                self._cache[name] = text
                return text

        raise FileNotFoundError(
            f"Prompt template '{name}' not found in {self._dir}. "
            f"Available: {self.list_prompts()}"
        )

    def list_prompts(self) -> List[str]:
        """Return names of all available prompt templates."""
        if not self._dir.exists():
            return []
        return [
            p.stem
            for p in self._dir.iterdir()
            if p.suffix in (".md", ".txt") and not p.name.startswith("_")
        ]

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self, name: str, **kwargs) -> str:
        """
        Load template and substitute {PLACEHOLDER} with kwargs values.

        Example:
            store.render("planner", OBJETIVO="Build RBAC", CONTEXTO="...", RESTRICCIONES="...")
        """
        template = self.load(name)
        for key, value in kwargs.items():
            placeholder = "{" + key + "}"
            template = template.replace(placeholder, str(value))
        return template

    def render_raw(self, template: str, **kwargs) -> str:
        """Render an already-loaded template string."""
        for key, value in kwargs.items():
            template = template.replace("{" + key + "}", str(value))
        return template

    # ── Validation ────────────────────────────────────────────────────────────

    def get_placeholders(self, name: str) -> List[str]:
        """Return list of {PLACEHOLDER} keys in a template."""
        template = self.load(name)
        return re.findall(r"\{([A-Z_]+)\}", template)

    def validate_render(self, name: str, **kwargs) -> List[str]:
        """Return list of unfilled placeholders after render attempt."""
        placeholders = self.get_placeholders(name)
        return [p for p in placeholders if p not in kwargs]

    # ── Cache ─────────────────────────────────────────────────────────────────

    def clear_cache(self) -> None:
        self._cache.clear()

    def reload(self, name: str) -> str:
        """Force reload a template (bypasses cache)."""
        self._cache.pop(name, None)
        return self.load(name)

    def __repr__(self) -> str:
        return f"PromptStore(dir={self._dir}, cached={list(self._cache.keys())})"
