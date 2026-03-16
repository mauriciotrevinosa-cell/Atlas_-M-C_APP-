# 📦 ATLAS — ML ENGINES + RL AGENT + AUTO-TRADER

**Generado por:** Claude (Arquitecto/Constructor)  
**Fecha:** 2026-02-08

---

## 🎯 QUÉ CONTIENE

El stack completo para que Atlas pase de sistema analítico a **híbrido humano-AI autónomo**.

### 3 Componentes

| Componente | Archivo | Qué es |
|-----------|---------|--------|
| **ML Engines** | `ml_suite.py` | LSTM (PyTorch), XGBoost, RandomForest + FeaturePipeline |
| **RL Agent** | `rl_trading_agent.py` | Trading Environment (Gym-style) + DQN Agent + Trainer |
| **Auto-Trader** | `auto_trader.py` | Hybrid decision system: Rules + ML + RL + Human override |

---

## 📋 DESTINOS

| Archivo | Destino |
|---------|---------|
| `ml_engines/ml_suite.py` | `python/src/atlas/core_intelligence/engines/ml/ml_suite.py` |
| `rl_agent/rl_trading_agent.py` | `python/src/atlas/core_intelligence/engines/rl/rl_trading_agent.py` |
| `auto_trader/auto_trader.py` | `python/src/atlas/auto_trader/auto_trader.py` |

---

## 📝 INSTRUCCIONES

### PASO 1: Crear carpetas
```bash
cd python/src/atlas/
mkdir -p core_intelligence/engines/ml
mkdir -p core_intelligence/engines/rl
mkdir -p auto_trader
```

### PASO 2: `__init__.py`
```bash
echo '"ML Engines"' > core_intelligence/engines/ml/__init__.py
echo '"RL Agent"' > core_intelligence/engines/rl/__init__.py
echo '"Auto-Trader"
from atlas.auto_trader.auto_trader import AutoTrader, TradingMode, GuardRails
' > auto_trader/__init__.py
```

### PASO 3: Copiar archivos

### PASO 4: Dependencias
```
torch>=2.0.0        # Para LSTM y DQN
xgboost>=1.7.0      # Para XGBoost engine
scikit-learn>=1.2.0  # Para RandomForest
```

### PASO 5: Verificar
```python
python -c "
from atlas.core_intelligence.engines.ml.ml_suite import XGBoostEngine, RandomForestEngine, LSTMEngine, FeaturePipeline
from atlas.core_intelligence.engines.rl.rl_trading_agent import TradingEnvironment, DQNAgent, RLTrainer
from atlas.auto_trader.auto_trader import AutoTrader, TradingMode, GuardRails
print('✅ ML + RL + AutoTrader loaded')
"
```

---

## 🔗 CÓMO SE INTEGRA AL WORKFLOW

```
                    ┌──────────────┐
                    │  HUMAN INPUT │
                    │  (override)  │
                    └──────┬───────┘
                           │
    ┌──────────┐    ┌──────▼───────┐    ┌─────────────┐
    │  RULES   │───▶│              │◀───│  ML ENGINES  │
    │ (SMA,RSI)│    │  AUTO-TRADER │    │(XGB,LSTM,RF) │
    └──────────┘    │  (consensus) │    └─────────────┘
                    │              │
    ┌──────────┐    │  GuardRails  │    ┌─────────────┐
    │ RL AGENT │───▶│  ↓           │    │   RISK      │
    │  (DQN)   │    │  Decision    │───▶│   ENGINE    │
    └──────────┘    │  ↓           │    └─────────────┘
                    │  Execute?    │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  EXECUTION   │
                    │ (TWAP/VWAP)  │
                    └──────────────┘
```

### 4 Operating Modes:

| Mode | Quién decide | Quién ejecuta |
|------|-------------|---------------|
| **MANUAL** | Humano | Humano |
| **ADVISORY** | Atlas recomienda | Humano aprueba |
| **SEMI_AUTO** | Atlas (>75% confidence auto) | Atlas (con guardrails) |
| **FULL_AUTO** | Atlas | Atlas (con guardrails + kill switch) |

---

## 🔒 GUARDRAILS (siempre activos)

Estos limits **NUNCA** se pueden violar, ni en FULL_AUTO:

| Guardrail | Default |
|-----------|---------|
| Max position size | 10% del capital |
| Max daily loss | 2% |
| Max drawdown | 10% |
| Max trades/day | 20 |
| Min confidence | 60% |
| Max leverage | 1x |

---

## 💡 USO RÁPIDO

### Entrenar ML
```python
from atlas.core_intelligence.engines.ml.ml_suite import XGBoostEngine, FeaturePipeline

pipeline = FeaturePipeline(lookback=20, forecast_horizon=5)
X, y, feature_names = pipeline.prepare(ohlcv_df, label_method="direction")

engine = XGBoostEngine()
metrics = engine.train(X, y)
print(metrics)  # {"train_accuracy": 0.58, "val_accuracy": 0.54}

predictions = engine.predict(X[-10:])
```

### Entrenar RL Agent
```python
from atlas.core_intelligence.engines.rl.rl_trading_agent import (
    TradingEnvironment, DQNAgent, RLTrainer
)

env = TradingEnvironment(features, prices, reward_type="sharpe")
agent = DQNAgent(state_size=env.observation_size)
trainer = RLTrainer(env, agent)

stats = trainer.train(n_episodes=200)
eval_results = trainer.evaluate(n_episodes=10)
print(eval_results)  # {"mean_pnl": 1250, "win_rate": 0.6}
```

### Auto-Trader
```python
from atlas.auto_trader.auto_trader import AutoTrader, TradingMode, GuardRails, Decision

trader = AutoTrader(mode=TradingMode.ADVISORY)

# Register sources
trader.register_source("rules", my_rules_fn, weight=0.2)
trader.register_source("ml_xgboost", my_xgb_fn, weight=0.3)
trader.register_source("rl_agent", my_rl_fn, weight=0.3)

# Run decision
result = trader.decide("AAPL", features, portfolio_state)
# → {"consensus": {"action": "buy", "confidence": 0.72}, "guardrails": {"approved": True}}
```

---

## ⚠️ NOTAS

1. **PyTorch es requerido** para LSTM y DQN. Sin él, XGBoost y RandomForest siguen funcionando.
2. **El RL agent necesita entrenamiento** — no es plug-and-play. Mínimo 100 episodios para resultados decentes.
3. **FULL_AUTO mode** debería usarse solo con paper trading primero. Los guardrails son la última línea de defensa.
4. **FeaturePipeline** genera ~20 features estándar. Se puede extender con features de Atlas (derivatives, microstructure, etc.).
