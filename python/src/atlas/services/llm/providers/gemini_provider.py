"""Google Gemini provider — used for repo scout, research, comparisons."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from .base import BaseLLMProvider, LLMResponse


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini API provider.

    Requires GEMINI_API_KEY environment variable.
    Best for: repo scout, research comparative, alternative ideas.

    Default model: gemini-1.5-flash (fast + large context)
    Strong model:  gemini-1.5-pro
    """

    provider_name: str = "gemini"
    default_model: str = "gemini-1.5-flash"
    API_BASE:      str = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key:       Optional[str] = None,
        default_model: str           = "gemini-1.5-flash",
        timeout:       int           = 120,
    ):
        self.api_key       = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.default_model = default_model
        self.timeout       = timeout

    def generate(
        self,
        prompt:      str,
        model:       Optional[str] = None,
        temperature: float         = 0.3,
        max_tokens:  int           = 4096,
        **kwargs,
    ) -> LLMResponse:
        if not self.api_key:
            raise EnvironmentError("GEMINI_API_KEY not set")

        model = model or self.default_model
        t0    = time.perf_counter()

        url = f"{self.API_BASE}/{model}:generateContent?key={self.api_key}"
        body: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature":    temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url     = url,
            data    = payload,
            headers = {"Content-Type": "application/json"},
            method  = "POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini API error {e.code}: {body_err}") from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"Gemini API unreachable: {e}") from e

        elapsed = int((time.perf_counter() - t0) * 1000)

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            text = str(data)

        usage = data.get("usageMetadata", {})

        return LLMResponse(
            text       = text,
            model      = model,
            provider   = self.provider_name,
            tokens_in  = usage.get("promptTokenCount", 0),
            tokens_out = usage.get("candidatesTokenCount", 0),
            latency_ms = elapsed,
            raw        = data,
        )

    def is_available(self) -> bool:
        return bool(self.api_key)
