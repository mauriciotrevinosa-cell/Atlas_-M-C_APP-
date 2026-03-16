# 🧭 PROJECT ATLAS — WORKFLOW v4.0

**Última Actualización:** 2026-02-08  
**Versión:** 4.0 (Added ML/RL, Auto-Trader, C++ Core, 3D Viz)

---

## 🎯 CHANGELOG v3.0 → v4.0

### **AGREGADO:**
- ✅ ML Engine Suite (XGBoost, LSTM, RandomForest)
- ✅ RL Trading Agent (DQN + Gym Environment)
- ✅ Auto-Trader Hybrid System (4 operating modes)
- ✅ C++ High-Performance Core (Order Book, Signals, Execution)
- ✅ 3D Visualizations (Vol Surface, Correlation Mountain, MC Mountain)
- ✅ ARIA Math Toolset (27 financial calculations + code executor)
- ✅ Point-in-Time Manager (no look-ahead bias)
- ✅ Run Context System (reproducible runs)

---

## 📊 WORKFLOW COMPLETO (20 FASES)

```
FASE 0    → Fundación                          ✅ COMPLETE
FASE 1    → Data Ingestion                     ✅ COMPLETE (Yahoo)
  1.2     → Derivatives data                   ⬜ NEEDS API KEYS
  1.3     → Point-in-Time Manager              ✅ GENERATED (in ZIP)
FASE 2    → Market State                       ✅ COMPLETE (Regime, Vol)
  2.3     → Derivatives Sentiment              ⬜ NEEDS DATA SOURCES
FASE 3    → Feature Extraction                 ✅ COMPLETE
  3.1     → Technical Indicators               ✅ IN REPO
  3.2     → Microstructure (VPIN, Kyle)        ✅ IN REPO
  3.3     → Candlestick Patterns               ✅ GENERATED (in ZIP)
  3.8     → Derivatives Features               ⬜ NEEDS DATA SOURCES
FASE 3.5  → Chaos & Nonlinear                  ⬜ FUTURE
FASE 4    → Specialized Engines                ✅ PARTIAL
  4.1     → Rule-Based (SMA Crossover)         ✅ IN REPO
  4.2     → ML Engines (XGB, LSTM, RF)         ✅ GENERATED (in ZIP)
  4.3     → RL Agent (DQN)                     ✅ GENERATED (in ZIP)
FASE 5    → Signal Composition                 ✅ BASIC IN REPO
FASE 6    → Discrepancy Analysis               ⬜ FUTURE
FASE 7    → Risk & Fragility                   ✅ GENERATED (in ZIP)
  7.1     → VaR/CVaR, Stress Testing           ✅ GENERATED
  7.5     → Liquidation Risk                   ⬜ NEEDS DERIV DATA
FASE 8    → Monte Carlo                        ✅ COMPLETE
  8.1     → GBM, Heston, Jump-Diffusion        ✅ IN REPO
  8.2     → Dynamic Correlation                ✅ GENERATED (in ZIP)
FASE 9    → Orchestration / Auto-Trader        ✅ GENERATED (in ZIP)
  9.1     → Multi-Engine Consensus             ✅ GENERATED
  9.2     → GuardRails                         ✅ GENERATED
  9.3     → 4 Operating Modes                  ✅ GENERATED
FASE 10   → Memory                             ✅ BASIC IN REPO
FASE 11   → Backtest                           ✅ BASIC IN REPO
FASE 12   → Visualization                      ✅ GENERATED (in ZIP)
  12.1    → 2D Charts (matplotlib)             ✅ GENERATED
  12.2    → 3D Static (matplotlib 3D)          ✅ GENERATED
  12.3    → 3D Interactive (Three.js HTML)     ✅ GENERATED
  12.4    → Derivatives Dashboard              ⬜ NEEDS UI WORK
FASE 13   → ARIA                               ✅ FUNCTIONAL
  13.1    → Chat + Tool Calling                ✅ IN REPO
  13.2    → Math Toolset (27 tools)            ✅ GENERATED (in ZIP)
  13.3    → Code Executor                      ✅ GENERATED (in ZIP)
FASE 14   → User Decision                      ✅ BASIC IN REPO
FASE 14.5 → Execution                          ✅ PARTIAL
  14.5.1  → Paper Broker                       ✅ IN REPO
  14.5.2  → C++ TWAP/VWAP                     ✅ GENERATED (in ZIP)
FASE 15   → Post-Trade                         ⬜ FUTURE
FASE 16   → C++ HFT Core                       ✅ GENERATED (in ZIP)
  16.1    → Order Book Engine                  ✅ GENERATED
  16.2    → Signal Engine (streaming)          ✅ GENERATED
  16.3    → pybind11 Bridge                    ✅ GENERATED
```

---

## 🤖 FASE 9 — AUTO-TRADER (NEW)

### Architecture

```
              ┌──────────────┐
              │  HUMAN INPUT │
              │  (override)  │
              └──────┬───────┘
                     │
┌──────────┐  ┌──────▼───────┐  ┌─────────────┐
│  RULES   │─▶│              │◀─│  ML ENGINES  │
│(SMA, RSI)│  │  AUTO-TRADER │  │(XGB,LSTM,RF) │
└──────────┘  │  (consensus) │  └─────────────┘
              │              │
┌──────────┐  │  GuardRails  │  ┌─────────────┐
│ RL AGENT │─▶│  ↓           │  │   RISK      │
│  (DQN)   │  │  Decision    │─▶│   ENGINE    │
└──────────┘  │  ↓           │  └─────────────┘
              │  Execute?    │
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │  EXECUTION   │
              │ (TWAP/VWAP)  │
              └──────────────┘
```

### Operating Modes

| Mode | Decision | Execution | When to Use |
|------|----------|-----------|-------------|
| **MANUAL** | Human | Human | Learning, research |
| **ADVISORY** | Atlas recommends | Human approves | Building trust |
| **SEMI_AUTO** | Atlas (>75% conf auto) | Atlas + guardrails | Proven strategies |
| **FULL_AUTO** | Atlas | Atlas + guardrails | Paper trading / tested |

### GuardRails (ALWAYS active, even in FULL_AUTO)

| Rule | Default | Configurable |
|------|---------|-------------|
| Max position size | 10% of capital | Yes |
| Max daily loss | 2% | Yes |
| Max drawdown | 10% | Yes |
| Max trades/day | 20 | Yes |
| Min confidence | 60% | Yes |
| Max leverage | 1x | Yes |

---

## 🧠 FASE 4.2 — ML ENGINES (NEW)

### Models Available

| Engine | Type | Input | Best For |
|--------|------|-------|---------|
| **XGBoost** | Gradient Boosted Trees | Tabular features | Structured data, fast training |
| **RandomForest** | Ensemble Trees | Tabular features | Baseline, feature importance |
| **LSTM** | Recurrent Neural Network | Sequences | Sequential patterns, temporal |

### Feature Pipeline
Automatic feature generation from OHLCV:
- Returns (1d, 5d, 10d, 20d)
- Volatility (5d, 10d, 20d rolling)
- Volume ratios and changes
- Price position (high-low range, close position)
- SMA distances (5, 10, 20, 50)
- RSI (14), MACD, Bollinger %B

### Label Types
- `direction`: Binary (up/down in horizon)
- `return`: Actual forward return
- `triple`: -1/0/1 based on volatility threshold

---

## 🎮 FASE 4.3 — RL AGENT (NEW)

### Environment
- **State:** Features + [position, unrealized_PnL, capital%, step%]
- **Actions:** HOLD(0), BUY(1), SELL(2), CLOSE(3)
- **Reward:** Risk-adjusted PnL (Sharpe or Sortino aware)

### Agent (DQN)
- 3-layer fully connected network
- Experience replay (50K buffer)
- Target network (updated every 10 steps)
- Epsilon-greedy decay (1.0 → 0.01)
- Minimum 100 episodes training recommended

---

## 📊 FASE 12 — VISUALIZATION (EXPANDED)

### 2D Charts (matplotlib Agg)
1. Correlation heatmap
2. Monte Carlo fan (percentile bands)
3. Drawdown chart
4. PnL distribution (histogram + VaR lines)

### 3D Static (matplotlib 3D → PNG)
1. Volatility Surface (strike × expiry × IV)
2. Correlation Mountain (asset × asset × ρ)
3. P&L Surface (parameter sweeps)
4. Monte Carlo Mountain (density over time)
5. Risk Landscape (VaR across allocations)
6. Order Book Depth 3D (depth over time)

### 3D Interactive (Three.js → standalone HTML)
1. Volatility Surface (drag/rotate/zoom)
2. Correlation Mountain (colored bars)
3. Monte Carlo Mountain (density bars)

---

## 🎯 INTEGRATION PRIORITY

### Tier 1: CRITICAL (integrate first)
1. `ATLAS_WORKFLOW_V3_GAPS.zip` — Fills 90% of empty modules
2. `ATLAS_ML_RL_AUTOTRADER.zip` — Enables AI trading

### Tier 2: HIGH (integrate next)
3. `ATLAS_CPP_AND_3D.zip` — Enables 3D viz + future HFT
4. `ARIA_MATH_TOOLS.zip` — Enhances ARIA capabilities

### Tier 3: AFTER INTEGRATION
5. Wire auto_trader to connect all engines
6. Train ML models on historical data
7. Train RL agent on paper trading environment
8. Derivatives data sources (needs API keys)
9. Full web UI (React/Next.js)

---

**Workflow v4.0 — Completado**  
**Última Actualización:** 2026-02-08  
**Próxima Revisión:** After ZIP integration complete
