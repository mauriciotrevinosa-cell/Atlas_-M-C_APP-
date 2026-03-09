"""
OpenAI Provider — Cloud LLM backend (GPT-4, GPT-4o, etc.)

Usage:
    provider = OpenAIProvider(model="gpt-4o", api_key="sk-...")
    response = provider.chat([{"role": "user", "content": "Hello"}])
"""

import os
import time
import json
from typing import List, Dict, Any, Optional

from .base import BaseProvider, LLMResponse


class OpenAIProvider(BaseProvider):
    """
    OpenAI API provider.

    Supports:
      - GPT-4, GPT-4o, GPT-4o-mini, etc.
      - Tool/function calling
      - Structured outputs
    """

    def __init__(self,
                 model: str = "gpt-4o-mini",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 4096,
                 **kwargs):
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._client = None
        if self.api_key:
            self._connect()

    def _connect(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Run: pip install openai"
            )

    def chat(self,
             messages: List[Dict[str, str]],
             tools: Optional[List[Dict]] = None,
             temperature: Optional[float] = None) -> LLMResponse:
        """Send messages to OpenAI API."""
        if not self._client:
            if not self.api_key:
                return LLMResponse(
                    content="[OpenAI Error] No API key configured. Set OPENAI_API_KEY env variable.",
                    model=self.model,
                    provider="openai",
                )
            self._connect()

        t0 = time.time()
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "max_tokens": self.max_tokens,
            }

            # Convert tool schemas to OpenAI format if needed
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            raw = self._client.chat.completions.create(**kwargs)

            latency = (time.time() - t0) * 1000
            choice = raw.choices[0] if raw.choices else None
            msg = choice.message if choice else None

            # Extract tool calls
            tool_calls = []
            if msg and msg.tool_calls:
                for tc in msg.tool_calls:
                    args = tc.function.arguments
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    tool_calls.append({
                        "name": tc.function.name,
                        "arguments": args,
                        "id": tc.id,
                    })

            tokens = raw.usage.total_tokens if raw.usage else 0

            response = LLMResponse(
                content=msg.content if msg else "",
                model=self.model,
                provider="openai",
                tokens_used=tokens,
                latency_ms=latency,
                tool_calls=tool_calls,
                raw=raw,
            )
            self._track_request(response)
            return response

        except Exception as e:
            latency = (time.time() - t0) * 1000
            return LLMResponse(
                content=f"[OpenAI Error] {str(e)}",
                model=self.model,
                provider="openai",
                tokens_used=0,
                latency_ms=latency,
            )

    def is_available(self) -> bool:
        """Check if OpenAI API key is set and valid."""
        if not self.api_key:
            return False
        try:
            if not self._client:
                self._connect()
            # Quick check — list models
            self._client.models.list()
            return True
        except Exception:
            return False

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "OpenAIProvider",
            "type": "cloud",
            "model": self.model,
            "available": bool(self.api_key),
            "cost": "paid",
        }
