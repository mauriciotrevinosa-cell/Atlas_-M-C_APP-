# CLAUDE ACTION PLAN & ARCHITECTURAL BLUEPRINT: EL ECOSISTEMA M&C

## � 1. La Visión Real: Atlas no es solo un bot, es el Ecosistema
Claude, tu responsabilidad en el proyecto Atlas es actuar como la fuerza de generación de código pesada. Pero **ATENCIÓN**: Atlas no es simplemente un bot de trading. **Atlas es el ecosistema completo que sostiene a M&C**. ARIA es solo una extensión/núcleo dentro de él.
El objetivo final es tener una aplicación visual (cuando se ejecute `python run_atlas.py`) donde el usuario pueda experimentar, visualizar, y controlar todo.

## 🏗️ 2. Fases de Desarrollo (Nuestra Estrategia Actual: FASE 1)
Trabajaremos con este equipo: **Tú (Claude)** construyes los cimientos pesados, **Codex (ChatGPT)** arregla bugs e implementa detalles, y **Antigravity (Google)** organiza, filtra y dirige la arquitectura.

El ciclo de desarrollo se divide así:
- **FASE 1 (DÓNDE ESTAMOS HOY): Implementación Bruta.** Agregar absolutamente todo lo que se pueda agregar. Construir los cimientos algorítmicos y visuales básicos para que TODO exista, funcione y sea visible al correr la app. **Nota: NUNCA BORREs NADA**, si crees que algo es inútil muévelo a `/trash/`.
- **FASE 2: Optimización e Integración.** Hacer que todo lo construido corra simultáneamente en local. Mezclar mecánicas, upgradear sistemas y optimizar la velocidad.
- **FASE 3: Beautify & Minify.** Hacer el código lo más minimalista posible (sin perder función) y llevar la interfaz a un nivel visual ultra-premium y hermoso.

## 🛠️ 3. Tareas de Construcción Pesada (Lo que vas a construir hoy)

Basado en los repositorios parseados en `info_instructions/Folder 1` y los documentos de historia (`info_instructions/Repo usage complete/updates to workflow and implementation to the project.pdf`), tu trabajo es construir la estructura de código para:

### A. Terminal Interna Interactiva (Visualización)
- Construir una terminal/UI interna dentro de Atlas donde el usuario pueda:
  - Visualizar todos los indicadores técnicos y candlestick patterns.
  - "Toggle on/off" (encender o apagar) indicadores a voluntad para combinarlos visualmente.
  - Correr simulaciones directamente desde este panel visual.

### B. El Núcleo Jarvis (ARIA UI)
- Crear una representación visual en el frontend (ThreeJS / JS) para el cerebro de ARIA.
- Un núcleo de energía que reaccione físicamente (movimiento, pulso, color) al procesar u hablar. Todo el análisis del ecosistema (índices enteros, no solo el portafolio) se le alimenta a este núcleo.

### C. Trader Spreadsheet & Mercado Global
- ARIA necesita acceder a los datos masivos de la capa de extracción (Data Layer) más allá del portafolio actual (todo el mercado/sectores).
- Debe tener su propia "Spreadsheet" (Paper trading) interno donde pruebe estrategias agresivas autónomas para que las auditemos.

### D. Advanced Institutional Architecture
1. **Ingesta de Macroeconomía y Sentimiento Social (NLP):** Motor para procesar noticias, minutas de FED y redes (Twitter/Reddit) convirtiendo variables sociales en matemáticas.
2. **Sistema Multi-Agente (Swarm):** Un comité de agentes especializados (Riesgo/Opciones/Momentum) que alimentan datos a ARIA (La CEO).
3. **Cisnes Negros:** Integración de modelos algorítmicos complejos (N-dimensionales, basados en ALADDIN/Qlib) para simular caídas severas de mercado y generar hedges.

## 🚀 Siguientes Pasos (Tu Tarea Inmediata)
Extrae todo el valor pesado de la `Folder 1` y el `PDF de actualizaciones`, y empieza a escribir los módulos (`.py` y el esqueleto del frontend/terminal). Deja los pedazos de código de tal manera que, al correr `run_atlas.py`, el usuario vea que las bases (terminal, indicadores, núcleo ARIA, entorno RL) existen y corren sin crashear. De la limpieza y optimización nos encargamos Antigravity y Codex después.
