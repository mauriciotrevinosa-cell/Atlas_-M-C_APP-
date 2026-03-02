"""
Base class for data providers

Copyright (c) 2026 M&C. All rights reserved.
"""

from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional


class DataProvider(ABC):
    """
    Clase base abstracta para proveedores de datos
    
    Todos los providers (Yahoo, Alpaca, Polygon) heredan de esta clase
    y deben implementar estos métodos.
    """
    
    @abstractmethod
    def download(self, symbol: str, start: str, end: str, 
                 interval: str = "1d") -> pd.DataFrame:
        """
        Descargar datos históricos
        
        Args:
            symbol: Ticker symbol
            start: Fecha inicio (YYYY-MM-DD)
            end: Fecha fin (YYYY-MM-DD)
            interval: Timeframe (1d, 1h, 5m, etc.)
        
        Returns:
            pd.DataFrame con OHLCV
        """
        pass
    
    @abstractmethod
    def validate(self, data: pd.DataFrame) -> dict:
        """
        Validar calidad de datos
        
        Args:
            data: DataFrame a validar
        
        Returns:
            dict con resultados de validación
        """
        pass
    
    @abstractmethod
    def normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Normalizar formato de datos
        
        Args:
            data: DataFrame raw del provider
        
        Returns:
            pd.DataFrame normalizado a formato Atlas
        """
        pass
    
    def get_info(self) -> dict:
        """
        Información del provider
        
        Returns:
            dict con metadata del provider
        """
        return {
            'name': self.__class__.__name__,
            'version': getattr(self, 'version', '1.0.0'),
            'supported_assets': getattr(self, 'supported_assets', []),
            'rate_limit': getattr(self, 'rate_limit', None)
        }
