# ATLAS MASTER ROADMAP 2026 - CONSOLIDATED

Last updated: 2026-05-08

Purpose: consolidate the older Atlas roadmaps, the March 25 audit, the M&C OS
vision, and the newly added `info_instructions` repositories into one working
roadmap. Older roadmaps should stay as historical context; this file is the new
source of truth for planning.

## 1. Current Identity

Atlas is the local-first operating system for M&C. Market finance is the first
implemented domain, but not the final identity of the product.

Core product flow:

```text
DATA -> ANALYTICS -> SIMULATION -> RISK -> VISUALIZATION -> DECISION SUPPORT
```

ARIA is the assistant/orchestrator interface beside that flow. ARIA should call
tools, explain outputs, coordinate workflows, and help research, but it should
not own deterministic trading, risk, portfolio, or business rules.

## 2. Information Intake Rules

`info_instructions` is now the intake area for PDFs, repos, docs, API lists,
research, and external ideas that can improve Atlas.

Folder meanings:

| Folder | Meaning | Rule |
| --- | --- | --- |
| Folder 1 | Repos we can extract from without major issue | Code/patterns can be reused after normal license review and attribution. |
| Folder 2 | Repos with data/code limitations | Use for architecture and product patterns unless license obligations are explicitly accepted. |
| Folder 3 | Repos we can only inspect | No copy/paste. Rebuild ideas from scratch. |
| Folder 4 | Tools/mechanics that do not directly define Atlas | Use for workflows, APIs, CLIs, mechanics, or optional connectors. |
| Repo usage complete | Material already processed | Never delete. Move here only when the material has been fully mined. |

## 3. Newly Classified Sources

| Source | Folder | License/use signal | What Atlas should extract |
| --- | --- | --- | --- |
| `awesome-llm-apps-main - 2026-05-08.zip` | Folder 1 | Apache-2.0 | Agent/RAG/MCP/voice app templates, multi-agent team patterns, production examples. |
| `everything-claude-code-main.zip` | Folder 1 | MIT | Skills-first agent workflows, hooks, MCP config patterns, cross-harness plugin structure. |
| `public-apis-master (1) - 2026-05-08.zip` | Folder 1 | MIT | API discovery catalog for weather, commodities, macro, shipping, real estate, news, and alternative data. |
| `quant-traderr-lab-main (1).zip` | Folder 1 | MIT | Econophysics ideas: RMT correlation filters, wavelets, Fisher transform, PSR-style alpha discovery. |
| `QuantDinger-main.zip` | Folder 1 | Apache-2.0 | Local-first quant stack, Docker Compose, Agent Gateway, scoped tokens, OpenAPI/MCP bridge, strategy runtime. |
| `tensortrade-master.zip` | Folder 1 | Apache-2.0 | RL trading architecture: environments, action schemes, reward schemes, data feeds, Ray/RLlib training. |
| `TradingAgents-main.zip` | Folder 1 | Apache-2.0 | Structured-output financial agents, checkpoint resume, persistent decision log, multi-provider model catalog. |
| `FinceptTerminal-main.zip` | Folder 2 | AGPL/commercial dual license | Product architecture only: terminal-grade multi-asset analytics, 100+ data connectors, broker matrix, node workflows. |
| `git-city-main - 2026-05-08.zip` | Folder 2 | AGPL | 3D contribution-city UI mechanics only; do not copy code into Atlas without accepting AGPL terms. |
| `QuantDinger-Vue-main.zip` | Folder 2 | Source-available | UI/product reference only: research workspace, strategy editor, execution views, Polymarket UI. |
| `QuantDinger-Mobile-master.zip` | Folder 2 | Source-available | Mobile shell reference: Vue 3/Vite/Capacitor, API base switching, mobile H5/native deployment. |
| `AI-Trader-main.zip` | Folder 3 | README says MIT badge but no license found in quick scan | Rebuild ideas only: agent-native trading registration, background workers, Polymarket paper trading. |
| `moon-dev-ai-agents-main.zip` | Folder 3 | No license found in quick scan | Rebuild ideas only: trading/risk/copy/whale/liquidation/funding/OI agents and swarm coordination notes. |
| `computacao-quantica-aplicada-ao-mercado-financeiro-main.zip` | Folder 3 | Academic notebooks, no license found in quick scan | Rebuild ideas only: Markowitz + QAOA/VQE portfolio experiments. |
| `polymarket-cli-main - 2026-05-08.zip` | Folder 4 | No license found in quick scan | Optional prediction-market connector mechanics; early/experimental and must remain paper/advisory first. |

## 4. Updated Progress Snapshot

Progress estimates are repo-level working estimates, not marketing claims.

| Area | Progress | Status | Notes |
| --- | ---: | --- | --- |
| M&C OS vision and governance | 80% | Active | Vision exists; needs to stay reflected in README, UI, and roadmap. |
| Info intake workflow | 70% | Active | Folder policy exists; needs an extraction log and repeatable checklist. |
| Foundation/build hygiene | 75% | Active | Makefile, pyproject, tests exist; repo still has many historical/untracked artifacts. |
| Data layer/provider registry | 70% | Active | Yahoo and several provider modules exist; next step is validation and key health checks. |
| API ecosystem | 65% | Active | FRED, Alpha Vantage, Finnhub, Polygon, SEC EDGAR, NewsAPI, HuggingFace are in roadmap/code; add DBnomics, IMF, World Bank, BLS, Treasury, AkShare, Kraken, Hyperliquid, weather/commodity context. |
| AtlasServiceBus/event system | 50% | Active | Event bus/artifact registry exist; needs typed channels, state store, WebSocket bridge. |
| ARIA assistant | 65% | Active | Multi-provider/tooling/memory direction exists; needs integration into the actual product loop. |
| Agent gateway/MCP boundary | 15% | New | Add scoped agent tokens, audit log, paper-only defaults, OpenAPI contract, MCP read/backtest tools. |
| Market analytics/features | 55% | Active | Indicators, volatility, derivatives, microstructure exist; add wavelets, RMT filters, commodity/weather context. |
| Simulation layer | 50% | Active | Monte Carlo exists; add scenario library, regime simulation, QAOA/VQE lab experiments. |
| Risk layer | 45% | Active | VaR/CVaR/liquidation risk exists; add portfolio-level guardrails, agent approval gates, broker risk limits. |
| Portfolio/allocation | 30% | Partial | Add Markowitz, risk parity, Black-Litterman, PyPortfolioOpt/RiskFolio/skfolio-style adapters. |
| Backtesting | 30% | Partial | Needs event-driven execution, realistic fills, persisted runs, walk-forward validation. |
| RL/ML trading | 25% | Partial | Use TensorTrade-style environment/action/reward/data-feed separation before training models. |
| Execution/paper trading | 25% | Partial | Add Alpaca/IBKR/MT5/Kraken/Hyperliquid paper-first adapters; live trading stays gated. |
| Signal terminal | 45% | Beta | Existing collectors/classifier; add decision logs, source confidence, alert audit. |
| Desktop UI | 55% | Active | Existing Electron-style desktop app has many modules; needs product polish and consistent navigation. |
| Web UI | 40% | Active | Vite/React glass dashboard builds; needs real data, WebSocket state, app launcher depth. |
| Mobile UI | 5% | New | Add mobile H5/Capacitor roadmap, not immediate implementation. |
| Real Estate Engine | 10% | Concept | Needs zoning, comps, feasibility, unit mix, IRR/NPV, sensitivity engine. |
| Knowledge/research layer | 25% | Active | RAG/memory direction exists; needs intake pipeline from `info_instructions`. |
| DevOps/deployment | 35% | Partial | Add Docker Compose, CI, preview builds, API health checks, backup policy. |

## 5. New Roadmap Phases

### Phase 0 - Governance and Intake Discipline

Goal: keep Atlas from becoming scattered again.

Deliverables:

- `info_instructions` extraction log with source, folder, license, ideas mined,
  and final status.
- Rule: nothing is deleted from intake. Processed material moves to
  `Repo usage complete`.
- A source classification checklist:
  license, stack, direct-copy allowed, modules worth extracting, ideas to
  rebuild, roadmap deltas.
- README update that presents Atlas as M&C OS, with market finance as Phase 1.

### Phase 1 - Data and API Expansion

Goal: make Atlas useful beyond yfinance and isolated datasets.

Already present or planned:

- Yahoo, FRED, Alpha Vantage, Finnhub, Polygon, SEC EDGAR, NewsAPI,
  HuggingFace.

Add from new sources:

- DBnomics, IMF, World Bank, BLS, Treasury.gov, AkShare.
- Kraken and Hyperliquid for crypto/derivatives streaming.
- Weather APIs for commodity/oil/agriculture context.
- Shipping/freight and energy inventory APIs for oil and macro commodities.
- Polymarket/prediction-market data as sentiment/event probability input,
  initially read-only or paper-only.

Milestone: provider health dashboard with key status, rate limits, cache hit
rate, and fallback path visibility.

### Phase 2 - Agent Gateway and MCP Safety Boundary

Goal: let external agents work with Atlas without giving them uncontrolled
power.

Inspired by QuantDinger and ECC:

- `/api/agent/v1` gateway with scoped tokens.
- Capability classes:
  - R: read data
  - W: workspace write
  - B: backtest/simulation
  - N: notify/report
  - C: credentials/admin only
  - T: trading, paper-only by default
- Token rules: expiration, market whitelist, asset whitelist, rate limits,
  paper-only flag.
- Audit log for every agent call.
- Async job model for long tasks: submit, poll, stream progress.
- MCP server exposing R and B tools first; no live trading through MCP.

Milestone: Codex/Claude/ARIA can request a backtest through a scoped token and
receive job status without touching live execution.

### Phase 3 - Service Bus and Live State

Goal: connect the existing modules into one system.

Deliverables:

- Typed AtlasServiceBus channels:
  `MARKET_DATA`, `MACRO`, `NEWS`, `FILINGS`, `SIGNALS`, `RISK`, `PORTFOLIO`,
  `ORDERS`, `AGENT_JOBS`, `UI_STATE`.
- Shared state store with observable updates.
- WebSocket/SSE bridge to web and desktop UIs.
- Artifact registry integration for every run, decision, chart, and report.

Milestone: one market tick updates features, risk, UI cards, and ARIA context.

### Phase 4 - Market Finance Core Completion

Goal: finish the half-built finance system.

Deliverables:

- Backtesting: event-driven runs, slippage, commission, liquidity assumptions,
  walk-forward validation, persisted history.
- Portfolio: Markowitz, risk parity, Black-Litterman, constraints, exposure
  caps, correlation clustering.
- Risk: portfolio VaR/CVaR, max drawdown, concentration, leverage, liquidation
  zones, paper-trading kill switches.
- Options/derivatives: real chain data, IV surface, greeks, funding/OI,
  liquidation heatmaps.
- Signal terminal: persistent decision log, source confidence, alert audit,
  research-to-signal traceability.

Milestone: Atlas can produce an audited advisory trade proposal with data,
features, simulation, risk, and decision explanation.

### Phase 5 - RL/ML Lab Hardening

Goal: make RL/ML experiments useful without contaminating production logic.

Inspired by TensorTrade:

- Define formal trading environments.
- Separate action schemes, reward schemes, data feeds, and portfolio state.
- Add baseline reward schemes:
  PnL, Sharpe-adjusted, drawdown penalty, turnover penalty, risk budget.
- Add checkpoint management and experiment registry.
- Keep RL in Lab until it beats baselines out-of-sample.

Milestone: one reproducible RL experiment with train/evaluate/report artifacts.

### Phase 6 - ARIA and Multi-Agent Research

Goal: make ARIA a serious research operator, not only a chatbot.

Inspired by TradingAgents, ECC, awesome-llm-apps, and moon-dev notes:

- Structured-output agents: Research Manager, Trader, Risk Reviewer,
  Portfolio Manager, Execution Reviewer.
- Persistent decision log with thesis, evidence, risk notes, outcome, and
  reflection.
- Checkpoint/resume for long research sessions.
- Skills-first workflows for common tasks:
  source intake, API integration, backtest review, risk review, UI QA.
- Multi-agent results must resolve into deterministic artifacts, not only text.

Milestone: ARIA can run a research workflow that produces a saved decision log,
charts, risk report, and next-step task list.

### Phase 7 - Visual OS Surface

Goal: make Atlas feel like an app, not terminals.

Current direction:

- Desktop app remains useful for module access.
- `ui_web` becomes the modern app surface: dashboard, wallet-style portfolio,
  app launcher, ARIA drawer, MMO 3D canvas.

Add from new sources:

- Research workspace, strategy editor, backtest history, execution monitor.
- Mobile H5/Capacitor path for watchlists, alerts, job status, and read-only
  dashboards.
- 3D map mechanics inspired by Git City/MMO, rebuilt under Atlas design rules.

Milestone: web UI shows live system health, portfolio/risk cards, job progress,
and a working module launcher.

### Phase 8 - M&C Domain Expansion

Goal: preserve the broader OS vision.

Real Estate Engine:

- Zoning inputs, comps, FAR/CUS/COS, setbacks, buildable area.
- Development finance: IRR, NPV, equity multiple, debt service, sensitivity.
- Scenario simulation: delays, cost overruns, rent/price assumptions.

Engineering/Design Layer:

- CAD/Blender/parametric design research.
- Physics/CFD hooks later, not before finance core stabilizes.

Knowledge Layer:

- Ingest PDFs, repos, notes, API catalogs.
- Summarize ideas into roadmap deltas and module tickets.
- Track when a source moves to `Repo usage complete`.

## 6. High-Priority Backlog Additions

1. Build `info_instructions/EXTRACTION_LOG.md`.
2. Add `docs/AGENT_GATEWAY_DESIGN.md`.
3. Add scoped agent token schema and audit table design.
4. Add MCP read/backtest server design.
5. Add provider health dashboard endpoint.
6. Add alternative-data provider backlog: weather, shipping, energy,
   DBnomics, IMF, World Bank, AkShare.
7. Add prediction-market data adapter plan for Polymarket, paper/read-only
   first.
8. Add TensorTrade-style RL architecture doc before adding more RL code.
9. Add persistent decision log schema for ARIA/trading agents.
10. Add Docker Compose plan for backend + UI + database + worker.
11. Add mobile UI roadmap: read-only first, alerts second, approvals third.
12. Add UI module pages: research, strategies, backtests, risk, execution,
    knowledge intake.

## 7. Immediate Next Sprint

Recommended order:

1. Create the extraction log and register all newly classified sources.
2. Update README/project governance to point to this consolidated roadmap.
3. Design Agent Gateway and MCP safety boundary before giving agents more
   control.
4. Add provider health/status endpoint and UI card.
5. Connect `ui_web` to real `/api/health` and then to ServiceBus/WebSocket
   events.
6. Draft the RL environment/reward/action/data-feed spec.

## 8. Non-Negotiable Rules

- No live trading by default.
- External agents get scoped, audited, revocable access only.
- Lab modules can fail; they cannot silently drive production decisions.
- Source-available, AGPL, unclear-license, and academic notebook repos are
  references unless license obligations are accepted explicitly.
- Processed source material moves to `Repo usage complete`; nothing is deleted.
- Every roadmap item must map to an Atlas layer, an owner module, and a
  verification method before implementation starts.
