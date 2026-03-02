"""
Core Intelligence Engines
========================

Trading engines (Signal Generators).

Submodules:
- rule_based: Classic logic (MA cross, breakouts)
- ml: Machine Learning models (RF, XGB, LSTM)
- rl: Reinforcement Learning agents

Copyright (c) 2026 M&C. All rights reserved.
"""

from .base_engine import BaseEngine, EngineType, Signal
from .registry import EngineRegistry

__all__ = ['BaseEngine', 'EngineType', 'Signal', 'EngineRegistry']
