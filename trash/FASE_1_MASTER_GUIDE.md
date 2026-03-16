# 📊 FASE 1: DATA LAYER - MASTER GUIDE COMPLETO

**Fecha:** 2026-02-04  
**Objetivo:** Implementar capa de datos completa para Atlas  
**Tiempo estimado:** 1-2 semanas  
**Archivos a crear:** 15 archivos Python

---

## 🎯 QUÉ VAMOS A LOGRAR

Al terminar FASE 1, esto funcionará:

```python
from atlas.data_layer import get_data

# Descargar datos
data = get_data("AAPL", start="2024-01-01", end="2024-12-31")

print(data.head())
# Output:
#              Open    High     Low   Close    Volume
# 2024-01-02  185.28  186.36  184.35  185.64  45023100
# 2024-01-03  184.22  185.88  183.43  184.25  58840400
# ...
```

**Capacidades:**
- ✅ Descargar datos históricos (Yahoo Finance - GRATIS)
- ✅ Validar calidad de datos (gaps, spikes, missing data)
- ✅ Normalizar formatos (diferentes providers → formato único)
- ✅ Cache inteligente (evitar redescargas)
- ✅ Soporte multi-asset (acciones, crypto, forex, futuros)

---

## 📁 ESTRUCTURA COMPLETA DE ARCHIVOS

```
Atlas/python/src/atlas/data_layer/
│
├── __init__.py                    # API pública (get_data)
├── base.py                        # Clase base DataProvider
│
├── sources/                       # Proveedores de datos
│   ├── __init__.py
│   ├── yahoo.py                   # Yahoo Finance (PRINCIPAL)
│   ├── alpaca.py                  # Alpaca Markets (futuro)
│   └── polygon.py                 # Polygon.io (futuro)
│
├── quality/                       # Validación de calidad
│   ├── __init__.py
│   └── validator.py               # Data quality checks
│
├── normalization/                 # Normalización
│   ├── __init__.py
│   └── normalizer.py              # Format standardization
│
└── cache/                         # Sistema de cache
    ├── __init__.py
    └── cache_manager.py           # Cache de datos

Total: 15 archivos
```

---

## 📝 ARCHIVOS INDIVIDUALES (CON CÓDIGO COMPLETO)

### **ARCHIVO 1: data_layer/__init__.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/__init__.py`

**Propósito:** API pública simplificada

**Código:**

```python
"""
Atlas Data Layer

Capa de ingesta, validación y normalización de datos de mercado.

Copyright (c) 2026 M&C. All rights reserved.
"""

__version__ = "1.0.0"

from .sources.yahoo import YahooProvider
from .quality.validator import DataValidator
from .normalization.normalizer import DataNormalizer
from .cache.cache_manager import CacheManager

__all__ = [
    'get_data',
    'YahooProvider',
    'DataValidator',
    'DataNormalizer',
    'CacheManager'
]


def get_data(symbol, start, end, provider="yahoo", use_cache=True):
    """
    API principal para obtener datos de mercado
    
    Args:
        symbol (str): Ticker symbol (ej: "AAPL", "BTC-USD")
        start (str): Fecha inicio ("2024-01-01")
        end (str): Fecha fin ("2024-12-31")
        provider (str): Proveedor de datos ("yahoo", "alpaca", "polygon")
        use_cache (bool): Usar cache si está disponible
    
    Returns:
        pd.DataFrame: DataFrame con OHLCV normalizado
    
    Example:
        >>> from atlas.data_layer import get_data
        >>> data = get_data("AAPL", "2024-01-01", "2024-12-31")
        >>> print(data.head())
    
    Raises:
        ValueError: Si el provider no está soportado
        Exception: Si hay errores en descarga o validación
    """
    cache = CacheManager()
    
    # Verificar cache
    if use_cache and cache.exists(symbol, start, end, provider):
        print(f"📦 Loading {symbol} from cache...")
        return cache.load(symbol, start, end, provider)
    
    # Descargar datos según provider
    if provider == "yahoo":
        yahoo = YahooProvider()
        data = yahoo.download(symbol, start, end)
    elif provider == "alpaca":
        raise NotImplementedError("Alpaca provider coming soon")
    elif provider == "polygon":
        raise NotImplementedError("Polygon provider coming soon")
    else:
        raise ValueError(f"Provider '{provider}' no soportado. Use: yahoo, alpaca, polygon")
    
    # Validar calidad
    validation = DataValidator.validate_all(data)
    if validation['missing_data']['exceeds_threshold']:
        print("⚠️  Warning: Data quality issues detected")
        print(f"   Missing data: {validation['missing_data']['missing_pct']:.1f}%")
    
    # Normalizar formato
    data = DataNormalizer.to_atlas_format(data, provider)
    data = DataNormalizer.add_metadata(data, symbol, provider)
    
    # Guardar en cache
    if use_cache:
        cache.save(data, symbol, start, end, provider)
    
    return data
```

---

### **ARCHIVO 2: data_layer/base.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/base.py`

**Propósito:** Clase base abstracta para todos los providers

**Código:**

```python
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
```

---

### **ARCHIVO 3: data_layer/sources/__init__.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/sources/__init__.py`

**Propósito:** Exports de providers

**Código:**

```python
"""
Data sources (providers)

Copyright (c) 2026 M&C. All rights reserved.
"""

from .yahoo import YahooProvider

# Uncomment when implemented:
# from .alpaca import AlpacaProvider
# from .polygon import PolygonProvider

__all__ = [
    'YahooProvider',
    # 'AlpacaProvider',
    # 'PolygonProvider'
]
```

---

### **ARCHIVO 4: data_layer/sources/yahoo.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/sources/yahoo.py`

**Propósito:** Yahoo Finance provider (el MÁS IMPORTANTE - GRATIS)

**Código:**

```python
"""
Yahoo Finance Data Provider

Provider gratuito para datos históricos de mercado.

Soporta:
- Acciones (AAPL, GOOGL, etc.)
- Crypto (BTC-USD, ETH-USD)
- Forex (EURUSD=X)
- Índices (^GSPC, ^DJI)
- Futuros (GC=F, CL=F)

Copyright (c) 2026 M&C. All rights reserved.
"""

import yfinance as yf
import pandas as pd
from typing import Optional
from ..base import DataProvider
from ..quality.validator import DataValidator
from ..normalization.normalizer import DataNormalizer


class YahooProvider(DataProvider):
    """
    Yahoo Finance data provider
    
    Ventajas:
    - ✅ 100% GRATIS
    - ✅ No requiere API key
    - ✅ Datos históricos ilimitados
    - ✅ Multi-asset (stocks, crypto, forex, etc.)
    
    Limitaciones:
    - ⚠️  No real-time tick data
    - ⚠️  No order book / Level 2
    - ⚠️  Rate limits no documentados
    
    Example:
        >>> yahoo = YahooProvider()
        >>> data = yahoo.download("AAPL", "2024-01-01", "2024-12-31")
        >>> print(data.head())
    """
    
    version = "1.0.0"
    supported_assets = ["stocks", "crypto", "forex", "indices", "futures"]
    rate_limit = "No oficial (usar con moderación)"
    
    def download(self, symbol: str, start: str, end: str, 
                 interval: str = "1d") -> pd.DataFrame:
        """
        Descargar datos históricos de Yahoo Finance
        
        Args:
            symbol: Ticker symbol
                   Stocks: "AAPL", "GOOGL"
                   Crypto: "BTC-USD", "ETH-USD"
                   Forex: "EURUSD=X"
                   Indices: "^GSPC", "^DJI"
                   Futures: "GC=F", "CL=F"
            start: Fecha inicio (YYYY-MM-DD)
            end: Fecha fin (YYYY-MM-DD)
            interval: Timeframe
                     Valid: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        
        Returns:
            pd.DataFrame con columnas: Open, High, Low, Close, Volume
        
        Raises:
            ValueError: Si el símbolo es inválido
            Exception: Si hay errores de red o API
        """
        try:
            # Descargar con yfinance
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start, end=end, interval=interval)
            
            # Verificar que hay datos
            if data.empty:
                raise ValueError(f"No data found for {symbol} between {start} and {end}")
            
            # Remover columnas innecesarias
            columns_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
            data = data[columns_to_keep]
            
            # Limpiar index (remover timezone info si existe)
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            
            return data
        
        except Exception as e:
            raise Exception(f"Error downloading {symbol} from Yahoo Finance: {str(e)}")
    
    def validate(self, data: pd.DataFrame) -> dict:
        """
        Validar calidad de datos
        
        Delega a DataValidator para consistencia
        """
        return DataValidator.validate_all(data)
    
    def normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Normalizar formato
        
        Delega a DataNormalizer para consistencia
        """
        return DataNormalizer.to_atlas_format(data, provider="yahoo")
    
    def get_current_price(self, symbol: str) -> float:
        """
        Obtener precio actual (último cierre)
        
        Args:
            symbol: Ticker symbol
        
        Returns:
            float: Último precio de cierre
        
        Example:
            >>> yahoo = YahooProvider()
            >>> price = yahoo.get_current_price("AAPL")
            >>> print(f"AAPL: ${price:.2f}")
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Intentar varios campos (depende del tipo de asset)
            price = (
                info.get('currentPrice') or
                info.get('regularMarketPrice') or
                info.get('previousClose')
            )
            
            if price is None:
                raise ValueError(f"Could not get price for {symbol}")
            
            return float(price)
        
        except Exception as e:
            raise Exception(f"Error getting current price for {symbol}: {str(e)}")
    
    def get_info(self) -> dict:
        """Información del provider"""
        return {
            'name': 'Yahoo Finance',
            'version': self.version,
            'supported_assets': self.supported_assets,
            'rate_limit': self.rate_limit,
            'api_key_required': False,
            'cost': 'FREE',
            'data_quality': 'Good for EOD, acceptable for intraday'
        }


# ==================== TESTS ====================

if __name__ == "__main__":
    """
    Tests rápidos del Yahoo Provider
    
    Run:
        cd Atlas/python/src/atlas/data_layer/sources
        python yahoo.py
    """
    
    print("=" * 60)
    print("🧪 TESTING YAHOO FINANCE PROVIDER")
    print("=" * 60)
    
    yahoo = YahooProvider()
    
    # Test 1: Descargar AAPL
    print("\n[Test 1] Downloading AAPL (2024)...")
    try:
        data = yahoo.download("AAPL", "2024-01-01", "2024-12-31")
        print(f"✅ Success! Downloaded {len(data)} rows")
        print(data.head())
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 2: Descargar BTC-USD
    print("\n[Test 2] Downloading BTC-USD (last 30 days)...")
    try:
        data = yahoo.download("BTC-USD", "2024-12-01", "2024-12-31")
        print(f"✅ Success! Downloaded {len(data)} rows")
        print(data.tail())
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 3: Símbolo inválido
    print("\n[Test 3] Invalid symbol (INVALID123)...")
    try:
        data = yahoo.download("INVALID123", "2024-01-01", "2024-12-31")
        print(f"❌ Should have failed but didn't")
    except Exception as e:
        print(f"✅ Correctly failed: {e}")
    
    # Test 4: Current price
    print("\n[Test 4] Getting current price for AAPL...")
    try:
        price = yahoo.get_current_price("AAPL")
        print(f"✅ AAPL current price: ${price:.2f}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 5: Provider info
    print("\n[Test 5] Provider info...")
    info = yahoo.get_info()
    print("✅ Provider info:")
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 60)
```

---

### **ARCHIVO 5: data_layer/quality/__init__.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/quality/__init__.py`

**Propósito:** Exports de validación

**Código:**

```python
"""
Data quality validation

Copyright (c) 2026 M&C. All rights reserved.
"""

from .validator import DataValidator

__all__ = ['DataValidator']
```

---

### **ARCHIVO 6: data_layer/quality/validator.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/quality/validator.py`

**Propósito:** Validación de calidad de datos

**Código:**

```python
"""
Data Quality Validator

Valida calidad de datos de mercado antes de usarlos.

Checks:
- Missing data (NaN values)
- Price spikes (volatility anormal)
- Gaps (fechas faltantes)
- Volume anomalies
- Data consistency

Copyright (c) 2026 M&C. All rights reserved.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any


class DataValidator:
    """
    Validador de calidad de datos
    
    Detecta problemas comunes en datos de mercado:
    - Datos faltantes (NaN)
    - Spikes de precio (>10% en 1 día)
    - Gaps de fecha (días faltantes)
    - Volumen = 0 (sospechoso)
    
    Example:
        >>> from atlas.data_layer.quality import DataValidator
        >>> validation = DataValidator.validate_all(data)
        >>> if validation['overall_quality'] == 'PASS':
        >>>     print("✅ Data quality OK")
    """
    
    # Thresholds de calidad
    MAX_MISSING_PCT = 5.0  # Máximo 5% de datos faltantes
    MAX_PRICE_SPIKE_PCT = 50.0  # Spike >50% es sospechoso
    MIN_VOLUME_THRESHOLD = 1000  # Volumen mínimo esperado
    
    @staticmethod
    def check_missing_data(data: pd.DataFrame, threshold: float = MAX_MISSING_PCT) -> Dict[str, Any]:
        """
        Detectar datos faltantes (NaN)
        
        Args:
            data: DataFrame con OHLCV
            threshold: % máximo de datos faltantes aceptable
        
        Returns:
            dict con resultados:
                - missing_count: int
                - missing_pct: float
                - exceeds_threshold: bool
                - affected_columns: list
        """
        total_cells = data.shape[0] * data.shape[1]
        missing_count = data.isna().sum().sum()
        missing_pct = (missing_count / total_cells) * 100
        
        # Columnas afectadas
        affected = data.columns[data.isna().any()].tolist()
        
        return {
            'missing_count': int(missing_count),
            'missing_pct': float(missing_pct),
            'exceeds_threshold': missing_pct > threshold,
            'affected_columns': affected,
            'threshold': threshold
        }
    
    @staticmethod
    def check_price_spikes(data: pd.DataFrame, threshold: float = MAX_PRICE_SPIKE_PCT) -> Dict[str, Any]:
        """
        Detectar spikes anormales de precio
        
        Un spike es un cambio >threshold% en 1 día sin justificación
        
        Args:
            data: DataFrame con OHLCV
            threshold: % de cambio que se considera spike
        
        Returns:
            dict con resultados:
                - spike_count: int
                - spike_dates: list
                - max_spike_pct: float
        """
        if 'Close' not in data.columns:
            return {
                'spike_count': 0,
                'spike_dates': [],
                'max_spike_pct': 0.0,
                'threshold': threshold
            }
        
        # Calcular % de cambio diario
        pct_change = data['Close'].pct_change() * 100
        
        # Detectar spikes (cambios >threshold%)
        spikes = np.abs(pct_change) > threshold
        spike_count = spikes.sum()
        spike_dates = data.index[spikes].tolist() if spike_count > 0 else []
        max_spike = pct_change.abs().max() if not pct_change.empty else 0.0
        
        return {
            'spike_count': int(spike_count),
            'spike_dates': spike_dates,
            'max_spike_pct': float(max_spike),
            'threshold': threshold
        }
    
    @staticmethod
    def check_gaps(data: pd.DataFrame, expected_freq: str = 'B') -> Dict[str, Any]:
        """
        Detectar gaps (fechas faltantes)
        
        Args:
            data: DataFrame con DatetimeIndex
            expected_freq: Frecuencia esperada
                          'B' = Business days (lun-vie)
                          'D' = Daily
                          'H' = Hourly
        
        Returns:
            dict con resultados:
                - gap_count: int
                - gap_dates: list
        """
        if not isinstance(data.index, pd.DatetimeIndex):
            return {
                'gap_count': 0,
                'gap_dates': [],
                'expected_freq': expected_freq
            }
        
        # Generar rango de fechas esperado
        expected_dates = pd.date_range(
            start=data.index.min(),
            end=data.index.max(),
            freq=expected_freq
        )
        
        # Detectar fechas faltantes
        missing_dates = expected_dates.difference(data.index)
        
        return {
            'gap_count': len(missing_dates),
            'gap_dates': missing_dates.tolist(),
            'expected_freq': expected_freq
        }
    
    @staticmethod
    def check_volume_anomalies(data: pd.DataFrame, 
                               threshold: int = MIN_VOLUME_THRESHOLD) -> Dict[str, Any]:
        """
        Detectar anomalías de volumen
        
        Volumen = 0 o muy bajo es sospechoso
        
        Args:
            data: DataFrame con columna Volume
            threshold: Volumen mínimo esperado
        
        Returns:
            dict con resultados:
                - zero_volume_count: int
                - low_volume_count: int
                - affected_dates: list
        """
        if 'Volume' not in data.columns:
            return {
                'zero_volume_count': 0,
                'low_volume_count': 0,
                'affected_dates': []
            }
        
        # Detectar volumen = 0
        zero_volume = data['Volume'] == 0
        zero_count = zero_volume.sum()
        
        # Detectar volumen bajo
        low_volume = (data['Volume'] > 0) & (data['Volume'] < threshold)
        low_count = low_volume.sum()
        
        # Fechas afectadas
        affected = data.index[zero_volume | low_volume].tolist()
        
        return {
            'zero_volume_count': int(zero_count),
            'low_volume_count': int(low_count),
            'affected_dates': affected,
            'threshold': threshold
        }
    
    @staticmethod
    def validate_all(data: pd.DataFrame) -> Dict[str, Any]:
        """
        Ejecutar TODAS las validaciones
        
        Args:
            data: DataFrame con OHLCV
        
        Returns:
            dict con todos los resultados + overall_quality
        
        Example:
            >>> validation = DataValidator.validate_all(data)
            >>> print(validation['overall_quality'])
            'PASS'
        """
        results = {
            'missing_data': DataValidator.check_missing_data(data),
            'price_spikes': DataValidator.check_price_spikes(data),
            'gaps': DataValidator.check_gaps(data),
            'volume_anomalies': DataValidator.check_volume_anomalies(data)
        }
        
        # Determinar calidad general
        issues = []
        
        if results['missing_data']['exceeds_threshold']:
            issues.append('missing_data')
        
        if results['price_spikes']['spike_count'] > 5:
            issues.append('price_spikes')
        
        if results['gaps']['gap_count'] > 10:
            issues.append('gaps')
        
        if results['volume_anomalies']['zero_volume_count'] > 5:
            issues.append('volume_anomalies')
        
        # Overall quality
        if len(issues) == 0:
            overall = 'PASS'
        elif len(issues) <= 2:
            overall = 'WARNING'
        else:
            overall = 'FAIL'
        
        results['overall_quality'] = overall
        results['issues'] = issues
        
        return results
```

---

### **ARCHIVO 7: data_layer/normalization/__init__.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/normalization/__init__.py`

**Propósito:** Exports de normalización

**Código:**

```python
"""
Data normalization

Copyright (c) 2026 M&C. All rights reserved.
"""

from .normalizer import DataNormalizer

__all__ = ['DataNormalizer']
```

---

### **ARCHIVO 8: data_layer/normalization/normalizer.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/normalization/normalizer.py`

**Propósito:** Normalizar datos a formato único Atlas

**Código:**

```python
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
```

---

### **ARCHIVO 9: data_layer/cache/__init__.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/cache/__init__.py`

**Propósito:** Exports de cache

**Código:**

```python
"""
Data cache system

Copyright (c) 2026 M&C. All rights reserved.
"""

from .cache_manager import CacheManager

__all__ = ['CacheManager']
```

---

### **ARCHIVO 10: data_layer/cache/cache_manager.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/cache/cache_manager.py`

**Propósito:** Sistema de cache para evitar redescargas

**Código:**

```python
"""
Cache Manager

Sistema de cache en disco para datos de mercado.
Evita redescargar datos que ya tenemos.

Estructura:
Atlas/data/cache/
├── yahoo/
│   ├── AAPL_2024-01-01_2024-12-31_1d.parquet
│   └── BTC-USD_2024-01-01_2024-12-31_1d.parquet
├── alpaca/
└── polygon/

Copyright (c) 2026 M&C. All rights reserved.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import hashlib


class CacheManager:
    """
    Gestor de cache de datos
    
    Guarda datos descargados en disco (formato Parquet) para:
    - ✅ Evitar redescargas
    - ✅ Reducir latencia (100x más rápido)
    - ✅ Reducir calls a APIs (rate limits)
    - ✅ Trabajar offline
    
    Example:
        >>> from atlas.data_layer.cache import CacheManager
        >>> cache = CacheManager()
        >>> 
        >>> # Guardar
        >>> cache.save(data, "AAPL", "2024-01-01", "2024-12-31", "yahoo")
        >>> 
        >>> # Cargar
        >>> if cache.exists("AAPL", "2024-01-01", "2024-12-31", "yahoo"):
        >>>     data = cache.load("AAPL", "2024-01-01", "2024-12-31", "yahoo")
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Inicializar cache manager
        
        Args:
            cache_dir: Directorio base de cache
                      Default: Atlas/data/cache/
        """
        if cache_dir is None:
            # Default: Atlas/data/cache/
            self.cache_dir = Path(__file__).parents[4] / "data" / "cache"
        else:
            self.cache_dir = Path(cache_dir)
        
        # Crear directorio si no existe
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, symbol: str, start: str, end: str, 
                       provider: str, interval: str = "1d") -> Path:
        """
        Generar path del archivo de cache
        
        Formato: cache/{provider}/{symbol}_{start}_{end}_{interval}.parquet
        
        Args:
            symbol: Ticker symbol
            start: Fecha inicio
            end: Fecha fin
            provider: Nombre del provider
            interval: Timeframe
        
        Returns:
            Path del archivo de cache
        """
        # Crear subdirectorio del provider
        provider_dir = self.cache_dir / provider
        provider_dir.mkdir(exist_ok=True)
        
        # Nombre del archivo
        # Ejemplo: AAPL_2024-01-01_2024-12-31_1d.parquet
        filename = f"{symbol}_{start}_{end}_{interval}.parquet"
        
        return provider_dir / filename
    
    def exists(self, symbol: str, start: str, end: str, 
              provider: str, interval: str = "1d") -> bool:
        """
        Verificar si los datos están en cache
        
        Args:
            symbol: Ticker symbol
            start: Fecha inicio
            end: Fecha fin
            provider: Nombre del provider
            interval: Timeframe
        
        Returns:
            bool: True si existe en cache
        """
        cache_path = self._get_cache_path(symbol, start, end, provider, interval)
        return cache_path.exists()
    
    def save(self, data: pd.DataFrame, symbol: str, start: str, end: str,
            provider: str, interval: str = "1d") -> Path:
        """
        Guardar datos en cache
        
        Args:
            data: DataFrame con OHLCV
            symbol: Ticker symbol
            start: Fecha inicio
            end: Fecha fin
            provider: Nombre del provider
            interval: Timeframe
        
        Returns:
            Path del archivo guardado
        
        Note:
            Usa formato Parquet (10x más rápido que CSV, 3x más compacto)
        """
        cache_path = self._get_cache_path(symbol, start, end, provider, interval)
        
        # Guardar en formato Parquet (rápido y compacto)
        data.to_parquet(cache_path, compression='snappy')
        
        return cache_path
    
    def load(self, symbol: str, start: str, end: str,
            provider: str, interval: str = "1d") -> pd.DataFrame:
        """
        Cargar datos desde cache
        
        Args:
            symbol: Ticker symbol
            start: Fecha inicio
            end: Fecha fin
            provider: Nombre del provider
            interval: Timeframe
        
        Returns:
            pd.DataFrame con OHLCV
        
        Raises:
            FileNotFoundError: Si no existe en cache
        """
        cache_path = self._get_cache_path(symbol, start, end, provider, interval)
        
        if not cache_path.exists():
            raise FileNotFoundError(f"Cache not found: {cache_path}")
        
        # Cargar desde Parquet
        data = pd.read_parquet(cache_path)
        
        return data
    
    def clear(self, provider: Optional[str] = None) -> int:
        """
        Limpiar cache
        
        Args:
            provider: Si se especifica, solo limpia ese provider
                     Si None, limpia TODO el cache
        
        Returns:
            int: Número de archivos eliminados
        """
        count = 0
        
        if provider:
            # Limpiar solo un provider
            provider_dir = self.cache_dir / provider
            if provider_dir.exists():
                for file in provider_dir.glob("*.parquet"):
                    file.unlink()
                    count += 1
        else:
            # Limpiar TODO
            for file in self.cache_dir.rglob("*.parquet"):
                file.unlink()
                count += 1
        
        return count
    
    def get_stats(self) -> dict:
        """
        Obtener estadísticas del cache
        
        Returns:
            dict con estadísticas:
                - total_files: int
                - total_size_mb: float
                - providers: dict
        """
        total_files = 0
        total_size = 0
        providers = {}
        
        for provider_dir in self.cache_dir.iterdir():
            if provider_dir.is_dir():
                files = list(provider_dir.glob("*.parquet"))
                file_count = len(files)
                size = sum(f.stat().st_size for f in files)
                
                providers[provider_dir.name] = {
                    'files': file_count,
                    'size_mb': size / (1024 * 1024)
                }
                
                total_files += file_count
                total_size += size
        
        return {
            'total_files': total_files,
            'total_size_mb': total_size / (1024 * 1024),
            'providers': providers
        }
```

---

## 📚 ARCHIVOS ADICIONALES (STUBS PARA EL FUTURO)

### **ARCHIVO 11: data_layer/sources/alpaca.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/sources/alpaca.py`

**Propósito:** Alpaca Markets provider (FUTURO)

**Código (STUB):**

```python
"""
Alpaca Markets Data Provider

Provider para trading real y datos real-time.

Requiere:
- API Key de Alpaca
- Cuenta en Alpaca Markets

STATUS: 🚧 COMING SOON

Copyright (c) 2026 M&C. All rights reserved.
"""

from ..base import DataProvider
import pandas as pd


class AlpacaProvider(DataProvider):
    """
    Alpaca Markets data provider
    
    🚧 COMING SOON
    
    Features planeados:
    - Real-time data streaming
    - Order book Level 2
    - Trade execution
    - Paper trading
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        """
        Initialize Alpaca provider
        
        Args:
            api_key: Alpaca API key
            api_secret: Alpaca API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        
        if not api_key:
            raise ValueError("Alpaca API key required. Get it from: alpaca.markets")
    
    def download(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        """Download historical data"""
        raise NotImplementedError("Alpaca provider coming soon. Use 'yahoo' for now.")
    
    def validate(self, data: pd.DataFrame) -> dict:
        """Validate data quality"""
        raise NotImplementedError("Alpaca provider coming soon.")
    
    def normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize data format"""
        raise NotImplementedError("Alpaca provider coming soon.")
```

---

### **ARCHIVO 12: data_layer/sources/polygon.py**

**Ubicación:** `Atlas/python/src/atlas/data_layer/sources/polygon.py`

**Propósito:** Polygon.io provider (FUTURO)

**Código (STUB):**

```python
"""
Polygon.io Data Provider

Provider profesional para datos de alta calidad.

Requiere:
- API Key de Polygon
- Subscription (paid)

STATUS: 🚧 COMING SOON

Copyright (c) 2026 M&C. All rights reserved.
"""

from ..base import DataProvider
import pandas as pd


class PolygonProvider(DataProvider):
    """
    Polygon.io data provider
    
    🚧 COMING SOON
    
    Features planeados:
    - Level 2 market data
    - Tick-by-tick data
    - Options data
    - Real-time quotes
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize Polygon provider
        
        Args:
            api_key: Polygon API key
        """
        self.api_key = api_key
        
        if not api_key:
            raise ValueError("Polygon API key required. Get it from: polygon.io")
    
    def download(self, symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        """Download historical data"""
        raise NotImplementedError("Polygon provider coming soon. Use 'yahoo' for now.")
    
    def validate(self, data: pd.DataFrame) -> dict:
        """Validate data quality"""
        raise NotImplementedError("Polygon provider coming soon.")
    
    def normalize(self, data: pd.DataFrame) -> pd.DataFrame:
        """Normalize data format"""
        raise NotImplementedError("Polygon provider coming soon.")
```

---

## 🧪 TESTING

### **ARCHIVO 13: tests/test_data_layer.py**

**Ubicación:** `Atlas/python/tests/test_data_layer.py`

**Propósito:** Tests completos del Data Layer

**Código:**

```python
"""
Tests para Data Layer

Run:
    cd Atlas/python
    python -m pytest tests/test_data_layer.py -v

Copyright (c) 2026 M&C. All rights reserved.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Imports del data layer
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from atlas.data_layer import get_data
from atlas.data_layer.sources.yahoo import YahooProvider
from atlas.data_layer.quality.validator import DataValidator
from atlas.data_layer.normalization.normalizer import DataNormalizer
from atlas.data_layer.cache.cache_manager import CacheManager


class TestYahooProvider:
    """Tests para Yahoo Finance provider"""
    
    def test_download_stock(self):
        """Test: Descargar datos de acción (AAPL)"""
        yahoo = YahooProvider()
        data = yahoo.download("AAPL", "2024-01-01", "2024-01-31")
        
        assert not data.empty
        assert 'Close' in data.columns
        assert len(data) > 0
    
    def test_download_crypto(self):
        """Test: Descargar datos de crypto (BTC-USD)"""
        yahoo = YahooProvider()
        data = yahoo.download("BTC-USD", "2024-01-01", "2024-01-31")
        
        assert not data.empty
        assert 'Close' in data.columns
    
    def test_invalid_symbol(self):
        """Test: Símbolo inválido debe fallar"""
        yahoo = YahooProvider()
        
        with pytest.raises(Exception):
            yahoo.download("INVALID123", "2024-01-01", "2024-01-31")
    
    def test_current_price(self):
        """Test: Obtener precio actual"""
        yahoo = YahooProvider()
        price = yahoo.get_current_price("AAPL")
        
        assert isinstance(price, float)
        assert price > 0


class TestDataValidator:
    """Tests para Data Validator"""
    
    def test_validate_clean_data(self):
        """Test: Validar datos limpios"""
        # Crear datos de prueba limpios
        dates = pd.date_range("2024-01-01", periods=100, freq='D')
        data = pd.DataFrame({
            'Open': range(100, 200),
            'High': range(101, 201),
            'Low': range(99, 199),
            'Close': range(100, 200),
            'Volume': [1000000] * 100
        }, index=dates)
        
        validation = DataValidator.validate_all(data)
        
        assert validation['overall_quality'] == 'PASS'
        assert not validation['missing_data']['exceeds_threshold']
    
    def test_detect_missing_data(self):
        """Test: Detectar datos faltantes"""
        dates = pd.date_range("2024-01-01", periods=100, freq='D')
        data = pd.DataFrame({
            'Open': [None] * 50 + list(range(100, 150)),
            'Close': range(100, 200)
        }, index=dates)
        
        result = DataValidator.check_missing_data(data)
        
        assert result['missing_count'] > 0
        assert result['exceeds_threshold']


class TestDataNormalizer:
    """Tests para Data Normalizer"""
    
    def test_normalize_format(self):
        """Test: Normalizar a formato Atlas"""
        # Datos con formato diferente
        dates = pd.date_range("2024-01-01", periods=10, freq='D')
        data = pd.DataFrame({
            'open': range(100, 110),
            'high': range(101, 111),
            'low': range(99, 109),
            'close': range(100, 110),
            'volume': [1000] * 10
        }, index=dates)
        
        normalized = DataNormalizer.to_atlas_format(data, "test")
        
        # Verificar columnas capitalizadas
        assert 'Open' in normalized.columns
        assert 'Close' in normalized.columns
        assert 'open' not in normalized.columns
        
        # Verificar timezone UTC
        assert str(normalized.index.tz) == 'UTC'
    
    def test_add_metadata(self):
        """Test: Agregar metadata"""
        data = pd.DataFrame({'Close': [100]})
        data_with_meta = DataNormalizer.add_metadata(data, "AAPL", "yahoo")
        
        assert data_with_meta.attrs['symbol'] == 'AAPL'
        assert data_with_meta.attrs['provider'] == 'yahoo'
        assert data_with_meta.attrs['normalized'] == True


class TestCacheManager:
    """Tests para Cache Manager"""
    
    def setup_method(self):
        """Setup antes de cada test"""
        # Usar directorio temporal para tests
        self.cache_dir = Path("./test_cache")
        self.cache = CacheManager(cache_dir=self.cache_dir)
    
    def teardown_method(self):
        """Cleanup después de cada test"""
        # Limpiar cache de prueba
        self.cache.clear()
        if self.cache_dir.exists():
            self.cache_dir.rmdir()
    
    def test_save_and_load(self):
        """Test: Guardar y cargar desde cache"""
        # Crear datos de prueba
        dates = pd.date_range("2024-01-01", periods=10, freq='D')
        data = pd.DataFrame({
            'Open': range(100, 110),
            'Close': range(100, 110),
            'Volume': [1000] * 10
        }, index=dates)
        
        # Guardar en cache
        self.cache.save(data, "TEST", "2024-01-01", "2024-01-10", "test")
        
        # Verificar que existe
        assert self.cache.exists("TEST", "2024-01-01", "2024-01-10", "test")
        
        # Cargar desde cache
        cached_data = self.cache.load("TEST", "2024-01-01", "2024-01-10", "test")
        
        # Verificar que es igual
        pd.testing.assert_frame_equal(data, cached_data)
    
    def test_cache_stats(self):
        """Test: Estadísticas de cache"""
        # Crear y guardar datos
        dates = pd.date_range("2024-01-01", periods=10, freq='D')
        data = pd.DataFrame({'Close': range(10)}, index=dates)
        
        self.cache.save(data, "TEST1", "2024-01-01", "2024-01-10", "test")
        self.cache.save(data, "TEST2", "2024-01-01", "2024-01-10", "test")
        
        stats = self.cache.get_stats()
        
        assert stats['total_files'] == 2
        assert 'test' in stats['providers']


class TestGetDataAPI:
    """Tests para la API principal get_data()"""
    
    def test_get_data_basic(self):
        """Test: Uso básico de get_data()"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31", use_cache=False)
        
        assert not data.empty
        assert 'Close' in data.columns
        assert data.attrs['symbol'] == 'AAPL'
        assert data.attrs['provider'] == 'yahoo'
        assert data.attrs['normalized'] == True
    
    def test_get_data_with_cache(self):
        """Test: get_data() con cache"""
        # Primera llamada (descarga)
        data1 = get_data("AAPL", "2024-01-01", "2024-01-10", use_cache=True)
        
        # Segunda llamada (desde cache - debería ser más rápido)
        data2 = get_data("AAPL", "2024-01-01", "2024-01-10", use_cache=True)
        
        # Verificar que son iguales
        pd.testing.assert_frame_equal(data1, data2)


# ==================== RUN TESTS ====================

if __name__ == "__main__":
    """
    Run tests directamente
    
    python tests/test_data_layer.py
    """
    pytest.main([__file__, '-v', '--tb=short'])
```

---

## 📖 EJEMPLO DE USO COMPLETO

### **ARCHIVO 14: examples/data_layer_demo.py**

**Ubicación:** `Atlas/python/examples/data_layer_demo.py`

**Propósito:** Demo completo del Data Layer

**Código:**

```python
"""
Data Layer - Demo Completo

Ejemplo de cómo usar el Data Layer de Atlas.

Run:
    cd Atlas/python
    python examples/data_layer_demo.py

Copyright (c) 2026 M&C. All rights reserved.
"""

from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from atlas.data_layer import get_data
from atlas.data_layer.sources.yahoo import YahooProvider
from atlas.data_layer.quality.validator import DataValidator
from atlas.data_layer.cache import CacheManager


def demo_basic_download():
    """Demo 1: Descarga básica"""
    print("\n" + "=" * 60)
    print("DEMO 1: Descarga Básica")
    print("=" * 60)
    
    # Descargar AAPL 2024
    print("\n📥 Downloading AAPL (2024)...")
    data = get_data("AAPL", "2024-01-01", "2024-12-31")
    
    print(f"✅ Downloaded {len(data)} rows")
    print("\nFirst 5 rows:")
    print(data.head())
    print("\nLast 5 rows:")
    print(data.tail())
    print(f"\nMetadata: {data.attrs}")


def demo_multi_asset():
    """Demo 2: Múltiples assets"""
    print("\n" + "=" * 60)
    print("DEMO 2: Múltiples Assets")
    print("=" * 60)
    
    symbols = ["AAPL", "GOOGL", "BTC-USD", "ETH-USD"]
    
    for symbol in symbols:
        print(f"\n📥 Downloading {symbol}...")
        data = get_data(symbol, "2024-11-01", "2024-12-31", use_cache=True)
        
        last_price = data['Close'].iloc[-1]
        print(f"✅ {symbol}: Last close = ${last_price:.2f}")


def demo_data_quality():
    """Demo 3: Validación de calidad"""
    print("\n" + "=" * 60)
    print("DEMO 3: Validación de Calidad")
    print("=" * 60)
    
    print("\n📥 Downloading data...")
    data = get_data("AAPL", "2024-01-01", "2024-12-31", use_cache=True)
    
    print("\n🔍 Running quality checks...")
    validation = DataValidator.validate_all(data)
    
    print(f"\n✅ Overall Quality: {validation['overall_quality']}")
    print(f"   Missing data: {validation['missing_data']['missing_pct']:.2f}%")
    print(f"   Price spikes: {validation['price_spikes']['spike_count']}")
    print(f"   Date gaps: {validation['gaps']['gap_count']}")
    print(f"   Volume anomalies: {validation['volume_anomalies']['zero_volume_count']}")


def demo_cache_system():
    """Demo 4: Sistema de cache"""
    print("\n" + "=" * 60)
    print("DEMO 4: Sistema de Cache")
    print("=" * 60)
    
    cache = CacheManager()
    
    # Primera descarga (sin cache)
    print("\n⏱️  First download (no cache)...")
    import time
    start = time.time()
    data1 = get_data("AAPL", "2024-01-01", "2024-12-31", use_cache=True)
    time1 = time.time() - start
    print(f"   Time: {time1:.2f}s")
    
    # Segunda descarga (con cache)
    print("\n⚡ Second download (from cache)...")
    start = time.time()
    data2 = get_data("AAPL", "2024-01-01", "2024-12-31", use_cache=True)
    time2 = time.time() - start
    print(f"   Time: {time2:.2f}s")
    
    print(f"\n✅ Speedup: {time1/time2:.1f}x faster with cache")
    
    # Stats de cache
    stats = cache.get_stats()
    print(f"\n📊 Cache Stats:")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Total size: {stats['total_size_mb']:.2f} MB")


def demo_provider_directly():
    """Demo 5: Usar provider directamente"""
    print("\n" + "=" * 60)
    print("DEMO 5: Usar Provider Directamente")
    print("=" * 60)
    
    yahoo = YahooProvider()
    
    # Info del provider
    info = yahoo.get_info()
    print("\n📋 Yahoo Finance Provider Info:")
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # Descargar datos
    print("\n📥 Downloading with provider...")
    data = yahoo.download("AAPL", "2024-12-01", "2024-12-31")
    
    # Validar
    print("\n🔍 Validating...")
    validation = yahoo.validate(data)
    print(f"   Quality: {validation['overall_quality']}")
    
    # Normalizar
    print("\n🔧 Normalizing...")
    normalized = yahoo.normalize(data)
    print(f"   Timezone: {normalized.index.tz}")
    print(f"   Columns: {list(normalized.columns)}")


def main():
    """
    Run all demos
    """
    print("\n" + "=" * 60)
    print("🚀 ATLAS DATA LAYER - DEMO COMPLETO")
    print("=" * 60)
    
    try:
        demo_basic_download()
        demo_multi_asset()
        demo_data_quality()
        demo_cache_system()
        demo_provider_directly()
        
        print("\n" + "=" * 60)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
```

---

## 📊 ORDEN DE IMPLEMENTACIÓN

### **Paso a Paso:**

```
SEMANA 1 - Core (Archivos 1-4):
├─ Día 1: __init__.py + base.py
├─ Día 2-3: yahoo.py (MÁS IMPORTANTE)
└─ Día 4: Test yahoo.py

SEMANA 2 - Quality & Normalization (Archivos 5-8):
├─ Día 1-2: validator.py
├─ Día 3-4: normalizer.py
└─ Día 5: Test validation + normalization

SEMANA 3 - Cache & Polish (Archivos 9-14):
├─ Día 1-2: cache_manager.py
├─ Día 3: Stubs (alpaca.py, polygon.py)
├─ Día 4: Tests completos
└─ Día 5: Demo + documentación
```

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

```
□ Archivo 1: data_layer/__init__.py
□ Archivo 2: data_layer/base.py
□ Archivo 3: sources/__init__.py
□ Archivo 4: sources/yahoo.py ⭐ (CRÍTICO)
□ Archivo 5: quality/__init__.py
□ Archivo 6: quality/validator.py
□ Archivo 7: normalization/__init__.py
□ Archivo 8: normalization/normalizer.py
□ Archivo 9: cache/__init__.py
□ Archivo 10: cache/cache_manager.py
□ Archivo 11: sources/alpaca.py (stub)
□ Archivo 12: sources/polygon.py (stub)
□ Archivo 13: tests/test_data_layer.py
□ Archivo 14: examples/data_layer_demo.py

□ Instalar dependencies (yfinance, pandas, pyarrow)
□ Probar descarga de AAPL
□ Probar cache
□ Probar validación
□ Documentar TODO
```

---

## 🚀 DEPENDENCIES

**Instalar antes de empezar:**

```bash
cd Atlas/python
pip install -r requirements.txt
```

**requirements.txt:**
```
yfinance>=0.2.40
pandas>=2.1.0
pyarrow>=15.0.0  # Para cache Parquet
pytest>=7.4.0    # Para tests
```

---

## 🎯 RESULTADO FINAL

**Al completar FASE 1, tendrás:**

```python
# ✅ Esto funcionará:

from atlas.data_layer import get_data

# Descargar cualquier asset
aapl = get_data("AAPL", "2024-01-01", "2024-12-31")
btc = get_data("BTC-USD", "2024-01-01", "2024-12-31")
spy = get_data("SPY", "2024-01-01", "2024-12-31")

# Con cache automático
data = get_data("AAPL", "2024-01-01", "2024-12-31", use_cache=True)

# Datos ya normalizados y validados
print(data.head())
print(data.attrs)  # Metadata incluida
```

---

## 📞 TROUBLESHOOTING

**Problema:** yfinance no instala  
**Solución:** `pip install yfinance --upgrade`

**Problema:** Error de timezone  
**Solución:** Ya está manejado en normalizer.py

**Problema:** Cache no funciona  
**Solución:** Verificar que existe `Atlas/data/cache/`

**Problema:** Tests fallan  
**Solución:** `pip install pytest` y correr desde `Atlas/python/`

---

## 🎉 PRÓXIMO PASO

**Una vez FASE 1 esté completa:**

→ **FASE 2: MARKET STATE** (Regímenes, internals, sentiment)

**O si prefieres:**

→ **FASE 1.5: ARIA** (Voice assistant + tools)

---

**Status:** 📋 Master Guide Completo  
**Archivos:** 15 archivos Python  
**Tiempo:** 1-2 semanas  
**Dificultad:** ⭐⭐ (Media)

🚀 **¡Listo para implementar FASE 1!**
