"""
OpenRouter Provider — Multi-model cloud aggregator with free options.

OpenRouter provides access to multiple models including free ones through a unified API.
Models: meta-llama/llama-3.3-70b-instruct, google/gemma-3-27b-it, etc.

Free tier: varies by model (some unlimited)

Usage:
    provider = OpenRouterProvider(model="meta-llama/llama-3.3-70b-instruct")
    response = provider.chat([{"role": "user", "content": "Hello"}])
"""

import os
import time
import json
import logging
from typing import List, Dict, Any, Optional

from .base import BaseProvider, LLMResponse

logger = logging.getLogger("atlas.aria.providers.openrouter")


class OpenRouterProvider(BaseProvider):
    """
    OpenRouter multi-model provider with free tier access.

    Supports:
      - Multiple models (Llama 3.3, Gemma 3, Mistral, etc.)
      - Tool/function calling
      - Free models available
      - Unified API across providers
    """

    # Free and freemium models on OpenRouter
    AVAILABLE_MODELS = {
        "meta-llama/llama-3.3-70b-instruct:free": {
            "context": 8192,
            "free": True,
        },
        "google/gemma-3-27b-it:free": {
            "context": 6144,
            "free": True,
        },
        "mistralai/mistral-7b-instruct:free": {
            "context": 8192,
            "free": True,
        },
        "meta-llama/llama-3.1-70b-instruct:free": {
            "context": 8192,
            "free": True,
        },
        "openai/gpt-4o-mini": {
            "context": 128000,
            "free": False,
        },
        "anthropic/claude-3-opus": {
            "context": 200000,
            "free": False,
        },
    }

    def __init__(self,
                 model: str = "meta-llama/llama-3.3-70b-instruct:free",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 4096,
                 base_url: str = "https://openrouter.ai/api/v1",
                 **kwargs):
        """
        Initialize OpenRouter provider.

        Args:
            model: OpenRouter model name (e.g., "meta-llama/llama-3.3-70b-instruct:free")
            api_key: OPENROUTER_API_KEY from environment or parameter
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            base_url: OpenRouter API base URL
        """
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = base_url

    def chat(self,
             messages: List[Dict[str, str]],
             tools: Optional[List[Dict]] = None,
             temperature: Optional[float] = None) -> LLMResponse:
        """
        Send messages to OpenRouter API.

        Uses requests library to make OpenAI-compatible API calls.
        OpenRouter requires HTTP-Referer and X-Title headers for rate limit tracking.
        """
        if not self.api_key:
            return LLMResponse(
                content="[OpenRouter Error] No API key configured. Set OPENROUTER_API_KEY environment variable.",
                model=self.model,
                provider="openrouter",
            )

        t0 = time.time()
        try:
            import requests
        except ImportError:
            return LLMResponse(
                content="[OpenRouter Error] requests library not installed. Run: pip install requests",
                model=self.model,
                provider="openrouter",
            )

        try:
            # Prepare request payload (OpenAI format)
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": self.max_tokens,
            }

            # Add tools if provided
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            # Headers - OpenRouter requires HTTP-Referer and X-Title
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://atlas.local",
                "X-Title": "ARIA - Atlas AI Assistant",
            }

            # Make request
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
            )

            latency = (time.time() - t0) * 1000

            # Check for errors
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                if isinstance(error_msg, dict):
                    error_msg = str(error_msg)
                logger.error(
                    "OpenRouter API error: %s (status %d)",
                    error_msg[:200], response.status_code
                )
                return LLMResponse(
                    content=f"[OpenRouter Error] {error_msg[:200]}",
                    model=self.model,
                    provider="openrouter",
                    latency_ms=latency,
                )

            # Parse response
            data = response.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            finish_reason = choice.get("finish_reason", "stop")

            # Extract tool calls if present
            tool_calls = []
            if "tool_calls" in message and message["tool_calls"]:
                for tc in message["tool_calls"]:
                    if tc.get("type") == "function":
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        tool_calls.append({
                            "name": fn.get("name", ""),
                            "arguments": args,
                            "id": tc.get("id", ""),
                        })

            # Token count from usage
            usage = data.get("usage", {})
            tokens_used = usage.get("completion_tokens", 0) + usage.get("prompt_tokens", 0)

            response_obj = LLMResponse(
                content=message.get("content", ""),
                model=self.model,
                provider="openrouter",
                tokens_used=tokens_used,
                latency_ms=latency,
                tool_calls=tool_calls,
                raw=data,
            )

            self._track_request(response_obj)
            logger.debug(
                "OpenRouter request successful: %s tokens, %.1f ms, finish=%s",
                tokens_used, latency, finish_reason
            )
            return response_obj

        except requests.exceptions.Timeout:
            latency = (time.time() - t0) * 1000
            logger.error("OpenRouter request timed out after %.1f ms", latency)
            return LLMResponse(
                content="[OpenRouter Error] Request timed out. Try simplifying your query.",
                model=self.model,
                provider="openrouter",
                latency_ms=latency,
            )
        except requests.exceptions.ConnectionError as e:
            latency = (time.time() - t0) * 1000
            logger.error("OpenRouter connection failed: %s", str(e))
            return LLMResponse(
                content="[OpenRouter Error] Unable to connect to OpenRouter API.",
                model=self.model,
                provider="openrouter",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - t0) * 1000
            logger.exception("OpenRouter provider error: %s", str(e))
            return LLMResponse(
                content=f"[OpenRouter Error] {str(e)[:200]}",
                model=self.model,
                provider="openrouter",
                latency_ms=latency,
            )

    def is_available(self) -> bool:
        """
        Check if OpenRouter provider is available (has valid API key).

        Note: This doesn't actually ping the API to avoid unnecessary requests.
        Real availability check happens on first request.
        """
        return bool(self.api_key)

    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        model_info = self.AVAILABLE_MODELS.get(self.model, {})
        return {
            "name": "OpenRouterProvider",
            "type": "cloud_aggregator",
            "model": self.model,
            "available": self.is_available(),
            "cost": "free" if model_info.get("free") else "paid",
            "context_window": model_info.get("context", 8192),
            "note": "Aggregates multiple providers through unified API",
        }
