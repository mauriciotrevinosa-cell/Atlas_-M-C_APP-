# 🤖 ARIA (AI Assistant) - Guía Completa de Activación

## 📖 ¿Qué es ARIA?

**ARIA** (Atlas Reasoning & Intelligence Assistant) es tu asistente de IA para explicar decisiones, ejecutar análisis y debuggear el sistema.

---

## ✨ ¿Para qué sirve?

- Explicar señales y decisiones
- Comparar backtests
- Generar reportes automáticos
- Debuggear errores
- Responder preguntas sobre el sistema
- Ejecutar análisis complejos
- Crear archivos y documentación

---

## 🎯 MODOS DE INTERACCIÓN

ARIA puede interactuar contigo de **4 formas diferentes**:

1. **Chat de Texto** (Código Python) - ⭐ Más fácil
2. **Chat Web UI** (Navegador) - 🌐 Más visual
3. **Voz Básica** (Gratis) - 🎤 Text-to-Speech
4. **Voz Avanzada** (Premium) - 🎤⭐ Ultra-realista

---

## 📋 SETUP INICIAL (Requerido para TODOS los modos)

### PASO 1: Instalar dependencias
```bash
cd Atlas/python
pip install -e ".[aria]"
```

### PASO 2: Obtener API key de Anthropic
1. Ir a https://console.anthropic.com
2. Crear cuenta / Iniciar sesión
3. Crear API key
4. Copiar la key (empieza con `sk-ant-...`)

### PASO 3: Configurar `.env`
```bash
# Copiar template
cp .env.example .env

# Editar .env
notepad .env

# Agregar tu key:
ANTHROPIC_API_KEY=sk-ant-tu-key-aqui
```

### PASO 4: Habilitar en `settings.toml`
```toml
[aria]
enabled = true
provider = "anthropic"
model = "claude-sonnet-4-20250514"

[aria.permissions]
can_execute_backtests = true
can_create_files = true
can_modify_configs = false  # Seguridad
can_execute_trades = false  # Requiere aprobación
```

### PASO 5: Probar que funciona
```python
from atlas.lab.aria import hello
hello()
```

**Output esperado:**
```
    _    ____  ___    _    
   / \  |  _ \|_ _|  / \   
  / _ \ | |_) || |  / _ \  
 / ___ \|  _ < | | / ___ \ 
/_/   \_\_| \_\|___/_/   \_\

🎯 ARIA (Atlas Reasoning & Intelligence Assistant) loaded!
Status: Experimental Lab Code
```

---

## 💬 MODO 1: Chat de Texto (Python)

### ¿Cuándo usar?
- Scripts automatizados
- Notebooks de Jupyter
- Análisis en código

### Implementación:

```python
from atlas.lab.aria import chat

# Iniciar conversación
aria = chat.ARIA()

# Preguntar algo
response = aria.ask("¿Por qué Atlas recomendó HOLD en AAPL?")
print(response)
```

**Output ejemplo:**
```
Atlas recomendó HOLD porque:

1. Signal Engine: LONG 65% (moderado, no fuerte)
2. Risk Engine: Correlación alta con MSFT (0.85)
   → Portfolio demasiado expuesto a tech
3. Monte Carlo: 45% de paths caen bajo stop loss
4. Discrepancy: Conflicto moderado detectado

Recomendación: Esperar a que baje la correlación
o reducir exposición a MSFT primero.
```

### Conversación con contexto:

```python
# ARIA mantiene contexto
aria.ask("¿Qué pasó con mi último backtest?")
# ARIA: "Tu backtest de momentum falló porque..."

aria.ask("¿Puedes arreglarlo?")
# ARIA: "Claro, el problema era data missing. Ya lo arreglé."

aria.ask("¿Cuál es el nuevo Sharpe?")
# ARIA: "El nuevo Sharpe Ratio es 1.85 (antes: 1.2)"
```

### Guardar conversaciones:

```python
# Exportar historial
aria.save_conversation("conversations/2024-01-29.json")

# Cargar conversación previa
aria.load_conversation("conversations/2024-01-29.json")
```

---

## 🌐 MODO 2: Chat Web UI (Navegador)

### ¿Cuándo usar?
- Explorar visualmente
- Comparar backtests con gráficos
- Interfaz más amigable

### Implementación (Futuro):

**PASO 1: Instalar UI**
```bash
cd Atlas/ui_web
npm install
```

**PASO 2: Iniciar servidor**
```bash
npm run dev
```

**PASO 3: Abrir en navegador**
```
http://localhost:3000/aria
```

### Interfaz:

```
┌──────────────────────────────────────────┐
│ ARIA - Atlas Assistant            [Send] │
├──────────────────────────────────────────┤
│                                          │
│ 👤 User:                                 │
│ ¿Qué pasó con mi backtest de ayer?       │
│                                          │
│ 🤖 ARIA:                                 │
│ Tu backtest falló porque faltaban datos  │
│ en 2024-01-15. Arreglé el gap usando     │
│ interpolación lineal.                    │
│                                          │
│ [Ver backtest corregido] [Ver gráfico]   │
│                                          │
├──────────────────────────────────────────┤
│ [Escribe tu mensaje...]           [Send] │
└──────────────────────────────────────────┘
```

### Características:
- ✅ Chat persistente
- ✅ Ver gráficos inline
- ✅ Descargar reportes
- ✅ Historial de conversaciones
- ✅ Búsqueda en conversaciones pasadas

---

## 🎤 MODO 3: Voz Básica (GRATIS)

### ¿Cuándo usar?
- Hands-free (mientras tradeas)
- Multitasking
- Exploración rápida

### Implementación:

**PASO 1: Instalar dependencias**
```bash
pip install SpeechRecognition gtts pyaudio
```

**PASO 2: Crear script de voz**
```python
# atlas/lab/aria/voice_basic.py
import speech_recognition as sr
from gtts import gTTS
import os
from atlas.lab.aria import chat

class ARIAVoice:
    def __init__(self):
        self.aria = chat.ARIA()
        self.recognizer = sr.Recognizer()
    
    def listen(self):
        """Escuchar del micrófono"""
        with sr.Microphone() as source:
            print("🎤 Escuchando...")
            audio = self.recognizer.listen(source)
            try:
                text = self.recognizer.recognize_google(audio, language='es-ES')
                print(f"👤 Tú: {text}")
                return text
            except sr.UnknownValueError:
                print("❌ No entendí, repite por favor")
                return None
    
    def speak(self, text):
        """Convertir texto a voz"""
        print(f"🤖 ARIA: {text}")
        tts = gTTS(text=text, lang='es')
        tts.save("temp_response.mp3")
        os.system("start temp_response.mp3")  # Windows
        # os.system("afplay temp_response.mp3")  # macOS
        # os.system("mpg321 temp_response.mp3")  # Linux
    
    def conversation_loop(self):
        """Loop de conversación por voz"""
        print("🎯 ARIA Voice Mode activado")
        print("Di 'salir' para terminar")
        
        while True:
            # Escuchar
            user_input = self.listen()
            
            if user_input is None:
                continue
            
            if "salir" in user_input.lower():
                self.speak("Hasta luego")
                break
            
            # Obtener respuesta de ARIA
            response = self.aria.ask(user_input)
            
            # Responder con voz
            self.speak(response)

# Usar
if __name__ == "__main__":
    aria_voice = ARIAVoice()
    aria_voice.conversation_loop()
```

**PASO 3: Ejecutar**
```bash
python atlas/lab/aria/voice_basic.py
```

### Ejemplo de uso:

```
🎯 ARIA Voice Mode activado

🎤 Escuchando...
👤 Tú: ¿Cuál es mi Sharpe Ratio?
🤖 ARIA: Tu Sharpe Ratio actual es 1.85
[Voz: "Tu Sharpe Ratio actual es uno punto ochenta y cinco"]

🎤 Escuchando...
👤 Tú: ¿Por qué bajó?
🤖 ARIA: Bajó porque hubo un drawdown de 8% la semana pasada
[Voz: "Bajó porque hubo un drawdown..."]
```

### Pros y Contras:

✅ **Pros:**
- Completamente GRATIS
- Funciona offline (después de primera instalación)
- Fácil de implementar

❌ **Contras:**
- Voz robótica (Google TTS)
- Reconocimiento básico (puede fallar con ruido)
- Latencia moderada (~2 segundos)

---

## 🎤⭐ MODO 4: Voz Avanzada (Premium - Ultra-Realista)

### ¿Cuándo usar?
- Presentaciones profesionales
- Calidad de voz humana
- Conversaciones largas

### Implementación:

**PASO 1: Obtener API keys**

1. **Whisper (OpenAI)** - Para Speech-to-Text
   - Ir a https://platform.openai.com
   - Crear API key
   - Copiar key

2. **ElevenLabs** - Para Text-to-Speech ultra-realista
   - Ir a https://elevenlabs.io
   - Crear cuenta ($11/mes o $99/año)
   - Copiar API key

**PASO 2: Configurar `.env`**
```env
OPENAI_API_KEY=sk-proj-tu-key-aqui
ELEVENLABS_API_KEY=tu-elevenlabs-key
```

**PASO 3: Instalar dependencias**
```bash
pip install openai elevenlabs pyaudio
```

**PASO 4: Crear script avanzado**
```python
# atlas/lab/aria/voice_advanced.py
import openai
from elevenlabs import generate, play, Voice, VoiceSettings
from atlas.lab.aria import chat
import pyaudio
import wave

class ARIAVoiceAdvanced:
    def __init__(self):
        self.aria = chat.ARIA()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Configurar voz de ARIA (ElevenLabs)
        self.voice = Voice(
            voice_id="EXAVITQu4vr4xnSDxMaL",  # "Bella" - voz femenina profesional
            settings=VoiceSettings(
                stability=0.75,
                similarity_boost=0.85,
                style=0.5,
                use_speaker_boost=True
            )
        )
    
    def record_audio(self, filename="temp_question.wav", duration=5):
        """Grabar audio del micrófono"""
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100
        
        p = pyaudio.PyAudio()
        
        print("🎤 Grabando... (habla ahora)")
        
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
        
        frames = []
        for i in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Guardar
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return filename
    
    def transcribe(self, audio_file):
        """Convertir voz a texto con Whisper"""
        with open(audio_file, "rb") as f:
            transcript = openai.Audio.transcribe(
                model="whisper-1",
                file=f,
                language="es"
            )
        return transcript.text
    
    def speak(self, text):
        """Convertir texto a voz ultra-realista"""
        print(f"🤖 ARIA: {text}")
        
        audio = generate(
            text=text,
            voice=self.voice,
            model="eleven_multilingual_v2"
        )
        
        play(audio)
    
    def conversation_loop(self):
        """Loop de conversación avanzado"""
        print("🎯 ARIA Voice Mode (Advanced) activado")
        print("Presiona ENTER para hablar, escribe 'salir' para terminar")
        
        while True:
            cmd = input("\n[Presiona ENTER para hablar] ")
            
            if cmd.lower() == "salir":
                self.speak("Hasta luego, que tengas un excelente día")
                break
            
            # Grabar audio
            audio_file = self.record_audio(duration=5)
            
            # Transcribir con Whisper
            user_text = self.transcribe(audio_file)
            print(f"👤 Tú: {user_text}")
            
            # Obtener respuesta de ARIA
            response = self.aria.ask(user_text)
            
            # Responder con voz ultra-realista
            self.speak(response)

# Usar
if __name__ == "__main__":
    aria_advanced = ARIAVoiceAdvanced()
    aria_advanced.conversation_loop()
```

**PASO 5: Ejecutar**
```bash
python atlas/lab/aria/voice_advanced.py
```

### Ejemplo de uso:

```
🎯 ARIA Voice Mode (Advanced) activado

[Presiona ENTER para hablar]
🎤 Grabando... (habla ahora)
👤 Tú: ARIA, ¿cómo está mi portafolio hoy?

🤖 ARIA: Tu portafolio tuvo un rendimiento excelente hoy.
         Ganaste 2.3% con AAPL subiendo 3.5% y MSFT 1.8%.
         Tu Sharpe Ratio mejoró a 1.92.
[Voz ultra-realista - suena 100% humano]

[Presiona ENTER para hablar]
🎤 Grabando...
👤 Tú: ¿Debería tomar ganancias?

🤖 ARIA: Recomiendo tomar ganancias parciales en AAPL.
         Según el análisis técnico, está en resistencia.
         Considera vender 50% de la posición.
[Voz: Natural, con entonación profesional]
```

### Pros y Contras:

✅ **Pros:**
- Voz **indistinguible de humano**
- Reconocimiento perfecto (Whisper es mejor que Google)
- Baja latencia (~1 segundo)
- Soporta múltiples idiomas
- Puedes elegir voces (masculinas, femeninas, acentos)

❌ **Contras:**
- **Costo:** ~$11/mes (ElevenLabs) + API OpenAI ($0.006/minuto)
- Requiere internet
- Setup más complejo

---

## 📊 COMPARACIÓN DE MODOS

| Modo | Costo | Calidad Voz | Setup | Latencia | Offline |
|------|-------|-------------|-------|----------|---------|
| Chat Texto | $0.01/msg | N/A | ⭐ Fácil | Instantáneo | ❌ |
| Chat Web UI | Gratis | N/A | ⭐⭐ Medio | Instantáneo | ❌ |
| Voz Básica | **GRATIS** | 🤖 Robótica | ⭐⭐ Medio | ~2 seg | ✅ |
| Voz Avanzada | $11/mes | 👤 Humana | ⭐⭐⭐ Complejo | ~1 seg | ❌ |

---

## 🎯 RECOMENDACIONES

### Para empezar:
**Chat de Texto** → Simple, funciona ya

### Para explorar visualmente:
**Chat Web UI** → Cuando esté implementado

### Para hands-free:
**Voz Básica** → Gratis, suficiente para la mayoría

### Para presentaciones/profesional:
**Voz Avanzada** → Vale la pena si usas mucho

---

## 🆘 TROUBLESHOOTING

### Problema: `No module named 'speech_recognition'`
```bash
pip install SpeechRecognition pyaudio
```

### Problema: Micrófono no funciona
- **Windows:** Verificar permisos de micrófono
- **macOS:** System Preferences → Security → Microphone
- **Linux:** `sudo apt-get install portaudio19-dev`

### Problema: ElevenLabs quota exceeded
- Has alcanzado el límite mensual
- Upgrade plan o esperar al próximo mes

### Problema: Whisper muy lento
- Usar modelo más pequeño: `model="whisper-1-tiny"`
- O usar reconocimiento de Google (gratis pero menos preciso)

---

## 📝 PRÓXIMOS PASOS

1. Probar **Chat de Texto** primero
2. Si te gusta, implementar **Voz Básica**
3. Si usas mucho, considerar **Voz Avanzada**
4. Customizar la **personalidad** de ARIA en `settings.toml`

---

**¿Preguntas sobre ARIA?**  
Pregúntale a ARIA misma: `aria.ask("¿Cómo funcionas?")` 😉
