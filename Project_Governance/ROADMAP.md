# Project Roadmap

Last updated: 2026-05-11

Planning source of truth:
`docs/ATLAS_MASTER_ROADMAP_2026_CONSOLIDATED.md`.

This file tracks the active sprint and near-term execution focus. Historical
roadmaps remain useful context, but sprint planning should follow the
consolidated 2026 roadmap.

## Current Sprint: Governance, Intake, and Agent Boundary

Objective: stabilize Atlas planning around the consolidated roadmap, document
the Agent Gateway/MCP safety boundary, and prepare the next implementation
slice without expanding backend or frontend code prematurely.

Status: In progress.

### Active Tasks

- [x] Point project governance at the consolidated 2026 roadmap.
- [x] Replace the placeholder roadmap template with a concrete sprint board.
- [x] Draft `docs/AGENT_GATEWAY_DESIGN.md` for `/api/agent/v1`, scoped tokens,
  capabilities, paper-only defaults, audit logging, async jobs, MCP boundary,
  and verification.
- [ ] Maintain `info_instructions/EXTRACTION_LOG.md` as the intake register for
  newly classified sources.
- [ ] Convert Agent Gateway design into implementation tickets only after
  review.
- [x] Add provider health/status endpoint and UI card.
- [x] Connect `ui_web` to real `/api/health`.
- [ ] Connect `ui_web` to ServiceBus/WebSocket events in a later code sprint.
- [ ] Draft the RL environment, reward, action, and data-feed specification
  before adding more RL code.

## Sprint Deliverables

### 1. Governance and Intake Discipline

Atlas is the local-first operating system for M&C. Market finance is the first
implemented domain, not the final product identity.

Deliverables:

- Keep `docs/ATLAS_MASTER_ROADMAP_2026_CONSOLIDATED.md` as the planning source
  of truth.
- Track external sources in `info_instructions/EXTRACTION_LOG.md` with source,
  folder, license signal, ideas mined, and final status.
- Preserve the rule that processed source material moves to `Repo usage
  complete`; nothing is deleted from intake.
- Require every roadmap item to map to an Atlas layer, owner module, and
  verification method before implementation starts.

### 2. Agent Gateway and MCP Safety Boundary

Goal: let external agents work with Atlas without uncontrolled backend,
credential, filesystem, or trading access.

Deliverables:

- `/api/agent/v1` design.
- Scoped agent token model with expiration, rate limits, market whitelist,
  asset whitelist, job limits, and paper-only flag.
- Capability classes:
  - `R`: read data.
  - `W`: workspace write.
  - `B`: backtest/simulation.
  - `N`: notify/report.
  - `C`: credentials/admin only.
  - `T`: trading, paper-only by default.
- Audit log requirements for every allowed and denied agent call.
- Async job lifecycle for long backtests, simulations, research runs, and
  reports.
- MCP boundary exposing read and backtest tools first, with no live trading.
- Verification checklist before implementation.

Milestone: Codex, Claude, or ARIA can request a backtest through a scoped token
and receive job status without touching live execution.

### 3. Near-Term Product Integration

These items follow after documentation review and should be implemented as
separate code changes:

- Provider health dashboard endpoint showing registered channels, available
  providers, recent requests, and fallback visibility.
- UI health card connected to real `/api/health` and `/api/providers/health`.
- ServiceBus/WebSocket event bridge for live state updates.
- Artifact registry integration for every run, decision, chart, and report.
- RL lab architecture spec modeled around environments, action schemes, reward
  schemes, data feeds, and portfolio state.

## Short-Term Roadmap

### Phase 1: Data and API Expansion

Focus: move beyond isolated datasets while keeping provider health observable.

- Add or validate providers for DBnomics, IMF, World Bank, BLS, Treasury.gov,
  AkShare, Kraken, Hyperliquid, weather, shipping/freight, energy inventory,
  and prediction-market context.
- Keep prediction-market data read-only or paper-only at first.
- Build visible provider health and fallback paths before depending on new
  providers in user-facing workflows.

### Phase 2: Agent Gateway and MCP Safety Boundary

Focus: implement the reviewed gateway design.

- Add token schema and audit table design.
- Add route-level capability enforcement.
- Add async job submit/poll/stream behavior.
- Add MCP read/backtest server tools.
- Verify paper-only defaults and denied live execution paths.

### Phase 3: Service Bus and Live State

Focus: connect existing modules into one observable system.

- Define typed AtlasServiceBus channels:
  `MARKET_DATA`, `MACRO`, `NEWS`, `FILINGS`, `SIGNALS`, `RISK`, `PORTFOLIO`,
  `ORDERS`, `AGENT_JOBS`, and `UI_STATE`.
- Add shared state store and WebSocket/SSE bridge.
- Make UI and ARIA consume deterministic artifacts rather than ad hoc text.

## Long-Term Roadmap

- Complete market finance core: event-driven backtesting, realistic fills,
  portfolio construction, risk guardrails, derivatives analytics, signal
  decision logs, and audited advisory trade proposals.
- Harden RL/ML lab: reproducible experiments, checkpoint management, baseline
  reward schemes, and out-of-sample evaluation before production influence.
- Mature ARIA and multi-agent research: structured-output agents, persistent
  decision logs, checkpoint/resume, and artifact-producing workflows.
- Build the visual OS surface: web dashboard, research workspace, strategy
  editor, backtest history, execution monitor, mobile read-only views, alerts,
  and module launcher.
- Preserve M&C domain expansion: real estate engine, engineering/design layer,
  and knowledge intake pipeline after finance core stabilizes.

## Non-Negotiable Rules

- No live trading by default.
- External agents get scoped, audited, revocable access only.
- Lab modules can fail, but they cannot silently drive production decisions.
- Source-available, AGPL, unclear-license, and academic notebook repos remain
  references unless license obligations are accepted explicitly.
- Processed source material moves to `Repo usage complete`; nothing is deleted.
- Every implementation item needs an Atlas layer, owner module, and verification
  method before code changes begin.
