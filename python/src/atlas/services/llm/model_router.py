"""
ModelRouter — decides which LLM provider + model to use for each agent/task.

Rules (overridable):
  - planner_agent      → ollama:qwen2.5     (fast, free, good planning)
  - context_curator    → ollama:llama3.1    (light summarization)
  - reviewer_agent     → openai:gpt-4o-mini (strict critical analysis)
  - test_agent         → claude:haiku       (code + test generation)
  - code_builder_agent → claude:haiku       (code generation)
  - repo_scout_agent   → gemini:flash       (research, large context)
  - ingestion_agent    → ollama:llama3.1    (summarization)
  - docs_agent         → claude:haiku       (structured writing)

High-risk tasks always use a stronger model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .providers.base import BaseLLMProvider, LLMResponse
from .providers.ollama_provider import OllamaProvider
from .providers.claude_provider import ClaudeProvider
from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider  import GeminiProvider


@dataclass
class ModelRoute:
    provider: str
    model:    str


# Default routing table — maps agent_name → (provider, model)
_DEFAULT_ROUTES: Dict[str, Dict[str, ModelRoute]] = {
    # agent_name → { risk_level → ModelRoute }
    "planner_agent": {
        "low":      ModelRoute("ollama",  "qwen2.5"),
        "medium":   ModelRoute("ollama",  "qwen2.5"),
        "high":     ModelRoute("openai",  "gpt-4o-mini"),
        "critical": ModelRoute("claude",  "claude-3-5-haiku-20241022"),
    },
    "reviewer_agent": {
        "low":      ModelRoute("openai",  "gpt-4o-mini"),
        "medium":   ModelRoute("openai",  "gpt-4o-mini"),
        "high":     ModelRoute("openai",  "gpt-4o"),
        "critical": ModelRoute("openai",  "gpt-4o"),
    },
    "test_agent": {
        "low":      ModelRoute("claude",  "claude-3-5-haiku-20241022"),
        "medium":   ModelRoute("claude",  "claude-3-5-haiku-20241022"),
        "high":     ModelRoute("claude",  "claude-sonnet-4-5"),
        "critical": ModelRoute("claude",  "claude-sonnet-4-5"),
    },
    "context_curator_agent": {
        "low":      ModelRoute("ollama",  "llama3.1"),
        "medium":   ModelRoute("ollama",  "qwen2.5"),
        "high":     ModelRoute("claude",  "claude-3-5-haiku-20241022"),
        "critical": ModelRoute("claude",  "claude-3-5-haiku-20241022"),
    },
    "code_builder_agent": {
        "low":      ModelRoute("claude",  "claude-3-5-haiku-20241022"),
        "medium":   ModelRoute("claude",  "claude-3-5-haiku-20241022"),
        "high":     ModelRoute("claude",  "claude-sonnet-4-5"),
        "critical": ModelRoute("claude",  "claude-sonnet-4-5"),
    },
    "repo_scout_agent": {
        "low":      ModelRoute("gemini",  "gemini-1.5-flash"),
        "medium":   ModelRoute("gemini",  "gemini-1.5-flash"),
        "high":     ModelRoute("gemini",  "gemini-1.5-pro"),
        "critical": ModelRoute("gemini",  "gemini-1.5-pro"),
    },
    "ingestion_agent": {
        "low":      ModelRoute("ollama",  "llama3.1"),
        "medium":   ModelRoute("ollama",  "qwen2.5"),
        "high":     ModelRoute("claude",  "claude-3-5-haiku-20241022"),
        "critical": ModelRoute("claude",  "claude-3-5-haiku-20241022"),
    },
    "docs_agent": {
        "low":      ModelRoute("claude",  "claude-3-5-haiku-20241022"),
        "medium":   ModelRoute("claude",  "claude-3-5-haiku-20241022"),
        "high":     ModelRoute("claude",  "claude-sonnet-4-5"),
        "critical": ModelRoute("claude",  "claude-sonnet-4-5"),
    },
}

_FALLBACK_ROUTE = ModelRoute("ollama", "llama3.1")


class ModelRouter:
    """
    Routes agent tasks to the right LLM provider and model.

    Supports:
    - Static routing table (default)
    - Per-task model preference overrides (model_prefs in AgentTask)
    - Fallback chain: preferred → fallback_provider → ollama
    - Availability checking before routing
    """

    def __init__(
        self,
        ollama_url:   str  = "http://localhost:11434",
        claude_key:   Optional[str] = None,
        openai_key:   Optional[str] = None,
        gemini_key:   Optional[str] = None,
        routes:       Optional[Dict] = None,
    ):
        self._providers: Dict[str, BaseLLMProvider] = {
            "ollama": OllamaProvider(base_url=ollama_url),
            "claude": ClaudeProvider(api_key=claude_key),
            "openai": OpenAIProvider(api_key=openai_key),
            "gemini": GeminiProvider(api_key=gemini_key),
        }
        self._routes = routes or _DEFAULT_ROUTES

    # ── Public API ────────────────────────────────────────────────────────────

    def route(
        self,
        agent_name:  str,
        risk_level:  str = "low",
        model_prefs: Optional[Dict[str, str]] = None,
    ) -> ModelRoute:
        """
        Return the best ModelRoute for this agent + risk combination.

        Priority:
          1. Task-level model_prefs override
          2. Routing table match
          3. Fallback default
        """
        # 1. Task override
        if model_prefs:
            provider = model_prefs.get("provider") or model_prefs.get("primary", "").split(":")[0]
            model    = model_prefs.get("model") or (
                model_prefs.get("primary", "").split(":", 1)[1]
                if ":" in model_prefs.get("primary", "") else ""
            )
            if provider and model:
                return ModelRoute(provider=provider, model=model)

        # 2. Routing table
        agent_routes = self._routes.get(agent_name, {})
        route = agent_routes.get(risk_level) or agent_routes.get("low") or _FALLBACK_ROUTE

        return route

    def get_provider(self, route: ModelRoute) -> BaseLLMProvider:
        """Return the provider instance for a given route."""
        provider = self._providers.get(route.provider)
        if provider is None:
            raise KeyError(f"Unknown provider: {route.provider!r}")
        return provider

    def generate(
        self,
        prompt:      str,
        agent_name:  str,
        risk_level:  str = "low",
        model_prefs: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Full pipeline: route → get provider → generate → return.

        Tries primary route first, falls back to ollama on provider error.
        """
        route    = self.route(agent_name, risk_level, model_prefs)
        provider = self.get_provider(route)

        try:
            return provider.generate(prompt, model=route.model, **kwargs)
        except (ConnectionError, EnvironmentError, RuntimeError):
            # Fallback to ollama
            if route.provider != "ollama":
                fallback = self._providers["ollama"]
                return fallback.generate(prompt, model="llama3.1", **kwargs)
            raise

    def check_availability(self) -> Dict[str, bool]:
        """Return availability status of each provider."""
        return {name: p.is_available() for name, p in self._providers.items()}

    def add_provider(self, name: str, provider: BaseLLMProvider) -> None:
        """Register a custom provider."""
        self._providers[name] = provider

    def set_route(self, agent_name: str, risk_level: str, route: ModelRoute) -> None:
        """Override a specific route."""
        self._routes.setdefault(agent_name, {})[risk_level] = route

    def __repr__(self) -> str:
        available = [k for k, v in self.check_availability().items() if v]
        return f"ModelRouter(available={available})"
