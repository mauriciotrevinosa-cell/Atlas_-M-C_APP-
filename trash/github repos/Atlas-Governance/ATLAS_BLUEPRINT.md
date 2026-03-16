# 🧠 ATLAS BLUEPRINT OPERATIVO — ULTRA DESGLOSADO (v1)

**Origen:** Definición canónica (Chat/PDF).
**Propósito:** Definición quirúrgica de componentes, archivos y estados.
**Regla:** Nada es abstracto. Todo termina en código, datos o decisiones.

---

## 🟥 FASE 0 — FUNDACIÓN ABSOLUTA
**Estado:** ✅ COMPLETO (Estructuralmente) / ⚠️ Parcial (Archivos config)

### 0.1 Estructura de Proyecto
- **Qué es:** Skeleton del repo.
- **Qué hace:** Define límites mentales y técnicos.
- **Uso:** Todos los módulos viven aquí.
- **Consume:** Todo.

### 0.2 Configuración Global
- **Archivos:**
    - `configs/settings.toml` (Central flags, paths)
    - `.env` (Secrets)
    - `configs/logging.yaml` (Log definition)
- **Qué hace:** Centraliza configuración, evita hardcoding.
- **Consume:** Core, Services, UI.

### 0.3 Sistema de Logging
- **Archivos:**
    - `logs/app.log`
    - `logs/errors.log`
    - `logs/metrics.log`
- **Qué hace:** Traza decisiones, auditoría.

---

## 🟧 FASE 1 — DATA LAYER
**Estado:** ✅ FUNCIONAL (Yahoo) / ⚠️ Parcial (Normalization) / ❌ Pendiente (Cache)

### 1.1 Market Data Provider
#### 1.1.1 Yahoo Finance Client
- **Archivo:** `python/src/atlas/data_layer/sources/traditional/yfinance_client.py` (Ref: `yahoo.py`)
- **Qué hace:** OHLCV, Timeframes.
- **Uso:** Base para todo análisis.

### 1.2 Normalización de Datos
- **Archivo:** `python/src/atlas/data_layer/normalize.py`
- **Qué hace:** Limpia NaNs, alinea timeframes.

### 1.3 Cache de Datos
- **Archivo:** `python/src/atlas/data_layer/cache_store.py`
- **Qué hace:** Evita redescargas, reduce latencia.

---

## 🟨 FASE 2 — INDICATOR REGISTRY (EL CORAZÓN MATEMÁTICO)
**Estado:** ⏳ En Progreso

### 📈 TREND
- **2.1 SMA:** `indicators/trend/sma.py`
- **2.2 EMA:** `indicators/trend/ema.py`
- **2.3 WMA:** `indicators/trend/wma.py`

### ⚡ MOMENTUM
- **2.4 RSI:** `indicators/momentum/rsi.py`
- **2.5 MACD:** `indicators/momentum/macd.py`
- **2.6 Stochastic:** `indicators/momentum/stoch.py`

### 🌪️ VOLATILITY
- **2.7 ATR:** `indicators/volatility/atr.py`
- **2.8 BB:** `indicators/volatility/bb.py`

### 📊 VOLUME
- **2.9 Vol:** `indicators/volume/vol.py`
- **2.10 OBV:** `indicators/volume/obv.py`

### 🧱 LEVELS
- **2.11 S/R:** `indicators/levels/support_resistance.py`
- **2.12 VWAP:** `indicators/levels/vwap.py`

---

## 🟩 FASE 3 — PATTERN RECOGNITION
**Estado:** ⏳ Pendiente

- **3.1 Candlestick:** Doji, Engulfing (`indicators/patterns/candles.py`)
- **3.2 Market Structure:** HH/HL, BOS (`indicators/patterns/structure.py`)

---

## 🟦 FASE 4 — SIGNAL ENGINE
**Estado:** ❌ Pendiente

- **4.1 Engine:** `python/src/atlas/core_intelligence/signal_engine.py`
- **4.2 Dynamic Weights:** `python/src/atlas/core_intelligence/dynamic_weights.py`

---

## 🟪 FASE 5 — PROBABILITY ENGINE
**Estado:** ⏳ Pendiente

- **5.1 Engine:** `python/src/atlas/core_intelligence/prob_engine.py`
- **Output:** `{ bullish: 0.62, bearish: 0.21, neutral: 0.17 }`

---

## 🧪 FASE 6 — BACKTESTING
**Estado:** ❌ Pendiente

- **6.1 Runner:** `python/src/atlas/backtesting/runner.py`
- **6.2 Metrics:** `python/src/atlas/backtesting/metrics.py` (Sharpe, Drawdown)

---

## 🧠 FASE 7 — MEMORY & CALIBRATION
**Estado:** ❌ Pendiente

- **7.1 Store:** `python/src/atlas/memory/store.py`
- **7.2 Calibration:** `python/src/atlas/memory/calibration.py`

---

## 🤖 FASE 8 — ARIA (AI ASSISTANT)
**Estado:** ⏳ Funcional (v2.5)

- **8.1 Query Router:** `python/src/atlas/assistants/aria/router.py`
- **8.2 Explainability:** `python/src/atlas/assistants/aria/explain.py`
- **8.3 Permissions:** `python/src/atlas/assistants/aria/permissions.py`

---

# 📸 INVENTARIO COMPLETO (CANÓNICO)
*Basado en análisis visual y requerimientos.*

### 1️⃣ CONCEPTOS FUNDAMENTALES (MENTAL MODEL)
- Market State, Features, Signals, Confidence, Explainability, One Engine Rule, User-in-Control.

### 2️⃣ DATA & INGESTA
- Yahoo Finance, DOM Data, Microstructure, Data Quality.

### 3️⃣ MARKET MICROSTRUCTURE
- DOM, Order Ladder, Liquidity Imbalance, Absorption, Slippage.

### 4️⃣ FEATURE ENGINEERING
- Tech Indicators, Trend, Momentum, Volatility, Correlation, Portfolio Topology.

### 5️⃣ CORRELATION & PORTFOLIO
- Matrix, Rolling Correlation, Clustering, Crowding Detection.

### 6️⃣ SIGNAL & DECISION LOGIC
- Rule-Based, Aggregation, Dynamic Weights, Conflict Resolution.

### 7️⃣ REASONING
- Decision Trees, Reasoning Graphs, Rulesets.

### 8️⃣ OPTIMIZATION
- Gradient Descent, Loss Functions, Surfaces.

### 9️⃣ MACHINE LEARNING
- SVM, Clustering, PCA, Validation, Model Cards.

### 🔟 REINFORCEMENT LEARNING
- Environments, Agents, Reward Design, Safety.

### 11️⃣ SIMULATION & MONTE CARLO
- Price Paths, Stress Scenarios, Risk Envelopes.

### 12️⃣ RISK & FRAGILITY
- Position Sizing, VaR/CVaR, Drawdown Control, Kill Switches.

### 13️⃣ MEMORY & CALIBRATION
- Experience Store, Calibration Memory, Audit.

### 14️⃣ BACKTESTING
- Unified Engine, Multi-Run, Parameter Sweeps.

### 15️⃣ ORCHESTRATION
- Engine Registry, Discrepancy Analysis.

### 16️⃣ VISUALIZATION
- Render Store, Monte Carlo Viz, DOM Viz.

### 17️⃣ UI / BRAIN VIEWER
- Runs Explorer, Detail View, Time Travel.

### 18️⃣ ASSISTANTS
- Explain, Compare, Summarize.

### 19️⃣ CRYPTO SPECIALS
- On-Chain, Funding Rates (Derivatives).

### 20️⃣ RESEARCH
- Notebooks, Papers.

### 21️⃣ INFRA
- API, Workers, CLI, Configs.
