# 🧭 PROJECT ATLAS — WORKFLOW v3.0

**Última Actualización:** 2026-01-30  
**Versión:** 3.0 (Agregado Derivatives Dashboard & CoinGlass-style features)

---

## 🎯 CHANGELOG v2.0 → v3.0

### **AGREGADO:**
- ✅ Derivatives Dashboard (CoinGlass-style)
- ✅ Liquidation Heatmap analysis
- ✅ Open Interest tracking
- ✅ Funding Rate analysis  
- ✅ Long/Short Ratio sentiment
- ✅ Top Trader positioning
- ✅ Nueva doc: `11_DERIVATIVES_DASHBOARD.md`

---

## 📊 WORKFLOW COMPLETO (17 FASES)

```
FASE 0  → Fundación
FASE 1  → Data Ingestion (+ Derivatives data 🆕)
FASE 2  → Market State (+ Funding sentiment 🆕)
FASE 3  → Feature Extraction (7 subcategorías)
  3.2   → Microstructure
  3.8   → Derivatives Features 🆕
FASE 3.5 → Chaos & Nonlinear
FASE 4  → Specialized Engines
FASE 5  → Signal Composition
FASE 6  → Discrepancy Analysis
FASE 7  → Risk & Fragility
FASE 8  → Monte Carlo
FASE 9  → Orchestration
FASE 10 → Memory
FASE 11 → Backtest
FASE 12 → Visualization (+ Derivatives Dashboard 🆕)
FASE 13 → ARIA
FASE 14 → User Decision
FASE 14.5 → Execution
FASE 15 → Post-Trade
```

---

## FASE 1 — DATA INGESTION (EXPANDIDO 🆕)

### **1.1 Traditional Data (Ya existente)**
- OHLCV (Yahoo, Alpaca, Polygon)
- L2 Order Book
- Trade ticks

### **1.2 Derivatives Data 🆕**

**Motores:** `data_layer/sources/derivatives/`

**Proveedores:**
- CoinGlass API
- Hyperliquid Direct API
- Binance Futures API
- Bybit API

**Datos a Ingerir:**
```python
# Liquidation Data
- liquidation_events (timestamp, price, side, size)
- liquidation_clusters (price zones con alta concentración)
- cumulative_liquidations (running total)

# Open Interest
- oi_by_exchange (total OI per exchange)
- oi_by_expiry (futures by expiration)
- oi_changes (hourly/daily deltas)

# Funding Rate
- current_funding (8h funding rate)
- predicted_funding (next period)
- funding_history (timeseries)
- funding_divergence (vs other symbols)

# Sentiment
- long_short_ratio (aggregate across exchanges)
- top_trader_positions (whale data if available)
- elite_trader_ratio (Binance elite data)

# Volume
- spot_vs_futures_volume
- perpetual_vs_dated_volume
```

**Archivos:**
```
data_layer/sources/derivatives/
├─ coinglass.py          # CoinGlass API wrapper
├─ hyperliquid.py        # Hyperliquid direct
├─ binance_futures.py    # Binance Futures API
└─ data_aggregator.py    # Combine multiple sources
```

---

## FASE 2 — MARKET STATE (EXPANDIDO 🆕)

### **2.3 Derivatives Sentiment 🆕**

**Motores:** `core_intelligence/market_state/derivatives_sentiment/`

**Métricas:**
```python
# Funding as Sentiment
- funding_extremes (>0.1% or <-0.1% = extreme)
- funding_divergence (BTC funding vs ETH funding)
- funding_reversals (sudden changes = potential reversal)

# Open Interest as Conviction
- oi_price_divergence:
  - OI ↑ + Price ↑ = Strong bullish conviction
  - OI ↑ + Price ↓ = Distribution / Weak hands
  - OI ↓ + Price ↑ = Profit taking
  - OI ↓ + Price ↓ = Capitulation

# Long/Short Ratio
- extreme_long (>70% long = contrarian short signal)
- extreme_short (<30% long = contrarian long signal)
- neutral_zone (40-60% = no clear bias)
```

**Output:**
```python
derivatives_state = {
    'funding_sentiment': 'extreme_long',  # overfunded
    'oi_conviction': 'weak',              # price down, OI up
    'lsr_signal': 'contrarian_short',     # too many longs
    'liquidation_risk': 'high'            # many stops clustered
}
```

---

## FASE 3.8 — DERIVATIVES FEATURES 🆕

**Motores:** `core_intelligence/features/derivatives/`

### **3.8.1 Liquidation Features**

```python
# liquidation_zones.py
class LiquidationZones:
    def detect_clusters(self, liquidation_data):
        """
        Detectar zonas con alta concentración de liquidaciones
        """
        clusters = []
        for price_level in liquidation_data:
            if density > threshold:
                clusters.append({
                    'price': price_level,
                    'size': total_size,
                    'side': 'long' or 'short',
                    'probability': estimate_trigger_probability()
                })
        return clusters
    
    def liquidation_cascade_risk(self, current_price, clusters):
        """
        Estimar riesgo de cascada de liquidaciones
        """
        nearest_cluster = find_nearest(clusters, current_price)
        if distance < 2%:
            return {
                'risk': 'HIGH',
                'trigger_price': nearest_cluster['price'],
                'estimated_impact': nearest_cluster['size']
            }
```

### **3.8.2 Funding Features**

```python
# funding_analysis.py
class FundingAnalysis:
    def funding_divergence(self, symbol_a, symbol_b):
        """
        Detectar divergencias en funding (pairs trade signal)
        """
        if abs(funding_a - funding_b) > threshold:
            return {
                'signal': 'divergence',
                'overpriced': symbol_a if funding_a > funding_b else symbol_b,
                'trade': 'short_overpriced_long_underpriced'
            }
    
    def funding_reversal_signal(self, funding_history):
        """
        Detectar reversals en funding (change in sentiment)
        """
        if funding was positive and now negative:
            return 'long_exhaustion → potential_reversal_down'
```

### **3.8.3 Open Interest Features**

```python
# oi_analysis.py
class OIAnalysis:
    def oi_price_divergence(self, oi_data, price_data):
        """
        Analizar divergencia OI vs Price
        """
        if oi_increasing and price_decreasing:
            return {
                'signal': 'distribution',
                'interpretation': 'weak hands adding shorts',
                'confidence': 'medium'
            }
```

---

## FASE 7 — RISK (EXPANDIDO 🆕)

### **7.5 Liquidation Risk Management 🆕**

**Motores:** `risk/liquidation_risk/`

```python
# liquidation_risk_manager.py
class LiquidationRiskManager:
    def calculate_liquidation_price(self, entry, leverage, side):
        """
        Calcular precio de liquidación
        """
        if side == 'long':
            liq_price = entry * (1 - 1/leverage)
        else:
            liq_price = entry * (1 + 1/leverage)
        return liq_price
    
    def avoid_liquidation_clusters(self, proposed_entry, leverage):
        """
        Verificar que stop/liquidation no esté en zona caliente
        """
        liq_price = self.calculate_liquidation_price(...)
        nearby_clusters = self.get_liquidation_clusters(liq_price)
        
        if nearby_clusters:
            return {
                'warning': 'Liquidation near cluster',
                'recommendation': 'Lower leverage or adjust entry',
                'safe_leverage': calculate_safe_leverage()
            }
```

---

## FASE 12 — VISUALIZATION (EXPANDIDO 🆕)

### **12.3 Derivatives Dashboard 🆕**

**UI Components:** `ui_web/src/pages/DerivativesDashboard/`

#### **A) Liquidation Heatmap**
```tsx
// LiquidationHeatmap.tsx
<HeatmapViz
  data={liquidationClusters}
  currentPrice={currentPrice}
  colorScheme="red-green"  // red=long liq, green=short liq
  interactive={true}
  onClick={(cluster) => showClusterDetails(cluster)}
/>
```

**Visualización:**
```
Price Levels (Y-axis)
    ↑
$45,000 |████████████ (Long liquidations - RED)
$44,500 |██
$44,000 |═══════════════ (Current Price)
$43,500 |██
$43,000 |████████ (Short liquidations - GREEN)
    ↓
```

#### **B) Open Interest Chart**
```tsx
// OpenInterestChart.tsx
<DualAxisChart
  leftAxis={oi_data}       // Open Interest
  rightAxis={price_data}   // Price
  highlightDivergences={true}
/>
```

#### **C) Funding Rate Gauge**
```tsx
// FundingRateGauge.tsx
<CircularGauge
  value={current_funding}
  min={-0.5}
  max={0.5}
  zones={[
    {range: [-0.5, -0.1], color: 'green', label: 'Extreme Short'},
    {range: [-0.1, 0.1], color: 'yellow', label: 'Neutral'},
    {range: [0.1, 0.5], color: 'red', label: 'Extreme Long'}
  ]}
/>
```

#### **D) Long/Short Ratio**
```tsx
// LongShortRatio.tsx
<StackedBar
  long_pct={long_percentage}
  short_pct={short_percentage}
  threshold_lines={[30, 70]}  // Extreme zones
/>
```

#### **E) Top Traders Table**
```tsx
// TopTradersTable.tsx
<DataTable
  columns={['Trader', 'Position', 'Size', 'Entry', 'PnL']}
  data={topTraders}
  sortable={true}
  filterable={true}
/>
```

**Layout del Dashboard:**
```
┌─────────────────────────────────────────────────────┐
│  DERIVATIVES DASHBOARD                              │
├──────────────┬──────────────────────────────────────┤
│ Liquidation  │  Open Interest vs Price              │
│ Heatmap      │                                      │
│              │  [Chart showing divergences]         │
│ [Heatmap]    │                                      │
├──────────────┼──────────────────┬───────────────────┤
│ Funding Rate │ Long/Short Ratio │ Top Traders      │
│              │                  │                  │
│ [Gauge]      │ [Stacked Bar]    │ [Table]          │
└──────────────┴──────────────────┴───────────────────┘
```

---

## 📁 SKELETON ACTUALIZADO (NUEVAS SECCIONES)

```
Atlas/
├─ python/src/atlas/
│  │
│  ├─ data_layer/sources/
│  │  └─ derivatives/ 🆕
│  │     ├─ __init__.py
│  │     ├─ coinglass.py           # CoinGlass API
│  │     ├─ hyperliquid.py         # Hyperliquid direct
│  │     ├─ binance_futures.py     # Binance Futures
│  │     └─ data_aggregator.py     # Combine sources
│  │
│  ├─ core_intelligence/
│  │  ├─ market_state/
│  │  │  └─ derivatives_sentiment/ 🆕
│  │  │     ├─ __init__.py
│  │  │     ├─ funding_sentiment.py
│  │  │     └─ oi_conviction.py
│  │  │
│  │  └─ features/
│  │     └─ derivatives/ 🆕
│  │        ├─ __init__.py
│  │        ├─ liquidation_zones.py
│  │        ├─ funding_analysis.py
│  │        ├─ oi_analysis.py
│  │        └─ lsr_analysis.py
│  │
│  ├─ risk/
│  │  └─ liquidation_risk/ 🆕
│  │     ├─ __init__.py
│  │     ├─ liquidation_calculator.py
│  │     └─ cluster_avoidance.py
│  │
│  └─ derivatives/ (expandido)
│     └─ dashboard_metrics/ 🆕
│        ├─ __init__.py
│        ├─ heatmap_data.py
│        └─ sentiment_scores.py
│
├─ ui_web/src/
│  └─ pages/
│     └─ DerivativesDashboard/ 🆕
│        ├─ index.tsx
│        ├─ LiquidationHeatmap.tsx
│        ├─ OpenInterestChart.tsx
│        ├─ FundingRateGauge.tsx
│        ├─ LongShortRatio.tsx
│        ├─ TopTradersTable.tsx
│
└─ docs/
   └─ 11_DERIVATIVES_DASHBOARD.md 🆕
```

---

## 📊 USO EN TRADING (EJEMPLOS)

### **Ejemplo 1: Evitar Liquidation Cluster**
```python
# Quieres entrar long en BTC a $44,000 con 10x
entry = 44000
leverage = 10

# Atlas detecta:
liq_price = 44000 * (1 - 1/10) = $39,600
nearby_cluster = liquidation_zones.get_nearest($39,600)

# Resultado:
{
  'warning': 'Liquidation at $39,600 overlaps with cluster at $39,500',
  'cluster_size': '$50M in long liquidations',
  'recommendation': 'Lower leverage to 5x (liq at $35,200) or wait'
}
```

### **Ejemplo 2: Funding Divergence Trade**
```python
# BTC funding: +0.15% (extreme long)
# ETH funding: +0.02% (neutral)

signal = funding_analysis.detect_divergence('BTC', 'ETH')

# Output:
{
  'signal': 'BTC overheated relative to ETH',
  'trade': 'Short BTC / Long ETH',
  'rationale': 'BTC longs paying 7x more funding',
  'confidence': 'high'
}
```

### **Ejemplo 3: OI Divergence**
```python
# OI increasing 20%
# Price decreasing 5%

signal = oi_analysis.detect_divergence(oi_data, price_data)

# Output:
{
  'pattern': 'Distribution',
  'interpretation': 'Weak hands adding shorts into decline',
  'contrarian_signal': 'Potential bounce (shorts will cover)',
  'confidence': 'medium'
}
```

---

## 🎯 PRIORIDAD DE IMPLEMENTACIÓN

### **Tier 2: ALTO (Después de Core)**

**Razón:**
- Muy útil para crypto/futures
- Mejora visibilidad del mercado
- No crítico para funcionalidad básica
- Requiere data layer funcionando primero

**Orden Sugerido:**
1. ✅ Completar FASE 1 (data ingestion básico)
2. ✅ Implementar derivatives data sources
3. ✅ Agregar derivatives features
4. ✅ Crear dashboard UI
5. ✅ Integrar con risk management

---

## 📚 NUEVA DOCUMENTACIÓN

### **`docs/11_DERIVATIVES_DASHBOARD.md`** (A crear)

**Contenido:**
- Qué es un derivatives dashboard
- Por qué es útil (liquidations, funding, OI)
- APIs a usar (CoinGlass, Hyperliquid, etc.)
- Features implementadas
- Cómo interpretar cada métrica
- Ejemplos de uso en trading
- Integration con workflow

---

**Workflow v3.0 - Completado**  
**Última Actualización:** 2026-01-30  
**Próxima Revisión:** Después de implementar derivatives data sources