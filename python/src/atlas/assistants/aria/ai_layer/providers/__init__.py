"""
LLM Provider Interface — Swappable backends

Change your AI provider with one variable:
    provider = get_provider("ollama")   # Local
    provider = get_provider("openai")   # Cloud
    provider = get_provider("mock")     # Testing
"""

from .base import BaseProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .mock_provider import MockProvider

PROVIDER_MAP = {
    "ollama": OllamaProvider,
    "local": OllamaProvider,
    "openai": OpenAIProvider,
    "cloud": OpenAIProvider,
    "mock": MockProvider,
    "test": MockProvider,
}

def get_provider(name: str = "ollama", **kwargs) -> BaseProvider:
    """
    Factory to get LLM provider by name.

    Args:
        name: Provider name ("ollama", "openai", "mock")
        **kwargs: Provider-specific config

    Returns:
        Configured provider instance
    """
    provider_cls = PROVIDER_MAP.get(name.lower())
    if not provider_cls:
        raise ValueError(
            f"Unknown provider '{name}'. "
            f"Available: {list(PROVIDER_MAP.keys())}"
        )
    return provider_cls(**kwargs)

__all__ = ["get_provider", "BaseProvider", "OllamaProvider", "OpenAIProvider", "MockProvider"]
