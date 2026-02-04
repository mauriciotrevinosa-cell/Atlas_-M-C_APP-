from typing import Dict, Type
from .base import Indicator
from .trend.moving_averages import SMA, EMA, WMA
from .momentum.oscillators import RSI, MACD, Stochastic
from .volatility.bands import ATR, BollingerBands
from .volume.volume_indicators import OBV, VWAP

class IndicatorRegistry:
    """
    Central registry for all available indicators.
    Allows dynamic lookup and instantiation.
    """
    
    _registry: Dict[str, Type[Indicator]] = {
        "SMA": SMA,
        "EMA": EMA,
        "WMA": WMA,
        "RSI": RSI,
        "MACD": MACD,
        "STOCH": Stochastic,
        "ATR": ATR,
        "BB": BollingerBands,
        "OBV": OBV,
        "VWAP": VWAP
    }
    
    @classmethod
    def get(cls, name: str) -> Type[Indicator]:
        """Get indicator class by name (case-insensitive)."""
        key = name.upper()
        if key not in cls._registry:
            raise ValueError(f"Indicator '{name}' not found in registry.")
        return cls._registry[key]
    
    @classmethod
    def list_all(cls) -> list:
        """List all available indicators."""
        return list(cls._registry.keys())
    
    @classmethod
    def create(cls, name: str, **kwargs) -> Indicator:
        """Factory method to instantiate an indicator."""
        indicator_cls = cls.get(name)
        return indicator_cls(**kwargs)
