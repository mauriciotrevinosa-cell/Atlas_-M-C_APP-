/**
 * ARIA Terminal - Frontend App
 * 
 * Handles chat UI, voice recognition, and ARIA communication
 */

// Configuration
const CONFIG = {
  serverUrl: '', // Relative path - uses same server as frontend
  sessionId: localStorage.getItem('aria_session_id') || `session-${Date.now()}`,
  deviceId: 'desktop-terminal'
};

// Save session ID
localStorage.setItem('aria_session_id', CONFIG.sessionId);

// DOM Elements
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const voiceBtn = document.getElementById('voice-btn');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const status = document.getElementById('status');

// State
let isConnected = false;
let isVoiceListening = false;
let recognition = null;

// ==================== INITIALIZATION ====================

async function init() {
  // Check server connection
  await checkServerConnection();

  // Setup event listeners
  setupEventListeners();

  // Initialize voice recognition
  initVoiceRecognition();

  // Welcome message
  addMessage('assistant', 'Hi! I\'m ARIA. How can I help you today?');

  // Hide status after 3 seconds if connected
  if (isConnected) {
    setTimeout(() => {
      status.style.opacity = '0';
      setTimeout(() => status.style.display = 'none', 300);
    }, 3000);
  }
}

// ==================== SERVER CONNECTION ====================

async function checkServerConnection() {
  try {
    const response = await fetch(`${CONFIG.serverUrl}/api/health`, {
      method: 'GET',
      timeout: 3000
    });

    if (response.ok) {
      setStatus('connected', 'Connected to ARIA');
      isConnected = true;
    } else {
      setStatus('disconnected', 'Server error');
    }
  } catch (error) {
    setStatus('disconnected', 'Server offline - Start ARIA server');
    console.error('Connection error:', error);
  }
}

function setStatus(state, text) {
  statusDot.className = `status-dot ${state === 'disconnected' ? 'disconnected' : ''}`;
  statusText.textContent = text;

  // Update Dashboard Card
  const dashStatus = document.getElementById('status-text-display');
  const dashCard = document.querySelector('.status-card');
  if (dashStatus && dashCard) {
    if (state === 'connected') {
      dashStatus.textContent = "All systems operational";
      dashCard.style.background = "#C5E0A5"; // Green
    } else {
      dashStatus.textContent = "System Offline - Connect Server";
      dashCard.style.background = "#E85656"; // Red
    }
  }
}

// ==================== EVENT LISTENERS ====================

function setupEventListeners() {
  // Enter key to send
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input.value);
    }
  });

  // Voice button
  voiceBtn.addEventListener('click', toggleVoice);

  // Window controls (if Electron API available)
  // Window controls (Electron-agnostic)
  if (typeof window.electron !== 'undefined') {
    window.minimize = () => window.electron.minimize();
    window.maximize = () => window.electron.maximize();
    window.close = () => window.electron.close();
  } else {
    // Browser Mode - hiding controls handled by CSS usually, but here we just log
    console.log('Running in Browser Mode');
    // Hide title bar controls if not in Electron
    const controls = document.querySelector('.title-bar-controls');
    if (controls) controls.style.display = 'none';
  }
}

// ==================== CHAT ====================

function addMessage(role, content, timestamp = null) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;

  const contentDiv = document.createElement('div');
  contentDiv.textContent = content;

  const timeDiv = document.createElement('div');
  timeDiv.className = 'message-time';
  timeDiv.textContent = timestamp || new Date().toLocaleTimeString();

  messageDiv.appendChild(contentDiv);
  messageDiv.appendChild(timeDiv);

  chat.appendChild(messageDiv);
  chat.scrollTop = chat.scrollHeight;
}

async function sendMessage(text) {
  if (!text.trim()) return;

  // Clear input
  input.value = '';

  // Add user message
  addMessage('user', text);

  // Check connection
  if (!isConnected) {
    addMessage('assistant', '❌ Not connected to ARIA server. Please start the server.');
    return;
  }

  // Show loading
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'message assistant';
  loadingDiv.innerHTML = '<div class="loading"></div> Thinking...';
  chat.appendChild(loadingDiv);
  chat.scrollTop = chat.scrollHeight;

  try {
    // Query ARIA
    const response = await fetch(`${CONFIG.serverUrl}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message: text,
        device_id: CONFIG.deviceId,
        session_id: CONFIG.sessionId
      })
    });

    // Remove loading
    chat.removeChild(loadingDiv);

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const data = await response.json();

    // Update session ID
    CONFIG.sessionId = data.session_id;
    localStorage.setItem('aria_session_id', data.session_id);

    // Add ARIA response
    addMessage('assistant', data.response, data.timestamp);

  } catch (error) {
    // Remove loading
    chat.removeChild(loadingDiv);

    // Show error
    addMessage('assistant', `❌ Error: ${error.message}\n\nMake sure ARIA server is running:\npython -m apps.server.server`);

    console.error('Send message error:', error);
  }
}

// ==================== VOICE RECOGNITION ====================

function initVoiceRecognition() {
  // Check if Web Speech API is available
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    console.warn('Speech recognition not supported');
    voiceBtn.disabled = true;
    voiceBtn.title = 'Voice not supported in this browser';
    return;
  }

  // Create recognition instance
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();

  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';

  // Event handlers
  recognition.onstart = () => {
    isVoiceListening = true;
    voiceBtn.classList.add('listening');
    setStatus('listening', '🎤 Listening...');
    status.style.display = 'flex';
    status.style.opacity = '1';
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    input.value = transcript;
    sendMessage(transcript);
  };

  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    setStatus('disconnected', `Voice error: ${event.error}`);
  };

  recognition.onend = () => {
    isVoiceListening = false;
    voiceBtn.classList.remove('listening');

    if (isConnected) {
      setTimeout(() => {
        status.style.opacity = '0';
        setTimeout(() => status.style.display = 'none', 300);
      }, 2000);
    }
  };
}

function toggleVoice() {
  if (!recognition) {
    alert('Voice recognition not available');
    return;
  }

  if (isVoiceListening) {
    recognition.stop();
  } else {
    recognition.start();
  }
}

// ==================== KEYBOARD SHORTCUTS ====================

document.addEventListener('keydown', (e) => {
  // Ctrl/Cmd + K - Focus input
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    input.focus();
  }

  // Ctrl/Cmd + Shift + V - Toggle voice
  if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'V') {
    e.preventDefault();
    toggleVoice();
  }

  // Ctrl/Cmd + L - Clear chat (optional)
  if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
    e.preventDefault();
    if (confirm('Clear chat history?')) {
      chat.innerHTML = '';
      addMessage('assistant', 'Chat cleared. How can I help you?');
    }
  }
});

// ==================== WEBSOCKET (Optional - for real-time sync) ====================

function connectWebSocket() {
  const ws = new WebSocket(`ws://${CONFIG.serverUrl.replace('http://', '')}/ws/${CONFIG.sessionId}`);

  ws.onopen = () => {
    console.log('WebSocket connected');
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'new_message' && data.role === 'assistant') {
      // New message from another device
      addMessage('assistant', data.content, data.timestamp);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
    // Reconnect after 5 seconds
    setTimeout(connectWebSocket, 5000);
  };
}

// Uncomment to enable WebSocket
// connectWebSocket();

// ==================== START APP ====================

init();

console.log('ARIA Terminal loaded');
console.log('Session ID:', CONFIG.sessionId);
console.log('Server URL:', CONFIG.serverUrl);
