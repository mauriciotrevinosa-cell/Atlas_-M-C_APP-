# 🔧 TODOS LOS ARCHIVOS DE FIXES

**Contiene:** 8 archivos completos listos para copiar

**Instrucciones:** Ver `INSTRUCCIONES_FIXES.md` para orden de ejecución

---

## 📄 ARCHIVO 1: data_layer/__init__.py

**Ruta:** `python/src/atlas/data_layer/__init__.py`

**Acción:** REEMPLAZAR todo el contenido con esto:

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

def get_data(symbol: str, start: str, end: str, use_cache: bool = False) -> pd.DataFrame:
    """
    Get OHLCV data for a symbol
    
    Args:
        symbol: Ticker symbol (e.g., "AAPL")
        start: Start date "YYYY-MM-DD"
        end: End date "YYYY-MM-DD"
        use_cache: Whether to use cache (not implemented yet)
    
    Returns:
        DataFrame with OHLCV data
    
    Raises:
        ValueError: If no data found
        RuntimeError: If download fails
    
    Example:
        >>> data = get_data("AAPL", "2024-01-01", "2024-12-31")
        >>> print(data.head())
    """
    logger.info(f"Fetching data for {symbol} from {start} to {end}")
    
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(start=start, end=end)
        
        if data.empty:
            raise ValueError(f"No data found for {symbol} between {start} and {end}")
        
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        logger.info(f"Successfully fetched {len(data)} bars for {symbol}")
        
        return data
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        raise RuntimeError(f"Failed to fetch data: {str(e)}")


__all__ = ['get_data']
```

---

## 📄 ARCHIVO 2: test_data_layer.py

**Ruta:** `python/tests/unit/test_data_layer.py`

**Acción:** CREAR archivo nuevo con esto:

```python
"""
Tests for Data Layer

Run with: pytest tests/unit/test_data_layer.py -v

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import pandas as pd
from atlas.data_layer import get_data


class TestDataLayer:
    """Test suite for Data Layer"""
    
    def test_get_data_aapl(self):
        """Test fetching AAPL data"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31")
        
        assert data is not None
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
        assert 'Open' in data.columns
        assert 'High' in data.columns
        assert 'Low' in data.columns
        assert 'Close' in data.columns
        assert 'Volume' in data.columns
    
    def test_get_data_msft(self):
        """Test fetching MSFT data"""
        data = get_data("MSFT", "2024-01-01", "2024-01-31")
        
        assert len(data) > 0
        assert data['Close'].iloc[0] > 0
    
    def test_data_order(self):
        """Test that data is sorted by date"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31")
        
        assert data.index.is_monotonic_increasing
    
    def test_ohlcv_validity(self):
        """Test OHLCV data validity"""
        data = get_data("AAPL", "2024-01-01", "2024-01-31")
        
        assert (data['High'] >= data['Low']).all()
        assert (data['Volume'] >= 0).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## 📄 ARCHIVO 3: market_state/__init__.py

**Ruta:** `python/src/atlas/market_state/__init__.py`

**Acción:** CREAR archivo nuevo con esto:

```python
"""
Market State Detection Module

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

---

## 📄 ARCHIVO 4: market_state/regime.py

**Ruta:** `python/src/atlas/market_state/regime.py`

**Acción:** CREAR archivo nuevo con esto:

```python
"""
Market Regime Detection

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
        
        adx = self._calculate_adx(data)
        trend_direction = self._detect_trend_direction(data)
        vol_regime = self._detect_volatility_regime(data)
        
        current_adx = adx.iloc[-1]
        
        if current_adx >= self.adx_threshold:
            if trend_direction > 0:
                regime = 'trending_up'
            else:
                regime = 'trending_down'
            confidence = min(current_adx / 50.0, 1.0)
        else:
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
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        dm_plus = high.diff()
        dm_minus = -low.diff()
        
        dm_plus[dm_plus < 0] = 0
        dm_minus[dm_minus < 0] = 0
        
        atr = tr.ewm(span=period, adjust=False).mean()
        di_plus = 100 * (dm_plus.ewm(span=period, adjust=False).mean() / atr)
        di_minus = 100 * (dm_minus.ewm(span=period, adjust=False).mean() / atr)
        
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

---

## 📄 ARCHIVO 5: market_state/volatility.py

**Ruta:** `python/src/atlas/market_state/volatility.py`

**Acción:** CREAR archivo nuevo con esto:

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
        
        returns = data['Close'].pct_change()
        rolling_vol = returns.rolling(window=window).std() * np.sqrt(252)
        
        current_vol = rolling_vol.iloc[-1]
        
        hist_vol = rolling_vol.dropna()
        p25 = hist_vol.quantile(0.25)
        p75 = hist_vol.quantile(0.75)
        p95 = hist_vol.quantile(0.95)
        
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

---

## 📄 ARCHIVO 6: market_state/internals.py

**Ruta:** `python/src/atlas/market_state/internals.py`

**Acción:** CREAR archivo nuevo con esto:

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
        
        returns_5d = close.pct_change(5).iloc[-1]
        returns_20d = close.pct_change(20).iloc[-1]
        
        vol_avg_20d = volume.rolling(20).mean().iloc[-1]
        vol_current = volume.iloc[-1]
        vol_ratio = vol_current / vol_avg_20d if vol_avg_20d > 0 else 1.0
        
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

---

## 📄 ARCHIVO 7: test_market_state.py

**Ruta:** `python/tests/unit/test_market_state.py`

**Acción:** CREAR archivo nuevo con esto:

```python
"""
Tests for Market State

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
    
    def test_detection(self):
        """Test detection"""
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

---

## 📄 ARCHIVO 8: vpin.py

**Ruta:** `python/src/atlas/core_intelligence/features/microstructure/vpin.py`

**Acción:** CREAR o REEMPLAZAR con esto:

```python
"""
VPIN (Volume-Synchronized Probability of Informed Trading)

Measures order flow toxicity.

Reference:
- Easley, D., López de Prado, M., O'Hara, M. (2012).
  "Flow Toxicity and Liquidity in a High-frequency World"

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class VPINCalculator:
    """
    Calculate VPIN (Order Flow Toxicity)
    
    Example:
        >>> vpin_calc = VPINCalculator(bucket_size=50, window=50)
        >>> vpin = vpin_calc.calculate(prices, volumes)
        >>> print(f"VPIN: {vpin[-1]:.4f}")
    """
    
    def __init__(self, bucket_size: int = 50, window: int = 50):
        if bucket_size <= 0:
            raise ValueError(f"Bucket size must be > 0, got {bucket_size}")
        
        if window < 2:
            raise ValueError(f"Window must be >= 2, got {window}")
        
        self.bucket_size = bucket_size
        self.window = window
        
        logger.info(f"Initialized VPIN (bucket_size={bucket_size}, window={window})")
    
    def calculate(self, prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """
        Calculate VPIN time series
        
        Args:
            prices: Array of trade prices
            volumes: Array of trade volumes
        
        Returns:
            Array of VPIN values (0-1)
        """
        if len(prices) != len(volumes):
            raise ValueError("Prices and volumes must have same length")
        
        buy_volume, sell_volume = self._classify_volume(prices, volumes)
        
        buckets = self._create_buckets(buy_volume, sell_volume, volumes)
        
        vpin = self._calculate_vpin_from_buckets(buckets)
        
        return vpin
    
    def _classify_volume(self, prices: np.ndarray, volumes: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Classify volume as buy/sell using tick rule"""
        price_change = np.diff(prices, prepend=prices[0])
        
        classification = np.zeros(len(prices))
        classification[price_change > 0] = 1  # Buy
        classification[price_change < 0] = -1  # Sell
        
        # Forward fill for zero changes
        for i in range(1, len(classification)):
            if classification[i] == 0:
                classification[i] = classification[i-1]
        
        buy_volume = volumes * (classification == 1)
        sell_volume = volumes * (classification == -1)
        
        return buy_volume, sell_volume
    
    def _create_buckets(self, buy_volume: np.ndarray, sell_volume: np.ndarray, 
                        total_volume: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create volume buckets"""
        cumulative_volume = np.cumsum(total_volume)
        bucket_indices = (cumulative_volume // self.bucket_size).astype(int)
        
        buy_buckets = []
        sell_buckets = []
        
        for bucket_idx in range(bucket_indices.max() + 1):
            mask = bucket_indices == bucket_idx
            buy_buckets.append(buy_volume[mask].sum())
            sell_buckets.append(sell_volume[mask].sum())
        
        return np.array(buy_buckets), np.array(sell_buckets)
    
    def _calculate_vpin_from_buckets(self, buckets: Tuple[np.ndarray, np.ndarray]) -> np.ndarray:
        """Calculate VPIN from buckets"""
        buy_buckets, sell_buckets = buckets
        
        total_volume = buy_buckets + sell_buckets
        imbalance = np.abs(buy_buckets - sell_buckets)
        
        normalized_imbalance = np.where(
            total_volume > 0,
            imbalance / total_volume,
            0.0
        )
        
        vpin = pd.Series(normalized_imbalance).rolling(
            window=self.window,
            min_periods=1
        ).mean().values
        
        return vpin
```

---

## ✅ VERIFICACIÓN

Después de copiar todos los archivos:

```bash
cd Atlas/python

# Verificar imports
python -c "from atlas.data_layer import get_data; print('✅ data_layer')"
python -c "from atlas.market_state import RegimeDetector; print('✅ market_state')"
python -c "from atlas.core_intelligence.features.microstructure.vpin import VPINCalculator; print('✅ vpin')"

# Correr tests
pytest tests/unit/ -v
```

**Esperado:** 10+ tests passing ✅

---

**Copyright © 2026 M&C. All Rights Reserved.**
