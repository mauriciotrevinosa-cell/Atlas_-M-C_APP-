# 📦 ATLAS — C++ CORE + 3D VISUALIZATIONS

**Generado por:** Claude (Arquitecto/Constructor)  
**Fecha:** 2026-02-08

---

## 🎯 QUÉ CONTIENE

### A) C++ High-Performance Core (Fases 16-17)
Header-only C++ engines listos para compilar:

| Componente | Archivo | Qué hace |
|-----------|---------|----------|
| **Order Book** | `orderbook.hpp` | L2 order book con O(log n) updates, mid price, spread, VWAP, imbalance |
| **Signal Engine** | `signal_engine.hpp` | Streaming RSI, MACD, Bollinger, ATR, EWMA, trade flow imbalance |
| **Execution** | `execution_engine.hpp` | TWAP/VWAP con nanosecond timing, slippage tracking |
| **Python Bindings** | `bindings.cpp` | pybind11 bridge — usa C++ desde Python |
| **Build System** | `CMakeLists.txt` | CMake build config |

### B) 3D Visualizations (Fase 12 expanded)

| Componente | Archivo | Qué genera |
|-----------|---------|------------|
| **Static 3D** | `renderer_3d.py` | PNG images via matplotlib (6 render types) |
| **Interactive 3D** | `interactive_3d.py` | Standalone HTML con Three.js (drag, rotate, zoom) |

---

## 📋 MAPA DE ARCHIVOS → DESTINOS

### C++ Core
| Archivo | Destino |
|---------|---------|
| `cpp_core/orderbook/orderbook.hpp` | `cpp/include/atlas/orderbook.hpp` |
| `cpp_core/signals/signal_engine.hpp` | `cpp/include/atlas/signal_engine.hpp` |
| `cpp_core/execution/execution_engine.hpp` | `cpp/include/atlas/execution_engine.hpp` |
| `cpp_core/bindings.cpp` | `cpp/src/bindings.cpp` |
| `cpp_core/CMakeLists.txt` | `cpp/CMakeLists.txt` |

### 3D Visualizations
| Archivo | Destino |
|---------|---------|
| `viz_3d/renderer_3d.py` | `python/src/atlas/visualization/renderer_3d.py` |
| `viz_3d/interactive_3d.py` | `python/src/atlas/visualization/interactive_3d.py` |

---

## 📝 INSTRUCCIONES

### C++ Setup

```bash
# Crear estructura
mkdir -p cpp/include/atlas cpp/src

# Copiar headers y source según tabla

# Build (requiere pybind11 y cmake)
cd cpp
pip install pybind11
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j4

# El resultado es atlas_cpp.so que se importa desde Python:
# import atlas_cpp
# book = atlas_cpp.OrderBook("BTCUSD")
```

### Build alternativo (sin CMake)
```bash
c++ -O3 -Wall -shared -std=c++17 -fPIC \
    $(python3 -m pybind11 --includes) \
    -I cpp/include \
    cpp/src/bindings.cpp \
    -o atlas_cpp$(python3-config --extension-suffix)
```

### 3D Visualization Setup

```bash
# Copiar archivos según tabla
# Agregar a visualization/__init__.py:
```
```python
from atlas.visualization.renderer_3d import Atlas3DRenderer
from atlas.visualization.interactive_3d import Interactive3DRenderer
```

### Test 3D
```python
from atlas.visualization.renderer_3d import Atlas3DRenderer
from atlas.visualization.interactive_3d import Interactive3DRenderer
import numpy as np

# Static 3D
r = Atlas3DRenderer()
strikes = np.linspace(80, 120, 20)
expiries = np.linspace(7, 365, 15)
iv = 0.2 + 0.1 * np.sin(np.outer(strikes/100, expiries/180))
r.volatility_surface(strikes, expiries, iv)
print("✅ Static vol surface saved")

# Interactive 3D
ir = Interactive3DRenderer()
ir.volatility_surface(strikes, expiries, iv)
print("✅ Interactive HTML saved — open in browser")
```

---

## 🔗 RENDERS DISPONIBLES

### Static (matplotlib → PNG)
1. **Volatility Surface** — Strike × Expiry × IV
2. **Correlation Mountain** — Asset × Asset × ρ
3. **P&L Surface** — Parameter sweep landscapes
4. **Monte Carlo Mountain** — Price density over time
5. **Risk Landscape** — VaR across allocation/scenarios
6. **Order Book Depth 3D** — Depth evolving over time

### Interactive (Three.js → HTML)
1. **Volatility Surface** — Drag/rotate/zoom
2. **Correlation Mountain** — Bar columns colored by ρ
3. **Monte Carlo Mountain** — Density bars over time

---

## ⚠️ NOTAS

1. **C++ es header-only** excepto `bindings.cpp`. No necesita compilar para que Python funcione — C++ es acelerador opcional.
2. **3D interactivo** genera HTMLs auto-contenidos. Three.js se carga desde CDN (necesita internet la primera vez).
3. **Static 3D** usa matplotlib `Agg` backend — funciona sin display.
4. Si no hay pybind11 instalado, el C++ no se compila pero **nada se rompe** — Python sigue funcionando.
