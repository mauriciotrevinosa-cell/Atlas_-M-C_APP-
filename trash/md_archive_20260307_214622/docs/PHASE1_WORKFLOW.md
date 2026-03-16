# ATLAS Phase 1 Workflow (Official v5 Execution)

Last updated: 2026-03-04

## Scope implemented in this iteration

- Data Layer: provider priority, cache + metadata, offline cache fallback, PIT (`as_of_utc`, `pit.version`, `dataset_hash`), integrity checks.
- Analytics Layer: simple/log returns, rolling volatility, rolling cross-asset correlation, correlation heatmap, candlestick patterns (doji + engulfing), per-run CSV/JSON/renders.
- Simulation Layer: multi-asset Monte Carlo (GBM moments from historical log returns), distribution outputs, sample paths, histogram, fan chart.
- Risk Layer: historical VaR, CVaR, simulated max drawdown, probability of loss threshold, quantile table, risk report render.
- ARIA Layer: formal tool registry for `atlas_get_data`, `atlas_analytics`, `atlas_simulate`, `atlas_risk`, `atlas_phase1_run`, and secure script runner.

## Operational status (2026-03-04)

- `python run_atlas.py` now registers official Phase 1 tools in browser mode by default.
- Launcher visibility: startup logs explicitly print active Phase 1 tools.
- New launcher env switch:
  - `ATLAS_ENABLE_PHASE1_TOOLS=1` (default)
  - `ATLAS_ENABLE_PHASE1_TOOLS=0` (disable registration)
- Verified tool list in runtime registration:
  - `atlas_get_data`
  - `atlas_analytics`
  - `atlas_simulate`
  - `atlas_risk`
  - `atlas_phase1_run`
  - `atlas_run_script`

## Extended modules now available (aligned with workflow expansion)

- `python/src/atlas/core/intraday_patterns/`
- `python/src/atlas/core/options_probability/`
- `python/src/atlas/core/whale_detection/`
- `python/src/atlas/core/signal_discovery/`
- `python/src/atlas/core/system_models/`
- `python/src/atlas/core/validation/`
- `python/src/atlas/research/`

These moved from partial skeleton state to importable runnable modules and are covered by focused unit tests.

## Validation snapshot

- Command:

```powershell
python -m pytest tests/unit/test_core_extensions.py tests/unit/test_phase1_workflow.py -q
```

- Result: `10 passed`

## Canonical code

- `python/src/atlas/market_finance/data_layer.py`
- `python/src/atlas/market_finance/analytics_layer.py`
- `python/src/atlas/market_finance/simulation_layer.py`
- `python/src/atlas/market_finance/risk_layer.py`
- `python/src/atlas/market_finance/pipeline.py`
- `python/src/atlas/assistants/aria/tools/atlas_phase1.py`

## One-command demo

```powershell
python run_atlas.py --demo
```

Optional direct script:

```powershell
python scripts/run_phase1_demo.py --symbols AAPL MSFT SPY
```

## Run artifacts

For each run id at `outputs/runs/<run_id>/`:

- `manifest.json`
- `logs/events.jsonl`
- `data/*/dataset.csv` + `metadata.json`
- `analytics/*.csv|*.json|correlation_heatmap.png`
- `simulation/*.csv|*.json|*.npz|portfolio_histogram.png|portfolio_fan_chart.png`
- `risk/risk_report.json` + `quantiles_table.csv` + `portfolio_distribution.png`
