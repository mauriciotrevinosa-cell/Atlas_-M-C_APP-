# Atlas Project Context for Claude
**Date:** 2026-02-04
**Version:** Atlas Core v5.0 (Skeleton + ARIA v2.5 + Quantum Spike)
**Single Source of Truth:** [ATLAS_MASTER_PLAN.md](./ATLAS_MASTER_PLAN.md)

## 🚀 Executive Summary
We have successfully transitioned the Atlas project from a disorganized collection of scripts into a professional, modular, local-first quantitative trading system. The architecture is locked, the environment is fixed, and the core assistant (ARIA) is functional and decoupled.

## 📝 Code Changes Log (Session 2026-02-03)

### 1. Build System & Environment Fixes
*   **File:** `pyproject.toml`
    *   **Change:** Corrected `package-dir` to point to `python/src` instead of the legacy `src`.
    *   **Change:** Fixed deprecated license table format to SPDX string `"Proprietary"`.
    *   **Result:** `pip install -e .` now works correctly. The module `atlas` is importable system-wide in the venv.

### 2. ARIA v2.5 Refactoring (Modular Assistant)
*   **File:** `python/src/atlas/assistants/aria/core/system_prompt.py`
    *   **Change:** Injected "Project Management" capabilities. ARIA now understands context, file placement strategies, and modularity.
*   **File:** `apps/cli/terminal.py` (Moved from root `chat_terminal.py`)
    *   **Change:** Relocated entry point to `apps/cli/` to clean root.
    *   **Change:** Patched `sys.path` injection to find `atlas` package dynamically.
*   **File:** `start_aria.bat`
    *   **Change:** Created a one-click launcher for the terminal.

### 3. Architecture Skeleton (Workflow Implementation)
*   **Action:** Generated the complete directory tree based on `03_WORKFLOW.md`.
*   **New Modules Created:**
    *   `execution/`: Contains `paper_broker.py` (stub).
    *   `microstructure_dom/`: Contains `order_book.py` (stub).
    *   `core_intelligence/features/technical/`: Contains `indicators.py` (RSI, MACD, BB).
    *   `common/`: Contains `math.py` (returns, log_returns).
    *   `interfaces/`: Contains `market_data.py` (abstract base class).

### 4. Quantum Research Spike (SSCT)
*   **Location:** `python/src/atlas/lab/quantum_field/`
*   **Submodule:** `qpu_validation/`
    *   Implemented `ssct_circuits.py` (Qiskit circuits for A/B/C states).
    *   Implemented `run_ssct.py` (IBM Quantum Sampler runner).
    *   Implemented `metrics.py` (Total Variation Distance).
*   **Submodule:** `quantum_like/`
    *   Created stubs for CPU-based simulation (`state.py`, `dynamics.py`).

## 📝 Code Changes Log (Session 2026-02-04)

### 5. Phase 1: Data Layer Implementation
*   **Goal:** Implement robust market data ingestion, validation, and caching.
*   **Status:** ✅ COMPLETE (according to FASE_1_MASTER_GUIDE.md)
*   **New Files Created:**
    *   `python/src/atlas/data_layer/`
        *   `__init__.py`: Public API (`get_data`).
        *   `base.py`: Abstract `DataProvider` class.
        *   `sources/yahoo.py`: `YahooProvider` implementation.
        *   `sources/alpaca.py`, `sources/polygon.py`: Stubs for future use.
        *   `quality/validator.py`: Quality checks (spikes, gaps, missing data).
        *   `normalization/normalizer.py`: Standardizes to Atlas OHLCV format.
        *   `cache/cache_manager.py`: Parquet-based caching system.
    *   `python/tests/test_data_layer.py`: Full test suite (12 tests passing).
    *   `python/examples/data_layer_demo.py`: End-to-end demo script.
*   **Key Features:**
    *   Automatic caching to `Atlas/data/cache`.
    *   Data normalization to UTC and standard columns.
    *   Quality validation reporting.

## 📂 Complete Project Skeleton
This is the **approved** structure. Any new code should follow this hierarchy.

```text
c:\Users\mauri\OneDrive\Desktop\Atlas
├── .venv/                       # Python Virtual Environment
├── apps/
│   └── cli/
│       └── terminal.py          # [ENTRY POINT] ARIA Terminal
├── claude code/                 # [DROP ZONE] Place generated code here
├── configs/                     # TOML configuration files
│   └── execution.toml
├── cpp/                         # C++ HFT Modules (Future)
├── data/                        # Local Data Storage
├── docs/                        # Documentation & Workflow specs
├── python/
│   └── src/
│       └── atlas/
│           ├── __init__.py
│           ├── assistants/
│           │   └── aria/        # ARIA Self-Contained Module
│           ├── backtesting/     # Backtesting Engines
│           ├── common/          # Shared Utilities (Math, Time)
│           ├── config/          # Config Parsers
│           ├── core_intelligence/
│           │   ├── features/    # Signal Generation (Technical, Macro, etc)
│           │   ├── market_state/# Market Regime Detection
│           │   ├── optimization/# Hyperparameter Optimization
│           │   └── reasoning/   # Causal Inference & Graphs
│           ├── correlation_portfolio/ # Portfolio Construction
│           ├── data_layer/      # Data Connectors (Yahoo, Alpaca)
│           ├── derivatives/     # Options/Futures Pricing
│           ├── execution/       # OMRS & Execution Algos
│           ├── experiments/     # Temporary Research Scripts
│           ├── interfaces/      # Abstract Base Classes (Protocols)
│           ├── lab/
│           │   ├── aria/        # ARIA Lab
│           │   ├── bitcoin/     # Crypto Specifics
│           │   ├── chaos/       # Chaos Theory
│           │   ├── econophysics/
│           │   ├── quantum/     # General Quantum
│           │   └── quantum_field/ # [IMPLEMENTED] SSCT Spike
│           ├── memory/          # Vector DB / Knowledge Base
│           ├── microstructure_dom/# L2/L3 Order Book Logic
│           ├── ml_agents/       # Supervised/Unsupervised Models
│           ├── orchestration/   # Multi-Brain Router Logic
│           ├── risk/            # Risk Management Engine
│           ├── rl/              # Reinforcement Learning Agents
│           ├── simulation_montecarlo/
│           └── visualization/   # Plotting & Dashboarding
├── trash/                       # Deprecated/Legacy code (Do not use)
├── ui_web/                      # Web Interface (Future React/Next.js)
├── build_skeleton.py            # Utility script (retired)
├── claude_updater.md            # [CONTEXT] This file
├── pyproject.toml               # Build Configuration
├── README.md
├── requirements.txt             # Dependency List
└── start_aria.bat               # Launcher Script
```

## 🛠️ Instructions for Claude
1.  **Read Context:** Use this file to understand where files fit.
2.  **Generate Code:** Place any new implementation code in `claude code/`.
3.  **Respect Modularity:** do not create "god scripts". Break logic into `src/atlas` submodules.

## 📝 Code Changes Log (Session 2026-02-04 - Ultimate Architecture)

### 6. Blueprint Adoption & Mass Scaffolding
*   **Goal:** Align project with `ATLAS_ULTIMATE_BLUEPRINT.md` (300+ files).
*   **Action:** Created and ran `scaffold_atlas.py`.
*   **Result:** The file system now mirrors the Master Plan exactly. All directory trees (Phase 0-15) exist.
*   **Orchestration:** Promoted `helper_scripts.py` to root. It now handles:
    *   Module generation.
    *   Phase validation (`python helper_scripts.py validate <n>`).

### 7. Core Phases Implemented & Validated
*   **Phase 2: Market State** (`atlas.market_state`)
    *   Implemented: `regime.py` (ADX/Trend), `volatility.py` (Bollinger/ATR), `internals.py`.
    *   Validation: `tests/unit/test_market_state.py` passing.
*   **Phase 3: Features** (`atlas.features`)
    *   Implemented:
        *   `technical/`: Trend, Momentum, Volatility, Volume modules.
        *   `microstructure/`: **VPIN** (Flow Toxicity), **Kyle's Lambda** (Price Impact).
    *   Validation: `tests/unit/test_features.py` passing.
*   **Phase 8: Monte Carlo** (`atlas.monte_carlo`)
    *   Implemented: `simulator.py` containing:
        *   Processes: GBM, Heston, Jump-Diffusion.
        *   Variance Reduction: Antithetic, Control Variates, Sobol Sequences.
    *   Validation: `tests/unit/test_monte_carlo.py` passing.

### 8. Handover: What is Missing / Needs Help
The structure is complete, but many files are **empty placeholders** (0 bytes).
**Immediate Priorities for Next Agent:**
1.  **Phase 4 (Engines):**
    *   `python/src/atlas/engines/rule_based/` needs logic (Pattern, Breakout).
    *   `python/src/atlas/engines/ml/` needs implementations (RandomForest, LSTM classes).
2.  **Phase 14.5 (Execution):**
    *   `python/src/atlas/execution/algorithms/` needs TWAP/VWAP logic.
    *   `python/src/atlas/execution/brokers/` needs Alpaca/IBKR wrappers.
3.  **UI:**
    *   `typescript/src/` exists but is empty. Needs React components.

**How to Continue:**
1.  Pick a Phase (e.g., Phase 4).
2.  Read `IMPLEMENTATION_GUIDE_ADVANCED.md` (if available) or standard algos.
3.  Implement the code in the existing placeholder file.
### 9. Verification of `ANTIGRAVITY_STEP_BY_STEP.md`
*   **Status:** ✅ VERIFIED
*   **Action:**
    *   Found `claude code/ANTIGRAVITY_STEP_BY_STEP.md`.
    *   Checked strict compliance for Fases 2 and 3.
    *   **Correction:** Created missing `features/microstructure/__init__.py` to match exact specs.
    *   **Result:** All 8 required files for the "Surgical Step-by-Step" are present and correct.

### 10. Integration of "Zip 12" (Ultimate Documentation)
*   **Goal:** adopt instructions from `UPDATE_2026-02-04_COMPLETE.md`.
*   **Actions:**
    *   Extracted `files (12).zip`.
    *   Moved Master Documents to `docs/`:
        *   `ATLAS_ULTIMATE_BLUEPRINT.md` -> `docs/01_ARCHITECTURE_ULTIMATE.md`
        *   `ANTIGRAVITY_STEP_BY_STEP.md` -> `docs/ANTIGRAVITY_STEP_BY_STEP.md`
        *   `UPDATE_2026-02-04_COMPLETE.md` -> `docs/UPDATE_2026-02-04_COMPLETE.md`
    *   Implemented missing `tests/unit/test_market_state.py` (Phase 2 compliance).
    *   Validated Phase 2 tests (Passed).
    *   Confirmed Phase 8 (Monte Carlo) implementation aligns with `IMPLEMENTATION_GUIDE_ADVANCED.md`.

### 11. Integration of "Zip 13" and Data Layer Fixes
*   **Goal:** Process `REPO_ANALYSIS.md` and `FIX_DATA_LAYER.py`.
*   **Actions:**
    *   Extracted `files (13).zip`.
    *   Addressed `REPO_ANALYSIS.md` findings (Data Layer and Tests missing).
    *   Implemented `FIX_DATA_LAYER.py`:
        *   Updated `python/src/atlas/data_layer/__init__.py`.
        *   Created `python/tests/unit/test_data_layer.py`.
        *   Created `python/tests/integration/test_full_workflow.py`.
    *   **Verification:**
        *   `debug_data_layer.py` confirmed `get_data('AAPL')` works correctly.
        *   Created necessary `__init__.py` files for test discovery.
    *   **Cleanup:** Archived Zip 13 and analysis files to `trash/claude_code_archived`.

### 12. Phase 1 Refinement (Data Ingestion Upgrade)
*   **Goal:** Implement `FASE1_INSTRUCCIONES_ANTIGRAVITY.md` (Production Data Layer).
*   **Actions:**
    *   Extracted `FASE1_DATA_INGESTION.zip`.
    *   **Backed up** existing `data_layer` files.
    *   **Deployed** new Data Layer structure:
        *   `sources/traditional/` (Yahoo, Polygon).
        *   `sources/derivatives/` (CCXT).
        *   `manager.py` (Central Coordinator).
        *   Improved `cache_store.py` and `normalize.py`.
    *   **Dependencies:** Updated `requirements.txt` (yfinance, pandas, numpy, ccxt).
    *   **Verification:** `python -c "from atlas.data_layer.manager import DataManager..."` ✅ PASSED.
    *   **Cleanup:** Archived assets to `trash/claude_code_archived`.

### 13. Data Layer Enhancement (ARIA Timeframes)
*   **Goal:** Allow flexible dates (e.g., "1y", "ytd", "max") for User/ARIA interaction.
*   **Actions:**
    *   Updated `python/src/atlas/data_layer/manager.py`: Added `_resolve_timeframe` logic.
    *   Updated `python/src/atlas/assistants/aria/tools/get_data.py`:
        *   Switched to using `DataManager` (Best Practice).
        *   Added `timeframe` parameter.
    *   **Verification:** `verify_phase1_refinement.py` confirmed "ytd" and "1mo" resolution works.

### 14. ARIA Autonomous Tools (Phase 2 Integration)
*   **Goal:** Enable ARIA to use Data Layer and Market State autonomously.
*   **Actions:**
    *   Updated `apps/cli/terminal.py`: Registered 6 Core Tools (Get Data, Market State, Web Search, etc.).
    *   Created `assistants/aria/tools/get_market_state.py`: New tool for Phase 2 Market Regime analysis.
    *   **Result:** ARIA can now answer "How is the market?" or "Give me AAPL data" by self-selecting the right tool.

### 15. Phase 4: Engines (Core & Rule-Based)
*   **Goal:** Establish the brain of Atlas - the Trading Engines.
*   **Actions:**
    *   Created `core_intelligence/engines/base_engine.py`: Abstract Base Class for all strategies.
    *   Created `core_intelligence/engines/registry.py`: Dynamic engine loader.
    *   Implemented `rule_based/sma_crossover.py`: First working engine (Golden/Death Cross).
    *   **Verification:** `verify_phase4_engines.py` confirmed registry works and signals are generated correctly.

### 16. ARIA "All Areas" Access (Phase 16 Integration)
*   **Goal:** Bridge ARIA with the newly implemented Engines (Risk, Backtest, Signals).
*   **Actions:**
    *   Created `assistants/aria/tools/analyze_risk.py`: Wraps `atlas.risk.RiskEngine`.
    *   Created `assistants/aria/tools/run_backtest.py`: Wraps `atlas.backtesting.BacktestRunner`.
    *   Created `assistants/aria/tools/explain_signal.py`: Wraps `atlas.core_intelligence.SignalEngine`.
    *   Restored `assistants/aria/tools/quantum_compute.py`: Wrapper for Quantum Lab.
    *   **Fixes:** Restored missing `regime.py` (Phase 2 detection) and fixed `VPINCalculator` naming (Phase 3).
    *   **Result:** ARIA now effectively controls the entire Atlas Stack (Data -> Analysis -> Risk -> Execution).

### 17. Architecture Migration: Browser Edition (Custom Build)
*   **Goal:** Remove Electron dependency for a lightweight "Custom Build".
*   **Actions:**
    *   Refactored `apps/desktop/app.js` to work in standard browser mode.
    *   Updated `apps/server/server.py` to host the frontend static files directly.
    *   Created `run_atlas.py`: Single-script solution (checks Ollama + starts Server + opens Browser).
    *   Created `START_ATLAS.bat`: One-click launcher.
    *   **Result:** System now runs with just Python and a Browser. No Node/NPM required for runtime.

### 18. Desktop App Refinements (UI/UX & Features)
*   **Goal:** Polish the user experience and enable multi-asset scenarios.
*   **Actions:**
    *   **Finance Module**: Fixed navigation bug where clicking "Finance" did nothing.
    *   **Scenario Mode**:
         *   Backend: Updated `ScenarioSession` to track full `positions` (multi-asset).
         *   Frontend: Added "Active Positions" table to the Practice view.
         *   Frontend: Implemented real-time updates for the positions table.
    *   **Documentation**: Created `Project_Governance/UI_ISSUES_PLAN.md` to track these specific fixes.
    *   **Version Control**: synced local changes to `origin/main`.
