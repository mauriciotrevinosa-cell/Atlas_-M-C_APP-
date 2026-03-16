# Atlas Roadmap and Tracking

This roadmap is the execution board for current work. It is aligned with
`ATLAS_MASTER_PLAN.md` and focused on actionable implementation status.

## Current Focus (Active Sprint)
Objective: stabilize and complete Phase 1 workflow while removing placeholder
sections in core modules.
Status: In Progress

### Active Tasks
- [x] Validate Pixel Agents build/package and lint status.
- [x] Restore legacy `atlas.data_layer.get_data(...)` compatibility wrapper.
- [x] Replace `NotImplementedError` in legacy Polygon/Alpaca providers with
      functional providers + controlled Yahoo fallback.
- [x] Fix broken Python test package markers (`python/tests/__init__.py` files).
- [x] Implement `market_state.sentiment` from placeholder to functional engine.
- [x] Wire `market_state` outputs into a public API endpoint in `apps/server`.
- [x] Add unit tests for market-state module and API contract.

## Short-Term Roadmap (Next Steps)
Focus: close workflow gaps that block end-to-end reliability.

- [ ] Milestone 1: Workflow Integration Hardening
- [x] Add `/api/market-state/{ticker}` endpoint (regime, vol, internals, sentiment).
- [ ] Add server-side schema validation for market-state payload.
- [x] Add unit tests for endpoint response contract and error handling.

- [ ] Milestone 2: Execution Layer Completion
- [ ] Extend `execution_engine` with explicit slippage and fee model config.
- [ ] Add paper-trading reconciliation report artifact per run.
- [ ] Add tests for TWAP/VWAP fill quality metrics.

- [ ] Milestone 3: Data Layer Reliability
- [ ] Add provider health diagnostics (availability, last error, fallback reason).
- [ ] Add deterministic offline fixture mode for tests without network access.
- [ ] Normalize encoding issues in legacy Spanish docs/modules to UTF-8.

## Long-Term Vision
Focus: move from partial modules to production-grade orchestrated system.

- [ ] Feature: unified Market State service consumed by strategy/risk/execution.
- [ ] Feature: multi-agent decision loop (signal -> consensus -> guardrails -> execution).
- [ ] Feature: full artifact lineage graph per run (data -> analytics -> sim -> risk -> trade).
- [ ] Integration: desktop workflow controls for Phase 1/market-state/execution in one panel.

## Backlog / Icebox
- [ ] CoinGlass/Hyperliquid connectors for derivatives sentiment and liquidation risk.
- [ ] Quantum-field experimental modules (`quantum_like`) from stub to research-ready.
- [ ] Chroma-backed ARIA vector memory (currently placeholder).

---
Last Updated: 2026-03-08
