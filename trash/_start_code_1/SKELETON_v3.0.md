# 🏗️ ATLAS SKELETON v3.0 - DERIVATIVES UPDATE

**Fecha:** 2026-01-30  
**Versión:** 3.0  
**Cambios:** Agregado Derivatives Dashboard (CoinGlass-style)

---

## 🆕 NUEVAS CARPETAS Y ARCHIVOS

### **1. Data Layer - Derivatives Sources** 🆕
```
python/src/atlas/data_layer/sources/derivatives/
├─ __init__.py
├─ coinglass.py              # CoinGlass API wrapper
├─ hyperliquid.py            # Hyperliquid direct API
├─ binance_futures.py        # Binance Futures API
└─ data_aggregator.py        # Combine multiple sources
```

### **2. Market State - Derivatives Sentiment** 🆕
```
python/src/atlas/core_intelligence/market_state/derivatives_sentiment/
├─ __init__.py
├─ funding_sentiment.py      # Funding as sentiment indicator
└─ oi_conviction.py          # Open Interest conviction analysis
```

### **3. Features - Derivatives** 🆕
```
python/src/atlas/core_intelligence/features/derivatives/
├─ __init__.py
├─ liquidation_zones.py      # Detect liquidation clusters
├─ funding_analysis.py       # Funding divergence & reversals
├─ oi_analysis.py            # OI vs Price divergence
└─ lsr_analysis.py           # Long/Short Ratio analysis
```

### **4. Risk - Liquidation Risk** 🆕
```
python/src/atlas/risk/liquidation_risk/
├─ __init__.py
├─ liquidation_calculator.py # Calculate liquidation prices
└─ cluster_avoidance.py      # Avoid liquidation clusters
```

### **5. Derivatives - Dashboard Metrics** 🆕
```
python/src/atlas/derivatives/dashboard_metrics/
├─ __init__.py
├─ heatmap_data.py           # Prepare heatmap data
└─ sentiment_scores.py       # Aggregate sentiment
```

### **6. UI - Derivatives Dashboard** 🆕
```
ui_web/src/pages/DerivativesDashboard/
├─ index.tsx                 # Main dashboard layout
├─ LiquidationHeatmap.tsx    # Interactive heatmap
├─ OpenInterestChart.tsx     # OI vs Price dual-axis chart
├─ FundingRateGauge.tsx      # Circular funding gauge
├─ LongShortRatio.tsx        # Stacked bar chart
└─ styles.module.css
```

### **7. Documentation** 🆕
```
docs/11_DERIVATIVES_DASHBOARD.md
```

---

## 📊 SKELETON COMPLETO (Resumido)

```
atlas/
├─ README.md
├─ LICENSE
├─ .gitignore
├─ .env.example
│
├─ docs/
│  ├─ 00_INDEX.md
│  ├─ 03_WORKFLOW.md (v3.0 🆕)
│  ├─ 11_DERIVATIVES_DASHBOARD.md 🆕
│  ├─ HOW_TO_ACTIVATE.md
│  └─ 99_EVOLUTION_LOG.md
│
├─ configs/
│  ├─ settings.toml (updated 🆕)
│  └─ execution.toml
│
├─ python/src/atlas/
│  ├─ config/
│  ├─ common/
│  │
│  ├─ data_layer/sources/
│  │  ├─ yahoo.py
│  │  ├─ alpaca.py
│  │  ├─ polygon.py
│  │  └─ derivatives/ 🆕
│  │     ├─ coinglass.py
│  │     ├─ hyperliquid.py
│  │     ├─ binance_futures.py
│  │     └─ data_aggregator.py
│  │
│  ├─ core_intelligence/
│  │  ├─ market_state/
│  │  │  ├─ regime.py
│  │  │  ├─ internals/
│  │  │  └─ derivatives_sentiment/ 🆕
│  │  │
│  │  ├─ features/
│  │  │  ├─ technical/
│  │  │  ├─ microstructure/
│  │  │  ├─ time_frequency/
│  │  │  ├─ volatility_advanced/
│  │  │  └─ derivatives/ 🆕
│  │  │
│  │  └─ signals/
│  │
│  ├─ risk/
│  │  ├─ engine/
│  │  ├─ stops/
│  │  └─ liquidation_risk/ 🆕
│  │
│  ├─ execution/
│  ├─ simulation_montecarlo/
│  ├─ backtesting/
│  ├─ memory/
│  │
│  ├─ derivatives/
│  │  ├─ options/
│  │  └─ dashboard_metrics/ 🆕
│  │
│  ├─ visualization/
│  │
│  └─ lab/
│     ├─ aria/
│     ├─ quantum/
│     ├─ chaos/
│     └─ econophysics/
│
├─ ui_web/src/
│  ├─ components/
│  └─ pages/
│     ├─ Dashboard/
│     ├─ Backtest/
│     └─ DerivativesDashboard/ 🆕
│
└─ scratch/
```

---

## 🎯 PRIORIDAD

**Tier 2: ALTO** (Después de Core - Data Layer y Features básicos)

**Estimado:** ~2 semanas de implementación

---

**Skeleton v3.0 Completado**  
**Total Nuevas Carpetas:** +7  
**Total Nuevos Archivos:** ~25
