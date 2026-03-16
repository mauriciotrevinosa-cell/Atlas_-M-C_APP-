# 🧭 PROJECT ATLAS — WORKFLOW v7.0: THE M&C ECOSYSTEM

**Última Actualización:** 2026-03-06
**Versión:** 7.0 (Paradigm Shift: Atlas as the M&C visual ecosystem, ARIA 3D Jarvis UI, Swarm Consensus, and Internal Interactive Terminal)

---

## 🎯 CHANGELOG v6.4 → v7.0 (2026-03-06) — The M&C Ecosystem Paradigm

### **NEW — Strategic Vision (Phase 1: Implementación Bruta)**
- **Atlas is no longer just a trading bot.** It is the comprehensive visual ecosystem and operating system that sustains M&C.
- **Interactive Internal Terminal:** A new UI panel inside Atlas where the user can visualize technical indicators, candlestick patterns, toggle them on/off, combine them visually, and run simulations directly.
- **ARIA 3D 'Jarvis' UI:** Frontend (Three.js/JS) integration to render ARIA as an interactive, pulsating 3D energy core/brain that reacts physically when processing or speaking.
- **Global Market Access & Paper Trading:** ARIA is unchained from the local portfolio. She can scan entire sectors/indices, generate proactive high-risk ideas, and manage her own "Trader Spreadsheet" (Paper Trading) to test alpha generation.
- **Institutional Quant Hedge Fund Architecture:**
  1. **Macroeconomic NLP Engine:** Real-time ingestion of FED minutes, social sentiment, and news into mathematical tensors.
  2. **Multi-Agent Consensus (Swarm):** A committee of specialized agents (Risk, Momentum, Options) reporting to ARIA (CEO) for final decisions.
  3. **Non-Linear Black Swan Optimization:** Using ALADDIN/Qlib models to calculate mathematical hedging strategies for market crashes.

---

## 🎯 CHANGELOG v6.3 → v6.4 (2026-03-04) — Phase 1 Consolidation + Core Expansion

### **NEW — Core Quant Modules Implemented (from skeleton to runnable code)**
- `python/src/atlas/core/intraday_patterns/`
  - `engine.py`, `gap_analyzer.py`, `opening_drive.py`, `session_model.py`
  - Gap continuation detection, opening-drive signals, session volatility profiles
- `python/src/atlas/core/options_probability/`
  - `engine.py`, `fetcher.py`, `iv_surface.py`, `distribution.py`
  - Options chain ingestion, IV surface extraction, risk-neutral style distribution approximation
- `python/src/atlas/core/whale_detection/`
  - `engine.py`, `flow.py`, `options_flow.py`, `volume.py`
  - Volume anomaly + institutional flow proxy + unusual options activity fusion
- `python/src/atlas/core/signal_discovery/`
  - `engine.py`, `pattern_scanner.py`, `correlation.py`, `feature_ranker.py`
  - Pattern mining, lead-lag correlations, feature relevance ranking
- `python/src/atlas/core/system_models/`
  - `utility_functions.py`, `constraint_engine.py`, `probabilistic_state.py`
  - Utility scoring, feasibility constraints, probabilistic regime-state inference
- `python/src/atlas/core/validation/`
  - `pbo.py`, `walk_forward.py`, `cross_validation.py`, `bootstrap_tests.py`, `scorer.py`
  - Anti-overfitting toolkit: PBO, purged CV, bootstrap significance, composite scoring
- `python/src/atlas/research/`
  - `pipeline.py`, `idea.py`, `validator.py`, `report.py`
  - End-to-end research loop (idea → data → returns model → statistical validation → artifacts)

### **NEW — Launcher Integration (run_atlas.py)**
- Browser launcher now registers official Phase 1 ARIA tools at startup by default:
  - `atlas_get_data`, `atlas_analytics`, `atlas_simulate`, `atlas_risk`, `atlas_phase1_run`, `atlas_run_script`
- New env toggle:
  - `ATLAS_ENABLE_PHASE1_TOOLS=1` (default enabled)
  - `ATLAS_ENABLE_PHASE1_TOOLS=0` disables this registration explicitly
- Startup logs now show which Phase 1 tools are active for visibility.

### **NEW — Test Baseline for New Modules**
- Added `tests/unit/test_core_extensions.py` for:
  - intraday patterns, whale detection, signal discovery, system models,
    validation stack, options probability engine (local chain), research pipeline
- Verified with:
  - `python -m pytest tests/unit/test_core_extensions.py tests/unit/test_phase1_workflow.py -q`
  - Result: `10 passed`

### **STATUS SNAPSHOT (2026-03-04)**
- Phase 1 official pipeline is operational end-to-end.
- Core expansion modules imported successfully and are now executable APIs instead of broken skeleton imports.
- Local-first implementation preserved (free providers + offline-safe pathways where possible).

---

## 🎯 CHANGELOG v6.0 → v6.1 (2026-02-27) — UI Polish + Bug Fixes

### **FIXED:**
- **Dark-view padding bug** — `#view-derivatives.active { padding: 0 }` was beating modules' injected
  `padding: 16px` due to higher CSS specificity (1-1-0 vs 1-0-0). Corrected to plain `#view-* { padding: 0 }`
  so injected styles (later cascade) win. Bottom padding updated to 80px in both modules.
- **pattern_memory.py missing from main repo** — was only in worktree; copied to
  `python/src/atlas/memory/pattern_memory.py` so server.py imports succeed.

### **IMPROVED:**
- **Dashboard live stats** — replaced hardcoded placeholders (12 / $4.2k / 8) with:
  - `_refreshDashboardStats()` in `app.js` fetches `/api/vizlab/system_status` + 5 strategy analyses
  - Stat 1 → active BUY/SELL signal count across SPY/QQQ/AAPL/NVDA/MSFT
  - Stat 2 → `online/total` modules (e.g. "9/11")
  - Stat 3 → "5" (engines always present)
  - Auto-refreshes every 60 seconds; graceful "—" fallback if offline

### **AUDITED:**
- 11 JS files, 9 Python modules, server.py — all pass AST/Function syntax checks ✅

---

## 🎯 CHANGELOG v6.2 → v6.3 (2026-02-28) — ARIA Multi-Provider v3.0

### **NEW — ARIA Multi-Provider Backend (server.py)**
- `_ask_with_provider(message, preferred)` — async route with Ollama → Groq → OpenRouter → Cerebras fallback chain
- `_ask_openai_compat_sync()` — OpenAI-compatible call reused by all cloud providers
- `_providers()` — lazy config load from env vars (`GROQ_API_KEY`, `OPENROUTER_API_KEY`, `CEREBRAS_API_KEY`)
- `_aria_audit_log` — in-memory append-only request log (capped at 500 entries)
- Provider fallback order: `ollama → groq → openrouter → cerebras`

### **NEW — ARIA Slash Commands (server.py `/query` fast path)**
- `/providers` — lists all 4 providers + availability + active model
- `/model <name>` — switches active provider (no LLM call)
- `/audit [n]` — shows last n audit log entries with latency + fallback info
- `/debug <topic>` — structured 4-step debug protocol
- `/review <ticker>` — strategy review checklist linking all relevant API endpoints
- `/help` — command reference table

### **NEW — ARIA API Routes (server.py)**
- `GET /api/aria/providers` — provider registry + active + fallback_order
- `POST /api/aria/set_provider` — switch active provider
- `GET /api/aria/audit?limit=20` — session audit log with stats
- `GET /api/aria/status` — quick health check: model, success rate, initialised

### **IMPROVED — QueryResponse model**
- Added `provider: Optional[str]` and `latency_ms: Optional[int]` fields

### **NEW — ARIA Provider Toolbar (index.html + app.js)**
- Provider pill buttons: ⚡ Auto | 🖥 Local | 🟣 Groq | 🌐 OpenRouter | 🧠 Cerebras
- Active provider highlighted in orange; unavailable (no key) shown dimmed
- Latency badge: updates after each response (color-coded green/amber/red)
- ARIA status dot: green online / red offline

### **NEW — Slash Command Hint Bar (index.html + app.js)**
- Appears when user types `/`; shows all commands as clickable chips
- Tab key autocompletes the closest matching command

### **NEW — Markdown Rendering for ARIA (app.js `_renderMarkdown()`)**
- Handles: **bold**, *italic*, `inline code`, ```code blocks```, # headers, tables, - lists, --- hr, [ ] checkboxes

### **NEW — CSS (styles.css)**
- Provider pill hover, slash hint hover, ARIA markdown colours (strong/em/pre/table/th)

---

## 🎯 CHANGELOG v5.0 → v6.0 (2026-02-27)

### **AGREGADO:**
- ✅ **Signal Compositor** (Fase 5) — `signal_composition/signal_compositor.py`
  - `Signal` + `OrderProposal` dataclasses, fully typed
  - Kelly Criterion (half-Kelly): f* = (p·b−q)/b × 0.5, capped at max_kelly
  - Volatility scaling: target_vol / realised_vol, clipped to [0.25, 4.0]
  - Weighted consensus voting across engines → (action, composite_confidence)
  - `SignalCompositor.compose()`: full pipeline → OrderProposal
  - Hard guardrails: daily loss limit + max drawdown enforcement
  - `.size_scenarios()` table for UI position sizing display
  - API: `GET /api/signal/compose/{ticker}`, `GET /api/signal/scenarios`
- ✅ **Post-Trade Analytics** (Fase 15) — `post_trade/post_trade.py`
  - `TradeRecord` dataclass with pnl/pnl_pct/won properties
  - `trade_attribution()`: P&L/win-rate/expectancy by engine + regime
  - `alpha_decay_analysis()`: IC vs forward horizon (1/3/5/10/20 bars)
  - `mae_mfe_analysis()`: MAE/MFE per trade, exit efficiency
  - `slippage_analysis()`: intra-bar half-spread vs assumed bps
  - `PostTradeAnalyzer` unified interface + `engine_leaderboard()`
  - API: `POST /api/posttrade/report`
- ✅ **Enhanced Memory** (Fase 10) — `memory/pattern_memory.py`
  - `MarketSnapshot` 7-dimensional state vector (trend, vol, RSI, momentum × 2, regime, conf)
  - `PatternMemory` with cosine/euclidean similarity search, rolling FIFO buffer (2000)
  - `RegimeMemory` regime transition tracking + per-regime P&L stats
  - `EnhancedMemoryStore` JSON persistence + `.memory_summary()`
  - API: `GET /api/memory/summary`, `POST /api/memory/snapshot`
- ✅ **Enhanced Backtest Runner** (Fase 11) — `backtesting/runner.py`
  - Sortino ratio (downside-deviation adjusted), Calmar ratio (CAGR/MaxDD), CAGR
  - Trade-by-trade log (entry, exit, direction, holding_bars, pnl_pct, won)
  - Walk-forward analysis: n_folds IS/OOS splits, degradation measurement
  - Commission model (bps one-way), vectorised execution
  - API: `GET /api/backtest/enhanced/{ticker}?walkforward=true`
- ✅ **Black-Scholes Options Engine** (Fase 12.4) — `derivatives/options/black_scholes.py`
  - Pure numpy: A&S normal CDF approximation (max error 7.5e-8)
  - Full Greeks: Delta, Gamma, Theta (per day), Vega (per 1%), Rho (per 1%)
  - Implied Vol: Newton-Raphson + bisection fallback (Brenner-Subrahmanyam init)
  - `options_chain()`: ATM ± n strikes with vol smile/skew proxy
  - `iv_surface()`: full term structure × strike grid
  - `synthetic_positions()`: Straddle, Strangle, Bull Spread, Bear Spread
  - API: `GET /api/options/chain/{ticker}`, `GET /api/options/greeks`, `GET /api/options/surface/{ticker}`
- ✅ **Derivatives Dashboard** (Fase 12.4 UI) — `apps/desktop/derivatives.js`
  - Greeks Calculator panel with live recalc on input change
  - Options Chain table (call/put, heatmap ATM row)
  - IV Surface heatmap (Canvas 2D, expiry × strike grid)
  - Synthetic Positions panel (Straddle, Strangle, Bull/Bear Spreads)
  - Signal Composer integration (Kelly + vol sizing per ticker)
  - Accessible from Dashboard + nav icon
- ✅ **Decision Center** (Fase 14 enhanced) — `apps/desktop/decision.js`
  - Live Signal Summary (5 tickers auto-polled, confidence bars)
  - Position Sizing Calculator: Kelly × vol scalar × confidence, fully interactive
  - Trade Approval Queue: Approve / Reject / Modify (resize) workflow
  - Risk Guardrails status panel (daily P&L, drawdown, capital)
  - Accessible from Dashboard + nav icon

### **ARCHITECTURAL NOTES:**
- All new Python modules: pure numpy, no scipy
- API routes all work offline via `_fetch_ohlcv_local()` synthetic fallback
- Decision Center is a client-side IIFE, no server state required for approvals
- Derivatives dashboard derives IV from realised vol; no options API keys needed

---

## 🎯 CHANGELOG v4.0 → v5.0 (2026-02-27)

### **AGREGADO:**
- ✅ **Chaos & Nonlinear Features** (Fase 3.5) — `chaos_features.py`
  - Hurst Exponent (R/S), DFA, Higuchi FD, Lyapunov proxy, ApEn, PermEn, Shannon
  - `ChaosFeatureExtractor` unified interface + regime labeling (6 regimes)
- ✅ **Entropy Features** — `entropy_features.py`
  - Rolling Shannon, Transfer Entropy (Schreiber 2000), IC Ratio (Spearman)
  - `MarketEntropyAnalyzer` + entropy regime classification (STRUCTURED/MODERATE/NOISY/CHAOTIC)
- ✅ **Advanced Volatility** — `vol_features.py`
  - Yang-Zhang 2000 (minimum variance OHLC), Garman-Klass, Realized Variance
  - Vol-of-Vol, vol regime state (LOW/NORMAL/HIGH/SPIKE), synthetic IV surface params
  - `RollingVolatilityEngine` unified interface
- ✅ **Factor Models** (Fase 4.4.4) — `factor_engine.py`
  - PCA decomposition (pure numpy/SVD, no scipy), factor attribution per asset
  - Factor timing signals (mean-reversion z-score), portfolio factor risk decomposition
  - `FactorModelEngine` full pipeline: fit → attribute → timing → summary
- ✅ **Viz Lab v2.0** — 10 new Canvas 2D visualizations (total: 20) — see v5.0 for details
- ✅ **Viz Lab v3.0** — 3 new Three.js particle shape visualizations (total: 23)
  - #11 Lorenz Attractor (two-attractor phase space, bull/bear regimes)
  - #12 Return Heatmap Calendar (GitHub-style, hover tooltips)
  - #13 Live Order Book (L2 bid/ask depth, spread dynamics, price chart)
  - #14 Vol Smile Surface (3D perspective IV surface, mouse-drag rotation)
  - #15 Entropy Cascade (time-frequency entropy waterfall)
  - #16 Portfolio Treemap (squarified, live PnL heat, hover detail)
  - #17 Candle River (scrolling OHLCV + MA20 + volume bars)
  - #18 Factor Wheel (PCA loadings on rotating wheel, 4 factor rings)
  - #19 Drawdown Mountain (equity curve + underwater drawdown terrain)
  - #20 Bid-Ask Spread Live (8-asset L2 monitor + sparklines + market impact)
- ✅ **5 New API Routes** (server.py) — all work 100% locally with synthetic fallback:
  - `GET /api/chaos/{ticker}` — chaos + entropy + vol features
  - `GET /api/volatility/{ticker}` — YZ/GK vol metrics + rolling panel
  - `GET /api/factors/decompose?tickers=...` — PCA factor decomposition
  - `GET /api/factors/attribution/{ticker}` — per-asset factor attribution
  - `GET /api/discrepancy/{ticker}` — multi-engine disagreement analysis
- ✅ `_generate_synthetic_ohlcv()` helper — GBM-based offline data fallback
- ✅ `_fetch_ohlcv_local()` helper — tries yfinance, gracefully falls back to synthetic

### **ARCHITECTURAL NOTES:**
- All new feature modules: pure numpy only, no scipy dependency
- Synthetic fallback seeded by ticker hash → deterministic, reproducible offline
- `ApEn` is O(n²) — documented; recommended for ≤200 bar series only

---

## 🎯 CHANGELOG v3.0 → v4.0

### **AGREGADO:**
- ✅ ML Engine Suite (XGBoost, LSTM, RandomForest)
- ✅ RL Trading Agent (DQN + Gym Environment)
- ✅ Auto-Trader Hybrid System (4 operating modes)
- ✅ C++ High-Performance Core (Order Book, Signals, Execution)
- ✅ 3D Visualizations (Vol Surface, Correlation Mountain, MC Mountain)
- ✅ ARIA Math Toolset (27 financial calculations + code executor)
- ✅ Point-in-Time Manager (no look-ahead bias)
- ✅ Run Context System (reproducible runs)

---

## 📊 WORKFLOW COMPLETO (20 FASES)

```
FASE 0    → Fundación                          ✅ COMPLETE
FASE 1    → Data Ingestion                     ✅ COMPLETE (Yahoo)
  1.2     → Derivatives data                   ⬜ NEEDS API KEYS
  1.3     → Point-in-Time Manager              ✅ GENERATED (in ZIP)
FASE 2    → Market State                       ✅ COMPLETE (Regime, Vol)
  2.3     → Derivatives Sentiment              ⬜ NEEDS DATA SOURCES
FASE 3    → Feature Extraction                 ✅ COMPLETE
  3.1     → Technical Indicators               ✅ IN REPO
  3.2     → Microstructure (VPIN, Kyle)        ✅ IN REPO
  3.3     → Candlestick Patterns               ✅ GENERATED (in ZIP)
  3.8     → Derivatives Features               ⬜ NEEDS DATA SOURCES
FASE 3.5  → Chaos & Nonlinear                  ✅ IN REPO (2026-02-27)
    3.5.1   → Hurst Exponent (R/S Analysis)     ✅ chaos_features.py
    3.5.2   → DFA Scaling Exponent              ✅ chaos_features.py
    3.5.3   → Higuchi Fractal Dimension          ✅ chaos_features.py
    3.5.4   → Shannon / ApEn / PermEn           ✅ chaos_features.py
    3.5.5   → Lyapunov Proxy (NN Divergence)    ✅ chaos_features.py
    3.5.6   → Transfer Entropy (Schreiber 2000) ✅ entropy_features.py
    3.5.7   → Rolling Shannon + IC Ratio        ✅ entropy_features.py
    3.5.8   → Yang-Zhang + Garman-Klass Vol     ✅ vol_features.py
    3.5.9   → Vol-of-Vol + Vol Regime State     ✅ vol_features.py
    3.5.10  → Synthetic IV Surface Params       ✅ vol_features.py
FASE 4    → Specialized Engines                ✅ PARTIAL
  4.1     → Rule-Based (SMA, RSI, MACD, BB, Momentum, MultiStrategy) ✅ IN REPO
  4.2     → ML Engines (XGB, LSTM, RF) + ml_agents Bridge  ✅ IN REPO
  4.3     → RL Agent (DQN)                     ✅ GENERATED (in ZIP)
  4.4     → Correlation Portfolio               ✅ IN REPO (NEW 2026-02-27)
    4.4.1   → Market Structure Analyzer        ✅ IN REPO
    4.4.2   → Pairs Trading Engine (ADF/Johansen) ✅ IN REPO
    4.4.3   → Regime Clustering (Ward/KMeans)  ✅ IN REPO
    4.4.4   → Factor Models (PCA)              ✅ IN REPO (2026-02-27)
              — factor_engine.py: pca_factor_decomposition, factor_attribution,
                factor_timing_signal, portfolio_factor_risk, FactorModelEngine
FASE 5    → Signal Composition                 ✅ COMPLETE (2026-02-27)
FASE 6    → Discrepancy Analysis               ✅ PARTIAL IN REPO (2026-02-27)
              — API route /api/discrepancy/{ticker} live
              — Runs all 5 strategy engines, computes disagreement score + consensus
FASE 7    → Risk & Fragility                   ✅ GENERATED (in ZIP)
  7.1     → VaR/CVaR, Stress Testing           ✅ GENERATED
  7.5     → Liquidation Risk                   ⬜ NEEDS DERIV DATA
FASE 8    → Monte Carlo                        ✅ COMPLETE
  8.1     → GBM, Heston, Jump-Diffusion        ✅ IN REPO
  8.2     → Dynamic Correlation                ✅ GENERATED (in ZIP)
FASE 9    → Orchestration / Auto-Trader        ✅ GENERATED (in ZIP)
  9.1     → Multi-Engine Consensus             ✅ GENERATED
  9.2     → GuardRails                         ✅ GENERATED
  9.3     → 4 Operating Modes                  ✅ GENERATED
FASE 10   → Memory                             ✅ ENHANCED (2026-02-27) — PatternMemory, RegimeMemory, similarity search
FASE 11   → Backtest                           ✅ ENHANCED (2026-02-27) — Sortino, Calmar, walk-forward, trade log
FASE 12   → Visualization                      ✅ GENERATED (in ZIP)
  12.1    → 2D Charts (matplotlib)             ✅ GENERATED
  12.2    → 3D Static (matplotlib 3D)          ✅ GENERATED
  12.3    → 3D Interactive (Three.js HTML)     ✅ GENERATED
  12.4    → Derivatives Dashboard              ✅ COMPLETE (2026-02-27) — Black-Scholes, Greeks, IV Surface, Synthetics, Composer
  12.5    → Viz Lab v2.0 (20 renders)         ✅ IN REPO (2026-02-27)
  12.6    → Viz Lab v3.0 (23 renders)         ✅ IN REPO (2026-02-27) — Particle Saturn/Heart/Morph (sphere-main inspired)
              — 10 original: Particle Universe, Neural Brain, Force Graph, Monte Carlo,
                Signal Radar, Risk Terrain, Flow Field, Correlation Galaxy, RL Track, Quantum
              — 10 new: Lorenz Attractor, Return Heatmap, Order Book, Vol Smile 3D,
                Entropy Cascade, Portfolio Treemap, Candle River, Factor Wheel,
                Drawdown Mountain, Bid-Ask Spread Live
  12.6    → Info Module (module documentation)  ✅ IN REPO (2026-02-27)
              — info.js: 36 documented entries across 8 categories
              — Categories: Data Sources, Strategies, Features, Correlation,
                Visualizations, AI/ML, Infrastructure
              — Per entry: description, data source, measurement method, API route, tags
              — Full-text search + category filter tabs + live result count
FASE 13   → ARIA                               ✅ FUNCTIONAL
  13.1    → Chat + Tool Calling                ✅ IN REPO
  13.2    → Math Toolset (27 tools)            ✅ GENERATED (in ZIP)
  13.3    → Code Executor                      ✅ GENERATED (in ZIP)
FASE 14   → User Decision                      ✅ ENHANCED (2026-02-27) — approval queue, sizing calc, guardrails panel
FASE 14.5 → Execution                          ✅ PARTIAL
  14.5.1  → Paper Broker                       ✅ IN REPO
  14.5.2  → C++ TWAP/VWAP                     ✅ GENERATED (in ZIP)
FASE 15   → Post-Trade                         ✅ COMPLETE (2026-02-27) — attribution, alpha decay, MAE/MFE, slippage
FASE 16   → C++ HFT Core                       ✅ GENERATED (in ZIP)
  16.1    → Order Book Engine                  ✅ GENERATED
  16.2    → Signal Engine (streaming)          ✅ GENERATED
  16.3    → pybind11 Bridge                    ✅ GENERATED
```

---

## 🤖 FASE 9 — AUTO-TRADER (NEW)

### Architecture

```
              ┌──────────────┐
              │  HUMAN INPUT │
              │  (override)  │
              └──────┬───────┘
                     │
┌──────────┐  ┌──────▼───────┐  ┌─────────────┐
│  RULES   │─▶│              │◀─│  ML ENGINES  │
│(SMA, RSI)│  │  AUTO-TRADER │  │(XGB,LSTM,RF) │
└──────────┘  │  (consensus) │  └─────────────┘
              │              │
┌──────────┐  │  GuardRails  │  ┌─────────────┐
│ RL AGENT │─▶│  ↓           │  │   RISK      │
│  (DQN)   │  │  Decision    │─▶│   ENGINE    │
└──────────┘  │  ↓           │  └─────────────┘
              │  Execute?    │
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │  EXECUTION   │
              │ (TWAP/VWAP)  │
              └──────────────┘
```

### Operating Modes

| Mode | Decision | Execution | When to Use |
|------|----------|-----------|-------------|
| **MANUAL** | Human | Human | Learning, research |
| **ADVISORY** | Atlas recommends | Human approves | Building trust |
| **SEMI_AUTO** | Atlas (>75% conf auto) | Atlas + guardrails | Proven strategies |
| **FULL_AUTO** | Atlas | Atlas + guardrails | Paper trading / tested |

### GuardRails (ALWAYS active, even in FULL_AUTO)

| Rule | Default | Configurable |
|------|---------|-------------|
| Max position size | 10% of capital | Yes |
| Max daily loss | 2% | Yes |
| Max drawdown | 10% | Yes |
| Max trades/day | 20 | Yes |
| Min confidence | 60% | Yes |
| Max leverage | 1x | Yes |

---

## 🧠 FASE 4.2 — ML ENGINES (NEW)

### Models Available

| Engine | Type | Input | Best For |
|--------|------|-------|---------|
| **XGBoost** | Gradient Boosted Trees | Tabular features | Structured data, fast training |
| **RandomForest** | Ensemble Trees | Tabular features | Baseline, feature importance |
| **LSTM** | Recurrent Neural Network | Sequences | Sequential patterns, temporal |

### Feature Pipeline
Automatic feature generation from OHLCV:
- Returns (1d, 5d, 10d, 20d)
- Volatility (5d, 10d, 20d rolling)
- Volume ratios and changes
- Price position (high-low range, close position)
- SMA distances (5, 10, 20, 50)
- RSI (14), MACD, Bollinger %B

### Label Types
- `direction`: Binary (up/down in horizon)
- `return`: Actual forward return
- `triple`: -1/0/1 based on volatility threshold

---

## 🎮 FASE 4.3 — RL AGENT (NEW)

### Environment
- **State:** Features + [position, unrealized_PnL, capital%, step%]
- **Actions:** HOLD(0), BUY(1), SELL(2), CLOSE(3)
- **Reward:** Risk-adjusted PnL (Sharpe or Sortino aware)

### Agent (DQN)
- 3-layer fully connected network
- Experience replay (50K buffer)
- Target network (updated every 10 steps)
- Epsilon-greedy decay (1.0 → 0.01)
- Minimum 100 episodes training recommended

---

## 📊 FASE 12 — VISUALIZATION (EXPANDED)

### 2D Charts (matplotlib Agg)
1. Correlation heatmap
2. Monte Carlo fan (percentile bands)
3. Drawdown chart
4. PnL distribution (histogram + VaR lines)

### 3D Static (matplotlib 3D → PNG)
1. Volatility Surface (strike × expiry × IV)
2. Correlation Mountain (asset × asset × ρ)
3. P&L Surface (parameter sweeps)
4. Monte Carlo Mountain (density over time)
5. Risk Landscape (VaR across allocations)
6. Order Book Depth 3D (depth over time)

### 3D Interactive (Three.js → standalone HTML)
1. Volatility Surface (drag/rotate/zoom)
2. Correlation Mountain (colored bars)
3. Monte Carlo Mountain (density bars)

---

## 🎯 INTEGRATION PRIORITY

### Tier 1: CRITICAL (integrate first)
1. `ATLAS_WORKFLOW_V3_GAPS.zip` — Fills 90% of empty modules
2. `ATLAS_ML_RL_AUTOTRADER.zip` — Enables AI trading

### Tier 2: HIGH (integrate next)
3. `ATLAS_CPP_AND_3D.zip` — Enables 3D viz + future HFT
4. `ARIA_MATH_TOOLS.zip` — Enhances ARIA capabilities

### Tier 3: AFTER INTEGRATION
5. Wire auto_trader to connect all engines
6. Train ML models on historical data
7. Train RL agent on paper trading environment
8. Derivatives data sources (needs API keys)
9. Full web UI (React/Next.js)

---

### FASE 12.5 — VIZ LAB (NEW 2026-02-27)
```
12.5.1  Particle Market Universe (Three.js, 15k pts, 5 regime shapes)  ✅ LIVE
12.5.2  ARIA Neural Brain (force-directed module graph)                 ✅ LIVE
12.5.3  Market Force Graph (correlation star field)                     ✅ LIVE
12.5.4  Monte Carlo Paths (animated GBM fan)                           ✅ LIVE
12.5.5  Signal Radar (multi-indicator spider chart)                     ✅ LIVE
12.5.6  Risk Terrain (procedural isometric 3D terrain)                 ✅ LIVE
12.5.7  Price Flow Field (vector field + particles)                     ✅ LIVE
12.5.8  Correlation Galaxy (Milky Way sector clusters)                  ✅ LIVE
12.5.9  RL Racing Track (speed-racer-rl inspired, DQN agent)           ✅ LIVE
12.5.10 Quantum Market Superposition (wave collapse on signal)          ✅ LIVE
```
Access via: Dashboard → Viz Lab card, or bottom nav atom icon.
Backend: 5 new `/api/vizlab/*` routes with live market data.

---

---

## 📊 FASE 4.4 — TRADING ALGORITHM EXPANSION (2026-02-27)

```
4.1  Rule-Based Engine Suite (5 strategies + consensus)
  sma_crossover.py       Fast(20)/Slow(50) MA crossover                ✅ LIVE
  rsi_mean_reversion.py  RSI + BB + ADX filter, oversold/overbought    ✅ LIVE
  macd_engine.py         3-trigger MACD (crossover/zero/histogram)     ✅ LIVE
  bb_squeeze.py          Keltner+BB compression → directional breakout ✅ LIVE
  momentum_engine.py     TSMOM (21/63/126d) + MA align + VPT           ✅ LIVE
  multi_strategy.py      Consensus engine, weighted 5-engine agreement  ✅ LIVE

4.2  ML Agents Bridge (ml_agents/__init__.py)
  MLSignalAdapter        AutoTrader-compatible wrapper for any MLEngine ✅ LIVE
  MLAgentBridge          Factory: XGBoost + RF + LSTM adapters          ✅ LIVE
  make_ml_sources()      Convenience for register_source()              ✅ LIVE

4.4  Correlation Portfolio
  market_structure.py    Rolling regime (low/normal/high/crisis), centrality  ✅ LIVE
  pairs_engine.py        ADF cointegration, z-score signals, half-life        ✅ LIVE
  regime_clustering.py   Ward/KMeans clustering + PCA + silhouette            ✅ LIVE
```

**Strategy API Routes** (server.py):
- `GET /api/strategy/analyze/{ticker}` — 5-engine consensus + per-engine signals
- `GET /api/strategy/backtest/{ticker}` — Walk-forward equity curve + Sharpe/DD
- `GET /api/strategy/engines` — Engine registry list
- `GET /api/correlation/cluster` — Hierarchical/KMeans clustering
- `GET /api/correlation/pairs` — Cointegrated pairs + z-score signals
- `GET /api/correlation/structure` — Market regime + diversification score

**Finance View UI** (strategy.js, ~280 lines):
- Multi-Strategy Scanner: ticker + period selector → consensus + per-engine grid
- Quick Backtest: walk-forward equity curve with Canvas chart
- Market Structure: regime + diversification + top correlated pairs
- Asset Clustering: colored cluster groups + silhouette score
- Pairs Trading: cointegrated pairs + current signal + z-score

---

**Workflow v4.2 — Trading Algorithm Expansion + Correlation Portfolio**
**Última Actualización:** 2026-02-27
**Próxima Revisión:** ML training pipeline, factor_models, and RL integration
