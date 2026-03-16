# 📦 ARIA MATH TOOLS + CODE EXECUTOR

**Generado por:** Claude (Arquitecto/Constructor)  
**Para:** Antigravity (Organizador)  
**Fecha:** 2026-02-08

---

## 🎯 QUÉ ES ESTO

Dos capacidades nuevas para ARIA:

### 1. Math Toolset (27 tools)
Funciones financieras/estadísticas que ARIA puede llamar directamente:

| Categoría | Tools |
|-----------|-------|
| **TVM** | `present_value`, `future_value`, `annuity_pv`, `perpetuity_pv`, `effective_rate` |
| **Bonds** | `bond_price`, `macaulay_duration`, `bond_convexity` |
| **Corporate** | `wacc`, `npv`, `irr` |
| **Options** | `black_scholes`, `greeks`, `put_call_parity`, `implied_volatility` |
| **Portfolio** | `portfolio_stats`, `capm`, `beta_from_data`, `value_at_risk`, `sharpe_ratio`, `sortino_ratio` |
| **Stats** | `descriptive_stats`, `ols_regression`, `correlation_matrix` |
| **Simulation** | `gbm_simulate` |

### 2. Code Executor
ARIA puede escribir y ejecutar código Python de forma autónoma, con sandbox de seguridad.

---

## 📋 MAPA DE ARCHIVOS

| Archivo | Destino en repo |
|---------|----------------|
| `tools/__init__.py` | `assistants/aria/tools/__init__.py` |
| `tools/financial_math.py` | `assistants/aria/tools/financial_math.py` |
| `tools/registry.py` | `assistants/aria/tools/registry.py` |
| `code_executor/__init__.py` | `assistants/aria/tools/code_executor/__init__.py` |
| `code_executor/executor.py` | `assistants/aria/tools/code_executor/executor.py` |

---

## 📝 INSTRUCCIONES

### PASO 1: Crear carpetas
```bash
cd assistants/aria/
mkdir -p tools/code_executor
```

### PASO 2: Copiar los 5 archivos según la tabla de arriba

### PASO 3: Verificar
```bash
python -c "
from atlas.assistants.aria.tools.financial_math import MATH_TOOLS
print(f'Math tools: {len(MATH_TOOLS)}')
for name in sorted(MATH_TOOLS.keys()):
    print(f'  ✅ {name}')
"
```

### PASO 4: Test rápido
```bash
python -c "
from atlas.assistants.aria.tools.financial_math import black_scholes, greeks, npv, wacc
print(black_scholes(S=150, K=155, T=0.25, r=0.05, sigma=0.20))
print(greeks(S=150, K=155, T=0.25, r=0.05, sigma=0.20))
print(npv(cashflows=[-100000, 30000, 40000, 50000, 40000], discount_rate=0.10))
print(wacc(equity=600, debt=400, cost_equity=0.12, cost_debt=0.06, tax_rate=0.25))
print('✅ ALL OK')
"
```

### PASO 5: Test code executor
```bash
python -c "
from atlas.assistants.aria.tools.code_executor.executor import CodeExecutor
ex = CodeExecutor()
result = ex.execute('''
import numpy as np
prices = [100, 105, 103, 108, 112, 115, 110]
returns = np.diff(prices) / prices[:-1]
print(f'Mean return: {returns.mean():.4f}')
print(f'Volatility: {returns.std():.4f}')
print(f'Sharpe (ann): {returns.mean()/returns.std()*252**0.5:.2f}')
''')
print(result)
"
```

---

## 🔗 INTEGRACIÓN CON ARIA

Para que ARIA use estos tools en conversación, agregar a `terminal.py` (o donde se registren tools):

```python
from atlas.assistants.aria.tools.registry import ToolRegistry

registry = ToolRegistry()

# ARIA tool call handler
def handle_tool_call(tool_name: str, **kwargs):
    return registry.call(tool_name, **kwargs)

# Generate system prompt section
tools_prompt = registry.to_system_prompt_block()
# Inyectar tools_prompt en el system prompt de ARIA
```

---

## 💡 EJEMPLOS DE USO POR ARIA

**Usuario:** "¿Cuánto vale una call de AAPL strike $180, expira en 3 meses, vol 25%?"

**ARIA internamente:**
```python
result = registry.call("black_scholes", S=175, K=180, T=0.25, r=0.05, sigma=0.25)
# → {"price": 5.42, "d1": -0.0812, "d2": -0.2062}
```

**Usuario:** "Dame el VaR de mi portfolio"

**ARIA internamente:**
```python
result = registry.call("execute_code", code="""
import numpy as np
returns = np.random.normal(0.0005, 0.02, 252)  # Simulated
var_95 = np.percentile(returns, 5)
print(f"VaR 95%: {-var_95:.4f}")
print(f"On $100K: ${-var_95 * 100000:,.0f}")
""")
```

**Usuario:** "Corre una regresión de NVDA contra el S&P"

**ARIA internamente:**
```python
result = registry.call("ols_regression",
    y=nvda_returns,
    X=[spy_returns],
    add_intercept=True
)
# → {"coefficients": {"intercept": 0.0003, "x1": 1.52}, "r_squared": 0.68}
```

---

## ⚠️ SEGURIDAD DEL CODE EXECUTOR

**PERMITIDO:** numpy, pandas, scipy, math, statistics, json, collections, datetime, re, csv

**BLOQUEADO:** os, sys, subprocess, socket, http, requests, open(), exec(), eval()

El executor captura stdout/stderr y tiene timeout de 30 segundos.
