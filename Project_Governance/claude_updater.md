# Atlas Project Context for Claude
**Date:** 2026-02-03
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
