"""
Ollama Provider — Local LLM backend (llama3.1, qwen, deepseek, etc.)

Usage:
    provider = OllamaProvider(model="llama3.1:8b")
    response = provider.chat([{"role": "user", "content": "Hello"}])
"""

import time
import json
from typing import List, Dict, Any, Optional

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
            self._ollama = ollama
        except ImportError:
            raise ImportError(
                "Ollama package not installed. Run: pip install ollama"
            )

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
            msg = raw.get("message", {})

            # Extract tool calls if present
            tool_calls = []
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
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
                    })

            # Token count (Ollama provides eval_count)
            tokens = raw.get("eval_count", 0) + raw.get("prompt_eval_count", 0)

            response = LLMResponse(
                content=msg.get("content", ""),
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
            model_names = [m.get("name", "") for m in models.get("models", [])]
            return any(self.model in n for n in model_names)
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
