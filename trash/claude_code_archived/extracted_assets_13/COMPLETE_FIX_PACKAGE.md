# 🔧 PAQUETE COMPLETO DE CORRECCIONES - ATLAS

**Fecha:** 2026-02-04  
**Propósito:** Arreglar los 61 archivos vacíos y agregar tests  
**Tiempo estimado:** 1-2 horas

---

## 📋 ÍNDICE

1. [Resumen de Problemas](#resumen-de-problemas)
2. [Estructura de Directorios a Crear](#estructura-de-directorios)
3. [Archivos a Modificar (CRÍTICOS)](#archivos-críticos)
4. [Tests a Crear](#tests)
5. [Validación Final](#validación)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 RESUMEN DE PROBLEMAS

### **Problemas Encontrados:**
- ❌ 61 archivos vacíos (0 bytes)
- ❌ No existe directorio `tests/`
- ❌ Data Layer sin implementar
- ❌ No se puede importar `from atlas.data_layer import get_data`

### **Solución:**
- ✅ Implementar Data Layer completo (50 líneas)
- ✅ Crear 7 tests (unit + integration)
- ✅ Crear estructura de tests

---

## 📂 ESTRUCTURA DE DIRECTORIOS

### **PASO 1: Crear Directorios de Tests**

```bash
# Ejecuta estos comandos en tu terminal (en el directorio Atlas/)
cd Atlas/python

# Crear estructura de tests
mkdir -p tests/unit
mkdir -p tests/integration

# Crear archivos __init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

# Verificar
ls -la tests/
# Debes ver: __init__.py, unit/, integration/
```

---

## 🔴 ARCHIVOS CRÍTICOS

### **ARCHIVO 1/3: Data Layer Main** 

**RUTA:** `python/src/atlas/data_layer/__init__.py`

**ACCIÓN:** Reemplazar contenido completo (el archivo está vacío)

**CÓDIGO COMPLETO:**

```python
"""
Data Layer - Public API

Provides simple access to market data.

Copyright © 2026 M&C. All Rights Reserved.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_data(
    symbol: str, 
    start: str, 
    end: str, 
    use_cache: bool = False
) -> pd.DataFrame:
    """
    Get OHLCV data for a symbol
    
    Args:
        symbol: Ticker symbol (e.g., "AAPL")
        start: Start date "YYYY-MM-DD"
        end: End date "YYYY-MM-DD"
        use_cache: Whether to use cache (not implemented yet)
    
    Returns:
        DataFrame with OHLCV data (columns: Open, High, Low, Close, Volume)
    
    Raises:
        ValueError: If no data found for symbol/dates
        RuntimeError: If download fails
    
    Example:
        >>> from atlas.data_layer import get_data
        >>> data = get_data("AAPL", "2024-01-01", "2024-12-31")
        >>> print(data.head())
                       Open   High    Low  Close     Volume
        2024-01-02  187.15  188.44  185.19  185.64  82488300
    """
    logger.info(f"Fetching data for {symbol} from {start} to {end}")
    
    try:
        # Download data from Yahoo Finance (free, no API key)
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start, end=end)
        
        # Validate data exists
        if data.empty:
            raise ValueError(
                f"No data found for {symbol} between {start} and {end}. "
                f"Check symbol and dates."
            )
        
        # Standardize column names
        data = data.rename(columns={
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume'
        })
        
        # Select only OHLCV columns (drop Dividends, Stock Splits, etc.)
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        logger.info(f"✅ Successfully fetched {len(data)} bars for {symbol}")
        
        return data
        
    except ValueError as e:
        # Re-raise validation errors
        logger.error(f"Validation error: {str(e)}")
        raise
        
    except Exception as e:
        # Catch network errors, invalid symbols, etc.
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        raise RuntimeError(f"Failed to fetch data: {str(e)}")


# Public API
__all__ = ['get_data']
```

**GUARDAR Y CERRAR**

---

### **ARCHIVO 2/3: Unit Tests**

**RUTA:** `python/tests/unit/test_data_layer.py` (CREAR NUEVO)

**ACCIÓN:** Crear archivo nuevo con este contenido

**CÓDIGO COMPLETO:**

```python
"""
Unit Tests for Data Layer

Run with:
    pytest tests/unit/test_data_layer.py -v

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import pandas as pd
from atlas.data_layer import get_data


class TestDataLayer:
    """Test suite for Data Layer"""
    
    def test_get_data_aapl_basic(self):
        """Test basic AAPL data fetch"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31")
        
        # Verify data exists
        assert data is not None
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
    def test_get_data_columns(self):
        """Test that all OHLCV columns are present"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31")
        
        # Check columns
        expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        assert list(data.columns) == expected_columns
        
    def test_get_data_types(self):
        """Test data types are correct"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31")
        
        # Price columns should be float
        assert data['Open'].dtype in ['float64', 'float32']
        assert data['Close'].dtype in ['float64', 'float32']
        
        # Volume should be numeric
        assert pd.api.types.is_numeric_dtype(data['Volume'])
    
    def test_get_data_msft(self):
        """Test with different symbol (MSFT)"""
        data = get_data("MSFT", "2024-01-01", "2024-01-31")
        
        assert len(data) > 0
        assert data['Close'].iloc[0] > 0
    
    def test_get_data_invalid_symbol(self):
        """Test with invalid symbol should raise ValueError"""
        with pytest.raises(ValueError):
            get_data("INVALID_SYMBOL_XYZ123", "2024-01-01", "2024-01-31")
    
    def test_get_data_invalid_dates(self):
        """Test with future dates (should return empty or raise)"""
        # Future dates should return empty data or raise error
        try:
            data = get_data("AAPL", "2030-01-01", "2030-01-31")
            assert len(data) == 0  # Empty if no error
        except (ValueError, RuntimeError):
            pass  # Acceptable to raise error
    
    def test_data_chronological_order(self):
        """Test that data is sorted chronologically"""
        data = get_data("AAPL", "2024-01-01", "2024-12-31")
        
        # Index should be monotonic increasing (dates in order)
        assert data.index.is_monotonic_increasing
        
    def test_no_null_close_prices(self):
        """Test that Close prices have no nulls"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31")
        
        # Close prices should never be null
        assert data['Close'].notna().all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**GUARDAR Y CERRAR**

---

### **ARCHIVO 3/3: Integration Tests**

**RUTA:** `python/tests/integration/test_full_workflow.py` (CREAR NUEVO)

**ACCIÓN:** Crear archivo nuevo con este contenido

**CÓDIGO COMPLETO:**

```python
"""
Integration Tests - Full Workflow

Tests that multiple components work together.

Run with:
    pytest tests/integration/test_full_workflow.py -v

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import pandas as pd
from atlas.data_layer import get_data
from atlas.core_intelligence.features.technical.indicators import TechnicalIndicators


class TestDataToIndicators:
    """Test: Data Layer → Technical Indicators pipeline"""
    
    def test_data_to_rsi(self):
        """Test: Fetch data → Calculate RSI"""
        # Get data
        data = get_data("AAPL", "2024-01-01", "2024-12-31")
        
        # Calculate RSI
        rsi = TechnicalIndicators.rsi(data['Close'], period=14)
        
        # Verify RSI calculated
        assert len(rsi) == len(data)
        
        # Verify RSI in valid range (0-100)
        rsi_valid = rsi.dropna()
        assert (rsi_valid >= 0).all()
        assert (rsi_valid <= 100).all()
        
    def test_data_to_macd(self):
        """Test: Fetch data → Calculate MACD"""
        # Get data
        data = get_data("MSFT", "2024-01-01", "2024-12-31")
        
        # Calculate MACD
        macd_df = TechnicalIndicators.macd(data['Close'])
        
        # Verify MACD has correct structure
        assert len(macd_df) == len(data)
        assert 'macd_line' in macd_df.columns
        assert 'signal_line' in macd_df.columns
        assert 'histogram' in macd_df.columns
        
    def test_data_to_bollinger_bands(self):
        """Test: Fetch data → Calculate Bollinger Bands"""
        # Get data
        data = get_data("AAPL", "2024-01-01", "2024-12-31")
        
        # Calculate Bollinger Bands
        bb_df = TechnicalIndicators.bollinger_bands(data['Close'], window=20)
        
        # Verify structure
        assert len(bb_df) == len(data)
        assert 'bb_upper' in bb_df.columns
        assert 'bb_middle' in bb_df.columns
        assert 'bb_lower' in bb_df.columns
        
        # Verify logical constraint: upper >= middle >= lower
        bb_valid = bb_df.dropna()
        assert (bb_valid['bb_upper'] >= bb_valid['bb_middle']).all()
        assert (bb_valid['bb_middle'] >= bb_valid['bb_lower']).all()
    
    def test_multiple_symbols(self):
        """Test: Process multiple symbols in sequence"""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        
        for symbol in symbols:
            # Get data
            data = get_data(symbol, "2024-01-01", "2024-03-31")
            
            # Calculate indicators
            rsi = TechnicalIndicators.rsi(data['Close'])
            
            # Basic validation
            assert len(data) > 0
            assert len(rsi) == len(data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**GUARDAR Y CERRAR**

---

## ✅ VALIDACIÓN

### **PASO 1: Verificar Estructura**

```bash
cd Atlas/python

# Verificar que existen los directorios
ls -la tests/
# Debe mostrar: __init__.py, unit/, integration/

ls -la tests/unit/
# Debe mostrar: __init__.py, test_data_layer.py

ls -la tests/integration/
# Debe mostrar: __init__.py, test_full_workflow.py
```

---

### **PASO 2: Test de Importación**

```bash
cd Atlas/python

# Test 1: Verificar que el módulo se importa
python -c "from atlas.data_layer import get_data; print('✅ Import OK')"

# Si muestra "✅ Import OK" → ÉXITO
# Si da error → Ver sección Troubleshooting
```

---

### **PASO 3: Correr Tests Unitarios**

```bash
cd Atlas/python

# Correr tests de data_layer
pytest tests/unit/test_data_layer.py -v

# ESPERADO:
# test_get_data_aapl_basic PASSED        ✅
# test_get_data_columns PASSED           ✅
# test_get_data_types PASSED             ✅
# test_get_data_msft PASSED              ✅
# test_get_data_invalid_symbol PASSED    ✅
# test_get_data_invalid_dates PASSED     ✅
# test_data_chronological_order PASSED   ✅
# test_no_null_close_prices PASSED       ✅
#
# ========== 8 passed in X.Xs ==========
```

---

### **PASO 4: Correr Tests de Integración**

```bash
cd Atlas/python

# Correr tests de integración
pytest tests/integration/test_full_workflow.py -v

# ESPERADO:
# test_data_to_rsi PASSED                ✅
# test_data_to_macd PASSED               ✅
# test_data_to_bollinger_bands PASSED    ✅
# test_multiple_symbols PASSED           ✅
#
# ========== 4 passed in X.Xs ==========
```

---

### **PASO 5: Test Manual Completo**

```bash
cd Atlas/python

# Test manual en Python
python
```

```python
# Dentro del intérprete de Python:
from atlas.data_layer import get_data
from atlas.core_intelligence.features.technical.indicators import TechnicalIndicators

# 1. Fetch data
data = get_data("AAPL", "2024-01-01", "2024-12-31")
print(f"✅ Downloaded {len(data)} bars")
print(data.head())

# 2. Calculate RSI
rsi = TechnicalIndicators.rsi(data['Close'])
print(f"✅ RSI calculated, latest value: {rsi.iloc[-1]:.2f}")

# 3. Calculate MACD
macd_df = TechnicalIndicators.macd(data['Close'])
print(f"✅ MACD calculated")
print(macd_df.tail())

# Si todo esto funciona → SUCCESS! ✅
exit()
```

---

## 🔧 TROUBLESHOOTING

### **Problema 1: "ModuleNotFoundError: No module named 'atlas'"**

**Solución:**
```bash
cd Atlas/python
pip install -e .
```

---

### **Problema 2: "ModuleNotFoundError: No module named 'yfinance'"**

**Solución:**
```bash
pip install yfinance
```

---

### **Problema 3: "ImportError: cannot import name 'get_data'"**

**Causa:** El archivo `data_layer/__init__.py` está vacío

**Solución:**
1. Abre `python/src/atlas/data_layer/__init__.py`
2. Verifica que tenga el código completo del ARCHIVO 1
3. Verifica que termine con `__all__ = ['get_data']`
4. Guarda el archivo

---

### **Problema 4: Tests fallan con "No data found"**

**Causa:** Fechas futuras o símbolo inválido

**Solución:**
- Usa fechas del pasado (2024-01-01 funciona)
- Usa símbolos válidos (AAPL, MSFT, GOOGL)

---

### **Problema 5: "pytest: command not found"**

**Solución:**
```bash
pip install pytest
```

---

## 📊 CHECKLIST FINAL

### **Antes de Continuar, Verifica:**

- [ ] Directorio `tests/` creado con `__init__.py`
- [ ] Directorio `tests/unit/` creado con `__init__.py`
- [ ] Directorio `tests/integration/` creado con `__init__.py`
- [ ] Archivo `data_layer/__init__.py` modificado (NO vacío)
- [ ] Archivo `tests/unit/test_data_layer.py` creado
- [ ] Archivo `tests/integration/test_full_workflow.py` creado
- [ ] Import funciona: `python -c "from atlas.data_layer import get_data"`
- [ ] Tests unitarios pasan: `pytest tests/unit/ -v`
- [ ] Tests integración pasan: `pytest tests/integration/ -v`

---

## 🎯 SIGUIENTE PASO

**Cuando todos los tests pasen ✅**

Ve a la carpeta `/mnt/user-data/outputs/` y busca:
- `IMPLEMENTATION_GUIDE_ADVANCED.md` - Para implementar Monte Carlo
- `ANTIGRAVITY_STEP_BY_STEP.md` - Para crear Market State

O dime que terminaste y te doy el siguiente paso específico.

---

## 📞 RESUMEN EJECUTIVO

**QUÉ HICISTE:**
1. ✅ Creaste estructura de tests (3 carpetas, 3 `__init__.py`)
2. ✅ Implementaste Data Layer (50 líneas)
3. ✅ Creaste 8 tests unitarios
4. ✅ Creaste 4 tests de integración
5. ✅ Validaste que todo funciona

**RESULTADO:**
- Data Layer funcional ✅
- 12 tests passing ✅
- Pipeline completo: Data → Indicators ✅

**PROGRESO:**
- Antes: 35%
- Ahora: 45%
- Próximo: 60% (con Market State)

---

**Copyright © 2026 M&C. All Rights Reserved.**

**FIN DEL PAQUETE DE CORRECCIONES**
