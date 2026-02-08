# REGISTRO MAESTRO COMPLETO - ATLAS

## Propósito de este Documento

Este es el registro histórico y operativo oficial del proyecto Atlas. Documenta decisiones, estado actual, arquitectura aprobada y evolución del proyecto.

**Regla de Uso:** Este documento solo se actualiza (append/update), nunca se reemplaza. El historial debe preservarse.

**Fuente de Verdad:** En caso de conflicto entre este registro y el repositorio, el código y estructura del repositorio tienen autoridad. Este registro documenta el "por qué", el repo documenta el "qué".

**Fecha de Creación:** 2026-02-01  
**Owner:** Claude AI (Arquitecto Principal)  
**Aprobador:** Humano (Product Owner)

## Índice Rápido

- [Qué es Atlas](#qué-es-atlas)
- [Línea de Tiempo](#línea-de-tiempo)
- [Estado Actual del Proyecto](#estado-actual-del-proyecto)
- [Arquitectura Aprobada](#arquitectura-aprobada)
- [Decisiones Importantes](#decisiones-importantes)
- [Riesgos Conocidos y Deuda Técnica](#riesgos-conocidos-y-deuda-técnica)
- [Reglas del Proyecto](#reglas-del-proyecto)
- [Cómo se Usa este Registro](#cómo-se-usa-este-registro)
- [Glosario](#glosario)
- [Estado del Documento](#estado-del-documento)

---

## Qué es Atlas

Atlas es un sistema de trading cuantitativo diseñado para análisis multi-dimensional de mercados financieros.

**Características principales:**
- Sistema modular con separación clara de responsabilidades (UI / Services / Core)
- Enfoque probabilístico sobre determinista
- Arquitectura preparada para escalar de personal a institucional
- Integración con ARIA (AI Assistant) para operación asistida
- Diseñado para mantenibilidad long-term por equipos pequeños

**Lo que NO es Atlas:**
- No es un bot de trading automático sin supervisión
- No es una plataforma de señales para vender
- No es un indicador técnico simple
- No es específico de un solo exchange o asset class

**Problema que resuelve:**
Análisis cuantitativo accesible y modular que integra técnico, fundamental y probabilístico en un solo sistema, sin depender de plataformas cerradas.

**Scope MVP (Minimum Viable Product):**
- ARIA conversacional con acceso a datos históricos
- Data Layer con al menos 1 proveedor funcional (Yahoo Finance)
- Query de datos por símbolo y rango de fechas
- Respuestas útiles sobre análisis básico (precio, retornos, volatilidad)
- Sistema básico de tools para ARIA

**Fuera de Scope MVP:**
- Backtesting completo (post-MVP)
- Ejecución automática de trades (post-MVP)
- UI web (post-MVP)
- Market state detection avanzado (post-MVP)
- Multiple exchange integration (post-MVP)

---

## Línea de Tiempo

### Q1-Q2 2024
- Proyecto Chronos iniciado como indicador en TradingView (Pine Script)
- Exploración de análisis técnico y proyección de movimientos
- Identificación de limitaciones de plataformas cerradas

### 2024-2025
- Fase de maduración conceptual
- Research sobre arquitecturas de sistemas de trading
- Decisión de rediseñar desde cero en Python
- Definición de principios arquitectónicos

### 2026-01-30
- Nacimiento oficial de Atlas como sistema Python
- Definición de arquitectura multi-capa
- Adopción de enfoque probabilístico como principio core
- Creación de skeleton completo del proyecto
- Documentación inicial de 17 fases de workflow
- Implementación de Data Layer con Yahoo Finance
- Testing exitoso de descarga de datos AAPL

### 2026-02-01
- Inicio de desarrollo de ARIA (AI Assistant)
- Decisión arquitectónica: ARIA autónoma con Ollama (local)
- Instalación de Ollama v0.15.4
- Descarga de modelos: llama3.1:8b, qwen2.5:7b, deepseek-coder:6.7b
- Generación de STATUS_2026-02-01.md
- Creación de este REGISTRO_MAESTRO_COMPLETO.md

### 2026-02-02 (Sesión 2 - ARIA Conversacional + Tools)
- ARIA conectada a Ollama exitosamente
- Primera conversación funcional con ARIA
- Terminal interactiva operativa con indicador "pensando..."
- Arquitectura de tools implementada
- get_data() tool creado con soporte Yahoo Finance + Alpaca
- Data providers system implementado (Yahoo, Alpaca架构)
- Tool calling system integrado en ARIA
- Primera query con datos reales exitosa: "¿Precio de AAPL el 31 dic 2024?"
- FASE 1.5 (Tools Básicos) completada al 100%
- Alpaca provider configurado pero en pausa (evaluación futura)
- Roles Claude + ChatGPT formalizados
- Testing manual exitoso de todo el sistema end-to-end

---

## Estado Actual del Proyecto

**Fase:** Early Development - Tools Integration  
**Versión:** 0.2.0-alpha  
**Progreso hacia MVP:** Aproximadamente 55%

**Lo que está sólido:**
- Estructura de proyecto completa y documentada
- Data Layer con Yahoo Finance operativo
- ARIA Foundation implementada y funcionando
- ARIA Terminal interactiva operativa
- Tool calling system implementado
- get_data() tool integrado y funcional
- Arquitectura multi-provider para datos (Yahoo + Alpaca)
- Sistema 100% autónomo sin dependencias de APIs comerciales
- Governance del proyecto establecido
- Documentación core completa

**Crítico pendiente:**
- ARIA Multi-Cerebro sin implementar
- Sistema de backtesting no iniciado
- Market State Detection no implementado
- Testing automatizado insuficiente
- UI web no desarrollada
- Voice system no implementado
- Web search tool no implementado
- Memory recursiva no implementada

**Siguiente milestone:**
Agregar más tools (create_file, web_search, execute_code) y comenzar sistema de memoria (objetivo: próxima sesión, 2-3 horas).

---

## Arquitectura Aprobada

### Capas del Sistema

**Capa 1: UI (User Interface)**
- Web dashboard (React/TypeScript)
- CLI tools
- ARIA conversational interface
- Ubicación: `ui_web/`

**Capa 2: Services (Business Logic)**
- Market State Detection
- Signal Generation
- Risk Management
- Backtesting Engine
- Execution Engine
- Ubicación: `services/`

**Capa 3: Core (Data & Intelligence)**
- Data Layer (ingesta, normalización, cache)
- ARIA (AI Assistant)
- Common utilities
- Config management
- Ubicación: `python/src/atlas/`

**Capa 4: C++ (High-Frequency Trading - futuro)**
- Reservado para FASE 16-17
- Ubicación: `cpp/`

### Principios No Negociables

1. **Modularidad sobre monolito** - Cada módulo debe ser independiente y testeable
2. **Probabilístico sobre determinista** - Modelar incertidumbre, no predecir con falsa certeza
3. **Documentación viva** - Docs reflejan diseño, código sigue
4. **Una fuente de verdad** - Este registro y el repositorio son autoridad
5. **Simplicidad sobre elegancia** - Código simple y mantenible antes que clever
6. **Testing desde el inicio** - Sin tests, no existe

### Decisiones Difíciles de Revertir

- Arquitectura multi-capa (impacta todo el sistema)
- Python como lenguaje primario (impacta hiring, performance, ecosystem)
- Enfoque probabilístico (impacta diseño de features y UX)
- ARIA local con Ollama (impacta costos, privacidad, dependencias)

Referencia completa: `docs/02_ARCHITECTURE.md`

---

## Decisiones Importantes

### 2026-01-30: Arquitectura Multi-Capa
**Decisión:** Separar en UI / Services / Core  
**Motivo:** Modularidad, testing aislado, escalabilidad  
**Estado:** Vigente  
**Referencia:** ADR-001

### 2026-01-30: Data Layer con Múltiples Proveedores
**Decisión:** Abstract base class para providers, múltiples implementaciones  
**Motivo:** Flexibilidad para cambiar/agregar fuentes sin reescribir  
**Estado:** Vigente  
**Referencia:** ADR-002

### 2026-02-01: ARIA Autónoma con Ollama
**Decisión:** Usar Ollama (local, open source) como backend primario  
**Motivo:** Control total, privacidad 100%, costo $0, sin vendor lock-in  
**Estado:** En implementación  
**Referencia:** ADR-003

### 2026-02-01: Multi-Cerebro System para ARIA
**Decisión:** Arquitectura con cerebro maestro + cerebros especializados  
**Motivo:** Mejor calidad por dominio, modularidad, escalabilidad  
**Estado:** Diseñado, pendiente implementación  
**Referencia:** ADR-004

### 2026-01-30: Enfoque Probabilístico
**Decisión:** Atlas es probabilístico, no determinista  
**Motivo:** Mercados son inherentemente probabilísticos  
**Estado:** Principio arquitectónico adoptado  
**Referencia:** ADR-005

### 2026-01-30: Python como Lenguaje Primario
**Decisión:** Python para desarrollo inicial, C++ reservado para HFT  
**Motivo:** Velocidad de desarrollo, ecosistema ML/quant, mantenibilidad  
**Estado:** Vigente  
**Referencia:** ADR-006

### 2026-02-02: Tool Calling System con Ollama
**Decisión:** Implementar tool calling usando patrón nativo de Ollama  
**Motivo:** Permite a ARIA usar herramientas automáticamente sin APIs externas  
**Trade-offs:** Sistema más simple que function calling de Anthropic, pero 100% local  
**Estado:** Implementado y funcionando  
**Referencia:** ADR-007

### 2026-02-02: Multi-Provider Data Architecture
**Decisión:** Sistema con múltiples providers (Yahoo, Alpaca) con fallback automático  
**Motivo:** Redundancia, flexibility, optimización (histórico vs real-time)  
**Estado:** Implementado (Alpaca en pausa, evaluación futura)  
**Referencia:** ADR-008

### ADR-009: IBM Quantum Integration (2026-02-03)
**Decisión:** Integrar IBM Quantum Platform en ARIA (tool quantum_compute) y roadmap en ATLAS
**Motivo:** Portfolio optimization cuántica, circuitos en QPU real, IBM+Vanguard ya en producción en finance
**Estado:** Tool implementado (quantum_compute.py). Open Plan gratuito (10 min/mes QPU real).
**Roadblock documentado:** Planes Flex ($30k+) y Premium en pausa hasta que Atlas llegue a producción industrial.
**Referencia:** ADR-009, IBM_QUANTUM_INTEGRACION.md

---

## Riesgos Conocidos y Deuda Técnica

### Riesgos Altos

**ARIA sin GPU potente**
- Impacto: Modelos grandes lentos en hardware actual (~60s por respuesta)
- Estado: Mitigado con modelos ligeros en FASE 1, latencia aceptada como trade-off
- Plan: Resolver con eGPU en 3-6 meses
- Actualización 2026-02-02: Latencia de 60s confirmada como aceptable para uso

**Falta de testing automatizado**
- Impacto: Regresiones no detectadas, refactors riesgosos
- Estado: Crítico - solo testing manual
- Plan: Setup pytest + CI/CD en próximo sprint (1-2 semanas)
- Actualización 2026-02-02: Testing manual exitoso pero insuficiente para escalar

**Sin backtesting engine**
- Impacto: No validación de estrategias, Atlas no usable para trading real
- Estado: Blocker para MVP
- Plan: Implementar en FASE 11 (4-6 semanas)

**Tool calling sin validación robusta**
- Impacto: ARIA podría ejecutar tools con parámetros incorrectos
- Estado: Nuevo riesgo identificado 2026-02-02
- Plan: Agregar validación de parámetros y error handling mejorado
- Timeline: Próximo sprint

### Riesgos Medios

**Documentación extensa pero código limitado**
- Impacto: Overhead de mantenimiento, posible desactualización
- Estado: Monitoreando
- Plan: Actualizar docs cada sprint, priorizar código funcional

**ARIA Multi-Cerebro no implementado**
- Impacto: ARIA limitada a conversación simple
- Estado: En roadmap inmediato
- Plan: Implementar en próximo sprint (1 semana)

**Falta de cache en Data Layer**
- Impacto: Descargas repetidas, lentitud
- Estado: Pendiente
- Plan: Cache CSV simple en próximo sprint (2-3 días)

**Sin CI/CD pipeline**
- Impacto: Deployments manuales propensos a error
- Estado: Pendiente
- Plan: GitHub Actions básico en próximo sprint (1 día)

### Riesgos Bajos

**UI web no implementada**
- Impacto: Atlas solo usable por CLI
- Estado: Aceptable para MVP
- Plan: FASE 12 (post-MVP, 3-4 semanas)

**C++ module vacío**
- Impacto: Delay si HFT se vuelve crítico
- Estado: Aceptable, focus en Python MVP
- Plan: FASE 16-17 (1+ año)

**Derivatives dashboard planeado pero no iniciado**
- Impacto: Missing features útiles (liquidation heatmaps)
- Estado: Aceptable para MVP
- Plan: Post-MVP (2-3 semanas)

### Deuda Técnica Identificada

- `data_layer/yahoo.py` tiene test manual inline, mover a pytest
- Faltan `__init__.py` en algunas carpetas de `services/`
- `.env.example` necesita documentación de variables
- `pyproject.toml` falta definir dependencies opcionales completas

---

## Reglas del Proyecto

### Inmutables

1. **Una sola fuente de verdad:** Este registro + repositorio son autoridad
2. **ADRs solo para cambios grandes:** No sobre-documentar decisiones triviales
3. **No optimización prematura:** Funcionalidad primero, performance después
4. **Simplicidad sobre elegancia:** Código mantenible > código clever
5. **Testing obligatorio:** Sin tests, el código no existe oficialmente
6. **Docs reflejan diseño:** Documentación guía, código implementa
7. **Cambios críticos pasan auditoría:** Claude propone, ChatGPT audita, humano decide
8. **Regla de Oro - No dejamos nada a medias (2026-02-02):** Si se identifica revisión/mejora, toma PRIORIDAD sobre features nuevas. Se completa ANTES de avanzar. EXCEPCIÓN: Roadblocks externos (servicios de pago, etc.) se marcan "en pausa" con plan futuro documentado. Razón: Bases sólidas > Features rápidas.

### Gobierno

**Roles:**
- Claude AI: Arquitecto + Constructor base
- ChatGPT: Auditor técnico + Pragmático
- Humano: Product Owner + Decisión final

**Flujo:**
1. Claude propone (arquitectura, código, docs)
2. Humano revisa initial
3. Claude genera resumen para ChatGPT
4. ChatGPT audita (riesgos, simplificación)
5. Humano trae feedback a Claude
6. Claude integra perspectivas
7. Humano decide
8. Merge + actualización de registro

---

## Cómo se Usa este Registro

### Cuándo Actualizarlo

- Al completar una fase mayor del proyecto
- Al tomar decisiones arquitectónicas importantes
- Al identificar riesgos o deuda técnica nueva
- Al final de cada sprint (cada 1-2 semanas)
- Al cambiar el estado crítico del proyecto

### Quién lo Actualiza

**Responsable primario:** Claude AI (Arquitecto)  
**Revisión:** ChatGPT (Auditor)  
**Aprobación:** Humano (Product Owner)

### Qué Tipo de Eventos Registrar

**SÍ registrar:**
- Decisiones arquitectónicas mayores
- Cambios de fase o milestone
- Riesgos críticos identificados
- Deuda técnica importante
- Cambios en principios o reglas del proyecto

**NO registrar:**
- Bugs individuales (van en issue tracker)
- Tareas menores (van en STATUS docs)
- Discusiones sin conclusión
- Experimentos que no impactan arquitectura

### Qué NO Va Aquí

- Roadmaps detallados (van en STATUS docs)
- Documentación técnica específica (va en `docs/`)
- Código o implementaciones
- Discusiones o debates
- Information que cambia frecuentemente

---

## Glosario

**Atlas:** Sistema de trading cuantitativo modular con análisis multi-dimensional  
**ARIA:** Atlas Reasoning & Intelligence Assistant - AI assistant para operación del sistema  
**Cerebro:** Modelo LLM especializado en un dominio específico (quant, code, etc.)  
**Multi-Cerebro:** Arquitectura donde múltiples modelos especializados colaboran bajo un orquestador  
**Data Layer:** Capa de ingesta y normalización de datos de mercado  
**Services:** Capa de lógica de negocio (market state, signals, backtesting)  
**Ollama:** Runtime local para ejecutar modelos LLM open source  
**MVP:** Minimum Viable Product - versión mínima funcional del sistema  
**ADR:** Architecture Decision Record - documento de decisión arquitectónica  
**Foundation:** Fase inicial del proyecto enfocada en estructura base y arquitectura

---

## Estado del Documento

**Última Actualización:** 2026-02-02  
**Próxima Revisión Sugerida:** 2026-02-09 (próxima sesión mayor)

## Changelog del Registro

### 2026-02-01 (v1.0 - Inicial)
- Documento inicial creado
- Timeline desde Project Chronos hasta actualidad documentado
- Estado actual post-foundation registrado
- Decisiones arquitectónicas mayores documentadas
- Riesgos y deuda técnica inicial identificada
- Reglas de governance establecidas
- Ajustes post-auditoría ChatGPT aplicados (índice, scope MVP, glosario)

### 2026-02-02 (v1.1 - ARIA Conversacional + Tools)
- Timeline actualizado con sesión 2 completa
- Estado actual actualizado: MVP 25% → 55%
- Versión actualizada: 0.1.0 → 0.2.0-alpha
- Agregadas decisiones ADR-007 (Tool Calling) y ADR-008 (Multi-Provider)
- Riesgos actualizados con nuevos identificados
- Confirmada latencia de 60s como aceptable
- FASE 1.5 (Tools Básicos) marcada como completa
- Documentado primer éxito end-to-end con datos reales

### 2026-02-05 (v1.2 - Phase 4 Engine Start)
- Inicio oficial de **FASE 4: Motores de Trading**
- Implementación de `BaseEngine` (ABC) y `EngineRegistry`
- Primer motor `Rule-Based` operativo (`SMACrossover`)
- Verificación exitosa de generación de señales
- Roadmap actualizado: ML Engines como siguiente paso prioritario

**Próximos Updates Esperados:**
- Resultado de auditoría ChatGPT sobre tool calling implementation
- Implementación de más tools (create_file, web_search, execute_code)
- Sistema de memoria recursiva
- Testing automatizado

---

## Referencias

- `docs/STATUS_2026-02-01.md` - Estado detallado actual del proyecto
- `docs/03_WORKFLOW.md` - Workflow completo de 17 fases
- `docs/02_ARCHITECTURE.md` - Arquitectura técnica detallada
- `docs/99_EVOLUTION_LOG.md` - Change log granular
- `docs/SKELETON_v3.0.md` - Estructura completa del proyecto
