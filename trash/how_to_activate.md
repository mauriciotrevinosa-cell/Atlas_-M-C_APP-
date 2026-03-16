# 🚀 ATLAS - Activation & Usage Guide

**Última actualización:** 2026-01-29  
**Versión:** 1.0

---

## 📖 ¿QUÉ ES ESTE DOCUMENTO?

Esta es tu **guía de referencia rápida** para activar y usar todos los módulos de Atlas.

**Cada sección incluye:**
- ✅ Qué es y para qué sirve
- ✅ Cómo activarlo
- ✅ Ejemplo de uso
- ✅ Troubleshooting básico

---

## 📚 ÍNDICE

1. [ARIA (AI Assistant)](#1-aria-ai-assistant)
2. [Data Providers](#2-data-providers)
3. [Microstructure (DOM)](#3-microstructure-dom)
4. [Time-Frequency (Wavelets)](#4-time-frequency-wavelets)
5. [Execution (Trading Real)](#5-execution-trading-real)
6. [Stop Loss Strategies](#6-stop-loss-strategies)
7. [Monte Carlo](#7-monte-carlo)
8. [Backtesting](#8-backtesting)
9. [Brain Viewer](#9-brain-viewer)
10. [Chaos Analysis](#10-chaos-analysis)

---

## 1. ARIA (AI Assistant)

### ¿Qué es?
**ARIA** (Atlas Reasoning & Intelligence Assistant) es tu asistente de IA para explicar decisiones, ejecutar análisis y debuggear el sistema.

### ¿Para qué sirve?
- Explicar señales y decisiones
- Comparar backtests
- Generar reportes automáticos
- Debuggear errores
- Responder preguntas sobre el sistema

### ¿Cómo activar?

#### **PASO 1: Instalar dependencias**
```bash
cd Atlas/python
pip install -e ".[aria]"
```

#### **PASO 2: Obtener API key**
1. Ir a https://console.anthropic.com
2. Crear cuenta / Iniciar sesión
3. Crear API key
4. Copiar la key (empieza con `sk-ant-...`)

#### **PASO 3: Configurar `.env`**
```bash
# Copiar template
cp .env.example .env

# Editar .env
notepad .env

# Agregar tu key:
ANTHROPIC_API_KEY=sk-ant-tu-key-aqui
```

#### **PASO 4: Habilitar en `settings.toml`**
```toml
[aria]
enabled = true
provider = "anthropic"
model = "claude-sonnet-4-20250514"
```

#### **PASO 5: Probar**
```python
from atlas.lab.aria import hello
hello()
```

### Output esperado:
```
    _    ____  ___    _    
   / \  |  _ \|_ _|  / \   
  / _ \ | |_) || |  / _ \  
 / ___ \|  _ < | | / ___ \ 
/_/   \_\_| \_\|___/_/   \_\

🎯 ARIA (Atlas Reasoning & Intelligence Assistant) loaded!
Status: Experimental Lab Code
```

### Troubleshooting:
- **Error: `No module named 'anthropic'`**
  → Instalar: `pip install anthropic`
  
- **Error: `AuthenticationError`**
  → Verificar que `ANTHROPIC_API_KEY` está en `.env`
  
- **ARIA no responde**
  → Verificar `[aria] enabled = true` en `settings.toml`

---

## 2. Data Providers

### Yahoo Finance (GRATIS - Ya activado)

#### ¿Qué es?
Fuente de datos históricos gratuita.

#### ¿Para qué sirve?
- OHLCV histórico
- Datos de múltiples activos
- Timeframes: 1m, 5m, 15m, 1h, 1d

#### Cómo usar:
```python
from atlas.data_layer.sources import yahoo

# Descargar datos
data = yahoo.download("AAPL", start="2024-01-01", end="2024-12-31")
```

**Ya está habilitado por defecto** - no requiere API key.

---

### Alpaca (Paper & Live Trading)

#### ¿Qué es?
Broker con API para trading automatizado.

#### ¿Para qué sirve?
- Paper trading (simulado)
- Real trading ($ real)
- Datos real-time

#### ¿Cómo activar?

**PASO 1: Crear cuenta**
1. Ir a https://alpaca.markets
2. Crear cuenta
3. Ir a "Paper Trading" (lado izquierdo)
4. Copiar API Key y Secret Key

**PASO 2: Configurar `.env`**
```env
ALPACA_API_KEY=tu_api_key_aqui
ALPACA_SECRET_KEY=tu_secret_key_aqui
ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

**PASO 3: Habilitar en `settings.toml`**
```toml
[execution]
enabled = true
broker = "alpaca"
mode = "paper"
```

**PASO 4: Probar**
```python
from atlas.execution.brokers import alpaca_broker

broker = alpaca_broker.AlpacaBroker()
account = broker.get_account_info()
print(f"Buying power: ${account.buying_power}")
```

---

### Polygon.io (Microstructure Data)

#### ¿Qué es?
Proveedor de datos L2 (order book depth).

#### ¿Para qué sirve?
- Order book data
- Trade ticks
- Real-time microstructure

#### ¿Cómo activar?

**PASO 1: Obtener API key**
1. Ir a https://polygon.io
2. Crear cuenta (tiene plan gratis)
3. Copiar API key

**PASO 2: Configurar `.env`**
```env
POLYGON_API_KEY=tu_polygon_key_aqui
```

**PASO 3: Habilitar en `settings.toml`**
```toml
[features.microstructure]
enabled = true
```

---

## 3. Microstructure (DOM)

### ¿Qué es?
Análisis de profundidad de mercado (Level 2 data).

### ¿Para qué sirve?
- **Order Flow Imbalance (OFI)** - Presión compradora vs vendedora
- **Volume Delta (CVD)** - Agresión neta
- **Liquidity Gaps** - Detectar zonas sin liquidez
- **Iceberg Detection** - Órdenes ocultas

### ¿Cómo activar?

**Requisitos:**
- ✅ Polygon.io API key (ver sección 2)
- ✅ Data de L2 book

**Config en `settings.toml`:**
```toml
[features.microstructure]
enabled = true
dom_levels = 10
ofi_window = 100
cvd_enabled = true
```

### Ejemplo de uso:
```python
from atlas.core_intelligence.features.microstructure import dom_features

# Analizar order book
dom = dom_features.analyze_dom(symbol="AAPL")
print(f"Bid/Ask Imbalance: {dom.imbalance}")
print(f"Liquidity Gap: {dom.gap_size}")
```

### Output esperado:
```
Bid/Ask Imbalance: 0.65 (bullish)
Liquidity Gap: 2.5 bps
Absorption at $150.00: 10,000 shares
```

---

## 4. Time-Frequency (Wavelets)

### ¿Qué es?
Análisis de señales en tiempo y frecuencia (CWT, FFT).

### ¿Para qué sirve?
- Separar señal de ruido
- Detectar ciclos cambiantes
- Análisis multi-escala

### ¿Cómo activar?

**PASO 1: Instalar dependencias**
```bash
pip install pywt scipy
```

**PASO 2: Habilitar en `settings.toml`**
```toml
[features.time_frequency]
enabled = true
wavelet_type = "morlet"
scales = [2, 4, 8, 16, 32, 64]
```

### Ejemplo de uso:
```python
from atlas.core_intelligence.features.time_frequency import cwt_analysis

# Analizar señal con wavelets
coeffs = cwt_analysis.analyze(data, wavelet="morlet")
print(f"Dominant scale: {coeffs.dominant_scale}")
```

---

## 5. Execution (Trading Real)

### ¿Qué es?
Sistema para ejecutar trades reales (paper o live).

### ¿Para qué sirve?
- Paper trading (simulado)
- Live trading ($ real)
- Slippage monitoring
- Post-trade analysis

### ¿Cómo activar?

**⚠️ IMPORTANTE: Empezar SIEMPRE con paper trading**

**PASO 1: Configurar broker (Alpaca)**
Ver sección 2 - Alpaca

**PASO 2: Habilitar en `settings.toml`**
```toml
[execution]
enabled = true
broker = "alpaca"
mode = "paper"  # ← SIEMPRE empezar en paper
require_confirmation = true
dry_run = false
```

**PASO 3: Primer trade (paper)**
```python
from atlas.execution.brokers import alpaca_broker
from atlas.execution.order_management import order

# Crear broker
broker = alpaca_broker.AlpacaBroker()

# Crear orden
order = order.Order(
    symbol="AAPL",
    side="buy",
    qty=1,
    order_type="market"
)

# Ejecutar (paper trading)
fill = broker.place_order(order)
print(f"Order filled at ${fill.price}")
```

### ⚠️ Pasar a LIVE trading:

**Solo cuando:**
1. ✅ Has probado extensivamente en paper
2. ✅ Entiendes los riesgos
3. ✅ Tienes capital que puedes perder
4. ✅ Has configurado límites de riesgo

**Cambios necesarios:**
```toml
[execution]
mode = "live"  # Cambiar de "paper" a "live"

[risk]
max_portfolio_leverage = 1.0
daily_loss_limit_pct = 2.0
```

```env
# En .env, cambiar URL:
ALPACA_BASE_URL=https://api.alpaca.markets
```

---

## 6. Stop Loss Strategies

### ¿Qué es?
Múltiples estrategias de stop loss que corren en paralelo.

### ¿Para qué sirve?
- Comparar diferentes stops
- Elegir el mejor para cada activo
- Adaptar stops al régimen

### Estrategias disponibles:

#### 1. **Fixed Stop**
```toml
[risk.stops]
default_strategy = "fixed"
fixed_stop_pct = 2.0  # 2%
```

#### 2. **Trailing Stop**
```toml
[risk.stops]
default_strategy = "trailing"
trailing_stop_pct = 1.5
```

#### 3. **ATR Stop**
```toml
[risk.stops]
default_strategy = "atr"
atr_multiplier = 2.0
atr_period = 14
```

#### 4. **Volatility Stop**
```toml
[risk.stops]
default_strategy = "volatility"
volatility_multiplier = 2.0
```

#### 5. **Adaptive Stop** (régimen-based)
```toml
[risk.stops]
default_strategy = "adaptive"
# Se ajusta automáticamente según régimen
```

### Ejemplo: Comparar todos los stops
```python
from atlas.risk.stops import fixed_stop, trailing_stop, atr_stop

stops = [
    fixed_stop.FixedStop(pct=2.0),
    trailing_stop.TrailingStop(pct=1.5),
    atr_stop.ATRStop(multiplier=2.0)
]

# Backtest cada uno
results = [stop.backtest(data) for stop in stops]

# Mejor stop
best = max(results, key=lambda x: x.sharpe_ratio)
print(f"Best stop: {best.name}, Sharpe: {best.sharpe}")
```

---

## 7. Monte Carlo

### ¿Qué es?
Simulación de miles de futuros posibles.

### ¿Para qué sirve?
- Explorar escenarios
- Calcular probabilidades
- Stress testing

### ¿Cómo activar?

**Ya está habilitado por defecto**

**Config en `settings.toml`:**
```toml
[monte_carlo]
enabled = true
num_paths = 1000
num_steps = 252  # ~1 año
process = "gbm"
```

### Ejemplo de uso:
```python
from atlas.simulation_montecarlo import monte_carlo

# Simular 1000 futuros
paths = monte_carlo.simulate(
    symbol="AAPL",
    num_paths=1000,
    horizon_days=30
)

# Probabilidades
prob_up = monte_carlo.probability(paths > current_price)
print(f"P(price > ${current_price}): {prob_up:.1%}")
```

---

## 8. Backtesting

### ¿Qué es?
Probar estrategias con datos históricos.

### ¿Para qué sirve?
- Validar estrategias
- Optimizar parámetros
- Walk-forward validation

### ¿Cómo usar?

**Config en `settings.toml`:**
```toml
[backtest]
slippage_bps = 5
commission_bps = 1
```

### Ejemplo de uso:
```python
from atlas.backtesting.engine import backtest_engine

# Crear backtest
bt = backtest_engine.Backtest(
    strategy="momentum",
    symbols=["AAPL", "MSFT"],
    start_date="2023-01-01",
    end_date="2024-01-01"
)

# Ejecutar
results = bt.run()

# Métricas
print(f"Sharpe Ratio: {results.sharpe:.2f}")
print(f"Max Drawdown: {results.max_dd:.1%}")
print(f"Win Rate: {results.win_rate:.1%}")
```

---

## 9. Brain Viewer

### ¿Qué es?
UI web para visualizar el "cerebro" de Atlas.

### ¿Para qué sirve?
- Ver decisiones en tiempo real
- Explorar backtests visualmente
- Comparar runs
- Time-travel (replay)

### ¿Cómo activar?

**PASO 1: Instalar UI (futuro)**
```bash
cd Atlas/ui_web
npm install
npm run dev
```

**PASO 2: Habilitar en `settings.toml`**
```toml
[visualization.brain_viewer]
enabled = true
port = 3000
auto_open = false
```

**PASO 3: Abrir**
```
http://localhost:3000
```

---

## 10. Chaos Analysis

### ¿Qué es?
Análisis no lineal (phase space, Lyapunov).

### ¿Para qué sirve?
- Detectar régimen caótico
- Horizonte de predictibilidad
- Fragilidad sistémica

### ¿Cómo activar?

**Config en `settings.toml`:**
```toml
[advanced]
chaos_enabled = true
phase_space_enabled = true
```

### Ejemplo de uso:
```python
from atlas.lab.chaos import lyapunov

# Calcular exponente de Lyapunov
lambda_exp = lyapunov.calculate(data)

if lambda_exp > 0:
    print("Régimen caótico - horizonte corto")
else:
    print("Régimen predecible - horizonte largo")
```

---

## 📋 CHECKLIST DE ACTIVACIÓN (Primera Vez)

### ✅ Setup Inicial (30 min)

- [ ] Copiar `.env.example` → `.env`
- [ ] Obtener Anthropic API key (ARIA)
- [ ] Obtener Alpaca API key (paper trading)
- [ ] Instalar dependencias: `pip install -e ".[aria]"`
- [ ] Probar ARIA: `from atlas.lab.aria import hello; hello()`
- [ ] Verificar configs en `settings.toml`

### ✅ Data Providers (opcional)

- [ ] Polygon.io API key (microstructure)
- [ ] IBKR account (si usas Interactive Brokers)

### ✅ Primer Trade (paper)

- [ ] Configurar Alpaca en paper mode
- [ ] Ejecutar primer trade simulado
- [ ] Verificar slippage monitoring

### ✅ Exploración

- [ ] Correr primer backtest
- [ ] Ver resultados en Brain Viewer
- [ ] Comparar diferentes stops

---

## 🆘 TROUBLESHOOTING GENERAL

### Problema: Imports no funcionan
```
ModuleNotFoundError: No module named 'atlas'
```

**Solución:**
```bash
cd Atlas/python
pip install -e .
```

---

### Problema: `.env` no se lee
```
KeyError: 'ANTHROPIC_API_KEY'
```

**Solución:**
1. Verificar que `.env` existe en raíz de Atlas
2. Verificar que tiene formato correcto (no espacios extra)
3. Reiniciar Python/terminal

---

### Problema: Settings no se cargan
```
FileNotFoundError: settings.toml
```

**Solución:**
Verificar que `configs/settings.toml` existe en la raíz del proyecto.

---

## 📚 PRÓXIMOS PASOS

Después de activar lo básico:

1. **Estudiar el workflow** - `docs/03_WORKFLOW.md`
2. **Explorar arquitectura** - `docs/02_ARCHITECTURE.md`
3. **Correr experimentos** - Ver `experiments/`
4. **Customizar configs** - Editar `settings.toml`

---

## 📝 NOTAS FINALES

- Este documento se actualiza cada vez que agregamos un módulo nuevo
- Si algo no funciona, revisar logs en `logs/atlas.log`
- Preguntar a ARIA: "¿Cómo activo X?" 😉

---

**Última actualización:** 2026-01-29  
**Versión del documento:** 1.0  
**Próxima actualización:** Cuando implementemos execution layer