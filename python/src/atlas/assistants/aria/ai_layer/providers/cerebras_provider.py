"""
Cerebras Provider — Ultra-fast AI accelerated inference.

Cerebras offers extremely fast inference via their specialized hardware.
Models: llama3.1-8b, llama3.1-70b

Free tier: Limited requests

Usage:
    provider = CerebrasProvider(model="llama3.1-70b")
    response = provider.chat([{"role": "user", "content": "Hello"}])
"""

import os
import time
import json
import logging
from typing import List, Dict, Any, Optional

from .base import BaseProvider, LLMResponse

logger = logging.getLogger("atlas.aria.providers.cerebras")


class CerebrasProvider(BaseProvider):
    """
    Cerebras ultra-fast AI inference provider.

    Supports:
      - Llama 3.1 models (8b and 70b)
      - Tool/function calling
      - Very fast inference via specialized hardware
      - Free tier available
    """

    AVAILABLE_MODELS = {
        "llama3.1-8b": {"context": 8192},
        "llama3.1-70b": {"context": 8192},
    }

    def __init__(self,
                 model: str = "llama3.1-70b",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 4096,
                 base_url: str = "https://api.cerebras.ai/v1",
                 **kwargs):
        """
        Initialize Cerebras provider.

        Args:
            model: Cerebras model name
            api_key: CEREBRAS_API_KEY from environment or parameter
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            base_url: Cerebras API base URL
        """
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.api_key = api_key or os.getenv("CEREBRAS_API_KEY", "")
        self.base_url = base_url

    def chat(self,
             messages: List[Dict[str, str]],
             tools: Optional[List[Dict]] = None,
             temperature: Optional[float] = None) -> LLMResponse:
        """
        Send messages to Cerebras API.

        Uses requests library to make OpenAI-compatible API calls.
        """
        if not self.api_key:
            return LLMResponse(
                content="[Cerebras Error] No API key configured. Set CEREBRAS_API_KEY environment variable.",
                model=self.model,
                provider="cerebras",
            )

        t0 = time.time()
        try:
            import requests
        except ImportError:
            return LLMResponse(
                content="[Cerebras Error] requests library not installed. Run: pip install requests",
                model=self.model,
                provider="cerebras",
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

            # Check for errors
            if response.status_code != 200:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                if isinstance(error_msg, dict):
                    error_msg = str(error_msg)
                logger.error(
                    "Cerebras API error: %s (status %d)",
                    error_msg[:200], response.status_code
                )
                return LLMResponse(
                    content=f"[Cerebras Error] {error_msg[:200]}",
                    model=self.model,
                    provider="cerebras",
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
                provider="cerebras",
                tokens_used=tokens_used,
                latency_ms=latency,
                tool_calls=tool_calls,
                raw=data,
            )

            self._track_request(response_obj)
            logger.debug(
                "Cerebras request successful: %s tokens, %.1f ms, finish=%s",
                tokens_used, latency, finish_reason
            )
            return response_obj

        except requests.exceptions.Timeout:
            latency = (time.time() - t0) * 1000
            logger.error("Cerebras request timed out after %.1f ms", latency)
            return LLMResponse(
                content="[Cerebras Error] Request timed out. Try simplifying your query.",
                model=self.model,
                provider="cerebras",
                latency_ms=latency,
            )
        except requests.exceptions.ConnectionError as e:
            latency = (time.time() - t0) * 1000
            logger.error("Cerebras connection failed: %s", str(e))
            return LLMResponse(
                content="[Cerebras Error] Unable to connect to Cerebras API.",
                model=self.model,
                provider="cerebras",
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - t0) * 1000
            logger.exception("Cerebras provider error: %s", str(e))
            return LLMResponse(
                content=f"[Cerebras Error] {str(e)[:200]}",
                model=self.model,
                provider="cerebras",
                latency_ms=latency,
            )

    def is_available(self) -> bool:
        """
        Check if Cerebras provider is available (has valid API key).

        Note: This doesn't actually ping the API to avoid unnecessary requests.
        Real availability check happens on first request.
        """
        return bool(self.api_key)

    def get_info(self) -> Dict[str, Any]:
        """Return provider metadata."""
        model_info = self.AVAILABLE_MODELS.get(self.model, {})
        return {
            "name": "CerebrasProvider",
            "type": "cloud",
            "model": self.model,
            "available": self.is_available(),
            "cost": "free_tier",
            "context_window": model_info.get("context", 8192),
            "latency_note": "Ultra-fast via specialized hardware",
        }
