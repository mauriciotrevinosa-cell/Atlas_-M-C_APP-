# Implementación de Portfolio + 3D Lab (Atlas OS)

Este paquete contiene los archivos actualizados para la vista de Finanzas con:
- **Modelos 3D reales** usando Three.js (no imágenes estáticas).
- **Formulario de creación de portfolio** con almacenamiento local.
- **Simulación 3D día a día** basada en decisiones.

## Archivos incluidos
- `index.html` → Vista de Finanzas con el lab 3D y formulario.
- `finance.js` → Lógica de portfolio, render 3D y simulación.

> Nota: Estos archivos son copias listas para integrarse en tu proyecto.

## Cómo implementar

1. **Reemplaza tus archivos actuales**:
   - Copia `deliverables/index.html` a `apps/desktop/index.html`.
   - Copia `deliverables/finance.js` a `apps/desktop/finance.js`.

2. **Asegura la carga de Three.js** (ya incluido en `index.html`):
   ```html
   <script src="https://unpkg.com/three@0.159.0/build/three.min.js"></script>
   <script src="finance.js"></script>
   ```
   - El script de Three.js debe cargarse **antes** de `finance.js`.

3. **Verifica el flujo del portfolio**:
   - Si la API `/api/portfolio` no está disponible, el sistema usa **localStorage**.
   - El formulario “Create Portfolio” permite crear posiciones y alimentar los modelos 3D.

4. **Inicia la simulación 3D**:
   - Selecciona una decisión (Hold / Risk On / Risk Off / Hedge).
   - Presiona **Start Sim** y luego **Next Day** para avanzar día por día.
   - El render se actualiza con los parámetros de la simulación.

## Comprobación rápida
1. Abre la app en el navegador.
2. Ve a **Finance**.
3. Agrega una posición con el formulario.
4. Presiona cualquiera de los botones 3D (Volatility / Correlation / Risk).
5. Verifica que se renderiza un modelo 3D interactivo.

## Resolución de problemas
- **No se ve el 3D**: confirma que `three.min.js` se cargó antes de `finance.js`.
- **No hay datos en el 3D**: agrega al menos una posición en el portfolio.
- **La API falla**: el sistema usa automáticamente localStorage como fallback.
