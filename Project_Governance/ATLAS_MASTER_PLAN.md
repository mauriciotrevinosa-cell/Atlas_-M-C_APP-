# 🗺️ ATLAS MASTER PLAN — v5.0

**Status:** ACTIVE
**Last Updated:** 2026-02-03
**Identity:** Local-First, Modular Quantitative Trading System with Autonomous AI (ARIA).
**Blueprint:** [ATLAS_BLUEPRINT.md](./ATLAS_BLUEPRINT.md) (Operational Detail)

---

## 📅 TIMELINE & PROGRESS

### 🕰️ HISTORY (Context)
- [x] **2024-Q1:** Project Chronos initiated (TradingView/PineScript).
- [x] **2025-Q4:** Decision to migrate to Python + Architecture Research.
- [x] **2026-01-30:** Official Atlas Birth (Foundation Phase).
- [x] **2026-02-01:** ARIA Conception (Local LLM Decision - ADR-003).

### ✅ COMPLETED (Recent)
- [x] **2026-01-30:** Workflow v3.0 Definition (Derivatives added).
- [x] **2026-02-02:** Successful ARIA & Tool Calling Integration (Session 2).
- [x] **2026-02-03:**
    - [x] **Skeleton Generation:** Full directory structure (Phases 0-15) created.
    - [x] **ARIA v3.0:** 100% Complete (Memory, Voice, Intelligence, Analysis, Integrations).
    - [x] **Quantum Spike:** SSCT implemented in `lab/quantum_field`.
    - [x] **Environment Fix:** `pyproject.toml` corrected, build system stable.

### 🚧 IN PROGRESS
- [ ] **Phase 1: Data Layer Upgrade** (Inspired by Qlib)
    - [ ] `AtlasDataHandler` implementation.
    - [ ] Multi-level Cache (Memory/Disk).
    - [ ] Universe Management.
- [ ] **Phase 1.2: Derivatives Data**
    - [ ] CoinGlass/Hyperliquid Connectors.
    - [ ] Liquidation Heatmaps.

### 🔮 FUTURE (ROADMAP)
- [ ] **Phase 2:** Factor Library (20+ indicators).
- [ ] **Phase 3:** Strategy Framework.
- [ ] **Phase 4:** Backtesting Engine (Qlib style).
- [ ] **Phase 9:** Multi-Brain Orchestration (Router).
- [ ] **Phase 14:** Web UI (Derivatives Dashboard).

---

## 📂 MASTER SKELETON (The Truth)

This structure must be strictly followed.

```text
Atlas/
├── apps/
│   └── cli/                 # ARIA Terminal
├── configs/                 # TOML Configs
├── data/                    # Local Storage
│   ├── cache/               # HDF5/Parquet Cache
│   └── universes/           # Asset Lists
├── python/
│   └── src/
│       └── atlas/
│           ├── assistants/
│           │   └── aria/    # AI Logic
│           ├── backtesting/ # [PHASE 11]
│           ├── common/      # Math, Dates
│           ├── config/      # Settings
│           ├── core_intelligence/
│           │   ├── features/
│           │   │   ├── technical/   # RSI, MACD
│           │   │   ├── microstructure/# L2, Order Flow
│           │   │   └── derivatives/ # [NEW] Funding, OI, Liquidations
│           │   ├── market_state/
│           │   │   └── derivatives_sentiment/ # [NEW]
│           │   └── reasoning/
│           ├── correlation_portfolio/
│           ├── data_layer/  # [PHASE 1]
│           │   ├── sources/
│           │   │   ├── traditional/ # Yahoo, Alpaca
│           │   │   └── derivatives/ # [NEW] CoinGlass, Hyperliquid
│           │   ├── cache.py         # Multi-level Cache
│           │   └── data_handler.py  # Abstraction
│           ├── derivatives/ # [PHASE 12] Dashboard Logic
│           │   └── dashboard_metrics/
│           ├── execution/   # [PHASE 14.5]
│           ├── interfaces/  # Protocols
│           ├── lab/         # Research Spikes
│           │   └── quantum_field/ # SSCT
│           ├── microstructure_dom/
│           ├── orchestration/ # [PHASE 9]
│           ├── risk/        # [PHASE 7]
│           │   └── liquidation_risk/ # [NEW]
│           └── strategies/  # [PHASE 4]
│               ├── base.py
│               └── registry.py
├── ui_web/                  # [PHASE 12] React/Next.js
└── requirements.txt
```

---

## ⚙️ WORKFLOW PHASES (v3.0 INTEGRATED)

### FASE 0: Fundación
- **Objetivo:** Entorno estable, imports funcionando, ARIA operativa.
- **Estado:** ✅ Completado.

### FASE 1: Data Ingestion
- **1.1 Traditional:** OHLCV (Yahoo/Alpaca).
- **1.2 Derivatives:** Liquidations, OI, Funding Rates.
- **Priority:** HIGH.

### FASE 2: Market State
- **2.1 Regime:** Trend vs Range.
- **2.2 Volatility:** GARCH/HV.
- **2.3 Derivatives Sentiment:** Funding divergence, OI/Price divergence.

### FASE 3: Feature Extraction
- **3.1 Technical:** Standard indicators (Migrated).
- **3.2 Microstructure:** Order Book Imbalance.
- **3.8 Derivatives:** Liquidation Clusters, Funding Reversals.

### FASE 7: Risk Management
- **7.1 Position Sizing:** Kelly, Volatility Target.
- **7.5 Liquidation Risk:** Avoid clusters, safe leverage calc.

### FASE 12: Visualization
- **12.3 Derivatives Dashboard:** React Based (Heatmaps, Gauges).

---

## 🧠 CONVENTIONS & RULES (The Constitution)

1.  **Local First:** No dependency on external cloud services unless needed for data.
2.  **Privacy:** User data never leaves the machine.
3.  **Modularity:** `aria` can exist without `atlas`. `data_layer` can exist without `strategies`.
4.  **No "Spaghetti Code":** Use the `interfaces` definitions.
5.  **Documentation:** Update this Master Plan if architectural changes occur.
