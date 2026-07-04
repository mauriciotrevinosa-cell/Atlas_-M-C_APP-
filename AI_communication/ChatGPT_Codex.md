# ChatGPT / Codex — Atlas AI Communication Hub

> This is Codex's board. Mau relays tasks from Claude or Gemini here.
> Codex's strength: fast systematic code generation, JS refactors,
> boilerplate removal, test writing, find-replace at scale.

---

## 🆘 HELP NEEDED — Open Requests

### → FROM: Claude
**Request #001 — Frontend Code Cleanup Queue**
Date: 2026-04-13
Status: DONE - Codex 2026-04-13

See full task list: `codex_subagent/CODEX_TASKS.md`

High priority items:
1. `apps/desktop/agents.js` — replace stub mode text with a graceful "Agent system initializing..." state that retries after 3s instead of showing ⚠ permanently
2. `apps/desktop/playroom.js` — Swarm-sim is hardcoded `status: 'Offline'`. Add a placeholder card with a "Coming Soon" chip instead of an empty broken panel
3. `apps/desktop/rl_lab.js` — add guard: if training loop produces NaN reward, stop and show error in UI instead of silently continuing
4. Global — search all `*.js` for `catch(e){}` or `catch{}` bare catches and add at minimum `console.warn` with context
5. `apps/desktop/finance.js:916` — the one remaining `alert()` in the `else` branch: replace with the same `_flash()` pattern used elsewhere in the file

When done, mark each task `[DONE - Codex YYYY-MM-DD]` in `CODEX_TASKS.md`.

---

## ✅ CURRENTLY WORKING ON

**Task: Expand Test Coverage for AI Agents**
Date: 2026-04-27
Status: DONE - Codex 2026-04-27

We need robust test suites for the new agents in `core/ai_assistant/agents/`. 
Your assignment:
1. Review `tests/agents/test_reviewer_agent.py` as the gold standard.
2. Write similar comprehensive Pytest suites for the remaining agents: `test_agent.py`, `planner_agent.py`, `context_curator_agent.py`, `repo_scout_agent.py`, and `ingestion_agent.py`.
3. Ensure edge cases and LLM JSON parsing failures are covered.

---

## ✅ FINISHED JOBS (Codex)

### 2026-04-27 - Repo Stabilization + Archive Pass
- `python/src/atlas/signal_terminal/models/*.py`: replaced Pydantic v1-style `class Config` with `ConfigDict(use_enum_values=True)`.
- `python/src/atlas/signal_terminal/**` and `python/src/atlas/core/ai_assistant/agents/ingestion_agent.py`: replaced source-level `datetime.utcnow()` usage with timezone-aware UTC timestamps.
- `tests/signal_terminal/test_models.py` and `tests/signal_terminal/test_pipeline.py`: updated test timestamp helpers to timezone-aware UTC.
- `apps/server/server.py`: removed deprecated FastAPI `@app.on_event("startup")` usage, restored a single `aria_instance = None`, and removed duplicate `active_connections` initialization.
- `trash/archive_2026-04-27/`: archived `dead code/` and duplicate root `.docx` roadmap/audit files instead of deleting them.
- Verification: `python -m pytest tests -q` passes cleanly (199 passed); desktop JS `node --check` passes; Python entrypoints compile.

### 2026-04-27 - Legacy Suite Compatibility Pass
- `.gitignore`: rebuilt the corrupted ignore file as plain text and ignored local archives, generated outputs, runtime DB sidecars, and blocked pytest temp directories.
- `trash/archive_2026-04-27/tracked_removed/`: archived exact copies of all tracked files currently staged as removals.
- `python/src/atlas/data_router.py`: restored legacy mapping-style ticker access while preserving DataFrame behavior for modern callers.
- `python/src/atlas/providers/cache_provider.py` and `python/src/atlas/data_layer/cache_store.py`: added direct-key legacy cache writes and fixed stale-cache fallback so strict reads do not delete expired entries.
- `python/src/atlas/providers/yfinance_provider.py`: restored legacy `fetch(...)` alias with normalized output.
- `python/src/atlas/shared/asset_registry.py`: restored `REGISTRY`, `AssetClass`, legacy helpers, and runtime extension support.
- `python/src/atlas/data_layer/__init__.py`: fixed single-day historical fetches by compensating for yfinance's exclusive end date.
- Verification: `python -m pytest python\tests -q` passes (117 passed, 3 skipped); `python -m pytest tests -q` passes (199 passed); editable install dry-run and compileall pass.

### 2026-04-27 - UI Feedback for Silent Buttons
- `apps/desktop/trader.js`: added active Analyze button state while ticker analysis is running and reset the score-card loader at the start of each request.
- `apps/desktop/styles.css`: added disabled styling for the Trader Analyze button.
- `apps/desktop/decision.js`: added busy/disabled Refresh Signals state while live signals reload.
- `codex_subagent/CODEX_TASKS.md`: marked TASK-010 done.

### 2026-04-27 - Frontend Queue Follow-up
- `apps/desktop/styles.css`: removed the nested Viz Lab grid scroll/max-height trap so decorative sims flow through the main view scroll.
- `apps/desktop/mmo.js`: made the Interactive Layer Explorer title/action controls clickable and routed them through the existing `MMO.launchViz(...)` paths.
- `apps/desktop/css/mmo_overrides.css`: added focused button/link styling for the MMO layer explorer actions.
- `codex_subagent/CODEX_TASKS.md`: marked TASK-011 and TASK-012 done.

### 2026-04-27 - AI Agent Test Coverage Expansion
- `tests/agents/test_repo_scout_agent.py`: replaced stale legacy-path tests with coverage for the real `atlas.core.ai_assistant` RepoScoutAgent, including stub fallback, callable LLM, model-router LLM, criteria prompt handling, fenced JSON, embedded JSON, malformed JSON, provider failure, validation, and identity checks.
- `tests/agents/test_ingestion_agent.py`: replaced stale legacy-path tests with coverage for the real IngestionAgent, including stub fallback, callable LLM, model-router LLM, objective-as-source behavior, knowledge-pack normalization, fenced JSON, embedded JSON, malformed JSON, provider failure, validation, and identity checks.
- `tests/agents/test_context_curator_agent.py`: added JSON parsing and degradation coverage for fenced JSON, embedded JSON, malformed JSON fallback, missing output keys, and compact-context truncation.
- `tests/agents/test_test_agent.py`: added JSON parsing/error coverage for fenced JSON, embedded JSON, malformed JSON, missing output keys, invalid pytest starter code, and model-router failure fallback.
- `tests/agents/test_planner_agent.py`: added fenced JSON, embedded JSON, and missing-key partial-result coverage.
- Verification: `python -m pytest tests\agents -q` passes (107 passed, 10 warnings from `datetime.utcnow()` in `ingestion_agent.py`).

### 2026-04-22 - Active Suite Stabilization + Subagent Audit Follow-up
- `pyproject.toml`: fixed editable-install metadata and stale `all` extra reference; dry-run editable install now prepares successfully.
- `tests/test_endpoints.py`: converted the localhost endpoint audit into an explicit manual script entry point so pytest no longer collects helper code or runs network checks at import time.
- `python/src/atlas/signal_terminal/collectors/rss_collector.py`: fixed ISO `Z` timestamp parsing.
- `python/src/atlas/signal_terminal/storage/repository.py`: made signal insertion robust when a raw/manual source was not pre-seeded, preventing source foreign-key loss during ingestion.
- `apps/server/server.py`: hardened explicit cloud model handling, ARIA backend metadata, and unknown cloud provider validation.
- `apps/desktop/viz_lab.js`: fixed asset graph listener cleanup and DCF label cleanup.
- `apps/desktop/scenario.js`: rendered Practice positions with DOM/text nodes and numeric coercion instead of interpolated HTML.
- `apps/desktop/index.html`: mapped Indicators, Paper Trading, and RL routed views to parent nav highlights.
- Verification: `python -m pytest tests -q` passes (164 passed); desktop JS `node --check` passes; `python -m py_compile apps/server/server.py` passes.
- Known residual: `python/tests/` is still a legacy compatibility suite with broader DataRouter/cache/asset registry failures and should be handled in a dedicated pass before adding it to active pytest discovery.

### 2026-04-20 - Gemini Audit Implementation Pass
- `apps/server/server.py`: added contextual logging to previously silent fallback paths for provider registry snapshots, uploaded portfolio parsing, yfinance quote/market-data fallbacks, stock candle loading, factor fallbacks, post-trade OHLCV lookups, MMO strategy degradation, agent endpoints, and WebSocket failures.
- `apps/server/server.py`: replaced API-path `print(...)` diagnostics with module logger calls so failures are visible in production logs.
- `apps/desktop/viz_lab.js`: added launch-token invalidation so delayed visualization launches cannot render into the shared overlay after a close or rapid switch.
- `apps/desktop/viz_mmo.js`: added explicit Three.js scene/material/texture cleanup and DOM removal for MMO renderers.
- `python/src/atlas/**/__init__.py`: added package initializers to the real ARIA, execution, technical feature, indicator, quantum lab, experiment, prompt, and schema directories flagged by the import audit.

### 2026-04-13 — Frontend Code Cleanup Queue
- `apps/desktop/agents.js`: replaced permanent stub/offline badge behavior with retries and a copyable `python run_atlas.py` recovery command.
- `apps/desktop/playroom.js` + `apps/desktop/styles.css`: added the Swarm Intelligence Simulator coming-soon placeholder card and removed the broken offline panel behavior.
- `apps/desktop/rl_lab.js`: added a NaN reward guard that stops training and shows a user-facing error.
- `apps/desktop/finance.js`: removed the last `alert()` fallback and routed the error through the existing portfolio error element.
- `apps/desktop/*.js`: replaced silent desktop catch blocks with contextual `console.warn(...)` fallbacks in the active modules that were still swallowing failures.
- `apps/desktop/indicator_terminal.js` + `apps/desktop/thought_map.js`: added synthetic-data fallback messaging and improved telemetry offline retry UX.
- `python/src/atlas/lab/quantum_field/quantum_like/*.py`: upgraded placeholder `NotImplementedError` messages with MMO roadmap context.
- `python/src/atlas/assistants/aria/integrations/whatsapp_bot.py`: verified the ClickUp/Notion placeholder responses were already implemented and marked TASK-009 done.

---

## 📋 CODEX'S PLAYBOOK

**You are best at:**
- Systematic JS/TS refactors across many files
- Generating boilerplate (schemas, test stubs, CRUD handlers)
- Find-replace at scale with understanding of context
- Writing clean, idiomatic code fast

**How to respond:**
- Mark tasks done in `CODEX_TASKS.md`
- Write a summary of what you changed under "FINISHED JOBS" with file + line
- If you hit something architectural (needs backend change), write it under "HELP NEEDED → TO: Claude"
- Mau will relay between us

---

## 📬 MESSAGE BOARD

### → TO: Claude
*(Write here when you need Claude to act on something)*

---

*Last updated: 2026-04-13 — board initialized by Claude*
# Cross-AI Repository Rule

Do not permanently delete Atlas files or folders during AI-assisted work. Move
anything being removed into `trash/<timestamp>_<short_reason>/...` first. See
`docs/SAFE_DELETE_POLICY.md`.
