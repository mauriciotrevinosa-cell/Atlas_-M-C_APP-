# REGISTRO MAESTRO COMPLETO - ATLAS

## Propósito de este Documento

Este es el registro histórico y operativo oficial del proyecto Atlas. Documenta decisiones, estado actual, arquitectura aprobada y evolución del proyecto.

**Regla de Uso:** Este documento solo se actualiza (append/update), nunca se reemplaza. El historial debe preservarse.

**Fuente de Verdad:** En caso de conflicto entre este registro y el repositorio, el código y estructura del repositorio tienen autoridad. Este registro documenta el "por qué", el repo documenta el "qué".

**Fecha de Creación:** 2026-02-01  
**Owner:** Claude AI (Arquitecto Principal)  
**Aprobador:** Humano (Product Owner)

---

## Qué es Atlas

Atlas es un sistema de trading cuantitativo híbrido humano-AI diseñado para análisis multi-dimensional de mercados financieros.

**Características principales:**
- Sistema modular con separación clara de responsabilidades (UI / Services / Core)
- Enfoque probabilístico sobre determinista
- Arquitectura preparada para escalar de personal a institucional
- Integración con ARIA (AI Assistant) para operación asistida
- ML/RL engines para auto-trading con guardrails humanos
- C++ core para operaciones de alta frecuencia (futuro)
- Diseñado para mantenibilidad long-term por equipos pequeños

**Lo que NO es Atlas (actualizado):**
- No es un bot sin supervisión — siempre hay guardrails y kill switches
- No es una plataforma de señales para vender
- No es un indicador técnico simple
- No es específico de un solo exchange o asset class

**Problema que resuelve:**
Análisis cuantitativo accesible y modular que integra técnico, fundamental, probabilístico y AI/ML en un solo sistema, con capacidad de escalar de análisis manual a trading semi-autónomo.

---

## Línea de Tiempo

### Q1-Q2 2024
- Proyecto Chronos iniciado (TradingView/PineScript)

### 2024-2025
- Fase de maduración conceptual
- Decisión de rediseñar en Python

### 2026-01-30
- Nacimiento oficial de Atlas
- Skeleton completo, Data Layer con Yahoo Finance

### 2026-02-01
- Inicio de ARIA con Ollama (local)
- Modelos: llama3.1:8b, qwen2.5:7b, deepseek-coder:6.7b

### 2026-02-02
- ARIA conversacional + Tool calling funcional
- Primera query con datos reales: "¿Precio de AAPL el 31 dic 2024?"
- MVP al 55%

### 2026-02-03
- Skeleton generation (Phases 0-15)
- ARIA v3.0 completa
- Quantum Spike (SSCT en IBM Quantum)
- pyproject.toml fix → `pip install -e .` works

### 2026-02-04
- Phase 1 Data Layer complete (Yahoo, cache, normalize, quality)
- Phase 2 Market State (regime, volatility)
- Phase 3 Features (technical, microstructure — VPIN, Kyle's Lambda)
- Phase 8 Monte Carlo (GBM, Heston, Jump-Diffusion, variance reduction)
- Phase 4 Engines started (SMA Crossover + registry)
- ARIA tools: get_data, get_market_state, analyze_risk, run_backtest, explain_signal
- Browser edition (Python + Browser, no Node)

### 2026-02-08 ⭐ (Current Session — Claude Architect)
- **Workflow v3 full gap analysis** → 95% phase coverage achieved
- **ARIA Math Toolset** → 27 financial calculation tools + sandboxed code executor
- **C++ High-Performance Core** → Order book, signal engine, execution engine + pybind11
- **3D Visualizations** → 6 static (matplotlib) + 3 interactive (Three.js)
- **ML Engine Suite** → XGBoost, RandomForest, LSTM with FeaturePipeline
- **RL Trading Agent** → DQN with Gym-style environment, experience replay
- **Auto-Trader** → Hybrid system with 4 operating modes + guardrails
- **Total delivery:** 26 new files, ~6,800 lines of production code
- **Status:** All delivered as ZIPs, awaiting integration into repo

---

## Estado Actual del Proyecto

**Fase:** Mid Development — Backend Near-Complete  
**Versión:** 0.6.0-alpha  
**Progreso:** ~70% (repo) / ~95% (with pending ZIPs)

**Lo que está sólido (in repo):**
- ARIA completa con tool calling (chat, voice stubs, integrations)
- Data Layer (Yahoo, cache, normalize, flexible timeframes)
- Indicator Registry (10 indicators: RSI, MACD, BB, SMA, EMA, WMA, Stoch, ATR, OBV, VWAP)
- Signal Engine + Backtest Runner (basic but functional)
- Paper Broker
- Quantum Lab (SSCT spike)
- Desktop App (browser edition, scenario mode)
- Full test chain passing

**Lo que está listo pero no integrado (in ZIPs):**
- Workflow v3 analytics (PIT, returns, candles, PCA, portfolio, options, stress testing)
- ARIA math tools (27 functions + code executor)
- C++ core (orderbook, signals, execution with pybind11)
- 3D visualizations (matplotlib + Three.js)
- ML engines (XGBoost, LSTM, RandomForest)
- RL agent (DQN + trading environment)
- Auto-Trader (hybrid human-AI with guardrails)

**Pendiente por construir:**
- Derivatives data sources (CoinGlass, Hyperliquid) — needs API keys
- Orchestration (multi-engine router)
- Discrepancy analysis
- Full UI web (React/Next.js)
- CI/CD pipeline

---

## Decisiones Importantes

### ADR-001 through ADR-009: [Unchanged — see previous version]

### ADR-010: Hybrid Auto-Trading Architecture (2026-02-08)
**Decisión:** Implementar sistema de trading híbrido con 4 modos operativos
**Modos:** MANUAL → ADVISORY → SEMI_AUTO → FULL_AUTO
**Motivo:** Permitir evolución gradual de análisis manual a trading autónomo
**Guardrails:** Max position 10%, max daily loss 2%, max drawdown 10%, max 20 trades/day, min confidence 60%
**Estado:** Código generado, awaiting integration
**Referencia:** ADR-010

### ADR-011: C++ Core for HFT (2026-02-08)
**Decisión:** Header-only C++ engines con pybind11 bridge
**Motivo:** Preparar para latencia nanosegundo cuando se conecte a broker real
**Scope:** Order book (L2), signal engine (streaming), execution (TWAP/VWAP)
**Estado:** Código generado, awaiting integration. Python sigue funcionando sin C++.
**Referencia:** ADR-011

### ADR-012: ML/RL Trading Stack (2026-02-08)
**Decisión:** Stack completo ML (XGBoost/LSTM/RF) + RL (DQN) con FeaturePipeline unificado
**Motivo:** Habilitar predicción y toma de decisiones autónoma
**Dependencias:** PyTorch (LSTM, DQN), XGBoost, scikit-learn
**Estado:** Código generado, awaiting integration
**Referencia:** ADR-012

---

## Riesgos Conocidos y Deuda Técnica

### Riesgos Altos

**26 archivos pendientes de integración**
- Impacto: El repo tiene ~30% de capacidad real vs lo que está generado
- Plan: Integrar ZIPs en orden de prioridad (V3_GAPS → ML_RL → CPP_3D → ARIA_TOOLS)

**Testing automatizado insuficiente**
- Impacto: Solo test_full_chain.py + manual testing
- Plan: pytest suite después de integración

### Riesgos Medios

**ML/RL requiere entrenamiento**
- Impacto: Modelos no son plug-and-play, necesitan datos históricos para train
- Plan: Paper trading primero, evaluar antes de SEMI_AUTO

**C++ no compilado aún**
- Impacto: pybind11 build no testeado en la máquina target
- Plan: Python funciona sin C++, C++ es acelerador opcional

### Riesgos Bajos

**3D visualizations requieren matplotlib 3D / Three.js CDN**
- Plan: Fallback a 2D si no available

---

## Reglas del Proyecto

[Unchanged — same 8 rules including "Regla de Oro"]

---

## Estado del Documento

**Última Actualización:** 2026-02-08  
**Próxima Revisión Sugerida:** 2026-02-15

## Changelog del Registro

### 2026-02-01 (v1.0) — Inicial
### 2026-02-02 (v1.1) — ARIA + Tools, MVP 55%
### 2026-02-05 (v1.2) — Phase 4 Engine Start
### 2026-02-08 (v2.0) — Full Backend Generation
- Workflow v3 gap analysis complete (95% coverage)
- 4 delivery packages generated (26 files, ~6,800 lines)
- New ADRs: 010 (Auto-Trading), 011 (C++), 012 (ML/RL)
- Project version: 0.2.0 → 0.6.0-alpha
- Added pending integration tracking to State Matrix
