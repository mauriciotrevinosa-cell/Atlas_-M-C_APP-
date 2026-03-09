"""OpenAI / ChatGPT provider — used for reviewer, architecture decisions."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from .base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI ChatGPT API provider.

    Requires OPENAI_API_KEY environment variable.
    Best for: reviewer agent, architectural validation, design decisions.

    Default model: gpt-4o-mini (fast + cheap)
    Strong model:  gpt-4o (best reasoning)
    """

    provider_name: str = "openai"
    default_model: str = "gpt-4o-mini"
    API_URL:       str = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        api_key:       Optional[str] = None,
        default_model: str           = "gpt-4o-mini",
        timeout:       int           = 120,
        base_url:      Optional[str] = None,   # supports OpenAI-compatible APIs
    ):
        self.api_key       = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.default_model = default_model
        self.timeout       = timeout
        self.api_url       = (base_url or self.API_URL).rstrip("/")
        if not self.api_url.endswith("completions"):
            self.api_url += "/chat/completions"

    def generate(
        self,
        prompt:      str,
        model:       Optional[str] = None,
        temperature: float         = 0.3,
        max_tokens:  int           = 4096,
        system:      str           = "You are a helpful assistant for the Atlas trading system.",
        **kwargs,
    ) -> LLMResponse:
        if not self.api_key:
            raise EnvironmentError("OPENAI_API_KEY not set")

        model = model or self.default_model
        t0    = time.perf_counter()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body: Dict[str, Any] = {
            "model":       model,
            "messages":    messages,
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url     = self.api_url,
            data    = payload,
            headers = {
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method = "POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error {e.code}: {body_err}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"OpenAI API unreachable: {e}") from e

        elapsed = int((time.perf_counter() - t0) * 1000)
        text    = data["choices"][0]["message"]["content"]
        usage   = data.get("usage", {})

        return LLMResponse(
            text       = text,
            model      = model,
            provider   = self.provider_name,
            tokens_in  = usage.get("prompt_tokens", 0),
            tokens_out = usage.get("completion_tokens", 0),
            latency_ms = elapsed,
            raw        = data,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)
