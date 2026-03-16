# ⚛️ INTEGRACIÓN IBM QUANTUM – ARIA & ATLAS

**ADR-009 – Quantum Computing Integration**
**Fecha:** 2026-02-03
**Status:** APROBADO

---

## 1. CONTEXTO & DECISIÓN

### ¿Por qué IBM Quantum?
- **Open Plan gratuito:** 10 min/mes en QPUs reales 100+ qubits
- **Ecosistema:** Qiskit es el SDK más popular del mundo para quantum
- **Finance-ready:** IBM + Vanguard ya demostraron optimización de portfolios en QPUs reales
- **Hybrid workflow:** Circuitos cuánticos + procesamiento clásico, ya en producción

### Planes (roadblock de pago documentado)

| Plan | Precio | Mínimo | Status |
|------|--------|--------|--------|
| **Open Plan** | **GRATIS** | 10 min/mes | ✅ Usamos esto |
| Pay-As-You-Go | $96/min | Sin mínimo | En pausa |
| Flex | $72/min | $30,000 | En pausa – evaluar cuando Atlas escale |
| Premium | $48/min | Suscripción | En pausa – producción industrial |

**Decisión:** Open Plan (gratis). Planes de pago se evalúan cuando Atlas llegue a producción.

---

## 2. ARQUITECTURA

```
USUARIO
   │  "Ejecuta Bell State" / "Optimiza portfolio"
   ▼
ARIA (chat.py → tool calling)
   │  quantum_compute registrado en tools registry
   ▼
quantum_compute.py  ←── ARCHIVO NUEVO
   │
   ├─ mode=simulate   → StatevectorSampler (local, sin red, sin costo)
   ├─ mode=ibm_cloud  → QiskitRuntimeService → QPU real IBM
   └─ mode=portfolio  → QUBO → circuito → simulate/ibm_cloud → evaluar
                                                          │
                                              IBM Quantum Platform
                                              quantum.cloud.ibm.com
                                                          │
ATLAS (futuro)                                           │
   ├─ data_layer/  → provee retornos & covarianza ◄──────┘
   ├─ risk/        → recibe resultado quantum
   └─ backtest/    → valida con optimización Q
```

---

## 3. ESTRUCTURA EN EL PROYECTO

### ARIA (inmediato)
```
src/aria/tools/
   ├─ base.py                 ✅ Existe
   ├─ get_data.py             ✅ Existe (patrón seguido)
   └─ quantum_compute.py      ⭐ NUEVO
```

### ATLAS (futuro – cuando implementemos risk/)
```
atlas/
   ├─ risk/portfolio.py            → usará quantum_compute
   └─ workflow/quantum_pipeline.py → orquestación end-to-end
```

### Dependencias
```toml
# pyproject.toml
qiskit = "^2.3.0"                          # core (simulate)
qiskit-ibm-runtime = {optional = true}     # cloud (ibm_cloud)
```

### .env
```env
IBM_QUANTUM_API_KEY=    # opcional, solo para ibm_cloud
```

---

## 4. REGISTRO EN ARIA

```python
# chat_terminal.py
from aria.tools.quantum_compute import QuantumComputeTool

aria.register_tool(GetDataTool())
aria.register_tool(QuantumComputeTool())   # ← nueva línea
```

---

## 5. WORKFLOWS

### A: Circuito en Simulador
```
Usuario → ARIA → quantum_compute(mode=simulate, circuit=bell_state)
   → _build_circuit(2, ["h(0)","cx(0,1)"])
   → StatevectorSampler.run() → counts → ARIA responde
```

### B: Circuito en QPU Real
```
Usuario → ARIA → quantum_compute(mode=ibm_cloud, circuit=bell_state)
   → verificar API key → least_busy() → transpile → SamplerV2.run()
   → esperar resultado → counts + job_id → ARIA responde
```

### C: Portfolio Optimization
```
Usuario → ARIA → quantum_compute(mode=portfolio, returns=[...], covariance=[...])
   → construir QUBO → circuito superposición (n qubits)
   → ejecutar simulate/cloud → evaluar combinaciones
   → ordenar por objetivo → best_portfolio → ARIA responde
```

---

## 6. CIRCUITOS PRESET

| Nombre | Qubits | Resultado esperado |
|--------|--------|--------------------|
| bell_state | 2 | 50% \|00⟩, 50% \|11⟩ |
| ghz_3 | 3 | 50% \|000⟩, 50% \|111⟩ |
| ghz_4 | 4 | 50% \|0000⟩, 50% \|1111⟩ |
| superposition_single | 1 | 50% \|0⟩, 50% \|1⟩ |
| deutsch_jozsa_constant | 2 | Confirma función constante |

Gates custom: h, x, y, z, t, s, cx, cz, swap, rx, ry, rz, measure

---

## 7. SETUP

```bash
# 1. Instalar
pip install qiskit numpy
pip install qiskit-ibm-runtime   # opcional, solo para QPU real

# 2. (Opcional) Configurar IBM
#    → https://quantum.cloud.ibm.com → cuenta gratuita → copiar API key
#    → agregar a .env: IBM_QUANTUM_API_KEY=xxx

# 3. Registrar tool (ver sección 4)

# 4. Testear
python quantum_compute.py
```

---

## 8. INTEGRACIÓN FUTURA CON ATLAS

```python
# atlas/workflow/quantum_pipeline.py (FUTURO)
class QuantumPortfolioPipeline:
    def run(self, symbols, lookback_days=252, risk_aversion=1.0):
        data = AtlasDataHandler().fetch(symbols=symbols)
        expected_returns = data.pct_change().mean().tolist()
        covariance = data.pct_change().cov().values.tolist()
        return QuantumComputeTool().execute(
            mode="portfolio",
            returns=expected_returns,
            covariance=covariance,
            risk_aversion=risk_aversion
        )
```

---

## 9. LIMITACIONES

| Limitación | Solución futura |
|------------|-----------------|
| Open Plan 10 min/mes | Flex/Premium si escala |
| Cola QPU real (minutos) | simulate para desarrollo |
| Max 20 activos local | IBM Quantum Portfolio Optimizer (Premium) |
| Ruido NISQ | Error mitigation automático en Runtime |

---

## 10. RESUMEN

```
✅ HOY (sin configuración):        ⏳ En pausa (roadblock $$$):
   - Simulador local                  - Quantum Portfolio Optimizer
   - 5 circuitos preset               - Portfolios > 20 activos QPU
   - Circuitos custom                 - Qiskit Functions Catalog
   - Portfolio optimization ≤20

✅ Con Open Plan (gratis):         ⏳ Futuro (cuando Atlas tenga risk/):
   - Todo en QPU real IBM             - QuantumPortfolioPipeline
   - 100+ qubits hardware real        - Datos reales → quantum → portfolio
```
