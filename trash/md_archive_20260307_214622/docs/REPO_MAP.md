# ATLAS Repository Map (Source of Truth)

Last updated: 2026-03-02

## 1. Core Folders (for active development)

- `apps/`: runtime applications and launchers.
- `configs/`: shared configuration files.
- `cpp/`: C++ components and bindings.
- `data/`: local data/cache/renders used by Atlas.
- `docs/`: canonical project documentation.
- `python/src/atlas/`: Python source of truth (data, analytics, sim, risk, ARIA).
- `services/`: system/service integrations.
- `tests/`: active test suite.
- `ui_web/`: web UI assets.
- `outputs/runs/`: per-run artifacts and manifests.

## 2. Temporary / Non-Core Folders

These folders are allowed for staging/archive only and should not host long-term production code:

- `info_instructions/`
- `project_governance/`
- `trash/`
- `.claude/`
- `.clone/`

Rule: if a document/file is retired from `docs/`, move it to `trash/` (do not hard-delete).

## 3. Entrypoints

- `python run_atlas.py`: browser launcher (default behavior).
- `python run_atlas.py --demo`: one-command official Phase 1 workflow demo.
- `python scripts/run_phase1_demo.py`: direct Phase 1 CLI runner.
- `python run_aria.py`: ARIA terminal with Phase 1 tool registry enabled.

## 4. Dependency Source of Truth

- **Primary source of truth:** `pyproject.toml`
- `requirements.txt` is compatibility-only and intentionally points to editable install (`-e .`).

## 5. Path-Naming Policy (CI/import friendly)

- No spaces in names inside core folders listed in section 1.
- Path compliance check:

```powershell
python scripts/check_core_paths.py
```

## 6. Official Phase 1 Workflow Location

Canonical implementation lives in:

- `python/src/atlas/market_finance/data_layer.py`
- `python/src/atlas/market_finance/analytics_layer.py`
- `python/src/atlas/market_finance/simulation_layer.py`
- `python/src/atlas/market_finance/risk_layer.py`
- `python/src/atlas/market_finance/pipeline.py`

Each run writes:

- `outputs/runs/<run_id>/manifest.json`
- `outputs/runs/<run_id>/logs/events.jsonl`
- stage artifacts under `data/`, `analytics/`, `simulation/`, `risk/`
