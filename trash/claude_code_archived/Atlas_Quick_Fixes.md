# Atlas / M&C App — Quick Fixes (Typos & Naming)

Este documento lista **correcciones rápidas** (typos, naming, consistencia) detectadas a nivel de **estructura del repo y documentación**, sin entrar en arquitectura final.

## 1. Carpetas con espacios
- `apps/ cli/` → `apps/cli/` o `apps_cli/`
Motivo: scripts, imports y CI fallan o se vuelven frágiles con espacios.

## 2. Carpetas temporales (marcar explícitamente)
Las siguientes carpetas son **temporales** y deben llevar un marcador claro:
- `Project_Governance/`
- `claude code/`
- `tras/` (si existe)

Acción:
- Agregar `README_TEMP.md` en cada una con:
  - Propósito
  - Owner
  - Fecha/condición de eliminación
  - Nota: “NO es parte del core”

## 3. Repo público vs README
Si el README menciona que el repo es privado:
- Actualizar texto para reflejar estado público
- O volver el repo privado

Evitar contradicciones de gobernanza.

## 4. Consistencia de naming (branding)
Nombre del repo: `Atlas_-M-C_APP-`

Acción:
- Definir un **spelling oficial** en README y docs:
  - Ejemplo: `Atlas (codename) / M&C App (public)`
- Evitar mezclar variantes en documentos.

## 5. Paths inconsistentes (ARIA)
Se detecta uso conceptual de:
- `src/aria/...`
- `python/src/atlas/...`

Acción:
- Consolidar ARIA en un solo path:
  - Recomendado: `python/src/atlas/assistants/aria/`
- Mover prototipos a `legacy/` o `lab/`

## 6. Dependencias duplicadas
Existen:
- `requirements.txt`
- `pyproject.toml`

Acción:
- Definir en README cuál es la fuente de verdad
  - Ejemplo: `pyproject.toml` manda, `requirements.txt` es export

## 7. Checklist rápido para detectar typos (local)
```bash
git ls-files | grep " "
rg -n "evollucionado|ah evollucionado|ves de|veses|haver|ahorita|andamos llendo" .
```

---

Estado del documento: **Listo para entregar a Antigravity**  
Tipo: Higiene / mantenimiento  
Impacto: Bajo riesgo, alto orden
