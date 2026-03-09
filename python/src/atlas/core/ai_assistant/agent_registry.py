"""
AgentRegistry — central catalog of all registered Atlas agents.

Agents must be registered before the orchestrator can dispatch tasks to them.
Supports lazy loading, version management, and capability queries.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from .agents.base import BaseAgent


class AgentRegistry:
    """
    Thread-safe registry for Atlas agents.

    Usage:
        registry = AgentRegistry()
        registry.register(PlannerAgent())
        agent = registry.get("planner_agent")
    """

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance. Overwrites if name already registered."""
        self._agents[agent.name] = agent

    def register_many(self, agents: List[BaseAgent]) -> None:
        """Register multiple agents at once."""
        for agent in agents:
            self.register(agent)

    def unregister(self, name: str) -> None:
        """Remove an agent by name."""
        self._agents.pop(name, None)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def get(self, name: str) -> BaseAgent:
        """
        Return agent by name.
        Raises KeyError if not registered.
        """
        if name not in self._agents:
            available = self.list_agents()
            raise KeyError(
                f"Agent '{name}' not registered. "
                f"Available agents: {available}"
            )
        return self._agents[name]

    def get_optional(self, name: str) -> Optional[BaseAgent]:
        """Return agent or None if not registered."""
        return self._agents.get(name)

    def has(self, name: str) -> bool:
        return name in self._agents

    # ── Introspection ─────────────────────────────────────────────────────────

    def list_agents(self) -> List[str]:
        """Return names of all registered agents."""
        return sorted(self._agents.keys())

    def info(self) -> List[Dict]:
        """Return info dict for each registered agent."""
        return [
            {"name": a.name, "version": a.version, "class": type(a).__name__}
            for a in self._agents.values()
        ]

    def __len__(self) -> int:
        return len(self._agents)

    def __repr__(self) -> str:
        return f"AgentRegistry(agents={self.list_agents()})"


# ── Singleton default registry ─────────────────────────────────────────────────
_default_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """Return the process-level default registry (lazy init)."""
    global _default_registry
    if _default_registry is None:
        _default_registry = AgentRegistry()
    return _default_registry
