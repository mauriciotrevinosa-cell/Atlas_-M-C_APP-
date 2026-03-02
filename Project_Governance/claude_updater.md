# Atlas Project Context for Claude
**Date:** 2026-02-08
**Version:** Atlas Core v6.0 (Full Backend + ARIA Tools + ML/RL + C++)
**Single Source of Truth:** [ATLAS_MASTER_PLAN.md](./ATLAS_MASTER_PLAN.md)

## 🚀 Executive Summary
Atlas has evolved from a skeleton into a near-complete quantitative trading backend. ARIA is functional with tool calling. The core analytical pipeline (data → indicators → signals → backtest) runs end-to-end. Multiple delivery packages have been generated covering all remaining phases. Integration is in progress.

---

## 📝 Code Changes Log (Sessions 2026-02-03 through 2026-02-04)

### 1. Build System & Environment Fixes
*   **File:** `pyproject.toml` — Corrected `package-dir`, fixed license format.
*   **Result:** `pip install -e .` works. `atlas` importable system-wide.

### 2. ARIA v2.5 Refactoring
*   System prompt with Project Management capabilities.
*   Terminal moved to `apps/cli/terminal.py`.
*   `start_aria.bat` one-click launcher.

### 3. Architecture Skeleton
*   Full directory tree (Phases 0-15) generated.
*   Stubs: `execution/paper_broker.py`, `microstructure_dom/order_book.py`, `indicators.py`, `common/math.py`.

### 4. Quantum Research Spike (SSCT)
*   `lab/quantum_field/qpu_validation/` — Qiskit circuits, IBM Quantum runner, TVD metrics.

### 5. Phase 1: Data Layer
*   `data_layer/` — YahooProvider, quality validator, normalizer, cache manager, DataManager.
*   Flexible timeframes ("1y", "ytd", "max").
*   12 tests passing.

### 6-8. Scaffold + Phases 2, 3, 8
*   Phase 2: `market_state/regime.py` (ADX), `volatility.py` (BB/ATR).
*   Phase 3: `features/technical/`, `features/microstructure/` (VPIN, Kyle's Lambda).
*   Phase 8: `monte_carlo/simulator.py` (GBM, Heston, Jump-Diffusion, Antithetic, Sobol).

### 9-14. Data Layer Fixes + Phase 4 Engines + ARIA Integration
*   Phase 4: `engines/base_engine.py` (ABC), `registry.py`, `rule_based/sma_crossover.py`.
*   ARIA tools: `get_data`, `get_market_state`, `analyze_risk`, `run_backtest`, `explain_signal`, `quantum_compute`.
*   Browser edition: `run_atlas.py` (Python + Browser, no Node).

### 15-18. Desktop App + UI Fixes
*   Finance module navigation fix.
*   Scenario mode: multi-asset positions table.
*   All synced to git.

---

## 📝 Code Changes Log (Session 2026-02-08 — Claude Architect)

### 19. Workflow v3 Gap Analysis + Full Implementation
*   **Delivery:** `ATLAS_WORKFLOW_V3_GAPS.zip` (10 files)
*   **New Modules:**
    *   `context/run_context.py` — Run tracking with SHA256 run_id
    *   `data_layer/pit_manager.py` — Point-in-Time awareness (no look-ahead bias)
    *   `transforms/returns_volatility.py` — Returns (simple/log), Volatility (rolling/EWMA/Parkinson/Garman-Klass)
    *   `core_intelligence/features/technical/candlestick_engine.py` — 7 pattern types
    *   `correlation_portfolio/market_structure.py` — Correlation, Clustering (Ward), PCA
    *   `simulation_montecarlo/dynamic_corr_stress.py` — Dynamic correlation, 6 stress scenarios
    *   `correlation_portfolio/portfolio_engine.py` — Mean-Variance, Risk Parity, Equal Weight
    *   `derivatives/options_engine.py` — Vol Surface, Breeden-Litzenberger implied distribution
    *   `visualization/renderer.py` — 4 chart types (heatmap, MC fan, drawdown, PnL dist)
    *   `notebooks/trial_portfolio_simulation.py` — Full $100K simulation 2000-2024
*   **Status:** ⬜ AWAITING INTEGRATION INTO REPO

### 20. ARIA Mathematical Toolset
*   **Delivery:** `ARIA_MATH_TOOLS.zip` (5 files)
*   **New Modules:**
    *   `assistants/aria/tools/financial_math.py` — 27 financial functions (TVM, bonds, Black-Scholes, Greeks, VaR, OLS, CAPM, GBM sim)
    *   `assistants/aria/tools/code_executor/executor.py` — Sandboxed Python execution
    *   `assistants/aria/tools/registry.py` — Central tool registry with descriptions
*   **Status:** ⬜ AWAITING INTEGRATION INTO REPO

### 21. C++ High-Performance Core
*   **Delivery:** `ATLAS_CPP_AND_3D.zip` (8 files)
*   **New Modules:**
    *   `cpp/include/atlas/orderbook.hpp` — L2 order book (O(log n), VWAP, imbalance, nanosecond timing)
    *   `cpp/include/atlas/signal_engine.hpp` — Streaming RSI, MACD, Bollinger, ATR, EWMA, TradeFlowImbalance
    *   `cpp/include/atlas/execution_engine.hpp` — TWAP/VWAP with slice management
    *   `cpp/src/bindings.cpp` — pybind11 Python bridge
    *   `cpp/CMakeLists.txt` — Build system
*   **3D Visualizations:**
    *   `visualization/renderer_3d.py` — 6 matplotlib 3D renders (vol surface, correlation mountain, P&L surface, MC mountain, risk landscape, orderbook depth)
    *   `visualization/interactive_3d.py` — 3 Three.js HTML renders (drag/rotate/zoom)
*   **Status:** ⬜ AWAITING INTEGRATION INTO REPO

### 22. ML/RL + Auto-Trader
*   **Delivery:** `ATLAS_ML_RL_AUTOTRADER.zip` (3 files)
*   **New Modules:**
    *   `core_intelligence/engines/ml/ml_suite.py` — FeaturePipeline (~20 features from OHLCV), XGBoostEngine, RandomForestEngine, LSTMEngine (PyTorch)
    *   `core_intelligence/engines/rl/rl_trading_agent.py` — TradingEnvironment (Gym-style), DQNAgent (experience replay, target network), RLTrainer
    *   `auto_trader/auto_trader.py` — Hybrid system (Rules + ML + RL + Human), 4 modes (MANUAL/ADVISORY/SEMI_AUTO/FULL_AUTO), GuardRails (always active)
*   **Status:** ⬜ AWAITING INTEGRATION INTO REPO

---

## 📊 Current State Matrix

### What WORKS (in repo, tested):
| Component | Lines | Status |
|-----------|-------|--------|
| ARIA (chat, tools, validation, prompts) | ~4,000 | ✅ Functional |
| Indicators (RSI, MACD, BB, SMA, EMA, WMA, Stoch, ATR, OBV, VWAP) | ~300 | ✅ Functional |
| Signal Engine (combines indicators → signals) | 55 | ✅ Basic |
| Backtest Runner (vectorized) | 43 | ✅ Basic |
| Paper Broker | 60 | ✅ Functional |
| Data Layer (Yahoo, cache, normalize) | ~200 | ✅ Functional |
| test_full_chain.py (end-to-end) | 58 | ✅ Passes |
| Quantum Lab (SSCT) | ~100 | ✅ Spike |
| Desktop App (browser edition) | ~400 | ✅ Functional |

### What's in ZIPs (awaiting copy to repo):
| ZIP | Contents | Files | Lines |
|-----|----------|-------|-------|
| `ATLAS_WORKFLOW_V3_GAPS.zip` | PIT, returns, candles, PCA, portfolio, options, viz | 10 | ~2,000 |
| `ARIA_MATH_TOOLS.zip` | 27 math tools + code executor | 5 | ~800 |
| `ATLAS_CPP_AND_3D.zip` | C++ engines + 3D visualizations | 8 | ~2,500 |
| `ATLAS_ML_RL_AUTOTRADER.zip` | ML, RL, Auto-Trader | 3 | ~1,500 |
| **TOTAL** | | **26 files** | **~6,800 lines** |

### What's EMPTY (skeleton only):
| Module | Needs | From ZIP |
|--------|-------|----------|
| `risk/` | VaR, CVaR, stress tests | V3_GAPS |
| `correlation_portfolio/` | Correlation, clustering, PCA, portfolio optimizer | V3_GAPS |
| `simulation_montecarlo/` | Dynamic correlation, stress | V3_GAPS |
| `derivatives/` | Options engine, vol surface | V3_GAPS |
| `visualization/` | 2D + 3D renderers | V3_GAPS + CPP_3D |
| `ml_agents/` | XGBoost, LSTM, RandomForest | ML_RL |
| `rl/` | DQN agent, environment | ML_RL |
| `orchestration/` | Multi-engine router | Future |
| `discrepancy_analysis/` | Engine disagreement analysis | Future |

---

## 📂 Complete Project Skeleton

```text
Atlas/
├── apps/
│   └── cli/terminal.py              # [ENTRY POINT] ARIA Terminal
├── configs/                          # TOML configuration
├── cpp/                              # ⬜ C++ HFT (from ATLAS_CPP_AND_3D.zip)
│   ├── include/atlas/
│   │   ├── orderbook.hpp
│   │   ├── signal_engine.hpp
│   │   └── execution_engine.hpp
│   ├── src/bindings.cpp
│   └── CMakeLists.txt
├── data/                             # Local storage
├── python/src/atlas/
│   ├── assistants/aria/              # ✅ ARIA complete
│   │   └── tools/                    # ⬜ Add financial_math.py, registry.py, code_executor/
│   ├── auto_trader/                  # ⬜ From ML_RL zip
│   │   └── auto_trader.py
│   ├── backtesting/runner.py         # ✅ Basic
│   ├── common/math.py               # ✅
│   ├── context/run_context.py        # ⬜ From V3_GAPS zip
│   ├── core_intelligence/
│   │   ├── engines/
│   │   │   ├── ml/ml_suite.py        # ⬜ From ML_RL zip
│   │   │   └── rl/rl_trading_agent.py # ⬜ From ML_RL zip
│   │   ├── features/technical/       # ✅ indicators.py
│   │   └── signal_engine.py          # ✅ Basic
│   ├── correlation_portfolio/        # ⬜ From V3_GAPS zip
│   ├── data_layer/                   # ✅ Functional
│   ├── derivatives/                  # ⬜ From V3_GAPS zip
│   ├── execution/brokers/            # ✅ paper_broker.py
│   ├── indicators/                   # ✅ Full registry
│   ├── lab/quantum_field/            # ✅ SSCT
│   ├── risk/                         # ⬜ From V3_GAPS zip
│   ├── simulation_montecarlo/        # ⬜ From V3_GAPS zip
│   ├── transforms/                   # ⬜ From V3_GAPS zip
│   └── visualization/               # ⬜ From V3_GAPS + CPP_3D zips
├── ui_web/                           # ✅ Browser edition
└── requirements.txt
```

---

## 🛠️ Instructions for Any AI Agent

### To Integrate Pending ZIPs:
1. Extract each ZIP
2. Copy files to destinations listed in each ZIP's `INSTRUCCIONES.md`
3. Create any missing `__init__.py` files
4. Install dependencies: `pip install scipy matplotlib xgboost torch scikit-learn pybind11`
5. Run verification commands from each instruction doc
6. Run `test_full_chain.py` to confirm nothing broke

### To Add New Code:
1. Read this file first
2. Check which module the code belongs to
3. Follow existing patterns (ABC base classes, registry pattern)
4. Place code in correct location per skeleton above
5. Update this file's changelog

### Priority Order:
1. **Integrate V3_GAPS** (fills most empty modules)
2. **Integrate ML_RL** (enables AI trading)
3. **Integrate CPP_3D** (enables 3D viz + future HFT)
4. **Integrate ARIA_MATH_TOOLS** (enhances ARIA capabilities)
5. **Wire everything together** (auto_trader connects ML+RL+Rules)
