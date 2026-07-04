# Atlas — As-Built Architecture

> This document describes what the code **actually does today**, derived only
> from source, configs, and runtime behavior (not from vision/roadmap docs).
> Written during the 2026-07 cleanup audit. Keep it factual; update it when the
> code changes.

## Entry points

| Launch | File | What it does |
|---|---|---|
| Primary (Windows) | `START_ATLAS.bat` | Menu → runs `run_atlas.py` (option 1) or `run_daemon.py` (option 2, auto-restart) |
| App bootstrap | `run_atlas.py` | Configures rotating logs, adds `python/src` to path, builds `ui_web` if stale, constructs the `ARIA` assistant, registers tools, then `uvicorn.run(server.app)` |
| 24/7 wrapper | `run_daemon.py` | Restarts `run_atlas.py` on crash; logs to `logs/daemon.log` |
| Backend module | `apps/server/server.py` | The FastAPI app (`server.app`): ~93 routes, WebSockets, SQLite, static file serving |

There is no separate API process — `run_atlas.py` imports `apps/server/server.py`
and serves everything from one uvicorn process.

## Network & serving (post-2026-07 security cleanup)

- **Bind host:** `127.0.0.1` by default. Set `ATLAS_LAN=1` (or `ATLAS_HOST=0.0.0.0`)
  to expose on the network. Pair network exposure with `ATLAS_API_TOKEN`.
- **Port:** `8088` by default (`ATLAS_PORT` to override; falls back to next free port).
- **CORS:** localhost origins only; extend with `ATLAS_CORS_ORIGINS` (comma-separated).
- **Auth:** off by default. Set `ATLAS_API_TOKEN` to require
  `Authorization: Bearer <token>` (or `X-Atlas-Token`) on `/query`, `/api/aria`, `/api/agents`.
- **Code-execution tool:** ARIA's `execute_code` tool runs `exec()` in-process
  (NOT sandboxed) and is only registered when `ATLAS_ENABLE_CODE_EXEC=1`.

## Frontend — which UI is canonical

There are multiple UI trees in the repo. The **canonical, served UI is `ui_web/`**:

- `run_atlas.py` builds `ui_web` (Vite) on startup and `server.py` mounts
  `ui_web/dist` at `/` when it exists.
- `apps/desktop/` (vanilla JS, ~34k lines) is the **older** UI. It is still
  mounted at `/desktop` as static files and used as the fallback root when
  `ui_web/dist` is absent. Treat it as legacy unless a view exists only there.
- `apps/desktop/` also ships an Electron shell (`main.js`, `package.json`),
  which is a separate desktop-app packaging path, not used by the web server.
- `FR_upgrade/` contains AI-generated JSX that **duplicates** `ui_web`
  components (e.g. `MMORender.jsx` is identical). It is a staging/scratch area,
  not wired into any build. Do not treat it as a source of truth.

**Rule of thumb:** build new UI in `ui_web/`. Only touch `apps/desktop/*.js`
for views that have not been ported yet.

## Backend layout

- `python/src/atlas/` — the installed package (`atlas-core`, src-layout, editable
  install via `pyproject.toml`). ~45 subpackages. High-traffic ones:
  - `assistants/aria/` — the ARIA assistant, its tools, providers, memory.
  - `core/ai_assistant/` — the **production** multi-agent system (orchestrator,
    registry, agents, audit, policies). Used by the server.
  - `data_layer/` — provider registry + market-data sources (yahoo_provider,
    alphavantage, polygon, etc.). `get_provider_registry()` is the entry API.
  - `signal_terminal/` — collectors (RSS/Reddit/SEC/nitter), services, API router
    mounted at `/api/signals`.
  - `indicators/`, `features/`, `risk/`, `rl/`, `quantitative/`, `monte_carlo/`,
    `black_swan/`, `market_state/` — analytics engines feeding the simulation +
    viz layers.

### Two parallel "agent core" lineages (do not confuse)

- `python/src/atlas/core/ai_assistant/` — the **evolved production** version
  (dataclasses, docstrings, risk gate, result validation). This is what the
  server and tests use.
- `core/ai_assistant/` (repo root) — an **earlier, simpler prototype** with a
  different API. It is only used by `scripts/run_agent_demo.py` (a standalone
  Ollama demo) together with `services/llm/`. It still runs; it is not wired
  into the server. Kept for the demo — do not import it from `atlas.*`.

## Data / storage

- SQLite DBs under `data/` (e.g. `aria_multi_device.db`, `signal_terminal.db`,
  `operations.db`, `simulation_artifacts.db`). All gitignored.
- Logs under `logs/` (rotating `atlas.log`, `daemon.log`). Gitignored.

## Tests

- `tests/` (295 tests, all passing) + `python/tests/`. Run with `pytest tests`.
- Notable: `tests/unit/test_ui_truth_contract.py` asserts the UI never presents
  fake/synthetic data as real — a guardrail worth preserving.

## Optional dependencies (features that need extra installs)

Some modules import third-party libs that aren't in the base install; the
feature is simply unavailable until installed. Known cases:
- `assistants/aria/integrations/whatsapp_bot.py` → needs `flask`
- `ui/artifact_renderers.py`, `ui/simulation_dashboard.py` → need `streamlit`

These fail to import in isolation by design; nothing in the core server loads
them unless the feature is used.
