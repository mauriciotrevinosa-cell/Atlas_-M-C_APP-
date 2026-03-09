"""Anthropic Claude provider — used for code builder, test agent, long docs."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from .base import BaseLLMProvider, LLMResponse


class ClaudeProvider(BaseLLMProvider):
    """
    Anthropic Claude API provider.

    Requires ANTHROPIC_API_KEY environment variable.
    Best for: code builder, test agent, complex reasoning, long documents.

    Default model: claude-3-5-haiku-20241022 (fast + cheap)
    Strong model:  claude-sonnet-4-5 (best quality)
    """

    provider_name: str = "claude"
    default_model: str = "claude-3-5-haiku-20241022"
    API_URL:       str = "https://api.anthropic.com/v1/messages"
    API_VERSION:   str = "2023-06-01"

    def __init__(
        self,
        api_key:       Optional[str] = None,
        default_model: str           = "claude-3-5-haiku-20241022",
        timeout:       int           = 120,
    ):
        self.api_key       = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.default_model = default_model
        self.timeout       = timeout

    def generate(
        self,
        prompt:      str,
        model:       Optional[str] = None,
        temperature: float         = 0.3,
        max_tokens:  int           = 4096,
        system:      str           = "",
        **kwargs,
    ) -> LLMResponse:
        if not self.api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set")

        model = model or self.default_model
        t0    = time.perf_counter()

        messages = [{"role": "user", "content": prompt}]
        body: Dict[str, Any] = {
            "model":      model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages":   messages,
        }
        if system:
            body["system"] = system

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url     = self.API_URL,
            data    = payload,
            headers = {
                "Content-Type":      "application/json",
                "x-api-key":         self.api_key,
                "anthropic-version": self.API_VERSION,
            },
            method  = "POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Claude API error {e.code}: {body_err}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"Claude API unreachable: {e}") from e

        elapsed   = int((time.perf_counter() - t0) * 1000)
        text      = data.get("content", [{}])[0].get("text", "")
        usage     = data.get("usage", {})

        return LLMResponse(
            text       = text,
            model      = model,
            provider   = self.provider_name,
            tokens_in  = usage.get("input_tokens", 0),
            tokens_out = usage.get("output_tokens", 0),
            latency_ms = elapsed,
            raw        = data,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)
