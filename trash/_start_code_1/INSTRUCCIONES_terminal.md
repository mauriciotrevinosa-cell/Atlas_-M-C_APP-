# 🖥️ ARIA Terminal Interactiva

## Terminal 100% Autónoma

Chat con ARIA usando SOLO Ollama local (sin APIs comerciales)

---

## 📥 Instalación

### 1. Copiar archivo:
```
chat_terminal.py → ARIA_FULL_CODE/Aria/
```

**Ubicación final:**
```
ARIA_FULL_CODE/Aria/chat_terminal.py
```

### 2. Verificar que Ollama está corriendo:

**Abrir terminal y ejecutar:**
```bash
ollama serve
```

**Dejar esa terminal abierta** (Ollama corriendo en background)

---

## 🚀 Uso

### Iniciar terminal:

```bash
cd C:\Users\mauri\OneDrive\Desktop\ARIA_FULL_CODE\Aria
python chat_terminal.py
```

### Deberías ver:

```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     █████╗ ██████╗ ██╗ █████╗                          ║
║    ██╔══██╗██╔══██╗██║██╔══██╗                         ║
║    ███████║██████╔╝██║███████║                         ║
║    ██╔══██║██╔══██╗██║██╔══██║                         ║
║    ██║  ██║██║  ██║██║██║  ██║                         ║
║    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝                         ║
║                                                          ║
║    Atlas Reasoning & Intelligence Assistant             ║
║    v5.0 - Autonomous Edition                            ║
║    100% Local | Powered by Ollama                       ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

🔄 Inicializando ARIA...
✅ Using Ollama (local, no API key needed)
✅ Ollama connected (model: llama3.1:8b)
🤖 ARIA initialized (ollama)
✅ ARIA lista

🧑 Tú: _
```

---

## 💬 Comandos

### Conversación normal:
```
🧑 Tú: ¿Qué es una opción call?
🤖 ARIA: [explicación detallada]

🧑 Tú: Dame un ejemplo con AAPL
🤖 ARIA: [ejemplo específico]
```

### Comandos especiales:

| Comando | Descripción |
|---------|-------------|
| `/exit` o `/quit` | Salir del terminal |
| `/clear` | Limpiar historial de conversación |
| `/save [nombre]` | Guardar conversación |
| `/help` | Mostrar ayuda |
| `/stats` | Ver estadísticas de sesión |

---

## 📝 Ejemplos de uso

### Ejemplo 1: Preguntas conceptuales
```
🧑 Tú: Explícame qué es la volatilidad implícita
🤖 ARIA: [explicación clara]

🧑 Tú: ¿Cómo se diferencia de la volatilidad histórica?
🤖 ARIA: [comparación detallada]
```

### Ejemplo 2: Análisis
```
🧑 Tú: ¿Qué factores debo considerar antes de comprar una opción?
🤖 ARIA: [lista de factores: IV, theta, delta, etc.]

🧑 Tú: Explícame el factor theta más a detalle
🤖 ARIA: [explicación profunda de theta decay]
```

### Ejemplo 3: Guardar conversación
```
🧑 Tú: /save analisis_opciones
✅ Conversación guardada: conversations/analisis_opciones.json
```

---

## 🔧 Troubleshooting

### Error: "Ollama not running"
```bash
# Solución:
# 1. Abre otra terminal
# 2. Ejecuta:
ollama serve

# 3. Deja esa terminal abierta
# 4. Vuelve a correr chat_terminal.py
```

### Error: "Module 'ollama' not found"
```bash
pip install ollama
```

### Error: "No module named 'aria'"
```bash
# Asegúrate de estar en la carpeta correcta:
cd ARIA_FULL_CODE/Aria
python chat_terminal.py
```

---

## ✨ Características

✅ **100% Local** - Sin APIs comerciales
✅ **Conversación natural** - Mantiene contexto
✅ **Comandos útiles** - Guardar, limpiar, stats
✅ **Banner profesional** - UI limpia
✅ **Error handling** - Maneja interrupciones
✅ **Historial persistente** - Durante la sesión

---

## 🎯 Próximos pasos

Una vez que funcione bien:

1. ✅ Conversación fluida
2. ⏭️ Agregar tool `get_data()`
3. ⏭️ ARIA puede buscar datos reales
4. ⏭️ Agregar más tools (create_file, execute_code, etc.)

---

## 📊 Progreso

```
╔══════════════════════════════════════════════════════════╗
║  FASE 1.5: TOOLS BÁSICOS                                 ║
╠══════════════════════════════════════════════════════════╣
║  Progreso: ████████████░░░░░░░░ 60%                      ║
╚══════════════════════════════════════════════════════════╝

COMPLETADO:
├─ [████████████████████] 100% - ARIA conversacional ✅
├─ [████████████████████] 100% - Terminal interactiva ✅
├─ [████████████████████] 100% - get_data() tool creado ✅
│
SIGUIENTE:
└─ [░░░░░░░░░░░░░░░░░░░░]   0% - Integrar tool en terminal
```

---

**¡Disfruta charlando con ARIA!** 💬🤖
