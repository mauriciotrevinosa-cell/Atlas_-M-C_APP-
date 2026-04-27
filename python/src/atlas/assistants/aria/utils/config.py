"""
Configuration management for ARIA — Multi-Backend Edition

Supports any combination of:
  - Local:  Ollama
  - Free cloud:   Groq, OpenRouter, Cerebras
  - Paid cloud:   OpenAI, Anthropic
  - Testing:  Mock

Backend is selected by ARIA_LLM_BACKEND. If unset, ARIA auto-picks the first
provider that has valid credentials (via ProviderManager).

Copyright (c) 2026 M&C. All rights reserved.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional — env vars still work if set manually.
    pass


# Providers that ARIA knows how to talk to. Order here also defines the
# default fallback priority (cheapest/fastest first).
SUPPORTED_BACKENDS = (
    "ollama",       # Local (no key)
    "groq",         # Free tier, very fast
    "openrouter",   # Free tier available
    "cerebras",     # Free tier, fastest inference
    "openai",       # Paid
    "anthropic",    # Paid
    "mock",         # No network, always works
    "auto",         # Let ProviderManager decide
)


class Config:
    """ARIA configuration — Multi-Backend Edition."""

    # --- LLM Backend selection -------------------------------------------
    # Set to "auto" (default) to let ProviderManager pick the first provider
    # with valid credentials. Or force a specific one.
    LLM_BACKEND = os.getenv("ARIA_LLM_BACKEND", "auto").lower()

    # --- Ollama (local) ---------------------------------------------------
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    # --- Cloud providers (all optional) ----------------------------------
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv(
        "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"
    )

    CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
    CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "llama3.1-70b")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    # --- Model settings ---------------------------------------------------
    MAX_TOKENS = int(os.getenv("ARIA_MAX_TOKENS", "4096"))
    TEMPERATURE = float(os.getenv("ARIA_TEMPERATURE", "0.7"))

    # --- Voice / memory ---------------------------------------------------
    VOICE_MODE = os.getenv("ARIA_VOICE_MODE", "basic")
    MEMORY_TYPE = os.getenv("ARIA_MEMORY_TYPE", "local")

    # --- Paths ------------------------------------------------------------
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    CACHE_DIR = DATA_DIR / "cache"
    MEMORY_DIR = DATA_DIR / "memory"

    # ------------------------------------------------------------- helpers
    @classmethod
    def available_cloud_keys(cls) -> list[str]:
        """Return names of cloud providers that have credentials set."""
        mapping = {
            "groq":       cls.GROQ_API_KEY,
            "openrouter": cls.OPENROUTER_API_KEY,
            "cerebras":   cls.CEREBRAS_API_KEY,
            "openai":     cls.OPENAI_API_KEY,
            "anthropic":  cls.ANTHROPIC_API_KEY,
        }
        return [name for name, key in mapping.items() if key]

    @staticmethod
    def _safe_print(msg: str) -> None:
        """Print safely across Windows cp1252 consoles (strips unicode if needed)."""
        try:
            print(msg)
        except UnicodeEncodeError:
            try:
                print(msg.encode("ascii", errors="replace").decode("ascii"))
            except Exception:
                pass

    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration. NEVER hard-fail — we always have a fallback
        (mock provider) so the app keeps running.
        """
        backend = cls.LLM_BACKEND

        if backend not in SUPPORTED_BACKENDS:
            cls._safe_print(f"[!] Unknown ARIA_LLM_BACKEND='{backend}'. "
                            f"Supported: {', '.join(SUPPORTED_BACKENDS)}. Falling back to 'auto'.")
            cls.LLM_BACKEND = "auto"
            backend = "auto"

        if backend == "ollama":
            cls._safe_print(f"[OK] ARIA backend: ollama (local) @ {cls.OLLAMA_HOST} - no API key needed")
        elif backend == "auto":
            cloud = cls.available_cloud_keys()
            if cloud:
                cls._safe_print(f"[OK] ARIA backend: auto (will try: ollama, {', '.join(cloud)}, mock)")
            else:
                cls._safe_print("[OK] ARIA backend: auto (will try ollama -> mock; "
                                "add GROQ_API_KEY or OPENROUTER_API_KEY to .env for free cloud fallback)")
        elif backend == "mock":
            cls._safe_print("[OK] ARIA backend: mock (testing mode - no real LLM calls)")
        else:
            key_attr = f"{backend.upper()}_API_KEY"
            key = getattr(cls, key_attr, None)
            if not key:
                cls._safe_print(f"[!] ARIA backend '{backend}' selected but {key_attr} not set. "
                                f"ARIA will auto-fallback to another available provider.")
            else:
                cls._safe_print(f"[OK] ARIA backend: {backend} (cloud)")

        return True

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories."""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.CACHE_DIR.mkdir(exist_ok=True)
        cls.MEMORY_DIR.mkdir(exist_ok=True)


# Validate on import (non-fatal)
try:
    Config.validate()
    Config.ensure_directories()
except Exception as _cfg_exc:
    # Config must never break the whole app.
    import logging as _l
    _l.getLogger("atlas.aria").warning("Config validation non-fatal error: %s", _cfg_exc)
