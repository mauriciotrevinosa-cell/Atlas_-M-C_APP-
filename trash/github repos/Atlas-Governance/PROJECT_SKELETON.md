# 🦴 ATLAS PROJECT SKELETON

This document defines the **Physical Structure** of the project. It serves as the map for where files must reside.
**Rule:** Every file must have a specific place. If you are unsure, check `ATLAS_MASTER_PLAN.md` or ask the Project Manager (ARIA).

## 📂 Root Directory (`Atlas/`)

```text
Atlas/
├── apps/                        # Application Entry Points
│   └── cli/                     # ARIA Command Line Interface & Terminal
├── configs/                     # Global Configuration Files (.toml)
├── data/                        # Local Data Storage (Do NOT commit large files)
│   ├── cache/                   # HDF5/Parquet fast access storage
│   └── universes/               # Asset Universe definitions (JSON/CSV)
├── docs/                        # Project Documentation
├── logs/                        # System Logs
├── python/                      # Main Python Codebase
│   └── src/
│       └── atlas/               # Root Package
│           ├── assistants/      # AI & Agent Logic (ARIA)
│           │   └── aria/
│           ├── backtesting/     # [PHASE 11] Engines for testing strategies
│           ├── common/          # Shared Utilities (Math, Dates, Logging)
│           ├── config/          # Configuration Loaders & Validators
│           ├── core_intelligence/ # Advanced Analysis
│           │   ├── features/
│           │   │   ├── technical/    # Indicators (RSI, MAS, etc.)
│           │   │   ├── microstructure/# Order Flow, Liquidity
│           │   │   └── derivatives/  # Funding Rates, Open Interest
│           │   ├── market_state/     # Regime Detection
│           │   └── reasoning/        # AI Inference Logic
│           ├── correlation_portfolio/ # Portfolio Level Logic
│           ├── data_layer/      # [PHASE 1] Data Ingestion & Handling
│           │   ├── sources/     # Connectors (Yahoo, Binace, etc.)
│           │   ├── cache.py
│           │   └── data_handler.py
│           ├── derivatives/     # [PHASE 12] Dashboard Specific Logic
│           ├── execution/       # [PHASE 14.5] Order Management System (OMS)
│           ├── interfaces/      # Abstract Base Classes (Protocols)
│           ├── lab/             # Exprimental / Research Spikes
│           │   └── quantum_field/
│           ├── microstructure_dom/ # Depth of Market Analysis
│           ├── orchestration/   # [PHASE 9] System Router
│           ├── risk/            # [PHASE 7] Risk Management Modules
│           ├── strategies/      # [PHASE 4] Trading Strategies
│           └── ui_web/          # [PHASE 12] Web Frontend Components
├── scripts/                     # DevOps & specific task scripts
├── tests/                       # Unit and Integration Tests
├── .gitignore
├── pyproject.toml               # Python Dependencies & Build Config
└── README.md
```

## 📍 Key Locations Guide

| Component | Path | Purpose |
| :--- | :--- | :--- |
| **ARIA Brain** | `atlas/assistants/aria/` | Where the AI logic lives. |
| **Indicators** | `atlas/core_intelligence/features/technical/` | Implement new technical indicators here. |
| **Data Sources** | `atlas/data_layer/sources/` | precise implementations for fetching data. |
| **Strategies** | `atlas/strategies/` | Trading logic and algos. |
| **Notebooks** | `lab/` | For Jupyter notebooks and messy research. |

---
**Note:** This skeleton is enforced by the Project Governance. Any deviation must be approved via ADR.
