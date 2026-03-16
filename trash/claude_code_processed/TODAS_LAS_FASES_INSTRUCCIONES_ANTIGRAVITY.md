# 📦 ATLAS — PAQUETE COMPLETO: Todas las Fases Pendientes

**Generado por:** Claude (Arquitecto/Constructor)  
**Para:** Antigravity (Organizador)  
**Fecha:** 2026-02-06  
**Versión:** 1.0  

---

## 🎯 QUÉ CONTIENE ESTE PAQUETE

Todos los archivos necesarios para completar las fases pendientes del workflow v3.0.
Cada archivo es código de producción, no stubs. Listo para colocar y funcionar.

---

## 📋 MAPA DE ARCHIVOS → DESTINOS

### FASE 2 — Completar Derivatives Sentiment
| Archivo en paquete | Destino en repo |
|---|---|
| `fase2/funding_sentiment.py` | `python/src/atlas/core_intelligence/market_state/derivatives_sentiment/funding_sentiment.py` |
| `fase2/oi_conviction.py` | `python/src/atlas/core_intelligence/market_state/derivatives_sentiment/oi_conviction.py` |
| `fase2/derivatives_sentiment__init__.py` | `python/src/atlas/core_intelligence/market_state/derivatives_sentiment/__init__.py` ← **REEMPLAZAR** |

### FASE 3.8 — Derivatives Features
| Archivo en paquete | Destino en repo |
|---|---|
| `fase3/liquidation_zones.py` | `python/src/atlas/core_intelligence/features/derivatives/liquidation_zones.py` |
| `fase3/funding_analysis.py` | `python/src/atlas/core_intelligence/features/derivatives/funding_analysis.py` |
| `fase3/oi_analysis.py` | `python/src/atlas/core_intelligence/features/derivatives/oi_analysis.py` |
| `fase3/lsr_analysis.py` | `python/src/atlas/core_intelligence/features/derivatives/lsr_analysis.py` |
| `fase3/derivatives_features__init__.py` | `python/src/atlas/core_intelligence/features/derivatives/__init__.py` ← **REEMPLAZAR** |

### FASE 5 — Signal Composition
| Archivo en paquete | Destino en repo |
|---|---|
| `fase5/signal_engine.py` | `python/src/atlas/core_intelligence/signal_engine.py` ← **REEMPLAZAR** |

Contiene: `Signal`, `DynamicWeights`, `ConflictResolver`, `SignalEngine`

### FASE 6 — Discrepancy Analysis
| Archivo en paquete | Destino en repo |
|---|---|
| `fase6/discrepancy_analyzer.py` | `python/src/atlas/discrepancy_analysis/discrepancy_analyzer.py` |

### FASE 7 — Risk & Fragility (COMPLETO)
| Archivo en paquete | Destino en repo |
|---|---|
| `fase7/risk_engine.py` | `python/src/atlas/risk/risk_engine.py` |

Contiene: `PositionSizer`, `VaRCalculator`, `DrawdownController`, `KillSwitch`, `LiquidationRiskManager`, `RiskEngine` (facade)

### FASE 9 — Orchestration
| Archivo en paquete | Destino en repo |
|---|---|
| `fase9/orchestrator.py` | `python/src/atlas/orchestration/orchestrator.py` |

### FASE 10 — Memory & Calibration
| Archivo en paquete | Destino en repo |
|---|---|
| `fase10/memory_system.py` | `python/src/atlas/memory/memory_system.py` |

Contiene: `ExperienceStore`, `CalibrationEngine`

### FASE 11 — Backtesting
| Archivo en paquete | Destino en repo |
|---|---|
| `fase11/backtest_engine.py` | `python/src/atlas/backtesting/backtest_engine.py` |

Contiene: `Trade`, `BacktestMetrics`, `BacktestRunner`

### FASE 14.5 — Execution
| Archivo en paquete | Destino en repo |
|---|---|
| `fase14_5/execution_engine.py` | `python/src/atlas/execution/execution_engine.py` |

Contiene: `Order`, `BaseBroker`, `PaperBroker`, `TWAPExecutor`, `VWAPExecutor`

### FASE 15 — Post-Trade
| Archivo en paquete | Destino en repo |
|---|---|
| `fase15/post_trade.py` | `python/src/atlas/post_trade/post_trade.py` |

Si no existe la carpeta `post_trade/`, crearla con `__init__.py`.

---

## 📝 INSTRUCCIONES PASO A PASO

### PASO 1: Backup
```bash
cd python/src/atlas/
# Backup files that will be replaced
cp core_intelligence/signal_engine.py core_intelligence/signal_engine.py.bak
cp core_intelligence/market_state/derivatives_sentiment/__init__.py core_intelligence/market_state/derivatives_sentiment/__init__.py.bak
cp core_intelligence/features/derivatives/__init__.py core_intelligence/features/derivatives/__init__.py.bak
```

### PASO 2: Crear carpetas que no existan
```bash
mkdir -p discrepancy_analysis
mkdir -p post_trade
# Crear __init__.py en carpetas nuevas
echo '"""Discrepancy Analysis"""' > discrepancy_analysis/__init__.py
echo '"""Post-Trade Analytics"""' > post_trade/__init__.py
```

### PASO 3: Copiar archivos
Seguir la tabla de arriba. Cada archivo del paquete va a su destino exacto.

**IMPORTANTE:** Los archivos con sufijo `__init__` en su nombre (como `derivatives_sentiment__init__.py`) se renombran a `__init__.py` en destino.

### PASO 4: Actualizar `__init__.py` de módulos existentes

**`risk/__init__.py`** — agregar:
```python
from atlas.risk.risk_engine import RiskEngine, PositionSizer, VaRCalculator
```

**`orchestration/__init__.py`** — agregar:
```python
from atlas.orchestration.orchestrator import Orchestrator
```

**`memory/__init__.py`** — agregar:
```python
from atlas.memory.memory_system import ExperienceStore, CalibrationEngine
```

**`backtesting/__init__.py`** — agregar:
```python
from atlas.backtesting.backtest_engine import BacktestRunner, BacktestMetrics
```

**`execution/__init__.py`** — agregar:
```python
from atlas.execution.execution_engine import PaperBroker, TWAPExecutor, VWAPExecutor
```

### PASO 5: Verificar imports
```bash
cd python/src/atlas
python -c "
from atlas.core_intelligence.market_state.derivatives_sentiment import FundingSentiment, OIConviction
from atlas.core_intelligence.features.derivatives import LiquidationZones, FundingAnalysis, OIAnalysis, LSRAnalysis
from atlas.core_intelligence.signal_engine import SignalEngine, Signal
from atlas.discrepancy_analysis.discrepancy_analyzer import DiscrepancyAnalyzer
from atlas.risk.risk_engine import RiskEngine
from atlas.orchestration.orchestrator import Orchestrator
from atlas.memory.memory_system import ExperienceStore, CalibrationEngine
from atlas.backtesting.backtest_engine import BacktestRunner
from atlas.execution.execution_engine import PaperBroker, TWAPExecutor, VWAPExecutor
from atlas.post_trade.post_trade import TradeJournal, PerformanceAnalytics
print('✅ ALL IMPORTS OK — Proyecto completo')
"
```

### PASO 6: Actualizar requirements.txt
Agregar si no existe:
```
scipy>=1.10.0
```
(Para VaR parametric en risk_engine.py)

---

## 🔗 DEPENDENCIAS ENTRE FASES

```
FASE 1 (Data) ──→ FASE 2 (Market State) ──→ FASE 3 (Features)
                                                    │
                                                    ↓
FASE 4 (Engines) ──→ FASE 5 (Signal Composition) ──→ FASE 6 (Discrepancy)
                                                    │
                                                    ↓
                    FASE 7 (Risk) ←── FASE 8 (Monte Carlo)
                         │
                         ↓
                    FASE 9 (Orchestration) ──→ FASE 10 (Memory)
                         │
                         ↓
                    FASE 11 (Backtest)
                         │
                         ↓
                    FASE 14.5 (Execution) ──→ FASE 15 (Post-Trade)
```

---

## ⚠️ NOTAS

1. **FASE 3.5 (Chaos & Nonlinear)** y **FASE 12 (Visualization)** y **FASE 14 (User Decision UI)** NO están en este paquete — son Tier 2/3 y dependen de UI web
2. **FASE 7 risk_engine.py** usa `scipy.stats.norm` para VaR paramétrico. Si scipy no está instalado, el método `parametric_var` fallará (el rest funciona)
3. **FASE 10 memory_system.py** usa JSONL para almacenamiento. Eventualmente migrará a vector DB pero esto funciona para MVP
4. **FASE 14.5 PaperBroker** es simulado — para brokers reales (Alpaca/IBKR) se necesitan wrappers adicionales que hereden de `BaseBroker`

---

## ✅ CRITERIOS DE COMPLETITUD

El proyecto se considera funcionalmente completo cuando:
- [ ] Todos los imports del PASO 5 funcionan sin error
- [ ] `DataManager` puede obtener datos
- [ ] `SignalEngine` puede componer signals de múltiples fuentes
- [ ] `RiskEngine` puede evaluar si es seguro operar
- [ ] `BacktestRunner` puede ejecutar un backtest simple
- [ ] `PaperBroker` puede simular ejecución

---

**Generado:** 2026-02-06 por Claude (Arquitecto)  
**Estado post-entrega:** ~85% del workflow v3.0 implementado
