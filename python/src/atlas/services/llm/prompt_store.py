"""
PromptStore — loads and caches prompt templates from markdown files.

Templates use {PLACEHOLDER} syntax for simple string formatting.
Files live in: python/src/atlas/core/ai_assistant/prompts/
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


# Default prompts directory (relative to this file)
_DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent.parent / "core" / "ai_assistant" / "prompts"


@dataclass(frozen=True)
class PromptTemplateInfo:
    """Auditable prompt template manifest row."""

    name: str
    path: str
    placeholders: List[str]
    size_chars: int
    line_count: int
    cached: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "path": self.path,
            "placeholders": self.placeholders,
            "size_chars": self.size_chars,
            "line_count": self.line_count,
            "cached": self.cached,
        }


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
        return sorted([
            p.stem
            for p in self._dir.iterdir()
            if p.suffix in (".md", ".txt") and not p.name.startswith("_")
        ])

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

    def render_strict(self, name: str, **kwargs) -> str:
        """
        Render a template and reject missing placeholders.

        Use this for agent prompts that must be reproducible/auditable. The
        existing render() method remains permissive for backwards compatibility.
        """
        missing = self.validate_render(name, **kwargs)
        if missing:
            raise ValueError(f"Missing prompt placeholders for {name}: {missing}")
        rendered = self.render(name, **kwargs)
        leftovers = self.find_unfilled_placeholders(rendered)
        if leftovers:
            raise ValueError(f"Unfilled prompt placeholders for {name}: {leftovers}")
        return rendered

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

    def get_manifest(self, name: str) -> PromptTemplateInfo:
        """Return metadata for one prompt template."""
        path = self._resolve_prompt_path(name)
        text = self.load(name)
        return PromptTemplateInfo(
            name=name,
            path=str(path.resolve()),
            placeholders=sorted(set(self.get_placeholders(name))),
            size_chars=len(text),
            line_count=len(text.splitlines()),
            cached=name in self._cache,
        )

    def list_manifests(self) -> List[PromptTemplateInfo]:
        """Return prompt manifests for all available templates."""
        return [self.get_manifest(name) for name in self.list_prompts()]

    def validate_render(self, name: str, **kwargs) -> List[str]:
        """Return list of unfilled placeholders after render attempt."""
        placeholders = self.get_placeholders(name)
        return [p for p in placeholders if p not in kwargs]

    @staticmethod
    def find_unfilled_placeholders(text: str) -> List[str]:
        """Return remaining {PLACEHOLDER} tokens in rendered text."""
        return sorted(set(re.findall(r"\{([A-Z_]+)\}", text)))

    # ── Cache ─────────────────────────────────────────────────────────────────

    def clear_cache(self) -> None:
        self._cache.clear()

    def reload(self, name: str) -> str:
        """Force reload a template (bypasses cache)."""
        self._cache.pop(name, None)
        return self.load(name)

    def _resolve_prompt_path(self, name: str) -> Path:
        for ext in (".md", ".txt"):
            path = self._dir / f"{name}{ext}"
            if path.exists():
                return path
        raise FileNotFoundError(
            f"Prompt template '{name}' not found in {self._dir}. "
            f"Available: {self.list_prompts()}"
        )

    def __repr__(self) -> str:
        return f"PromptStore(dir={self._dir}, cached={list(self._cache.keys())})"
