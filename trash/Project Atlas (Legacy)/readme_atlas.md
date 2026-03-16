# 🧠 PROJECT ATLAS — Technical Workflow & Development Log

---

## ⚙️ FASE 1 — Atlas Core (Functional Skeleton) ✅
**Objetivo:** Establecer la base funcional de Atlas.

### Core
- Arquitectura modular (`core/`) ✅  
- Conexión de datos (yFinance/APIs) ✅  
- Motor probabilístico base `prob_long_short()` ✅  
- Generación de señales (LONG / SHORT / HOLD) ✅  
- Logs y trazabilidad básica ✅  

### Indicadores (servicios)
- Tendencia: SMA, EMA, VWMA, HMA ✅  
- Momentum: RSI, MACD, Stochastic, CCI ✅  
- Volatilidad: Bollinger, ATR, Donchian ✅  
- Volumen/Flujo: OBV, MFI ✅  
- Ichimoku ✅  

### Reconocimiento
- Patrones de vela (engulfing, hammer, shooting, doji) ✅  
- Combinaciones (combo core) ✅  

### UI (Streamlit base)
- Visuales iniciales (candlestick, línea, overlays) ✅  
- Inputs (ticker, period, interval) ✅  

---

## 🧠 FASE 2 — Quantitative Intelligence (Dynamic Adjustments) 🔄
**Objetivo:** Ajustar probabilidades dinámicamente según rendimiento histórico.

### Pesos y calibración
- Pesos dinámicos (`dynamic_weights.py`) 🔄  
- Calibración Bayesiana con memoria (`MemoryCalibration`) ✅  
- Decaimiento exponencial (half-life) ✅  
- Blending prob. cruda ↔ memoria ✅  

### Backtesting & Métricas
- Backtest simple (hit rate, future return) ✅  
- Métricas: Hit Rate, Sharpe, Calmar, Total Return ✅  
- Módulos: `quant_metrics.py`, `atlas_backtest.py` ✅  

### Panel Quant
- Correlaciones de indicadores ✅  
- Historical accuracy / Z-Score ✅  
- Autoajuste si cae rendimiento 🔄  

### Motor de Profitabilidad (Atlas QX)
- Detección de indicadores improductivos 🔄  
- Profit Factor / Max Drawdown 🔄  
- Optimización de parámetros (α, β, γ) 🔄  

---

## 🧩 FASE 2.3 — Memory Calibration (núcleo actual) 🔄
**Objetivo:** Implementar memoria por ticker con decaimiento y suavizado bayesiano.  

### Persistencia
- DB única: `core/memory/atlas_memory.sqlite` ✅  
- Esquema estable `memory_calibration` ✅  

### API
- `MemoryCalibration.update_from_backtest()` ✅  
- `MemoryCalibration.calibrate()` ✅  
- `reliability_by_bin()` ✅  
- Export/Import (CSV/JSON) ✅  

### UI
- Dashboard de Memoria (tabla + métricas por bin) ✅  
- Panel histórico y sliders de parámetros ❌  

---

## ₿ FASE 2.5 — Crypto & Bitcoin Intelligence 🔄
- Bitcoin Analyzer (volatilidad, momentum, tendencia) ✅  
- Fear & Greed Index, Dominance Ratio 🔄  
- Integración BTC/USD y ETH/USD 🔄  
- Ajustes de probabilidad específicos cripto 🔄  
- Crypto Dashboard UI 🔄  

---

## 📈 FASE 3 — Machine Learning / AI Core ❌
- Modelos supervisados (RF, XGBoost, LSTM) ❌  
- No supervisado (K-Means, PCA, DBSCAN) ❌  
- Reinforcement Learning ❌  
- Feature importance dinámica ❌  
- Entrenamiento con ventanas móviles ❌  

---

## 🧩 FASE 4 — Atlas Terminal (UI + Analytics Hub) 🔄
### UI Modular
- Dashboard principal ✅  
- Candles + overlays + volumen ✅  
- Panel “Últimas Señales Atlas” ✅  
- Panels: Quant Insights / Calibration ✅  
- Selector dinámico de indicadores ✅  

### Integraciones & Export
- Exportación de resultados/logs 🔄  
- Integración CoinGecko / Alpha Vantage 🔄  

### Módulos UI
- `price_chart.py`, `quant_insights.py`, `calibration_table.py` ✅  
- `crypto_panel.py` 🔄  
- `mft_panel.py` 🔄  

---

## 🔍 FASE 4.5 — Market Flow Tracker (MFT) 🔄
- Presión de compra/venta 🔄  
- Volume Imbalance / Net Flow Strength 🔄  
- Peso dinámico en prob. engine 🔄  
- Overlay + panel UI 🔄  
- `core/mft_engine.py` y `ui/components/mft_panel.py` 🔄  

---

## 🏢 FASE 5 — Ecosystem M&C (Management & Clients) ❌
- Sistema de usuarios (roles/accesos) ❌  
- Integración con módulos financieros M&C ❌  
- Calendario, alertas, métricas internas ❌  
- Conector Atlas ↔ M&C API ❌  

---

## ♻️ FASE 6 — Expansion & Intelligence Loop ❌
- Feedback loop continuo ❌  
- Entrenamiento distribuido / Cloud sync ❌  
- Autoajuste de parámetros por rendimiento ❌  
- Sentiment & News ingestion ❌  
- API pública / sincronización global ❌  

---

## 📦 ESTRUCTURA ACTUAL DEL REPO


---

## 🚦 ESTADO ACTUAL
- `streamlit run ui/app.py` corre sin errores.  
- `atlas_memory_calibration.py` conectado correctamente a la DB.  
- Dashboard de calibración activo y estable.  
- Siguiente paso: agregar **visualización temporal de reliability** + **sliders de parámetros** (Phase 2.3 final).

---

## 👤 ESTILO DE TRABAJO
- Explicaciones **claras y estructuradas** (flujo de trabajo).  
- Reportes en formato paso a paso.  
- Si hay errores:  
  1. Qué lo causa  
  2. Qué línea se arregla  
  3. Cómo evitarlo  
- Nuevas funciones deben ser **compatibles con todo el sistema existente.**

---

## 🧭 SIGUIENTE META
> Crear la **UI avanzada del módulo de memoria**:  
> - Slider para `half_life_days`  
> - Slider para `min_bin_evidence`  
> - Gráfico temporal de evolución de accuracy  
> - Exportación de resultados históricos  