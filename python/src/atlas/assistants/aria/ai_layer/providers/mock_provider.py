"""
Mock Provider — For testing, development, and eval suites.

Returns deterministic responses without any LLM calls.
Perfect for:
  - Unit tests
  - CI/CD pipelines
  - Offline development
  - Eval harness
"""

import time
import hashlib
from typing import List, Dict, Any, Optional

from .base import BaseProvider, LLMResponse


# Canned responses keyed by intent keywords
MOCK_RESPONSES = {
    "hello": "Hello! I'm ARIA in mock mode. All systems nominal.",
    "kin towers": "KiN Towers is a mixed-use development in Cancun with 190 units, CTC of $1,700.6M MXN.",
    "ctc": "The CTC (Costo Total de Construccion) is $1,700,551,800 MXN ($102.8M USD at TC $16.55).",
    "tipo de cambio": "The current project exchange rate is $16.55 MXN per USD.",
    "terreno": "The lot is 9,506.69 m2 gross (7,267.99 m2 net after donations), located on Av. Bonampak, Cancun.",
    "unidades": "The project has 190 max units: 80 residential (Torre Norte) + 80 hotel (Torre Sur) + commercial.",
    "costo total": "Total project cost (Adquisicion): $3,574,235,296 MXN / $215,965,879 USD.",
    "equipo": "Director General: Mauricio Trevino, Dir. Adjunto: Carlos Pickering, Dir. Proyectos: Azyadeh Saldana.",
    "default": "I'm in mock mode. I can answer questions about KiN Towers project data.",
}


class MockProvider(BaseProvider):
    """
    Mock/test provider that returns canned responses.
    Zero latency, zero cost, deterministic.
    """

    def __init__(self,
                 model: str = "mock-v1",
                 latency_ms: float = 10.0,
                 **kwargs):
        super().__init__(model=model, temperature=0.0)
        self._latency_ms = latency_ms
        self._call_log: List[Dict] = []

    def chat(self,
             messages: List[Dict[str, str]],
             tools: Optional[List[Dict]] = None,
             temperature: Optional[float] = None) -> LLMResponse:
        """Return mock response based on keyword matching."""
        t0 = time.time()

        # Get last user message
        user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "").lower()
                break

        # Match response
        content = MOCK_RESPONSES["default"]
        for keyword, response in MOCK_RESPONSES.items():
            if keyword in user_msg:
                content = response
                break

        # Simulate latency
        elapsed = (time.time() - t0) * 1000
        if elapsed < self._latency_ms:
            time.sleep((self._latency_ms - elapsed) / 1000)

        # Fake token count based on content length
        tokens = len(content.split()) * 2

        # Log call
        self._call_log.append({
            "input": user_msg,
            "output": content,
            "timestamp": time.time(),
        })

        response = LLMResponse(
            content=content,
            model=self.model,
            provider="mock",
            tokens_used=tokens,
            latency_ms=self._latency_ms,
        )
        self._track_request(response)
        return response

    def is_available(self) -> bool:
        """Mock is always available."""
        return True

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": "MockProvider",
            "type": "mock",
            "model": self.model,
            "available": True,
            "cost": "free",
            "calls_made": len(self._call_log),
        }

    def get_call_log(self) -> List[Dict]:
        """Get all calls made to the mock provider (for test assertions)."""
        return self._call_log

    def reset(self):
        """Reset call log."""
        self._call_log = []
