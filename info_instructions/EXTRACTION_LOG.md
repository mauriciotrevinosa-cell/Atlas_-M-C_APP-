# Atlas Info Instructions Extraction Log

Last updated: 2026-05-13

Rule: never delete intake material. When a source has been fully mined, move it
to `Repo usage complete`.

## Folder Policy

| Folder | Meaning | Usage |
| --- | --- | --- |
| Folder 1 | Repos we can extract everything without problem | Permissive or usable source material; reuse only with normal license review and attribution. |
| Folder 2 | Repos that have limitations on data/code | Reference architecture/product patterns unless license obligations are accepted. |
| Folder 3 | Repos we can only check and rebuild ourselves | Inspiration only. No copy/paste. |
| Folder 4 | Does not directly help Atlas but can provide mechanics/tools | Optional connector/tool/workflow reference. |
| Repo usage complete | Source already mined | Archive only; do not delete. |

## 2026-05-08 Classification Pass

| Source | Destination | Reason | Extracted roadmap value | Status |
| --- | --- | --- | --- | --- |
| `awesome-llm-apps-main.zip` | Folder 1 as `awesome-llm-apps-main - 2026-05-08.zip` | Apache-2.0; duplicate existed. | Agent/RAG/MCP/voice app templates, multi-agent teams. | Partially mined |
| `everything-claude-code-main.zip` | Folder 1 | MIT. | Skills-first workflows, hooks, MCP config, cross-harness plugin patterns. | Partially mined |
| `public-apis-master (1).zip` | Folder 1 as `public-apis-master (1) - 2026-05-08.zip` | MIT; duplicate existed. | API discovery source for alternative data such as weather, energy, macro, commodities. | Partially mined |
| `quant-traderr-lab-main (1).zip` | Folder 1 | MIT. | Econophysics backlog: RMT filters, wavelets, Fisher transform. | Partially mined |
| `QuantDinger-main.zip` | Folder 1 | Apache-2.0. | Agent Gateway, scoped tokens, audit logs, MCP bridge, Docker Compose, strategy runtime. | Partially mined |
| `tensortrade-master.zip` | Folder 1 | Apache-2.0. | RL environment/action/reward/data-feed architecture. | Partially mined |
| `TradingAgents-main.zip` | Folder 1 | Apache-2.0. | Structured-output agents, checkpoint resume, persistent decision log. | Partially mined |
| `FinceptTerminal-main.zip` | Folder 2 | AGPL/commercial dual license. | Product architecture reference: 100+ connectors, multi-asset analytics, broker matrix, node workflows. | Partially mined |
| `git-city-main.zip` | Folder 2 as `git-city-main - 2026-05-08.zip` | AGPL; duplicate existed. | 3D city/map mechanics as UI inspiration only. | Not mined deeply |
| `QuantDinger-Vue-main.zip` | Folder 2 | Source-available. | UI/product reference: research workspace, strategy editor, execution views, prediction-market UI. | Partially mined |
| `QuantDinger-Mobile-master.zip` | Folder 2 | Source-available. | Mobile H5/native shell reference, API base switching, Capacitor deployment. | Partially mined |
| `AI-Trader-main.zip` | Folder 3 | No license file found in quick scan despite README badge. | Agent-native trading and Polymarket paper trading concepts; rebuild from scratch. | Partially mined |
| `moon-dev-ai-agents-main.zip` | Folder 3 | No license found in quick scan. | Trading/risk/copy/whale/liquidation/funding/OI agent concepts; rebuild from scratch. | Partially mined |
| `computacao-quantica-aplicada-ao-mercado-financeiro-main.zip` | Folder 3 | Academic notebooks; no license found in quick scan. | Markowitz + QAOA/VQE portfolio lab ideas; rebuild from scratch. | Partially mined |
| `polymarket-cli-main.zip` | Folder 4 as `polymarket-cli-main - 2026-05-08.zip` | No license found in quick scan; tool/mechanics reference. | Prediction-market CLI mechanics; read-only/paper-only adapter idea. | Partially mined |

## 2026-05-11 Implementation Pass

| Source | Atlas output | Use rule followed | Status |
| --- | --- | --- | --- |
| `public-apis-master (1) - 2026-05-08.zip` | Created Atlas-owned public macro API providers: `WorldBankProvider`, `BLSProvider`, and `TreasuryFiscalProvider`; registered them as `macro` fallback providers in `DataProviderRegistry`; added mock-based unit tests. | Used the repo as an API discovery signal only. Implementation is original Atlas code against official public APIs. | Mined into code; keep source archived. |
| `polymarket-cli-main - 2026-05-08.zip` | Created Atlas-owned `PolymarketGammaProvider` for read-only prediction-market search and market probability snapshots; added mock-based unit tests. | Folder 4/no-license caution followed: rebuilt from official public API behavior, no trading, no credential, no copied CLI code. | Partially mined into code; keep source archived. |
| `public-apis-master (1) - 2026-05-08.zip` | Added `IMFDataMapperProvider`, `OpenMeteoProvider`, and visible localhost APIs: `/api/macro/series/{series_id}`, `/api/context/weather`, `/api/prediction/markets`. | Converted API catalog ideas into first-class Atlas backend modules and routes. No external repo code copied. | Mined further into code; keep source archived. |
| `computacao-quantica-aplicada-ao-mercado-financeiro-main.zip` | Rebuilt the Markowitz/QAOA/VQE idea as Atlas-owned `QuantumPortfolioQUBO` feeding Mau's Market Ontology through `/api/mmo/quantum_portfolio`; added unit tests. | Folder 3 rule followed: no notebook/code copy; rebuilt a deterministic QUBO-style portfolio-state selector from scratch for Atlas MMO. | Partially mined into MMO code; keep source archived. |
| `moon-dev-ai-agents-main.zip` / `AI-Trader-main.zip` | Added Atlas-owned `MarketIntelAgent` inside the existing `atlas.core.ai_assistant` orchestrator. It summarizes Signal Terminal signals, whale/unusual-flow events, derivatives context, data gaps, and suggested follow-up agent tasks; it appears through existing `/api/agents` rather than a second agent system. | Folder 3 rule followed: used repo concepts only; no copied code, no external runtime, no trade execution. Integrated with the canonical Atlas agent surface. | Partially mined into agents; keep sources archived. |
| `moon-dev-ai-agents-main.zip` | Added Atlas-owned Signal Terminal microstructure ingest through `MarketEventService` and `/api/signals/market-events`, turning funding, open-interest, liquidation, and unusual-volume snapshots into normal Atlas signals and liquidation whale events. | Folder 3 rule followed: rebuilt scanner concepts from scratch and routed them through existing Signal Terminal ingestion/dedupe/scoring/storage instead of adding a parallel scanner system. | Partially mined into Signal Terminal; keep source archived. |
| `AI-Trader-main.zip` | Added Atlas-owned `ChallengeEvaluator` in `atlas.evaluation` plus `atlas.research.evaluate_research_reports()` for strategy/agent/research leaderboards and JSON/CSV exports. It scores existing Atlas backtest/research metrics instead of importing AI-Trader's full challenge app. | Folder 3 rule followed: rebuilt challenge scoring concepts from scratch with deterministic local evaluation and no copy-trading/social app code. | Partially mined into evaluation/research; keep source archived. |
| `polymarket-cli-main - 2026-05-08.zip` / `AI-Trader-main.zip` | Extended Atlas-owned `PolymarketGammaProvider` with read-only market resolution by market id, condition id, slug, or search text; normalized `clobTokenIds` into `outcome_tokens`; added `/api/prediction/resolve`. | Rebuilt resolver behavior inside the existing Atlas provider/API. No wallet, signing, order, bridge, or CLOB write paths were imported. | Mined further into prediction provider; keep sources archived. |
| `TradingAgents-main.zip` / `QuantDinger-main.zip` | Improved the existing Atlas `TaskLogger` with immutable per-task checkpoints, `load_checkpoint()`, and recent checkpoint manifests. This strengthens agent audit/resume foundations without adding a second graph runtime. | Used checkpoint/audit ideas only and extended Atlas's existing `core.ai_assistant` audit trail. No LangGraph/QuantDinger runtime code copied. | Partially mined into agent audit/checkpointing; keep sources archived. |
| `GitNexus-main (1).zip` | Added Atlas-owned lightweight `repo_map` support for agents: read-only Python/JS/TS file map, imports, symbols, top imports, and module summaries; `RepoScoutAgent` can attach a bounded repo map when given `repo_root`. | Folder 2/noncommercial caution followed: rebuilt simple AST/regex mapping from scratch, no GitNexus code, hooks, embeddings, or marketplace assets copied. | Partially mined into RepoScout/repo intelligence; keep source archived. |
| `tensortrade-master.zip` / `speed-racer-rl-main (1).zip` | Added Atlas-owned RL action/reward schemes and wired them into the existing lightweight `atlas.rl.TradingEnvironment`, so actions, risk-adjusted rewards, turnover penalties, and reward components are explicit and testable. | Used architecture concepts only. No TensorTrade/Ray/RLlib/speed-racer source or runtime was copied; Atlas keeps its pure-numpy RL path. | Partially mined into RL; keep sources archived. |
| `shannon-main (1).zip` / `awesome-n8n-templates-main (2).zip` / `system-prompts-and-models-of-ai-tools-main (2).zip` | Connected the existing Atlas permission table to `AgentOrchestrator` through gateway preflight: global tool denials, critical-risk approval checks, live/production mode blocking, and checkpointed audit metadata. | Used security/workflow patterns only. No AGPL Shannon runtime, n8n templates, or third-party system prompts were copied. | Partially mined into agent gateway security; keep sources archived. |
| `QuantDinger-Vue-main.zip` / `FinceptTerminal-main.zip` | Added an Atlas-owned `ResearchWorkspace` to `ui_web` that surfaces provider health, read-only prediction markets, Signal Terminal feed/whales, and agent status from current Atlas endpoints. | Used product/workspace patterns only. No Vue/AGPL/source-available UI code, text, or assets were copied. | Partially mined into localhost UI; keep sources archived. |
| `qlib-main (1).zip` / `quant-traderr-lab-main (1).zip` | Added an Atlas-owned qlib-lite `FeatureExpressionEngine` under `atlas.features` for safe declarative market features such as returns, rolling means, z-scores, and correlations. | Used symbolic-feature architecture concepts only. No qlib workflow/runtime/model code or notebook scripts were copied. | Partially mined into feature engineering; keep sources archived. |
| `everything-claude-code-main.zip` / `ai-engineering-hub-main (2).zip` / `picoclaw-main (1).zip` | Improved Atlas `PromptStore` with prompt manifests, placeholder introspection, and strict rendering for reproducible agent prompt contracts. | Used skill/prompt workflow concepts only. No Claude Code hooks, MCP configs, prompts, or Go service code were copied. | Partially mined into LLM service/prompt infrastructure; keep sources archived. |
| `free-llm-api-resources-main (1).zip` | Added local LLM route/provider catalog introspection to Atlas `ModelRouter`, exposing configured models, routed agents, and provider availability from Atlas's own provider objects. | Used provider-catalog workflow concepts only. No third-party free-provider endpoints, keys, or claims were copied. | Partially mined into LLM service/provider registry; keep source archived. |
| `open-genie-main (1).zip` | Added Atlas-owned `MarketStateTokenizer` for compact deterministic market-state tokens from OHLCV, regime, volatility, momentum, and volume context. | Used world-model tokenization as a design idea only. No video/world-model training stack, MagViT/MaskGIT code, or model artifacts were copied. | Partially mined into market-state simulation context; keep source archived. |
| `ALADDIN-master (1).zip` | Improved Atlas `black_swan.ScenarioReport` with `ScenarioRunManifest`, capturing run inputs, normalized weights, categories, scenarios, beta coverage, and sector coverage. | Used stress-test auditability as a concept only. No ALADDIN/MachSuite/gem5 code was copied or imported. | Lightly mined into stress-test reporting; keep source archived. |
| `git-city-main - 2026-05-08.zip` / `sphere-main (1).zip` | Extended Atlas `RepoMap` with a Mermaid module-dependency graph for visual repo summaries consumable by agents/UI. | Used visualization mechanics only. No AGPL git-city code, sphere React assets, or 3D scene code were copied. | Lightly mined into repo intelligence visualization; keep sources archived. |
| `awesome-llm-apps-main - 2026-05-08.zip` / `awesome-llm-apps-main.zip` | Added `PipelineRunReport` for Atlas multi-agent pipelines so chained agent workflows return auditable summaries, status counts, task IDs, agents, and serialized results. | Used multi-agent workflow concepts only. No demo app code, Streamlit/FastAPI templates, or vendor-specific agents were copied. | Partially mined into agent orchestration; keep sources archived. |

## 2026-05-13 Localhost Visibility Pass

| Source | Atlas output | Use rule followed | Status |
| --- | --- | --- | --- |
| `QuantDinger-Vue-main.zip` / `FinceptTerminal-main.zip` / prior mined sources | `START_ATLAS.bat` now reaches a `run_atlas.py` startup check that builds `ui_web` before `apps.server.server` is imported, so the served localhost root uses the current React dashboard instead of a stale `dist` or legacy-only desktop. | Build/serve integration only; no external UI code copied. Existing Atlas server/static mount remains canonical. | Mined into launcher/runtime visibility. |
| All currently mined `info_instructions` slices | Removed the separate Info Instructions panel and merged visible capabilities into existing Atlas surfaces: Provider Registry, Research Workspace, Atlas Data Intake, La Biblioteca, MMO, ARIA, Signals, RL Lab, Agents, Repo Intelligence, and Scenario Lab. | Followed the product rule that external repo ideas become Atlas-owned module improvements, not a parallel showcase. The removed panel and previous versions were copied into `trash/20260513_142438_start_atlas_visibility_backup`. | Mined into localhost UI; continue remaining sources through existing modules first. |

## Roadmap Output

Created:

- `docs/ATLAS_MASTER_ROADMAP_2026_CONSOLIDATED.md`

Key roadmap deltas added:

- Agent Gateway with scoped tokens, capability classes, audit logs, async jobs,
  and paper-only trading defaults.
- MCP boundary exposing read/backtest tools first.
- Persistent decision log and checkpoint/resume for ARIA and financial agents.
- TensorTrade-style RL architecture before deeper RL implementation.
- Alternative-data expansion: weather, shipping, energy, DBnomics, IMF,
  World Bank, BLS, Treasury, AkShare, Kraken, Hyperliquid.
- Prediction-market/Polymarket adapter as read-only or paper-only input.
- Mobile app roadmap using a read-only-first model.
- UI roadmap for research workspace, strategy editor, backtest history, risk,
  execution, and knowledge intake.
