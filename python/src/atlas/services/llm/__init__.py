"""Atlas LLM service layer — model routing, prompt store, providers."""

from .model_router import ModelProviderInfo, ModelRouter, ModelRoute
from .prompt_store import PromptStore, PromptTemplateInfo
from .providers.base          import BaseLLMProvider, LLMResponse
from .providers.ollama_provider import OllamaProvider
from .providers.claude_provider import ClaudeProvider
from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider  import GeminiProvider

__all__ = [
    "ModelRouter", "ModelRoute", "ModelProviderInfo",
    "PromptStore", "PromptTemplateInfo",
    "BaseLLMProvider", "LLMResponse",
    "OllamaProvider", "ClaudeProvider", "OpenAIProvider", "GeminiProvider",
]
