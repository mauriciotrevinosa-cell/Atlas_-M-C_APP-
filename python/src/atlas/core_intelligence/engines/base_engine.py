"""
Base Engine Module
=================

Defines the abstract base class for all Trading Engines (Signal Generators).
Engines are responsible for analyzing data and generating trading signals.

Copyright (c) 2026 M&C. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class EngineType(Enum):
    RULE_BASED = "rule_based"
    ML = "machine_learning"
    RL = "reinforcement_learning"
    HYBRID = "hybrid"

@dataclass
class Signal:
    """Standardized trading signal"""
    symbol: str
    action: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0 to 1.0
    engine_name: str
    timestamp: pd.Timestamp
    metadata: Dict[str, Any]

class BaseEngine(ABC):
    """
    Abstract Base Class for all Trading Engines.
    
    All engines (Rule-based, ML, RL) must inherit from this class
    and implement the `analyze` method.
    """
    
    def __init__(self, name: str, engine_type: EngineType, config: Dict[str, Any] = None):
        self.name = name
        self.engine_type = engine_type
        self.config = config or {}
        self.is_active = True
        logger.info(f"Initialized Engine: {self.name} ({self.engine_type.value})")

    @abstractmethod
    def analyze(self, data: pd.DataFrame, context: Optional[Dict] = None) -> List[Signal]:
        """
        Analyze market data and generate signals.
        
        Args:
            data: Market data (OHLCV)
            context: Additional context (Market State, Portfolio, etc.)
            
        Returns:
            List of Signal objects
        """
        pass

    def validate_data(self, data: pd.DataFrame) -> bool:
        """Basic data validation logic"""
        if data.empty:
            logger.warning(f"{self.name}: Received empty data")
            return False
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_cols):
            logger.error(f"{self.name}: Missing required columns. Got {data.columns}")
            return False
        return True
