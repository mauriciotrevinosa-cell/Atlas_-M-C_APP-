"""
Model Policy — defines which models are allowed per agent and risk level.

Centralized so you can change provider preferences without touching agent code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ModelSpec:
    provider: str
    model:    str
    max_tokens: int  = 4096
    temperature: float = 0.3

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


# Per-agent allowed providers (allowlist)
ALLOWED_PROVIDERS: Dict[str, List[str]] = {
    "planner_agent":         ["ollama", "openai", "claude"],
    "reviewer_agent":        ["openai", "claude"],
    "test_agent":            ["claude", "openai"],
    "context_curator_agent": ["ollama", "claude"],
    "code_builder_agent":    ["claude", "openai"],
    "repo_scout_agent":      ["gemini", "openai"],
    "ingestion_agent":       ["ollama", "claude"],
    "docs_agent":            ["claude", "openai"],
}

# Models that require human approval before use
HIGH_COST_MODELS = {
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "gpt-4o",
    "gemini-1.5-pro",
}

# Models completely blocked (too powerful for autonomous use)
BLOCKED_MODELS: List[str] = []


def is_provider_allowed(agent_name: str, provider: str) -> bool:
    allowed = ALLOWED_PROVIDERS.get(agent_name, [])
    return provider in allowed


def is_model_high_cost(model: str) -> bool:
    return model in HIGH_COST_MODELS


def is_model_blocked(model: str) -> bool:
    return model in BLOCKED_MODELS


def get_allowed_providers(agent_name: str) -> List[str]:
    return ALLOWED_PROVIDERS.get(agent_name, ["ollama"])
