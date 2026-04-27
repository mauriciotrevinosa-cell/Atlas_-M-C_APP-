**PROJECT ATLAS**

COMPREHENSIVE ROADMAP & ACTION PLAN

*From Scattered Modules to Unified, Real-Time Trading Platform*

M&C \| Confidential \| v1.0

March 25, 2026

Executive Summary

Project Atlas has grown from a concept into a 441-module quantitative
research and trading platform over the past two months. The Phase 1
pipeline (data, analytics, simulation, risk) is production-ready, ARIA
is functional with multi-provider LLM support, and 20+ phases of
functionality exist in various states of completion.

However, three critical gaps are preventing Atlas from reaching its full
potential:

1.  **Disconnected modules:** Many modules exist as standalone
    implementations that don\'t communicate with each other through a
    unified data bus or event system.

2.  **Untapped API ecosystem:** Atlas currently relies almost
    exclusively on yfinance for market data, with Ollama for LLM. Dozens
    of free and freemium APIs (FRED, Alpha Vantage, SEC EDGAR, Finnhub,
    NewsAPI) remain unwired.

3.  **Root-level clutter:** Orphan scripts, temp files, debug logs, and
    an empty Makefile create friction. The project needs a clean,
    professional structure.

This roadmap provides a phased, actionable plan to transform Atlas from
a collection of impressive but isolated modules into a fully integrated,
real-time trading and research platform.

Current State Audit

What Works (Production-Ready)

  -------------------- ------------------------------------------------------------------------------------------- ----------------
  **Component**        **Details**                                                                                 **Status**
  Phase 1 Pipeline     Data layer with Yahoo, caching, PIT support, analytics, Monte Carlo GBM, VaR/CVaR risk      **PRODUCTION**
  ARIA Assistant       Multi-provider (Ollama/Groq/OpenRouter/Cerebras), tool registry, 26+ tools, memory layers   **PRODUCTION**
  Artifact Framework   6 typed schemas, event bus, registry, SQLite persistence                                    **PRODUCTION**
  Signal Terminal      Twitter/Reddit/RSS/SEC collectors, classifier pipeline, whale detection                     **BETA**
  Viz Lab              23 renderers (Canvas 2D + Three.js), including particle systems                             **PRODUCTION**
  Pixel Agents         VS Code extension, TypeScript/React, published to marketplace                               **COMPLETE**
  -------------------- ------------------------------------------------------------------------------------------- ----------------

What Needs Work

  --------------------- ----------------------------------------------------------------------------------- --------------
  **Component**         **Gap**                                                                             **Status**
  RL/ML Agents          Framework scaffolding exists but no trained models, no data pipeline feeding them   **SKELETON**
  C++ HFT Module        CMakeLists.txt present, zero implementation code                                    **SKELETON**
  Auto-Trader           Logic present but no broker integration for real execution                          **PARTIAL**
  Options/Derivatives   Black-Scholes engine works but no real options data feed                            **PARTIAL**
  Web UI                Minimal Streamlit dashboard, needs full modern interface                            **SKELETON**
  API Integrations      Only yfinance for data; no FRED, Alpha Vantage, news APIs, etc.                     **MISSING**
  Inter-Module Bus      Modules don\'t share state; no unified event/message system                         **MISSING**
  Build System          Makefile empty, no CI/CD, root littered with orphan scripts                         **BROKEN**
  --------------------- ----------------------------------------------------------------------------------- --------------

Free & Freemium API Catalog

One of the biggest unlocks for Atlas is realizing that many powerful
APIs offer generous free tiers. Here is the complete catalog of APIs to
integrate, organized by category.

Market Data APIs

  ---------------------- ------------------------- ----------------------------------------------------- ------------ --------------
  **API**                **Free Tier**             **Data Types**                                        **Key?**     **Priority**
  Alpha Vantage          25 calls/day (free key)   Stocks, forex, crypto, indicators, fundamentals       Yes (free)   **HIGH**
  FRED (St. Louis Fed)   Unlimited (free key)      10,000+ macro series: GDP, CPI, unemployment, rates   Yes (free)   **HIGH**
  Polygon.io             5 calls/min (free)        Stocks, options, crypto, forex, news                  Yes (free)   **HIGH**
  Finnhub                60 calls/min (free)       Real-time quotes, news, fundamentals, crypto          Yes (free)   **HIGH**
  Yahoo Finance          Unlimited (no key)        Stocks, ETFs, options, fundamentals                   No           **ACTIVE**
  CoinGecko              10-30 calls/min           Crypto prices, market cap, volume, DeFi               Optional     **MEDIUM**
  Twelve Data            800 calls/day             Stocks, forex, crypto, technical indicators           Yes (free)   **MEDIUM**
  ---------------------- ------------------------- ----------------------------------------------------- ------------ --------------

News & Sentiment APIs

  -------------- ---------------------- ----------------------------------------- ----------------- --------------
  **API**        **Free Tier**          **Data Types**                            **Key?**          **Priority**
  NewsAPI        100 calls/day          Global news headlines, search, sources    Yes (free)        **HIGH**
  SEC EDGAR      10 calls/sec           10-K, 10-Q, 8-K filings, insider trades   No (User-Agent)   **HIGH**
  Finnhub News   Included in free       Market news, press releases, IPOs         Yes (free)        **HIGH**
  Reddit API     100 calls/min (free)   Subreddit posts, comments, sentiment      Yes (free)        **MEDIUM**
  GNews          100 calls/day          News articles, search by keyword/topic    Yes (free)        **MEDIUM**
  -------------- ---------------------- ----------------------------------------- ----------------- --------------

AI & Machine Learning APIs

  ------------------ --------------------- ------------------------------------------------------------ ------------ --------------
  **API**            **Free Tier**         **Capabilities**                                             **Key?**     **Priority**
  HuggingFace        Rate-limited free     NLP models, sentiment analysis, embeddings, classification   Yes (free)   **HIGH**
  Groq               Free tier available   Ultra-fast LLM inference (Llama, Mixtral)                    Yes (free)   **ACTIVE**
  OpenRouter         Some free models      Multi-model routing, 100+ models                             Yes (free)   **ACTIVE**
  Anthropic Claude   Pay per token         Advanced reasoning, analysis, code generation                Yes (paid)   **OPTIONAL**
  Ollama (local)     Unlimited (local)     Run any open model locally, zero cost                        No           **ACTIVE**
  ------------------ --------------------- ------------------------------------------------------------ ------------ --------------

Economic & Alternative Data APIs

  ----------------------- --------------- ---------------------------------------------------- ------------ --------------
  **API**                 **Free Tier**   **Data Types**                                       **Key?**     **Priority**
  FRED                    Unlimited       GDP, CPI, interest rates, employment, money supply   Yes (free)   **HIGH**
  World Bank              Unlimited       Global development indicators, country data          No           **LOW**
  BLS (Bureau of Labor)   Unlimited       Employment, CPI, wages, productivity                 Yes (free)   **MEDIUM**
  Treasury.gov            Unlimited       Treasury rates, yield curves, auction data           No           **MEDIUM**
  ----------------------- --------------- ---------------------------------------------------- ------------ --------------

Execution Roadmap

The roadmap is organized into 6 phases, each building on the previous.
Each phase has clear deliverables and can be validated independently.

Phase 1: Clean & Organize (Foundation)

**Timeline:** Week 1 \| **Risk:** Low

Before building anything new, we clean the house. A cluttered root and
empty build system signals an unfinished project.

Deliverables

-   **Root cleanup:** Move orphan scripts (find\_orphans.py,
    move\_orphans.py, calc\_portfolio.py, etc.) into scripts/utils/.
    Remove temp files (nul, orphans.txt, tmp\_\* files). Archive debug
    logs.

-   **Makefile:** Populate with targets: install, dev, test, lint,
    run-server, run-demo, run-aria, clean, docs.

-   **.env template:** Expand .env.example with all new API keys (FRED,
    Alpha Vantage, Finnhub, Polygon, NewsAPI, HuggingFace, Reddit) with
    clear documentation.

-   **pyproject.toml:** Add missing dependencies (fredapi,
    alpha\_vantage, finnhub-python, newsapi-python, feedparser,
    huggingface-hub). Create \[api\] optional dependency group.

Phase 2: API Integration Layer (Data Explosion)

**Timeline:** Weeks 2-3 \| **Risk:** Medium

This is the single biggest unlock. Every API integration multiplies what
every other module can do. We build a unified provider abstraction so
modules request data by type, not by source.

Architecture: Unified Data Provider

Create a DataProviderRegistry that routes requests to the best available
source with automatic fallback:

-   **get\_price(ticker, start, end)** tries: Polygon (real-time) -\>
    Finnhub -\> Alpha Vantage -\> Yahoo (fallback)

-   **get\_macro(series\_id)** tries: FRED -\> BLS -\> Treasury.gov

-   **get\_news(topic, ticker)** tries: Finnhub -\> NewsAPI -\> RSS
    feeds

-   **get\_filings(ticker)** tries: SEC EDGAR (primary, no fallback
    needed)

-   **get\_sentiment(text)** tries: HuggingFace -\> Ollama local model

Deliverables

-   Unified DataProviderRegistry in
    python/src/atlas/data\_layer/registry.py

-   Individual provider adapters: fred\_provider.py,
    alphavantage\_provider.py, polygon\_provider.py,
    finnhub\_provider.py, newsapi\_provider.py, sec\_edgar\_provider.py,
    huggingface\_provider.py

-   API key management via .env with graceful degradation (no key = skip
    provider)

-   Rate limiter per provider to respect free tier limits

-   Caching layer (SQLite) to minimize API calls

Phase 3: Inter-Module Communication Bus

**Timeline:** Week 3-4 \| **Risk:** Medium

The existing EventBus and ArtifactRegistry provide a foundation, but
modules still operate in silos. We extend this into a full service mesh
where any module can publish data and any other module can subscribe.

Architecture

-   **AtlasServiceBus:** Extends EventBus with typed channels
    (MARKET\_DATA, SIGNALS, RISK, NEWS, MACRO, ORDERS) and guaranteed
    delivery.

-   **Module Protocol:** Every module implements on\_data(channel,
    payload) and can publish(channel, payload). Standard interface for
    all 441 modules.

-   **State Store:** Shared, observable state dictionary. When
    data\_layer fetches new prices, analytics\_layer automatically
    recalculates, simulation\_layer re-runs, risk\_layer updates.

-   **WebSocket Bridge:** The service bus connects to the FastAPI
    WebSocket so the UI gets real-time updates without polling.

Phase 4: Complete Half-Built Modules

**Timeline:** Weeks 4-6 \| **Risk:** Medium-High

With the data layer and communication bus in place, we can now finish
the modules that have been waiting for real data.

  ----------------- ----------------------------------------------------------------------------------------------------------- ---------------- --------------
  **Module**        **Work Needed**                                                                                             **Depends On**   **Priority**
  ML Agents         Wire training pipeline to real data, implement feature engineering from live feeds, add model persistence   Phase 2 APIs     **HIGH**
  RL Agent          Connect DQN environment to real market data, implement proper reward shaping, add paper trading mode        Phase 2 + ML     **HIGH**
  Auto-Trader       Wire to Alpaca paper trading API (free), implement order management, connect to signal compositor           Phase 3 Bus      **HIGH**
  Options Engine    Connect to Polygon or Yahoo options data, replace synthetic IV with real IV, add real-time chain            Phase 2 APIs     **MEDIUM**
  Backtesting       Add multi-asset support, realistic fills, proper walk-forward with live data split                          Phase 2 APIs     **MEDIUM**
  Signal Terminal   Wire collectors to live feeds, add more sources, improve classifier with HuggingFace                        Phase 2 + 3      **MEDIUM**
  NLP Module        Integrate HuggingFace models for financial NER, connect to news pipeline                                    Phase 2 APIs     **MEDIUM**
  ----------------- ----------------------------------------------------------------------------------------------------------- ---------------- --------------

Phase 5: Real-Time Pipeline

**Timeline:** Weeks 6-8 \| **Risk:** High

The ultimate goal: Atlas processes real-time market data, runs signals
through all engines, presents decisions to the user, and can execute
trades with human approval.

The Real-Time Flow

4.  **Data Ingestion:** WebSocket connections to Finnhub/Polygon stream
    real-time quotes into the service bus.

5.  **Feature Extraction:** Analytics layer auto-recalculates on new
    ticks (volatility, indicators, chaos features).

6.  **Signal Generation:** All strategy engines (rule-based + ML + RL)
    generate signals on updated features.

7.  **Signal Composition:** Kelly criterion + volatility scaling produce
    weighted consensus.

8.  **Risk Check:** Guardrails verify position limits, daily P&L,
    drawdown constraints.

9.  **Decision Center:** UI presents trade proposals for human approval
    (ADVISORY mode).

10. **Execution:** Approved trades route to Alpaca paper trading via the
    auto-trader.

11. **Post-Trade:** Attribution, slippage analysis, and memory update
    close the loop.

Phase 6: Polish & Scale

**Timeline:** Weeks 8-12 \| **Risk:** Medium

-   **Modern Web UI:** Replace Streamlit with a React/Next.js dashboard
    that leverages the WebSocket service bus for real-time updates.

-   **C++ Performance Core:** Implement the order book engine and signal
    processing in C++ with pybind11 bridge for latency-critical paths.

-   **Testing & CI:** Expand test suite from 24 to 100+ tests, add
    GitHub Actions CI pipeline, automated linting.

-   **Documentation:** Auto-generate API docs from FastAPI, update all
    22 doc files, create user guide.

-   **Deployment:** Docker containerization, cloud deployment options,
    multi-device sync.

Immediate Actions (Starting Now)

These are the concrete first steps I will begin executing in this
session and the next:

  -------- --------------------------------------------------------------------- ---------------------------- ------------
  **\#**   **Action**                                                            **Impact**                   **Effort**
  1        Clean root directory: move orphans, delete temp files, archive logs   Professional codebase        30 minutes
  2        Populate Makefile with standard targets                               One-command operations       15 minutes
  3        Expand .env.example with all API key slots                            Clear onboarding for APIs    10 minutes
  4        Build FRED provider (unlimited free, macro data)                      10,000+ new data series      1 hour
  5        Build Alpha Vantage provider (stocks + fundamentals)                  Redundant data source        1 hour
  6        Build Finnhub provider (real-time + news)                             Real-time data + news feed   1 hour
  7        Build SEC EDGAR provider (filings)                                    Fundamental analysis data    1 hour
  8        Create DataProviderRegistry with fallback chain                       Unified data access          2 hours
  9        Wire providers to existing data\_layer.py                             All modules get new data     1 hour
  10       Update pyproject.toml with new dependencies                           Clean install process        10 minutes
  -------- --------------------------------------------------------------------- ---------------------------- ------------

Success Metrics

-   **Phase 1 complete:** Zero orphan files in root, Makefile with 8+
    targets, clean .env template

-   **Phase 2 complete:** 5+ API providers integrated,
    DataProviderRegistry operational, all existing modules can request
    data from multiple sources

-   **Phase 3 complete:** AtlasServiceBus handles 6+ typed channels,
    modules auto-react to data changes

-   **Phase 4 complete:** ML/RL agents train on real data, auto-trader
    executes paper trades

-   **Phase 5 complete:** End-to-end real-time pipeline: live data in,
    signals out, trades executed on paper

-   **Phase 6 complete:** Modern UI, 100+ tests, CI/CD, Docker
    deployment, documentation complete

Philosophy Going Forward

Atlas is a living system (sistema vivo). Every change follows the Atlas
Vision workflow: think improvement, implement small, connect to Atlas,
verify in UI/API, iterate. We don\'t build in isolation anymore. Every
new module must plug into the service bus, consume data from the
provider registry, and be testable independently. The era of standalone
scripts is over.
