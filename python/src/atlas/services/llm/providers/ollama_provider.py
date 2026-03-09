"""Ollama local LLM provider — primary/free tier for Atlas agents."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from .base import BaseLLMProvider, LLMResponse


class OllamaProvider(BaseLLMProvider):
    """
    Ollama local inference provider.

    Connects to a running Ollama instance (default: http://localhost:11434).
    No API key required. Best for planner, context curator, light tasks.

    Supported models (install via `ollama pull <model>`):
      - qwen2.5       (fast, good reasoning)
      - llama3.1      (general purpose)
      - deepseek-coder (code tasks)
      - mistral       (balanced)
    """

    provider_name: str = "ollama"
    default_model: str = "qwen2.5"

    def __init__(
        self,
        base_url:      str  = "http://localhost:11434",
        default_model: str  = "qwen2.5",
        timeout:       int  = 120,
    ):
        self.base_url      = base_url.rstrip("/")
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
        model = model or self.default_model
        t0    = time.perf_counter()

        payload = json.dumps({
            "model":   model,
            "prompt":  prompt,
            "stream":  False,
            "options": {
                "temperature":  temperature,
                "num_predict":  max_tokens,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            url     = f"{self.base_url}/api/generate",
            data    = payload,
            headers = {"Content-Type": "application/json"},
            method  = "POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise ConnectionError(f"Ollama unreachable at {self.base_url}: {e}") from e

        elapsed = int((time.perf_counter() - t0) * 1000)

        return LLMResponse(
            text       = data.get("response", ""),
            model      = model,
            provider   = self.provider_name,
            tokens_in  = data.get("prompt_eval_count", 0),
            tokens_out = data.get("eval_count", 0),
            latency_ms = elapsed,
            raw        = data,
        )

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            urllib.request.urlopen(req, timeout=3)
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """Return list of locally available models."""
        try:
            req  = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
