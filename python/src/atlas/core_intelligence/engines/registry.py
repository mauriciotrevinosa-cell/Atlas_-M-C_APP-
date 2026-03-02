"""
Engine Registry Module
=====================

Manages the registration and retrieval of trading engines.
Allows dynamic loading of strategies (Rule-Based, ML, RL).

Copyright (c) 2026 M&C. All rights reserved.
"""

from typing import Dict, List, Type, Optional
import logging
from .base_engine import BaseEngine, EngineType

logger = logging.getLogger(__name__)

class EngineRegistry:
    """
    Central registry for all trading engines.
    """
    
    _engines: Dict[str, BaseEngine] = {}
    
    @classmethod
    def register(cls, engine: BaseEngine):
        """Register a new engine instance"""
        if engine.name in cls._engines:
            logger.warning(f"Overwriting existing engine: {engine.name}")
        cls._engines[engine.name] = engine
        logger.info(f"Registered Engine: {engine.name}")
        
    @classmethod
    def get_engine(cls, name: str) -> Optional[BaseEngine]:
        """Retrieve an engine by name"""
        return cls._engines.get(name)
        
    @classmethod
    def get_all_engines(cls) -> List[BaseEngine]:
        """Get all registered engines"""
        return list(cls._engines.values())
        
    @classmethod
    def get_engines_by_type(cls, engine_type: EngineType) -> List[BaseEngine]:
        """Get all engines of a specific type"""
        return [e for e in cls._engines.values() if e.engine_type == engine_type]

    @classmethod
    def clear(cls):
        """Clear the registry (useful for testing)"""
        cls._engines.clear()
