"""
Provider Manager — Intelligent fallback chain with health tracking.

Manages multiple LLM providers with:
- Automatic provider detection based on available API keys
- Configurable fallback order
- Health tracking (skip providers that fail repeatedly)
- Audit logging of provider usage
- Per-request provider selection override

Design:
  1. Initialize with available providers
  2. Auto-detect which have valid API keys
  3. User can set preferred provider
  4. If preferred fails, fallback to next in chain
  5. Track health: 3 consecutive failures = temporary skip
"""

import os
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict

from .providers.base import BaseProvider, LLMResponse
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider
from .providers.groq_provider import GroqProvider
from .providers.openrouter_provider import OpenRouterProvider
from .providers.cerebras_provider import CerebrasProvider
from .providers.mock_provider import MockProvider

logger = logging.getLogger("atlas.aria.provider_manager")


class ProviderManager:
    """
    Manages multiple LLM providers with intelligent fallback.

    Tracks:
      - Available providers (those with valid API keys)
      - Health of each provider (consecutive failures)
      - Usage statistics per provider
      - Audit trail of which provider served each request
    """

    def __init__(self,
                 fallback_chain: Optional[List[str]] = None,
                 preferred_provider: Optional[str] = None,
                 ollama_model: Optional[str] = None):
        """
        Initialize provider manager.

        Args:
            fallback_chain: List of provider names in fallback order
                (default: real providers only; mock requires ARIA_ALLOW_MOCK=1)
            preferred_provider: User's preferred provider (may be overridden if unavailable)
            ollama_model: Optional Ollama model override.
        """
        self.mock_enabled = self._mock_enabled(preferred_provider)
        self.ollama_model = ollama_model

        # Default fallback chain (free/local options first, then paid).
        # Mock is intentionally excluded in normal runtime so ARIA never appears
        # "ready" while only serving canned answers.
        self.default_fallback_chain = [
            "ollama",
            "groq",
            "openrouter",
            "cerebras",
            "openai",
        ]
        if self.mock_enabled:
            self.default_fallback_chain.append("mock")

        selected_chain = fallback_chain or self.default_fallback_chain
        self.fallback_chain = self._filter_mock(selected_chain)
        self.preferred_provider = preferred_provider

        # Provider instances
        self._providers: Dict[str, BaseProvider] = {}

        # Health tracking
        self._consecutive_failures: Dict[str, int] = defaultdict(int)
        self._provider_skip_until: Dict[str, float] = {}
        self._last_failure_time: Dict[str, float] = {}

        # Usage statistics
        self._usage_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "requests": 0,
            "successes": 0,
            "failures": 0,
            "total_tokens": 0,
            "total_latency_ms": 0,
        })

        # Audit trail
        self._request_log: List[Dict[str, Any]] = []
        self._max_log_size = 1000

        # Initialize all providers
        self._initialize_providers()
        logger.info("ProviderManager initialized with chain: %s", self.fallback_chain)

    @staticmethod
    def _truthy(value: str | None) -> bool:
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    def _mock_enabled(self, preferred_provider: Optional[str]) -> bool:
        return (
            self._truthy(os.getenv("ARIA_ALLOW_MOCK"))
            or self._truthy(os.getenv("ATLAS_TEST_ALLOW_MOCK"))
            or (preferred_provider or "").lower() == "mock"
            or os.getenv("ARIA_LLM_BACKEND", "").lower() == "mock"
        )

    def _filter_mock(self, chain: List[str]) -> List[str]:
        if self.mock_enabled:
            return list(chain)
        return [name for name in chain if name != "mock"]

    def _initialize_providers(self):
        """Initialize all known providers (even if not available)."""
        providers_config = {
            "ollama": lambda: OllamaProvider(
                model=self.ollama_model or os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ),
            "openai": lambda: OpenAIProvider(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            ),
            "groq": lambda: GroqProvider(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            ),
            "openrouter": lambda: OpenRouterProvider(
                model=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
            ),
            "cerebras": lambda: CerebrasProvider(
                model=os.getenv("CEREBRAS_MODEL", "llama3.1-70b"),
            ),
            "mock": lambda: MockProvider(),
        }

        for name, factory in providers_config.items():
            if name == "mock" and not self.mock_enabled:
                continue
            try:
                self._providers[name] = factory()
                logger.debug("Initialized provider: %s", name)
            except Exception as e:
                logger.debug("Failed to initialize %s provider: %s", name, str(e))

    def set_provider_model(self, provider_name: str, model: str) -> None:
        """Update a provider's model when the UI switches model at runtime."""
        provider = self._providers.get(provider_name)
        if provider is not None and hasattr(provider, "model"):
            provider.model = model

    def get_available_providers(self) -> List[str]:
        """
        Get list of providers that are currently available (have valid keys/configs).

        Returns:
            List of provider names that can be used
        """
        available = []
        for name in self.fallback_chain:
            provider = self._providers.get(name)
            if provider and provider.is_available():
                # Check if temporarily skipped
                if name in self._provider_skip_until:
                    if time.time() < self._provider_skip_until[name]:
                        logger.debug("Provider %s is temporarily skipped", name)
                        continue
                    else:
                        del self._provider_skip_until[name]
                        self._consecutive_failures[name] = 0

                available.append(name)

        return available

    def set_preferred_provider(self, name: str) -> bool:
        """
        Set user's preferred provider.

        Args:
            name: Provider name

        Returns:
            True if provider is available, False otherwise
        """
        if name not in self._providers:
            logger.warning("Provider '%s' not found", name)
            return False

        provider = self._providers[name]
        if not provider.is_available():
            logger.warning("Provider '%s' is not available", name)
            return False

        self.preferred_provider = name
        logger.info("Preferred provider set to: %s", name)
        return True

    def chat_with_fallback(self,
                           messages: List[Dict[str, str]],
                           tools: Optional[List[Dict]] = None,
                           max_retries: int = 3) -> Tuple[LLMResponse, str]:
        """
        Send chat request with intelligent fallback.

        Tries providers in this order:
        1. Preferred provider (if set and available)
        2. Other available providers in fallback chain order
        3. Falls back on failure

        Args:
            messages: Chat messages
            tools: Optional tool definitions for function calling
            max_retries: Max times to retry with fallback chain

        Returns:
            Tuple of (LLMResponse, provider_name_used)
        """
        # Determine provider order
        available = self.get_available_providers()
        if not available:
            logger.error("No providers available!")
            return (
                LLMResponse(
                    content="[Fatal] No LLM providers available. Check API keys in .env",
                    model="unknown",
                    provider="none",
                ),
                "none"
            )

        # Start with preferred if available
        provider_order = []
        if self.preferred_provider and self.preferred_provider in available:
            provider_order.append(self.preferred_provider)

        # Add remaining providers
        for name in available:
            if name not in provider_order:
                provider_order.append(name)

        logger.debug("Provider order for fallback: %s", provider_order)

        # Try each provider
        last_response = None
        last_error = None

        for attempt, provider_name in enumerate(provider_order):
            if attempt >= max_retries:
                break

            try:
                provider = self._providers[provider_name]
                logger.debug("Attempting request with provider: %s", provider_name)

                # Send request
                response = provider.chat(messages, tools)

                # Check for error in response content
                if response.content.startswith("[") and "Error" in response.content:
                    logger.warning(
                        "Provider %s returned error response: %s",
                        provider_name, response.content[:100]
                    )
                    self._record_failure(provider_name)
                    last_error = response
                    continue

                # Success
                self._record_success(provider_name, response)
                self._log_request(provider_name, response, "success")
                logger.info(
                    "Request succeeded with %s (%d tokens, %.1f ms)",
                    provider_name, response.tokens_used, response.latency_ms
                )
                return (response, provider_name)

            except Exception as e:
                logger.exception("Provider %s failed with exception: %s", provider_name, str(e))
                self._record_failure(provider_name)
                last_error = str(e)
                continue

        # All providers failed
        logger.error("All providers exhausted. Last error: %s", str(last_error)[:200])
        fallback_response = last_error if isinstance(last_error, LLMResponse) else LLMResponse(
            content=f"[Fallback Failed] All providers exhausted. Last error: {str(last_error)[:100]}",
            model="unknown",
            provider="fallback",
        )
        self._log_request("fallback", fallback_response, "fallback")
        return (fallback_response, "fallback")

    def _record_success(self, provider_name: str, response: LLMResponse):
        """Record successful request."""
        stats = self._usage_stats[provider_name]
        stats["requests"] += 1
        stats["successes"] += 1
        stats["total_tokens"] += response.tokens_used
        stats["total_latency_ms"] += response.latency_ms

        # Reset failure counter on success
        self._consecutive_failures[provider_name] = 0
        if provider_name in self._last_failure_time:
            del self._last_failure_time[provider_name]

    def _record_failure(self, provider_name: str):
        """Record failed request and track consecutive failures."""
        stats = self._usage_stats[provider_name]
        stats["requests"] += 1
        stats["failures"] += 1

        self._consecutive_failures[provider_name] += 1
        self._last_failure_time[provider_name] = time.time()

        # If 3 consecutive failures, skip this provider for 5 minutes
        if self._consecutive_failures[provider_name] >= 3:
            skip_until = time.time() + 300  # 5 minutes
            self._provider_skip_until[provider_name] = skip_until
            logger.warning(
                "Provider %s skipped for 5 minutes after %d consecutive failures",
                provider_name, self._consecutive_failures[provider_name]
            )

    def _log_request(self, provider_name: str, response: LLMResponse, status: str):
        """Log request for audit trail."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "provider": provider_name,
            "model": response.model,
            "tokens": response.tokens_used,
            "latency_ms": response.latency_ms,
            "status": status,
        }

        self._request_log.append(entry)

        # Keep log size bounded
        if len(self._request_log) > self._max_log_size:
            self._request_log = self._request_log[-self._max_log_size:]

    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for all providers.

        Returns:
            Dictionary with stats per provider
        """
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "preferred_provider": self.preferred_provider,
            "available_providers": self.get_available_providers(),
            "providers": {}
        }

        for provider_name in self.fallback_chain:
            provider_stats = self._usage_stats.get(provider_name, {})
            if provider_stats["requests"] > 0:
                success_rate = (
                    provider_stats["successes"] / provider_stats["requests"] * 100
                    if provider_stats["requests"] > 0 else 0
                )
                avg_latency = (
                    provider_stats["total_latency_ms"] / provider_stats["requests"]
                    if provider_stats["requests"] > 0 else 0
                )

                stats["providers"][provider_name] = {
                    "requests": provider_stats["requests"],
                    "successes": provider_stats["successes"],
                    "failures": provider_stats["failures"],
                    "success_rate": f"{success_rate:.1f}%",
                    "avg_latency_ms": f"{avg_latency:.1f}",
                    "total_tokens": provider_stats["total_tokens"],
                }

        return stats

    def get_request_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent request log entries."""
        return self._request_log[-limit:]

    def reset_health(self, provider_name: Optional[str] = None):
        """
        Reset health tracking for a provider.

        Args:
            provider_name: Provider to reset (None = reset all)
        """
        if provider_name:
            self._consecutive_failures[provider_name] = 0
            if provider_name in self._provider_skip_until:
                del self._provider_skip_until[provider_name]
            logger.info("Reset health for provider: %s", provider_name)
        else:
            self._consecutive_failures.clear()
            self._provider_skip_until.clear()
            logger.info("Reset health for all providers")

    def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """Get detailed info about a specific provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            return {"error": f"Provider '{provider_name}' not found"}

        info = provider.get_info()
        info["stats"] = self._usage_stats.get(provider_name, {})
        info["consecutive_failures"] = self._consecutive_failures.get(provider_name, 0)

        if provider_name in self._provider_skip_until:
            skip_until = self._provider_skip_until[provider_name]
            seconds_remaining = max(0, skip_until - time.time())
            info["skipped_until_seconds"] = seconds_remaining

        return info
