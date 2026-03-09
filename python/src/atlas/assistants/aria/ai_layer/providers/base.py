"""
Base Provider Interface — All providers must implement this contract.

Design philosophy:
  - Every provider has the same API
  - Swap providers without changing application code
  - Each provider handles its own auth, formatting, error handling
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time


@dataclass
class LLMResponse:
    """Standardized response from any provider."""
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    tool_calls: List[Dict] = field(default_factory=list)
    raw: Any = None  # Raw provider response for debugging

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


@dataclass
class Message:
    """Standardized message format."""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None  # For tool messages
    tool_call_id: Optional[str] = None


class BaseProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement:
      - chat(): Send messages and get a response
      - is_available(): Check if the provider is ready
      - get_info(): Return provider metadata
    """

    def __init__(self, model: str = "", temperature: float = 0.7, max_tokens: int = 4096):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._request_count = 0
        self._total_tokens = 0
        self._total_latency_ms = 0.0

    @abstractmethod
    def chat(self,
             messages: List[Dict[str, str]],
             tools: Optional[List[Dict]] = None,
             temperature: Optional[float] = None) -> LLMResponse:
        """
        Send messages to the LLM and get a response.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional tool schemas for function calling
            temperature: Override default temperature

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is currently available."""
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata (name, model, status, etc.)."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Return usage statistics."""
        return {
            "provider": self.__class__.__name__,
            "model": self.model,
            "requests": self._request_count,
            "total_tokens": self._total_tokens,
            "avg_latency_ms": (
                self._total_latency_ms / self._request_count
                if self._request_count > 0 else 0
            )
        }

    def _track_request(self, response: LLMResponse):
        """Track request statistics."""
        self._request_count += 1
        self._total_tokens += response.tokens_used
        self._total_latency_ms += response.latency_ms
