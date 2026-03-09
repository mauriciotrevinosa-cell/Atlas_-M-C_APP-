from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    """
    Abstract contract for an LLM provider (Ollama, Claude, GPT, etc).
    This ensures that all agents can treat different models identically.
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Takes a prompt string and returns the generated text.
        Specific implementations should handle HTTP calls, retries, 
        and extracting the actual text from the response payload.
        """
        pass
