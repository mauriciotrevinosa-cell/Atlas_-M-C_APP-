# Atlas Simulation Pipeline

## Overview
This pipeline implements a visual, end-to-end flow:

1. Analysis modules compute state each tick.
2. Modules publish typed artifacts to a central event bus.
3. Event bus writes artifacts to the registry (single source of truth).
4. UI reads artifacts from the registry and renders by artifact type.

Analysis modules never import UI code.

## Artifact Flow
`AnalysisModule.on_tick(...)` -> `EventBus.publish(artifact)` -> `ArtifactRegistry.publish(...)` -> optional `SQLiteArtifactStore.save(...)` -> `ui/simulation_dashboard.py` reads from registry.

## Core Components
- `python/src/atlas/core/analytics/artifacts.py`
  - `ArtifactType`: `TIMESERIES`, `HISTOGRAM`, `TABLE`, `SCALAR`, `EVENT`, `LOG`
  - `Artifact`, `ArtifactFilter`, `AuditRecord`
- `python/src/atlas/core/engine/artifact_registry.py`
  - in-memory cache, `get_latest`, `get_history`, `get_audit_trail`, error event query
- `python/src/atlas/core/engine/event_bus.py`
  - publish/subscribe with optional filters
- `python/src/atlas/core/engine/simulation_runner.py`
  - scheduled tick loop for selected modules
- `python/src/atlas/services/storage/artifact_store.py`
  - optional sqlite persistence (`SQLiteArtifactStore`)
- `python/src/atlas/ui/simulation_dashboard.py`
  - module visibility toggles (open/closed), timeline, error stream, generic artifact renderers

## Demo Modules
- `python/src/atlas/core/analytics/modules/market_state.py`
  - histogram: regime probabilities
  - scalar: risk score
  - timeseries/log/event artifacts
- `python/src/atlas/core/analytics/modules/commodity_concentration.py`
  - scalar gauge: concentration HHI
  - table: commodity weights
  - timeseries/log/event artifacts

## Run
1. Install dependencies:
```bash
pip install -r requirements.txt
pip install streamlit
```
2. Set source path:
```bash
set PYTHONPATH=python/src
```
3. Start dashboard:
```bash
streamlit run python/src/atlas/ui/simulation_dashboard.py
```

`ATLAS_SIM_ARTIFACT_DB` can override sqlite path (default: `data/simulation_artifacts.db`).

## Validate
Run focused tests:
```bash
set PYTHONPATH=python/src
pytest tests/unit/test_artifact_schema.py tests/unit/test_eventbus_publish_subscribe.py tests/unit/test_simulation_runner_tick.py -q
```

## Add a New Analysis Module
1. Create a class under `python/src/atlas/core/analytics/modules/` implementing `AnalysisModule`.
2. In `on_tick`, publish artifacts with valid `ArtifactType` payload contracts.
3. Add the module instance to runtime setup in `python/src/atlas/ui/simulation_dashboard.py`.
4. No UI-specific code is required in the module; dashboard rendering is type-driven.
5. Add/extend unit tests for schema + publish behavior.

