"""
Data Normalizer

Convierte datos de diferentes providers a formato estándar de Atlas.

Formato Atlas:
- Index: DatetimeIndex (UTC)
- Columns: Open, High, Low, Close, Volume (capitalized)
- Sorted by date (ascending)
- No duplicates
- Metadata en attrs

Copyright (c) 2026 M&C. All rights reserved.
"""

import pandas as pd
from typing import Optional


class DataNormalizer:
    """
    Normalizador de datos de mercado
    
    Convierte datos de cualquier provider al formato estándar de Atlas:
    
    Formato Atlas:
    - Index: DatetimeIndex (timezone UTC)
    - Columns: ['Open', 'High', 'Low', 'Close', 'Volume']
    - Sorted: ascending by date
    - Clean: no duplicates, no NaN in critical columns
    - Metadata: symbol, provider, normalized flag
    
    Example:
        >>> from atlas.data_layer.normalization import DataNormalizer
        >>> data_normalized = DataNormalizer.to_atlas_format(data, provider="yahoo")
    """
    
    # Columnas estándar de Atlas (OHLCV)
    STANDARD_COLUMNS = ['Open', 'High', 'Low', 'Close', 'Volume']
    
    @staticmethod
    def to_atlas_format(data: pd.DataFrame, provider: str = "unknown") -> pd.DataFrame:
        """
        Convertir a formato estándar de Atlas
        
        Args:
            data: DataFrame raw del provider
            provider: Nombre del provider ("yahoo", "alpaca", etc.)
        
        Returns:
            pd.DataFrame normalizado
        
        Normalizaciones aplicadas:
        1. Index → DatetimeIndex (UTC)
        2. Columns → Capitalized standard names
        3. Sort → Ascending by date
        4. Duplicates → Removed
        5. Timezone → UTC
        """
        df = data.copy()
        
        # 1. Normalizar index a DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        
        # 2. Convertir timezone a UTC
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
        
        # 3. Ordenar por fecha (ascending)
        df = df.sort_index()
        
        # 4. Remover duplicados
        df = df[~df.index.duplicated(keep='first')]
        
        # 5. Normalizar nombres de columnas (case-insensitive)
        column_mapping = {
            col.lower(): col.capitalize()
            for col in ['open', 'high', 'low', 'close', 'volume']
        }
        
        df.columns = [
            column_mapping.get(col.lower(), col)
            for col in df.columns
        ]
        
        # 6. Asegurar que tenemos columnas estándar
        for col in DataNormalizer.STANDARD_COLUMNS:
            if col not in df.columns:
                # Si falta una columna crítica, llenar con NaN
                df[col] = pd.NA
        
        # 7. Ordenar columnas (OHLCV)
        df = df[DataNormalizer.STANDARD_COLUMNS]
        
        return df
    
    @staticmethod
    def add_metadata(data: pd.DataFrame, symbol: str, provider: str) -> pd.DataFrame:
        """
        Agregar metadata al DataFrame
        
        Metadata se guarda en DataFrame.attrs (diccionario especial de pandas)
        
        Args:
            data: DataFrame normalizado
            symbol: Ticker symbol
            provider: Nombre del provider
        
        Returns:
            pd.DataFrame con metadata
        
        Example:
            >>> df = DataNormalizer.add_metadata(df, "AAPL", "yahoo")
            >>> print(df.attrs)
            {'symbol': 'AAPL', 'provider': 'yahoo', 'normalized': True}
        """
        df = data.copy()
        
        df.attrs['symbol'] = symbol
        df.attrs['provider'] = provider
        df.attrs['normalized'] = True
        df.attrs['format'] = 'Atlas Standard (OHLCV)'
        
        return df
    
    @staticmethod
    def validate_format(data: pd.DataFrame, strict: bool = False) -> bool:
        """
        Validar que el DataFrame cumple con formato Atlas
        
        Args:
            data: DataFrame a validar
            strict: Si True, requiere metadata completa
        
        Returns:
            bool: True si cumple formato Atlas
        
        Validaciones:
        - Index es DatetimeIndex
        - Timezone es UTC
        - Tiene columnas OHLCV
        - Está ordenado por fecha
        - (strict) Tiene metadata completa
        """
        # Check 1: DatetimeIndex
        if not isinstance(data.index, pd.DatetimeIndex):
            return False
        
        # Check 2: UTC timezone
        if data.index.tz is None or str(data.index.tz) != 'UTC':
            return False
        
        # Check 3: Columnas OHLCV
        for col in DataNormalizer.STANDARD_COLUMNS:
            if col not in data.columns:
                return False
        
        # Check 4: Ordenado por fecha
        if not data.index.is_monotonic_increasing:
            return False
        
        # Check 5 (strict): Metadata
        if strict:
            required_attrs = ['symbol', 'provider', 'normalized']
            for attr in required_attrs:
                if attr not in data.attrs:
                    return False
        
        return True
    
    @staticmethod
    def clean_data(data: pd.DataFrame, 
                   drop_na: bool = True,
                   fill_method: Optional[str] = None) -> pd.DataFrame:
        """
        Limpiar datos (NaN, outliers, etc.)
        
        Args:
            data: DataFrame a limpiar
            drop_na: Si True, elimina filas con NaN
            fill_method: Método para rellenar NaN
                        'ffill' = forward fill
                        'bfill' = backward fill
                        'mean' = fill with mean
        
        Returns:
            pd.DataFrame limpio
        """
        df = data.copy()
        
        # Opción 1: Eliminar NaN
        if drop_na:
            df = df.dropna()
        
        # Opción 2: Rellenar NaN
        elif fill_method:
            if fill_method in ['ffill', 'bfill']:
                df = df.fillna(method=fill_method)
            elif fill_method == 'mean':
                df = df.fillna(df.mean())
        
        return df
