"""
Prompt Store — Versioned prompts as files, not hardcoded strings.

Design:
  - Prompts live as .md files in the prompts/ directory
  - Each prompt has a version header
  - Store loads, caches, and renders prompts with variables
  - Easy to audit, diff, and version control

Usage:
    store = PromptStore()
    system = store.render("system", project="KiN Towers")
    classify = store.get("router_classify")
"""

import os
from pathlib import Path
from typing import Dict, Optional
import re


class PromptStore:
    """
    File-based prompt management system.

    Loads .md files from the prompts/ directory,
    caches them in memory, and supports variable rendering.
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            self.prompts_dir = Path(__file__).parent / "prompts"

        self._cache: Dict[str, str] = {}
        self._metadata: Dict[str, Dict] = {}
        self._load_all()

    def _load_all(self):
        """Load all prompt files from directory."""
        if not self.prompts_dir.exists():
            return

        for f in self.prompts_dir.glob("*.md"):
            name = f.stem  # filename without extension
            content = f.read_text(encoding="utf-8")
            self._cache[name] = content
            self._metadata[name] = {
                "path": str(f),
                "size": len(content),
                "lines": content.count("\n") + 1,
            }

    def get(self, name: str) -> str:
        """
        Get a prompt by name.

        Args:
            name: Prompt name (filename without .md)

        Returns:
            Prompt content as string

        Raises:
            KeyError: If prompt not found
        """
        if name not in self._cache:
            # Try to load it fresh
            path = self.prompts_dir / f"{name}.md"
            if path.exists():
                self._cache[name] = path.read_text(encoding="utf-8")
            else:
                raise KeyError(
                    f"Prompt '{name}' not found. "
                    f"Available: {list(self._cache.keys())}"
                )
        return self._cache[name]

    def render(self, name: str, **variables) -> str:
        """
        Get prompt and render with variables.

        Supports {{variable}} syntax in .md files.

        Args:
            name: Prompt name
            **variables: Key-value pairs to substitute

        Returns:
            Rendered prompt string
        """
        template = self.get(name)

        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))

        return template

    def list_prompts(self) -> Dict[str, Dict]:
        """List all available prompts with metadata."""
        return {
            name: {
                **meta,
                "preview": self._cache[name][:100] + "..."
                if len(self._cache[name]) > 100 else self._cache[name]
            }
            for name, meta in self._metadata.items()
        }

    def reload(self, name: Optional[str] = None):
        """
        Reload prompts from disk.

        Args:
            name: Specific prompt to reload, or None for all
        """
        if name:
            path = self.prompts_dir / f"{name}.md"
            if path.exists():
                self._cache[name] = path.read_text(encoding="utf-8")
        else:
            self._cache.clear()
            self._metadata.clear()
            self._load_all()

    def get_with_context(self, name: str, context_name: str = "kin_towers_context") -> str:
        """
        Get prompt concatenated with project context.
        Useful for injecting project knowledge into any prompt.

        Args:
            name: Main prompt name
            context_name: Context prompt to append

        Returns:
            Combined prompt string
        """
        main = self.get(name)
        try:
            context = self.get(context_name)
            return f"{main}\n\n---\n\n{context}"
        except KeyError:
            return main
