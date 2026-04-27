"""
Groq Provider — Ultra-fast cloud LLM backend.

Groq API is OpenAI-compatible and provides very low latency inference.
Models: llama-3.3-70b-versatile, mixtral-8x7b-32768, gemma2-9b-it

Free tier: 30 requests/min

Usage:
    provider = GroqProvider(model="llama-3.3-70b-versatile")
    response = provider.chat([{"role": "user", "content": "Hello"}])
"""

import os
import time
import json
import logging
from typing import List, Dict, Any, Optional

from .base import BaseProvider, LLMResponse

logger = logging.getLogger("atlas.aria.providers.groq")


class GroqProvider(BaseProvider):
    """
    Groq cloud LLM provider with OpenAI-compatible API.

    Supports:
      - Ultra-fast inference (2-4x faster than alternatives)
      - llama-3.3-70b, mixtral-8x7b, gemma2-9b
      - Tool/function calling
      - Free tier: 30 requests/minute
    """

    # Groq free models with context windows
    AVAILABLE_MODELS = {
        "llama-3.3-70b-versatile": {"context": 8192, "tokens_per_min": 6000},
        "mixtral-8x7b-32768": {"context": 32768, "tokens_per_min": 5000},
        "gemma2-9b-it": {"context": 8192, "tokens_per_min": 15000},
        "llama-3.1-70b-versatile": {"context": 8192, "tokens_per_min": 6000},
        "llama-3.1-8b-instant": {"context": 8192, "tokens_per_min": 20000},
    }

    def __init__(self,
                 model: str = "llama-3.3-70b-versatile",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 4096,
                 base_url: str = "https://api.groq.com/openai/v1",
                 **kwargs):
        """
        Initialize Groq provider.

        Args:
            model: Groq model name
            api_key: GROQ_API_KEY from environment or parameter
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            base_url: Groq API base URL
        """
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.base_url = base_url
        self._rate_limit_remaining = 30
        self._rate_limit_reset_time = 0

    def chat(self,
             messages: List[Dict[str, str]],
             tools: Optional[List[Dict]] = None,
             temperature: Optional[float] = None) -> LLMResponse:
        """
        Send messages to Groq API.

        Uses requests library to make OpenAI-compatible API calls.
        """
        if not self.api_key:
            return LLMResponse(
                content="[Groq Error] No API key configured. Set GROQ_API_KEY environment variable.",
                model=self.model,
                provider="groq",
            )

        t0 = time.time()
        try:
            import requests
        except ImportError:
            return LLMResponse(
                content="[Groq Error] requests library not installed. Run: pip install requests",
                model=self.model,
                provider="groq",
            )

        try:
            # Check rate limits before making request
            if time.time() < self._rate_limit_reset_time:
                logger.warning(
                    "Groq rate limit approaching. Remaining: %d requests/min",
                    self._rate_limit_remaining
                )

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

            # Headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            # Make request
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=30,
            )

            latency = (time.time() - t0) * 1000

            # Handle rate limit headers
            if "x-ratelimit-remaining-requests" in response.headers:
                self._rate_limit_remaining = int(
                    response.headers.get("x-ratelimit-remaining-requests", 30)
                )
            if "x-ratelimit-reset-requests" in response.headers:
                reset_str = response.headers.get("x-ratelimit-reset-requests", "0s")
                if reset_str.endswith("s"):
                    self._rate_limit_reset_time = time.time() + int(reset_str[:-1])

            # Check for errors
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                logger.error("Groq API error: %s (status %d)", error_msg, response.status_code)
                return LLMResponse(
                    content=f"[Groq Error] {error_msg}",
                    model=self.model,
                    provider="groq",
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
                provider="groq",
                tokens_used=tokens_used,
                latency_ms=latency,
                tool_calls=tool_calls,
                raw=data,
            )

            self._track_request(response_obj)
            logger.debug(
                "Groq request successful: %s tokens, %.1f ms, finish=%s",
                tokens_used, latency, finish_reason
            )
            return response_obj

        except requests.exceptions.Timeout:
            latency = (time.time() - t0) * 1000
            logger.error("Groq request timed out after %.1f ms", latency)
            return LLMResponse(
                content="[Groq Error] Request timed out. Try simplifying your query.",
                model=self.model,
                provider="groq",
                latency_ms=latency,
            )
        except requests.exceptions.ConnectionError as e:
            latency = (time.time() - t0) * 1000
            logger.error("Groq connection failed: %s", str(e))
            return LLMResponse(
                content="[Groq Error] Unable to connect to Groq API.",
                model=self.model,
                provider="groq",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - t0) * 1000
            logger.exception("Groq provider error: %s", str(e))
            return LLMResponse(
                content=f"[Groq Error] {str(e)[:200]}",
                model=self.model,
                provider="groq",
                latency_ms=latency,
            )

    def is_available(self) -> bool:
        """
        Check if Groq provider is available (has valid API key).

        Note: This doesn't actually ping the API to avoid rate limit consumption.
        Real availability check happens on first request.
        """
        return bool(self.api_key)

    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        model_info = self.AVAILABLE_MODELS.get(self.model, {})
        return {
            "name": "GroqProvider",
            "type": "cloud",
            "model": self.model,
            "available": self.is_available(),
            "cost": "free_tier",
            "free_tier": "30 requests/min",
            "context_window": model_info.get("context", 8192),
            "latency_note": "2-4x faster than alternatives",
        }
