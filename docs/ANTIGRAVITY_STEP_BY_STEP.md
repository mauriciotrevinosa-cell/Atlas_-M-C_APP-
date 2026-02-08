# 🤖 ANTIGRAVITY - PASO A PASO QUIRÚRGICO

**Instrucciones Exactas para Implementar Atlas**  
**Copyright © 2026 M&C. All Rights Reserved.**

**IMPORTANTE:** Este documento te dice EXACTAMENTE qué archivos crear, dónde, y con qué código.

---

## 📋 ANTES DE EMPEZAR

### **Estructura Base (Ya existe):**

```
Atlas/
├── python/
│   ├── src/
│   │   └── atlas/
│   │       ├── __init__.py ✅ (ya existe)
│   │       ├── data_layer/ ✅ (FASE 1 completa)
│   │       └── [otros módulos por crear]
│   └── tests/
│       ├── unit/
│       └── integration/
├── docs/
├── configs/
└── data/
```

**Tu trabajo:** Crear los módulos faltantes (FASE 2 en adelante)

---

## 🎯 FASE 2: MARKET STATE DETECTION

**Objetivo:** Detectar régimen de mercado (trending, ranging, volatile)

**Archivos a crear:** 5 archivos exactos

---

### **ARCHIVO 1 DE 5**

**Ruta exacta:**
```
Atlas/python/src/atlas/market_state/__init__.py
```

**Acción:** Crear este archivo NUEVO

**Contenido EXACTO (copiar todo):**

```python
"""
Market State Detection Module

Detects and classifies market regimes.

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

from .regime import RegimeDetector
from .volatility import VolatilityRegime
from .internals import MarketInternals

__all__ = [
    'RegimeDetector',
    'VolatilityRegime',
    'MarketInternals'
]
```

**Guardar:** `Atlas/python/src/atlas/market_state/__init__.py`

---

### **ARCHIVO 2 DE 5**

**Ruta exacta:**
```
Atlas/python/src/atlas/market_state/regime.py
```

**Acción:** Crear este archivo NUEVO

**Contenido EXACTO (copiar todo):**

```python
"""
Market Regime Detection

Detects market regime using ADX and price action.

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
from typing import Literal, Dict
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

RegimeType = Literal['trending_up', 'trending_down', 'ranging', 'volatile']


@dataclass
class RegimeState:
    """Market regime state"""
    regime: RegimeType
    confidence: float
    metrics: Dict[str, float]
    timestamp: pd.Timestamp


class RegimeDetector:
    """
    Detect market regime
    
    Args:
        adx_threshold: ADX level for trending (default: 25)
        lookback: Period for detection (default: 20)
    
    Example:
        >>> detector = RegimeDetector(adx_threshold=25)
        >>> regime = detector.detect(data)
        >>> print(regime.regime)
        'trending_up'
    """
    
    def __init__(self, adx_threshold: float = 25.0, lookback: int = 20):
        if adx_threshold <= 0 or adx_threshold > 100:
            raise ValueError(f"ADX threshold must be 0-100, got {adx_threshold}")
        
        if lookback < 5:
            raise ValueError(f"Lookback must be >= 5, got {lookback}")
        
        self.adx_threshold = adx_threshold
        self.lookback = lookback
        
        logger.info(f"Initialized RegimeDetector (ADX={adx_threshold}, lookback={lookback})")
    
    def detect(self, data: pd.DataFrame) -> RegimeState:
        """
        Detect current market regime
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            RegimeState: Current regime with confidence
        """
        if len(data) < self.lookback:
            raise ValueError(f"Need at least {self.lookback} bars, got {len(data)}")
        
        # Calculate ADX
        adx = self._calculate_adx(data)
        trend_direction = self._detect_trend_direction(data)
        vol_regime = self._detect_volatility_regime(data)
        
        current_adx = adx.iloc[-1]
        
        if current_adx >= self.adx_threshold:
            # Trending
            if trend_direction > 0:
                regime = 'trending_up'
            else:
                regime = 'trending_down'
            confidence = min(current_adx / 50.0, 1.0)
        else:
            # Ranging or Volatile
            if vol_regime == 'high':
                regime = 'volatile'
                confidence = 0.7
            else:
                regime = 'ranging'
                confidence = 0.8
        
        metrics = {
            'adx': float(current_adx),
            'trend_direction': float(trend_direction),
            'volatility': float(vol_regime == 'high')
        }
        
        state = RegimeState(
            regime=regime,
            confidence=float(confidence),
            metrics=metrics,
            timestamp=data.index[-1]
        )
        
        logger.debug(f"Detected regime: {regime} (confidence={confidence:.2f})")
        
        return state
    
    def _calculate_adx(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX)"""
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        dm_plus = high.diff()
        dm_minus = -low.diff()
        
        dm_plus[dm_plus < 0] = 0
        dm_minus[dm_minus < 0] = 0
        
        # Smooth with EMA
        atr = tr.ewm(span=period, adjust=False).mean()
        di_plus = 100 * (dm_plus.ewm(span=period, adjust=False).mean() / atr)
        di_minus = 100 * (dm_minus.ewm(span=period, adjust=False).mean() / atr)
        
        # ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return adx.fillna(0)
    
    def _detect_trend_direction(self, data: pd.DataFrame) -> int:
        """Detect trend direction (+1 up, -1 down, 0 none)"""
        close = data['Close'].iloc[-self.lookback:]
        
        recent_avg = close.iloc[-5:].mean()
        old_avg = close.iloc[:5].mean()
        
        if recent_avg > old_avg * 1.02:
            return 1
        elif recent_avg < old_avg * 0.98:
            return -1
        else:
            return 0
    
    def _detect_volatility_regime(self, data: pd.DataFrame) -> Literal['high', 'low']:
        """Detect volatility regime"""
        returns = data['Close'].pct_change().iloc[-self.lookback:]
        current_vol = returns.std()
        
        hist_vol = data['Close'].pct_change().std()
        
        if current_vol > hist_vol * 1.5:
            return 'high'
        else:
            return 'low'
```

**Guardar:** `Atlas/python/src/atlas/market_state/regime.py`

---

### **ARCHIVO 3 DE 5**

**Ruta exacta:**
```
Atlas/python/src/atlas/market_state/volatility.py
```

**Acción:** Crear este archivo NUEVO

**Contenido EXACTO:**

```python
"""
Volatility Regime Detection

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
from typing import Literal
import logging

logger = logging.getLogger(__name__)

VolRegime = Literal['low', 'normal', 'high', 'extreme']


class VolatilityRegime:
    """
    Classify volatility regime
    
    Args:
        lookback: Historical period (default: 252)
    
    Example:
        >>> vol_detector = VolatilityRegime(lookback=252)
        >>> regime = vol_detector.classify(data)
        >>> print(regime)
        'normal'
    """
    
    def __init__(self, lookback: int = 252):
        if lookback < 20:
            raise ValueError(f"Lookback must be >= 20, got {lookback}")
        
        self.lookback = lookback
        logger.info(f"Initialized VolatilityRegime (lookback={lookback})")
    
    def classify(self, data: pd.DataFrame, window: int = 20) -> VolRegime:
        """
        Classify current volatility regime
        
        Args:
            data: OHLCV DataFrame
            window: Rolling window
        
        Returns:
            VolRegime classification
        """
        if len(data) < self.lookback:
            raise ValueError(f"Need >= {self.lookback} bars")
        
        # Calculate realized volatility
        returns = data['Close'].pct_change()
        rolling_vol = returns.rolling(window=window).std() * np.sqrt(252)
        
        current_vol = rolling_vol.iloc[-1]
        
        # Historical percentiles
        hist_vol = rolling_vol.dropna()
        p25 = hist_vol.quantile(0.25)
        p75 = hist_vol.quantile(0.75)
        p95 = hist_vol.quantile(0.95)
        
        # Classify
        if current_vol < p25:
            regime = 'low'
        elif current_vol < p75:
            regime = 'normal'
        elif current_vol < p95:
            regime = 'high'
        else:
            regime = 'extreme'
        
        logger.debug(f"Vol regime: {regime} (vol={current_vol:.4f})")
        
        return regime
```

**Guardar:** `Atlas/python/src/atlas/market_state/volatility.py`

---

### **ARCHIVO 4 DE 5**

**Ruta exacta:**
```
Atlas/python/src/atlas/market_state/internals.py
```

**Acción:** Crear este archivo NUEVO

**Contenido EXACTO:**

```python
"""
Market Internals

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class MarketInternals:
    """
    Calculate market internals
    
    Example:
        >>> internals = MarketInternals()
        >>> metrics = internals.calculate(data)
        >>> print(metrics['strength'])
    """
    
    def __init__(self):
        logger.info("Initialized MarketInternals")
    
    def calculate(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate market internals
        
        Args:
            data: OHLCV DataFrame
        
        Returns:
            dict of metrics
        """
        close = data['Close']
        volume = data['Volume']
        
        # Price momentum
        returns_5d = close.pct_change(5).iloc[-1]
        returns_20d = close.pct_change(20).iloc[-1]
        
        # Volume trend
        vol_avg_20d = volume.rolling(20).mean().iloc[-1]
        vol_current = volume.iloc[-1]
        vol_ratio = vol_current / vol_avg_20d if vol_avg_20d > 0 else 1.0
        
        # Simplified breadth
        recent_highs = (close.iloc[-5:] == close.iloc[-20:].max()).sum()
        breadth_ratio = recent_highs / 5.0
        
        metrics = {
            'returns_5d': float(returns_5d),
            'returns_20d': float(returns_20d),
            'volume_ratio': float(vol_ratio),
            'breadth_ratio': float(breadth_ratio),
            'strength': float((returns_5d + returns_20d) / 2)
        }
        
        logger.debug(f"Internals: strength={metrics['strength']:.4f}")
        
        return metrics
```

**Guardar:** `Atlas/python/src/atlas/market_state/internals.py`

---

### **ARCHIVO 5 DE 5**

**Ruta exacta:**
```
Atlas/python/tests/unit/test_market_state.py
```

**Acción:** Crear este archivo NUEVO

**Contenido EXACTO:**

```python
"""
Tests for Market State module

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import pandas as pd
import numpy as np
from atlas.market_state import RegimeDetector, VolatilityRegime, MarketInternals


class TestRegimeDetector:
    """Test RegimeDetector"""
    
    def test_initialization(self):
        """Test normal init"""
        detector = RegimeDetector(adx_threshold=25, lookback=20)
        assert detector.adx_threshold == 25
        assert detector.lookback == 20
    
    def test_invalid_adx(self):
        """Test invalid ADX"""
        with pytest.raises(ValueError):
            RegimeDetector(adx_threshold=-1)
    
    def test_detection(self):
        """Test detection"""
        # Create test data
        dates = pd.date_range('2024-01-01', periods=50)
        close = np.linspace(100, 120, 50)
        
        data = pd.DataFrame({
            'Open': close,
            'High': close * 1.01,
            'Low': close * 0.99,
            'Close': close,
            'Volume': [1000000] * 50
        }, index=dates)
        
        detector = RegimeDetector()
        regime = detector.detect(data)
        
        assert regime.regime in ['trending_up', 'trending_down', 'ranging', 'volatile']
        assert 0 <= regime.confidence <= 1


class TestVolatilityRegime:
    """Test VolatilityRegime"""
    
    def test_classification(self):
        """Test classification"""
        dates = pd.date_range('2024-01-01', periods=300)
        data = pd.DataFrame({
            'Close': 100 + np.random.randn(300).cumsum()
        }, index=dates)
        
        detector = VolatilityRegime(lookback=252)
        regime = detector.classify(data)
        
        assert regime in ['low', 'normal', 'high', 'extreme']


class TestMarketInternals:
    """Test MarketInternals"""
    
    def test_calculation(self):
        """Test calculation"""
        dates = pd.date_range('2024-01-01', periods=50)
        data = pd.DataFrame({
            'Close': range(100, 150),
            'Volume': [1000000] * 50
        }, index=dates)
        
        internals = MarketInternals()
        metrics = internals.calculate(data)
        
        assert 'strength' in metrics
        assert 'volume_ratio' in metrics
        assert isinstance(metrics['strength'], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Guardar:** `Atlas/python/tests/unit/test_market_state.py`

---

## ✅ CHECKLIST FASE 2

**Después de crear los 5 archivos, verifica:**

```bash
# Estructura debe verse así:
Atlas/python/src/atlas/market_state/
├── __init__.py          ✅
├── regime.py            ✅
├── volatility.py        ✅
└── internals.py         ✅

Atlas/python/tests/unit/
└── test_market_state.py ✅
```

**Prueba que funciona:**

```bash
cd Atlas/python
python -m pytest tests/unit/test_market_state.py -v
```

**Deberías ver:**
```
test_market_state.py::TestRegimeDetector::test_initialization PASSED
test_market_state.py::TestRegimeDetector::test_invalid_adx PASSED
test_market_state.py::TestRegimeDetector::test_detection PASSED
...
======== 6 passed in 0.5s ========
```

---

## 🎯 SIGUIENTE: FASE 3 (PARTE 1)

**Una vez FASE 2 esté completa y tests pasen, continúa con:**

### **FASE 3: FEATURES - VPIN (Microstructure)**

**Archivos a crear:** 3 archivos

---

### **ARCHIVO 1 DE 3**

**Ruta exacta:**
```
Atlas/python/src/atlas/features/__init__.py
```

**Contenido:**

```python
"""
Feature Extraction Module

Copyright © 2026 M&C. All Rights Reserved.
"""

__version__ = "1.0.0"

__all__ = []
```

---

### **ARCHIVO 2 DE 3**

**Ruta exacta:**
```
Atlas/python/src/atlas/features/microstructure/__init__.py
```

**Contenido:**

```python
"""
Market Microstructure Features

Copyright © 2026 M&C. All Rights Reserved.
"""

from .vpin import VPINCalculator, VPINConfig

__all__ = ['VPINCalculator', 'VPINConfig']
```

---

### **ARCHIVO 3 DE 3**

**Ruta exacta:**
```
Atlas/python/src/atlas/features/microstructure/vpin.py
```

**Contenido:** (Copiar del IMPLEMENTATION_GUIDE_ADVANCED.md - sección VPIN completa, ~400 líneas)

---

## 📊 RESUMEN DE TRABAJO

### **FASE 2: 5 archivos**
1. `market_state/__init__.py`
2. `market_state/regime.py`
3. `market_state/volatility.py`
4. `market_state/internals.py`
5. `tests/unit/test_market_state.py`

### **FASE 3 (Parte 1): 3 archivos**
1. `features/__init__.py`
2. `features/microstructure/__init__.py`
3. `features/microstructure/vpin.py`

### **Total Fase 2 + Fase 3.1: 8 archivos**

---

## 🤖 PARA ANTIGRAVITY

**INSTRUCCIONES CLARAS:**

1. **Crear EXACTAMENTE 5 archivos para FASE 2**
2. **Copiar el código EXACTO** (no modificar)
3. **Guardar en las rutas EXACTAS** indicadas
4. **Correr tests** para verificar
5. **Reportar:** "FASE 2 completa - 5 archivos creados - tests passing"

**LUEGO:**

6. **Crear EXACTAMENTE 3 archivos para FASE 3.1**
7. **Repetir proceso**
8. **Reportar:** "FASE 3.1 completa"

---

## ❌ ERRORES COMUNES A EVITAR

1. **NO crear carpetas en lugares incorrectos**
   - ✅ Correcto: `Atlas/python/src/atlas/market_state/`
   - ❌ Incorrecto: `Atlas/market_state/`

2. **NO modificar el código**
   - ✅ Copiar exactamente como está
   - ❌ "Mejorar" o cambiar cosas

3. **NO saltar archivos**
   - ✅ Crear los 5 archivos de FASE 2
   - ❌ Crear solo 3

4. **NO mezclar fases**
   - ✅ Completar FASE 2 antes de FASE 3
   - ❌ Crear archivos de diferentes fases

---

## 📞 VALIDACIÓN

**Después de cada fase:**

```python
# Test rápido en Python
from atlas.market_state import RegimeDetector
import pandas as pd
import numpy as np

# Create test data
dates = pd.date_range('2024-01-01', periods=50)
data = pd.DataFrame({
    'Open': range(100, 150),
    'High': range(101, 151),
    'Low': range(99, 149),
    'Close': range(100, 150),
    'Volume': [1000000] * 50
}, index=dates)

# Test
detector = RegimeDetector()
regime = detector.detect(data)
print(f"Regime: {regime.regime}")
print(f"Confidence: {regime.confidence:.2f}")
print("✅ FASE 2 WORKS!")
```

**Si esto funciona, FASE 2 está completa.**

---

**Copyright © 2026 M&C. All Rights Reserved.**

---

**PRÓXIMO DOCUMENTO:** Continuación con FASE 3, 4, 5... (solicitar cuando termine FASE 2)
