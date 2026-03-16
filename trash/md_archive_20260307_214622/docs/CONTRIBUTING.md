# CONTRIBUTING TO ATLAS

Bienvenido a las guías de contribución de la plataforma **Atlas** y el ecosistema **ARIA**. Para mantener la sanidad del repositorio y escalar el desarrollo a múltiples agentes y desarrolladores, apégate rigurosamente a estas reglas.

## 1. Convenciones Generales
- **Nomenclatura (Naming Space):** Los nombres de carpetas y archivos **NO** deben contener espacios (`mi_archivo.py`, `nueva_carpeta/`). Se recomienda fuertemente el uso de `snake_case`. Si encuentras algún nombre con espacios, corrígelo, renómbralo y refactoriza los imports.
- **Fuente de Verdad:** Todo el código implementado en Python y lógica de negocio debe ubicarse dentro de `python/src/atlas/`. No agrupes carpetas `src` en otros lugares de la raíz (`src/aria`, etc.); el `lab/` está previsto para prototipos no integrados.
- **Dependencias:** Utiliza siempre `pyproject.toml` como la única fuente de verdad para el empaquetado y las dependencias del proyecto. Si necesitas reportarlo hacia afuera, puedes generar un `requirements.txt` pero no añadas dependencias exclusivamente ahí sin actualizar el archivo `.toml`.

## 2. Regla "No Orphans" (Sin Código Huérfano)
- Está estrictamente prohibido el código muerto/inutilizado en los flujos principales (core). Cada módulo debe estar conectado con la pipeline o tener cobertura de tests que justifiquen su existencia.
- Cualquier archivo viejo, reemplazado o función abandonada que no sea importada en ningún lado debe ser eliminada o movida sistemáticamente a `python/src/atlas/lab/legacy/orphans/`.

## 3. Contratos de Código e Integración
- **Flujo de Ejecución:** Mantén claras las interfaces modulares usando la filosofía estándar: `Data -> Analytics -> Simulation -> Risk -> Renders`. No acoples capas (p. ej., Renders buscando datos puros directamente si no es indispensable).
- **Output de Scripts/Runs (Artefactos):** Todas las salidas en disco (CSVs, Renders HTML/JS, métricas, gráficas, run states) deben escribirse exclusivamente en el path de artefactos correspondiente a su run local. Estandariza todo a `outputs/runs/<run_id>/`. Puedes utilizar el helper central en `atlas/common/io.py` si programas en Python.

## 4. Utilities y Refactorización
- Si detectas lógica repetitiva transversal como la validación de config schemas, setup de logging, parseo de timestamps o configuraciones que ocurren en distintos features, es tu deber abstraerlas hacia el directorio modular `python/src/atlas/common/`.
