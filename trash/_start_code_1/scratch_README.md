# 🗑️ Scratch / Temporal Code

**Propósito:** Código temporal, experimentos rápidos, prototipos descartables

---

## 📖 ¿Qué es Scratch?

Esta carpeta es tu **zona libre** para:

- ✅ Probar ideas rápidas
- ✅ Hacer POCs (Proof of Concepts)
- ✅ Debuggear problemas
- ✅ Copiar código de ejemplos
- ✅ Scripts one-off
- ✅ Tests manuales

**Regla de oro:** Todo aquí es **temporal y descartable**.

---

## 🚫 Qué NO poner aquí

- ❌ Código de producción
- ❌ Funciones que se usan en múltiples lugares
- ❌ Tests importantes
- ❌ Documentación
- ❌ Configuraciones

**Si el código es importante → moverlo a `lab/` o al módulo correspondiente**

---

## 📁 Estructura Sugerida (Opcional)

```
scratch/
├─ README.md                    # Este archivo
├─ test_something.py            # Tests rápidos
├─ prototype_feature.py         # Prototipos
├─ debug_issue_123.py           # Debugging
├─ example_from_docs.py         # Ejemplos copiados
└─ temp_analysis.ipynb          # Notebooks temporales
```

**Nota:** No hay estructura obligatoria. Haz lo que quieras aquí.

---

## 🔄 Ciclo de Vida del Código

```
1. Idea rápida
   ↓
2. Código en scratch/ (prototipo)
   ↓
3a. No funciona → Eliminar
3b. Funciona → Refinar
   ↓
4. Mover a lab/ (experimental pero organizado)
   ↓
5. Validar y testear
   ↓
6. Promover a core/ (producción)
```

---

## 🧹 Limpieza

### Cuándo limpiar:
- Cada semana
- Antes de commits importantes
- Cuando la carpeta se llena

### Cómo limpiar:
```bash
# Ver qué hay
ls scratch/

# Eliminar todo (cuidado!)
rm scratch/*.py

# O revisar archivo por archivo
```

**Tip:** Si no lo has usado en 2 semanas, probablemente ya no lo necesitas.

---

## 🎯 Ejemplos de Uso

### Ejemplo 1: Probar una idea rápida
```python
# scratch/test_new_indicator.py
import pandas as pd

# Probar si un indicador funciona
def custom_indicator(data):
    return data.rolling(20).mean() * 1.5

# Probar con datos dummy
data = pd.Series([1, 2, 3, 4, 5])
print(custom_indicator(data))

# Si funciona → refinar y mover a indicators/
```

### Ejemplo 2: Debuggear un problema
```python
# scratch/debug_backtest_error.py

# Reproducir el error en aislamiento
from atlas.backtesting import backtest_engine

# Código minimal para reproducir el bug
bt = backtest_engine.Backtest(...)
bt.run()  # ← Aquí falla

# Encontrar el problema
# Arreglar en el código real (no aquí)
```

### Ejemplo 3: Script one-off
```python
# scratch/fix_data_2024_01_29.py

# Script para arreglar datos corruptos (solo se usa una vez)
import pandas as pd

data = pd.read_csv("data/raw/AAPL.csv")
# ... arreglar ...
data.to_csv("data/raw/AAPL_fixed.csv")

# Después de ejecutar → eliminar este script
```

---

## 🎓 Mejores Prácticas

### ✅ Hacer:
- Usa nombres descriptivos (`test_X`, `debug_Y`, `prototype_Z`)
- Comenta por qué existe el archivo
- Fecha los archivos si son específicos a un día
- Elimina cuando ya no sirven

### ❌ No hacer:
- No imports complejos de scratch/ en código real
- No dependencias de archivos en scratch/
- No tests críticos aquí (van en `tests/`)
- No código que se queda meses sin usar

---

## 📝 Template Sugerido

```python
"""
Propósito: [Por qué existe este archivo]
Fecha: 2026-01-29
Status: Temporal
Eliminar después de: [Fecha o condición]
"""

# Tu código aquí
```

---

## 🔗 Alternativas

Si tu código **no es descartable**:

- **Notebooks exploratorios** → `research/notebooks/`
- **Experimentos validados** → `lab/`
- **Código de producción** → Módulo correspondiente
- **Tests** → `tests/`

---

## ⚠️ Git & Scratch

**Scratch/ está en .gitignore (casi todo)**

Solo se sube a Git:
- ✅ Este README.md
- ❌ Todo lo demás

**Razón:** Código temporal no debe estar en control de versiones.

**Excepción:** Si un prototipo es muy valioso, moverlo a `lab/` primero.

---

## 💡 Tip Pro

Usa scratch/ como **tu sandbox personal**.

No hay reglas, no hay estructura, no hay juicios.

Es tu espacio para **romper cosas y experimentar** sin miedo.

Cuando algo funciona → lo mueves al lugar correcto.

---

**Última actualización:** 2026-01-29  
**Propósito:** Zona libre de experimentación  
**Regla de oro:** Todo aquí es temporal
