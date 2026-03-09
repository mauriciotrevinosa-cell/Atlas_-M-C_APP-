"""Atlas LLM service layer — model routing, prompt store, providers."""

from .model_router import ModelRouter, ModelRoute
from .prompt_store import PromptStore
from .providers.base          import BaseLLMProvider, LLMResponse
from .providers.ollama_provider import OllamaProvider
from .providers.claude_provider import ClaudeProvider
from .providers.openai_provider import OpenAIProvider
from .providers.gemini_provider  import GeminiProvider

__all__ = [
    "ModelRouter", "ModelRoute",
    "PromptStore",
    "BaseLLMProvider", "LLMResponse",
    "OllamaProvider", "ClaudeProvider", "OpenAIProvider", "GeminiProvider",
]
