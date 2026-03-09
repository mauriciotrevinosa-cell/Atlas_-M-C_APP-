"""
BaseLLMProvider — abstract interface for all LLM providers.

Every provider must implement:
  generate(prompt, **kwargs) -> str

Optional:
  generate_structured(prompt, schema, **kwargs) -> dict
  is_available() -> bool
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMResponse:
    """Normalized response from any provider."""
    text:       str
    model:      str
    provider:   str
    tokens_in:  int  = 0
    tokens_out: int  = 0
    latency_ms: int  = 0
    raw:        Dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out


class BaseLLMProvider(ABC):
    """Abstract base for all LLM providers (Ollama, Claude, OpenAI, Gemini)."""

    provider_name: str = "base"
    default_model: str = ""

    @abstractmethod
    def generate(
        self,
        prompt:      str,
        model:       Optional[str] = None,
        temperature: float         = 0.3,
        max_tokens:  int           = 4096,
        **kwargs,
    ) -> LLMResponse:
        """Generate a completion for the given prompt."""

    def generate_structured(
        self,
        prompt:  str,
        schema:  Dict[str, Any],
        model:   Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate and parse a structured JSON response.
        Default: call generate() then JSON-parse. Override for native JSON mode.
        """
        import json, re
        response = self.generate(prompt, model=model, **kwargs)
        text     = response.text.strip()
        # Extract JSON block if wrapped in markdown
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            text = match.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text, "_parse_error": True}

    def is_available(self) -> bool:
        """Check if this provider is reachable. Override for real health checks."""
        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(provider={self.provider_name!r}, model={self.default_model!r})"
