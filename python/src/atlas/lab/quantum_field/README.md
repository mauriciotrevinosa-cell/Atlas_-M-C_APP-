# Atlas Research Spike: Quantum Field — SSCT

**Estado:** Propuesto / Implementado (Spike)
**Objetivo:** Validar control de forma de estado usando IBM Quantum.

## Estructura

- `qpu_validation/`: Scripts para ejecución en hardware cuántico real (IBM Quantum).
- `quantum_like/`: Implementación futura en CPU inspirada en mecánica cuántica (si el spike es GO).

## Ejecución del Spike

1. Configurar cuenta IBM Quantum:
   ```python
   from qiskit_ibm_runtime import QiskitRuntimeService
   QiskitRuntimeService.save_account(channel="ibm_quantum", token="TU_TOKEN")
   ```

2. Ejecutar validación:
   ```bash
   python qpu_validation/run_ssct.py
   ```

3. Analizar resultados con `metrics.py` y decidir GO/NO-GO.

## Mapeo Conceptual

| Qubit | Dimensión | Significado |
|-------|-----------|-------------|
| q0    | X         | Drift       |
| q1    | Y         | Volatilidad |
| q2    | Z         | Shock       |

---
**Atlas Lab Project**
