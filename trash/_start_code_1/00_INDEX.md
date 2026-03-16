# 📚 ATLAS - Documentation Index

**Última actualización:** 2026-01-29  
**Versión:** 0.1.0

---

## 🎯 Bienvenido a la Documentación de Atlas

Esta es la puerta de entrada a toda la documentación del proyecto.

---

## 📖 DOCUMENTOS PRINCIPALES

### **Fundación**
- [README.md](../README.md) - Visión general del proyecto
- [02_ARCHITECTURE.md](02_ARCHITECTURE.md) - Decisiones arquitectónicas
- [03_WORKFLOW.md](03_WORKFLOW.md) - Workflow canónico (17 fases)
- [04_DATA_CONTRACTS.md](04_DATA_CONTRACTS.md) - Contratos de datos
- [05_MULTI_LANGUAGE_RULES.md](05_MULTI_LANGUAGE_RULES.md) - Cuándo usar Python/C++/TS

### **Guías de Usuario**
- [HOW_TO_ACTIVATE.md](HOW_TO_ACTIVATE.md) - Cómo activar cada módulo
- [06_TESTING_STRATEGY.md](06_TESTING_STRATEGY.md) - Estrategia de testing

### **Guías Técnicas**
- [07_MICROSTRUCTURE_GUIDE.md](07_MICROSTRUCTURE_GUIDE.md) - DOM, Order Flow
- [08_TIME_FREQUENCY_ANALYSIS.md](08_TIME_FREQUENCY_ANALYSIS.md) - Wavelets, FFT
- [09_CHAOS_NONLINEAR_GUIDE.md](09_CHAOS_NONLINEAR_GUIDE.md) - Phase space, Lyapunov
- [10_EXECUTION_GUIDE.md](10_EXECUTION_GUIDE.md) - Trading real (paper/live)

### **Glosario y Referencia**
- [01_GLOSSARY.md](01_GLOSSARY.md) - Términos del sistema
- [99_EVOLUTION_LOG.md](99_EVOLUTION_LOG.md) - Historial de cambios estructurales

---

## 🗂️ DOCUMENTACIÓN POR MÓDULO

### **Python Core**

#### `data_layer/`
- Ingesta de datos (Yahoo, Alpaca, Polygon)
- Quality checks
- Normalización

#### `core_intelligence/`
- **market_state/** - Detección de régimen
- **features/** - Extracción de features (7 categorías)
- **signals/** - Composición de señales

#### `reasoning/`
- Decision trees
- Rule-based systems
- Regime detection (HMM, Markov)

#### `risk/`
- Position sizing
- VaR / CVaR
- **stops/** - 5 estrategias de stop loss

#### `execution/`
- Brokers (Alpaca, IBKR)
- Order management
- Execution algorithms (TWAP, POV)
- Post-trade analysis

#### `simulation_montecarlo/`
- Simulación de paths
- Stress testing
- Distribuciones de probabilidad

#### `backtesting/`
- Engine de backtests
- Parameter sweeps
- Walk-forward validation

#### `correlation_portfolio/`
- Análisis de correlaciones
- Clustering jerárquico
- Pairs trading
- Factor models (PCA)

#### `memory/`
- Experience store
- Calibración bayesiana
- Time decay

#### `visualization/`
- Artifact builders
- Brain Viewer integration

#### `lab/`
- **aria/** - AI Assistant
- **quantum/** - Quantum finance
- **chaos/** - Análisis no lineal
- **econophysics/** - Power laws, sandpile

---

## 🎨 DIAGRAMAS

Todos los diagramas están en `docs/diagrams/`:

- `system_context.md` - Vista de contexto del sistema
- `dataflow.md` - Flujo de datos
- `one_engine_rule.md` - ONE ENGINE RULE
- `engine_graph.md` - Grafo de motores
- `discrepancy_matrix.md` - Matriz de conflictos
- `brain_viewer.md` - Arquitectura del Brain Viewer

---

## 🚀 GETTING STARTED

### **Para nuevos usuarios:**

1. Leer [README.md](../README.md)
2. Seguir [HOW_TO_ACTIVATE.md](HOW_TO_ACTIVATE.md)
3. Revisar [03_WORKFLOW.md](03_WORKFLOW.md)
4. Explorar módulos según necesidad

### **Para desarrolladores:**

1. Leer [02_ARCHITECTURE.md](02_ARCHITECTURE.md)
2. Revisar [04_DATA_CONTRACTS.md](04_DATA_CONTRACTS.md)
3. Estudiar [05_MULTI_LANGUAGE_RULES.md](05_MULTI_LANGUAGE_RULES.md)
4. Seguir [06_TESTING_STRATEGY.md](06_TESTING_STRATEGY.md)

### **Para investigadores:**

1. Explorar `lab/` modules
2. Leer guías técnicas (07-10)
3. Revisar [99_EVOLUTION_LOG.md](99_EVOLUTION_LOG.md)

---

## 📊 DOCUMENTOS POR STATUS

### ✅ Completados
- README.md
- 03_WORKFLOW.md (v2.0)
- HOW_TO_ACTIVATE.md
- 99_EVOLUTION_LOG.md

### 🚧 En Progreso
- 02_ARCHITECTURE.md
- 04_DATA_CONTRACTS.md
- 07_MICROSTRUCTURE_GUIDE.md

### ⏳ Planeados
- 01_GLOSSARY.md
- 05_MULTI_LANGUAGE_RULES.md
- 06_TESTING_STRATEGY.md
- 08_TIME_FREQUENCY_ANALYSIS.md
- 09_CHAOS_NONLINEAR_GUIDE.md
- 10_EXECUTION_GUIDE.md

---

## 🔍 BÚSQUEDA RÁPIDA

### Por Concepto:

- **Trading real** → [10_EXECUTION_GUIDE.md](10_EXECUTION_GUIDE.md)
- **ARIA** → [lab/aria/README.md](../python/src/atlas/lab/aria/README.md)
- **Microstructure** → [07_MICROSTRUCTURE_GUIDE.md](07_MICROSTRUCTURE_GUIDE.md)
- **Monte Carlo** → Workflow FASE 8
- **Stop Loss** → Workflow FASE 7, `risk/stops/`
- **Discrepancy** → Workflow FASE 6
- **Chaos** → [09_CHAOS_NONLINEAR_GUIDE.md](09_CHAOS_NONLINEAR_GUIDE.md)

### Por Tarea:

- **Activar un módulo** → [HOW_TO_ACTIVATE.md](HOW_TO_ACTIVATE.md)
- **Entender el workflow** → [03_WORKFLOW.md](03_WORKFLOW.md)
- **Configurar brokers** → [10_EXECUTION_GUIDE.md](10_EXECUTION_GUIDE.md)
- **Ver arquitectura** → [02_ARCHITECTURE.md](02_ARCHITECTURE.md)
- **Agregar features** → [04_DATA_CONTRACTS.md](04_DATA_CONTRACTS.md)

---

## 📝 CONTRIBUIR A LA DOCUMENTACIÓN

### Reglas:

1. **Un documento = Un propósito** - No mezclar temas
2. **Markdown limpio** - Usar headers, listas, código
3. **Ejemplos de código** - Siempre que sea posible
4. **Actualizar índice** - Cuando agregas nuevo doc
5. **Fecha de actualización** - Al inicio de cada doc

### Template para nuevos documentos:

```markdown
# Título del Documento

**Última actualización:** YYYY-MM-DD  
**Versión:** X.Y.Z  
**Status:** [Completo/En Progreso/Planeado]

---

## Contenido

[Tu contenido aquí]

---

**Próxima actualización:** [Cuándo/Por qué]
```

---

## 🆘 AYUDA

### ¿No encuentras algo?

1. Buscar en este índice
2. Usar búsqueda de archivos (Ctrl+P en VS Code)
3. Preguntar a ARIA: `aria.ask("¿Dónde está la doc de X?")`

### ¿Falta documentación?

1. Crear issue describiendo qué falta
2. O crear el documento y hacer PR
3. Actualizar este índice

---

## 📚 RECURSOS EXTERNOS

### Aprender más sobre:

- **Quantitative Finance:** "Advances in Financial Machine Learning" (Marcos López de Prado)
- **Monte Carlo:** "Monte Carlo Methods in Financial Engineering" (Glasserman)
- **Microstructure:** "Algorithmic and High-Frequency Trading" (Cartea et al.)
- **Wavelets:** "A Wavelet Tour of Signal Processing" (Mallat)
- **Chaos Theory:** "Nonlinear Dynamics and Chaos" (Strogatz)

---

**Última actualización del índice:** 2026-01-29  
**Próxima revisión:** Cuando se agreguen módulos nuevos
