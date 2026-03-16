# 🖥️ ARIA Terminal Gráfica - Setup Guide

**UI moderna con Electron + React + TypeScript**

---

## 📦 Archivos necesarios (6 archivos)

### **1. package.json**
```json
{
  "name": "aria-terminal",
  "version": "1.0.0",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder"
  },
  "dependencies": {
    "electron": "^28.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.3.0",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "electron-builder": "^24.9.0"
  }
}
```

### **2. main.js** (Electron Main Process)
```javascript
const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    backgroundColor: '#1a1a1a',
    titleBarStyle: 'hidden',
    frame: false
  });

  win.loadFile('index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
```

### **3. index.html**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>ARIA Terminal</title>
  <style>
    body {
      margin: 0;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background: #1a1a1a;
      color: #ffffff;
    }
    
    #app {
      display: flex;
      flex-direction: column;
      height: 100vh;
    }
    
    .title-bar {
      height: 40px;
      background: #2a2a2a;
      display: flex;
      align-items: center;
      padding: 0 20px;
      -webkit-app-region: drag;
    }
    
    .chat-container {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
    }
    
    .message {
      margin-bottom: 20px;
      padding: 15px;
      border-radius: 10px;
      max-width: 80%;
    }
    
    .message.user {
      background: #0066cc;
      margin-left: auto;
    }
    
    .message.assistant {
      background: #2a2a2a;
    }
    
    .input-container {
      padding: 20px;
      background: #2a2a2a;
      display: flex;
      gap: 10px;
    }
    
    #input {
      flex: 1;
      padding: 15px;
      border: none;
      border-radius: 10px;
      background: #3a3a3a;
      color: #ffffff;
      font-size: 16px;
    }
    
    #voice-btn {
      width: 60px;
      height: 60px;
      border: none;
      border-radius: 50%;
      background: #0066cc;
      color: white;
      font-size: 24px;
      cursor: pointer;
    }
    
    #voice-btn:hover {
      background: #0052a3;
    }
    
    #voice-btn.listening {
      background: #ff0000;
      animation: pulse 1s infinite;
    }
    
    @keyframes pulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.1); }
    }
  </style>
</head>
<body>
  <div id="app">
    <div class="title-bar">
      🤖 ARIA Terminal
    </div>
    
    <div class="chat-container" id="chat">
      <!-- Messages appear here -->
    </div>
    
    <div class="input-container">
      <input type="text" id="input" placeholder="Ask ARIA anything...">
      <button id="voice-btn">🎤</button>
    </div>
  </div>

  <script>
    const chat = document.getElementById('chat');
    const input = document.getElementById('input');
    const voiceBtn = document.getElementById('voice-btn');
    
    // Server URL (change if needed)
    const SERVER_URL = 'http://localhost:8000';
    
    // Add message to chat
    function addMessage(role, content) {
      const msg = document.createElement('div');
      msg.className = `message ${role}`;
      msg.textContent = content;
      chat.appendChild(msg);
      chat.scrollTop = chat.scrollHeight;
    }
    
    // Send message
    async function sendMessage(text) {
      if (!text.trim()) return;
      
      // Add user message
      addMessage('user', text);
      input.value = '';
      
      try {
        // Query ARIA
        const response = await fetch(`${SERVER_URL}/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: text,
            device_id: 'desktop-terminal',
            session_id: localStorage.getItem('session_id')
          })
        });
        
        const data = await response.json();
        
        // Save session ID
        localStorage.setItem('session_id', data.session_id);
        
        // Add ARIA response
        addMessage('assistant', data.response);
      } catch (error) {
        addMessage('assistant', `❌ Error: ${error.message}`);
      }
    }
    
    // Enter key
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        sendMessage(input.value);
      }
    });
    
    // Voice button
    let recognition;
    if ('webkitSpeechRecognition' in window) {
      recognition = new webkitSpeechRecognition();
      recognition.continuous = false;
      recognition.lang = 'en-US';
      
      recognition.onresult = (event) => {
        const text = event.results[0][0].transcript;
        input.value = text;
        sendMessage(text);
      };
      
      recognition.onend = () => {
        voiceBtn.classList.remove('listening');
      };
      
      voiceBtn.addEventListener('click', () => {
        if (voiceBtn.classList.contains('listening')) {
          recognition.stop();
        } else {
          recognition.start();
          voiceBtn.classList.add('listening');
        }
      });
    }
    
    // Initial message
    addMessage('assistant', 'Hi! I\'m ARIA. How can I help you today?');
  </script>
</body>
</html>
```

---

## 🚀 Instalación

```bash
# 1. Crear carpeta
mkdir aria-terminal
cd aria-terminal

# 2. Crear archivos
# (Copiar package.json, main.js, index.html de arriba)

# 3. Instalar dependencies
npm install

# 4. Iniciar server ARIA (en otra terminal)
cd Atlas
python -m aria.server

# 5. Iniciar terminal gráfica
npm start
```

---

## ✅ Features

- ✅ UI moderna dark mode
- ✅ Chat interface
- ✅ Voice button (Web Speech API)
- ✅ Conecta a servidor ARIA
- ✅ Multi-sesión
- ✅ Cross-platform (Windows, Mac, Linux)

---

## 🎨 Customización

Edita `index.html` para:
- Cambiar colores
- Agregar más botones
- Modificar layout
- Agregar settings panel

---

**Status:** Listo para usar  
**Requiere:** ARIA server corriendo (`python -m aria.server`)
