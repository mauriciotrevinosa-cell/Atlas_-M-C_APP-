"""
Ollama Provider — Local LLM backend (llama3.1, qwen, deepseek, etc.)

Usage:
    provider = OllamaProvider(model="llama3.1:8b")
    response = provider.chat([{"role": "user", "content": "Hello"}])
"""

import json
import time
from collections.abc import Mapping
from typing import Any, Dict, List, Optional

from .base import BaseProvider, LLMResponse


class OllamaProvider(BaseProvider):
    """
    Local LLM provider via Ollama.

    Supports:
      - Any model available in Ollama (llama3.1, qwen2.5, deepseek-r1, etc.)
      - Tool/function calling (model-dependent)
      - Streaming (future)
    """

    def __init__(self,
                 model: str = "llama3.1:8b",
                 host: str = "http://localhost:11434",
                 temperature: float = 0.7,
                 max_tokens: int = 4096,
                 **kwargs):
        super().__init__(model=model, temperature=temperature, max_tokens=max_tokens)
        self.host = host
        self._ollama = None
        self._connect()

    def _connect(self):
        """Lazy import and connect to Ollama."""
        try:
            import ollama
            client_cls = getattr(ollama, "Client", None)
            self._ollama = client_cls(host=self.host) if client_cls else ollama
        except ImportError:
            raise ImportError(
                "Ollama package not installed. Run: pip install ollama"
            )

    @staticmethod
    def _get_field(value: Any, name: str, default: Any = None) -> Any:
        """Read fields from either dict-like payloads or typed Ollama SDK objects."""
        if isinstance(value, Mapping):
            return value.get(name, default)
        return getattr(value, name, default)

    @classmethod
    def _extract_model_names(cls, payload: Any) -> List[str]:
        models = cls._get_field(payload, "models", []) or []
        names: List[str] = []
        for model in models:
            name = cls._get_field(model, "name") or cls._get_field(model, "model") or ""
            if name:
                names.append(str(name))
        return names

    def chat(self,
             messages: List[Dict[str, str]],
             tools: Optional[List[Dict]] = None,
             temperature: Optional[float] = None) -> LLMResponse:
        """Send messages to local Ollama model."""
        if not self._ollama:
            self._connect()

        t0 = time.time()
        try:
            opts = {
                "temperature": temperature or self.temperature,
                "num_predict": self.max_tokens,
            }

            kwargs = {
                "model": self.model,
                "messages": messages,
                "options": opts,
            }
            if tools:
                kwargs["tools"] = tools

            raw = self._ollama.chat(**kwargs)

            latency = (time.time() - t0) * 1000
            msg = self._get_field(raw, "message", {}) or {}

            # Extract tool calls if present
            tool_calls = []
            raw_tool_calls = self._get_field(msg, "tool_calls", []) or []
            if raw_tool_calls:
                for tc in raw_tool_calls:
                    fn = self._get_field(tc, "function", {}) or {}
                    args = self._get_field(fn, "arguments", {}) or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}
                    tool_calls.append({
                        "name": self._get_field(fn, "name", "") or "",
                        "arguments": args,
                    })

            # Token count (Ollama provides eval_count)
            tokens = (self._get_field(raw, "eval_count", 0) or 0) + (
                self._get_field(raw, "prompt_eval_count", 0) or 0
            )

            response = LLMResponse(
                content=self._get_field(msg, "content", "") or "",
                model=self.model,
                provider="ollama",
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
                content=f"[Ollama Error] {str(e)}",
                model=self.model,
                provider="ollama",
                tokens_used=0,
                latency_ms=latency,
            )

    def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            if not self._ollama:
                self._connect()
            models = self._ollama.list()
            model_names = self._extract_model_names(models)
            requested = (self.model or "").strip()
            if not requested:
                return bool(model_names)
            return any(
                name == requested
                or (":" not in requested and name.startswith(f"{requested}:"))
                for name in model_names
            )
        except Exception:
            return False

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "OllamaProvider",
            "type": "local",
            "model": self.model,
            "host": self.host,
            "available": self.is_available(),
            "cost": "free",
        }
