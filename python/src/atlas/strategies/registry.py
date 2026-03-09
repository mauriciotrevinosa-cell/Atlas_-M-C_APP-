"""
StrategyRegistry — Phase 4 Specialized Engines

Central factory for all registered Atlas strategies.
Follows the same Registry pattern used in atlas.indicators.registry.

Usage::

    from atlas.strategies.registry import StrategyRegistry

    # Register a strategy class (usually done in the module's __init__)
    StrategyRegistry.register("sma_crossover", SMACrossoverStrategy)

    # Instantiate with kwargs
    strategy = StrategyRegistry.create("sma_crossover", fast=10, slow=30)

    # List all available strategies
    print(StrategyRegistry.list())
"""

from __future__ import annotations

from typing import Any, Dict, List, Type

from atlas.strategies.base import BaseStrategy


class StrategyRegistry:
    """
    Class-level registry mapping strategy names → strategy classes.

    Strategies register themselves at import time via
    ``StrategyRegistry.register()``. The registry never holds live
    instances — it creates fresh ones via ``create()``.
    """

    _registry: Dict[str, Type[BaseStrategy]] = {}

    # ── Registration ─────────────────────────────────────────────────────────

    @classmethod
    def register(cls, name: str, strategy_cls: Type[BaseStrategy]) -> None:
        """
        Register a strategy class under the given name.

        Args:
            name:         Unique key (e.g. "sma_crossover").
            strategy_cls: Class that inherits from BaseStrategy.

        Raises:
            TypeError:  If strategy_cls does not subclass BaseStrategy.
            ValueError: If name is already registered.
        """
        if not issubclass(strategy_cls, BaseStrategy):
            raise TypeError(
                f"{strategy_cls.__name__} must inherit from BaseStrategy."
            )
        if name in cls._registry:
            raise ValueError(
                f"Strategy '{name}' is already registered. "
                "Use a different name or deregister first."
            )
        cls._registry[name] = strategy_cls

    @classmethod
    def deregister(cls, name: str) -> None:
        """Remove a strategy from the registry (useful in tests)."""
        cls._registry.pop(name, None)

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> BaseStrategy:
        """
        Instantiate a registered strategy.

        Args:
            name:    Registered strategy key.
            **kwargs: Passed to the strategy constructor.

        Returns:
            A fresh BaseStrategy instance.

        Raises:
            KeyError: If name is not registered.
        """
        if name not in cls._registry:
            available = cls.list()
            raise KeyError(
                f"Strategy '{name}' not found. "
                f"Available: {available}"
            )
        return cls._registry[name](**kwargs)

    # ── Introspection ─────────────────────────────────────────────────────────

    @classmethod
    def list(cls) -> List[str]:
        """Return sorted list of all registered strategy names."""
        return sorted(cls._registry.keys())

    @classmethod
    def get_class(cls, name: str) -> Type[BaseStrategy]:
        """Return the class registered under *name* without instantiating."""
        if name not in cls._registry:
            raise KeyError(f"Strategy '{name}' not found.")
        return cls._registry[name]

    @classmethod
    def clear(cls) -> None:
        """Remove all registrations (useful in tests)."""
        cls._registry.clear()
