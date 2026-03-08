/**
 * ARIA Terminal - Frontend App
 * 
 * Handles chat UI, voice recognition, and ARIA communication
 */

// Configuration
// Electron loads via file:// → hardcode localhost:8000 (run_server.py)
// Browser load via run_atlas.py → origin already contains the right host:port (default 8088)
const CONFIG = {
  serverUrl: (window.location.protocol === 'file:')
    ? 'http://localhost:8000'
    : window.location.origin,
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

// ── ARIA Local Model State ─────────────────────────────────────────────────
// 100% local — all inference runs via Ollama. No external APIs, no keys needed.
let _ariaActiveModel  = localStorage.getItem('aria_model') || '';
let _ariaActiveProvider = _ariaActiveModel || 'ollama'; // kept for compat
let _ariaModels = [];    // populated from /api/aria/models
let _ariaProviders = _ariaModels; // alias

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

  // Load provider toolbar
  _loadProviders();

  // Live dashboard stats
  _refreshDashboardStats();
  setInterval(_refreshDashboardStats, 60_000);   // refresh every 60 s
  _refreshCommandCenter();
  setInterval(_refreshCommandCenter, 45_000);    // refresh every 45 s

  // Slash hint listener on input
  const inp = document.getElementById('input');
  if (inp) {
    inp.addEventListener('input', _onInputChange);
    inp.addEventListener('keydown', _onInputKeyDown);
  }

  // Hide status after 3 seconds if connected
  if (isConnected) {
    setTimeout(() => {
      status.style.opacity = '0';
      setTimeout(() => status.style.display = 'none', 300);
    }, 3000);
  }
}

// ==================== DASHBOARD LIVE STATS ====================

async function _refreshDashboardStats() {
  const v1 = document.getElementById('dash-stat-val-1');
  const v2 = document.getElementById('dash-stat-val-2');
  const v3 = document.getElementById('dash-stat-val-3');
  const l1 = document.getElementById('dash-stat-label-1');
  const l2 = document.getElementById('dash-stat-label-2');
  if (!v1 || !v2) return;

  try {
    const res  = await fetch('/api/vizlab/system_status');
    if (!res.ok) throw new Error('status fetch failed');
    const data = await res.json();

    const mods  = data.modules || {};
    const total = Object.keys(mods).length;
    const online = Object.values(mods).filter(Boolean).length;

    // Stat 1: Active BUY/SELL signals across fast ticker set
    const tickers = ['SPY', 'QQQ', 'AAPL', 'NVDA', 'MSFT'];
    let signalCount = 0;
    await Promise.all(tickers.map(async t => {
      try {
        const r = await fetch(`/api/strategy/analyze/${t}`);
        if (r.ok) {
          const d = await r.json();
          if (d.consensus && d.consensus !== 'HOLD') signalCount++;
        }
      } catch (_) { /* offline graceful */ }
    }));

    if (v1) { v1.textContent = signalCount; if (l1) l1.textContent = 'Signals'; }
    if (v2) { v2.textContent = `${online}/${total}`; if (l2) l2.textContent = 'Online'; }
    if (v3) v3.textContent = '5';

  } catch (_) {
    // Fallback: show placeholder values
    if (v1) v1.textContent = '—';
    if (v2) v2.textContent = '—';
  }
}

function _setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function _formatIsoLocal(value) {
  if (!value) return 'n/a';
  try {
    return new Date(value).toLocaleString();
  } catch (_) {
    return String(value);
  }
}

async function _refreshCommandCenter() {
  const shell = document.getElementById('command-center-shell');
  if (!shell) return;

  try {
    const res = await fetch('/api/system/command_center');
    if (!res.ok) throw new Error('command center unavailable');
    const data = await res.json();

    const runtime = data.runtime || {};
    const project = data.project || {};
    const runs = data.runs || {};
    const aria = data.aria || {};

    const docsTotal = (project.docs_markdown || 0) + (project.governance_markdown || 0);
    _setText('cc-api-routes', `${runtime.api_routes ?? '-'}`);
    _setText('cc-ui-views', `${project.desktop_views ?? '-'}`);
    _setText('cc-docs-count', `${docsTotal}`);
    _setText('cc-runs-count', `${runs.count ?? 0}`);
    _setText('cc-active-model', aria.active_model || 'n/a');
    _setText(
      'cc-core-folders',
      `${project.core_folders_present ?? 0}/${project.core_folders_total ?? 0}`
    );

    const status = String(data.status || 'degraded').toLowerCase();
    const stateClass = (
      status === 'nominal' || status === 'critical' || status === 'degraded'
    ) ? `state-${status}` : 'state-degraded';
    shell.classList.remove('state-nominal', 'state-degraded', 'state-critical');
    shell.classList.add(stateClass);
    _setText('cc-pulse-status', status.toUpperCase());

    const generatedAt = _formatIsoLocal(data.generated_at);
    _setText('cc-last-updated', `Pulse ${data.pulse_score ?? 0}/100 | Updated ${generatedAt}`);

    if (runs.latest_run_id) {
      const latestAt = _formatIsoLocal(runs.latest_updated);
      _setText('cc-footnote', `Latest run: ${runs.latest_run_id} | ${latestAt}`);
    } else {
      _setText('cc-footnote', 'Latest run: none');
    }
  } catch (error) {
    shell.classList.remove('state-nominal', 'state-degraded', 'state-critical');
    shell.classList.add('state-critical');
    _setText('cc-pulse-status', 'OFFLINE');
    _setText('cc-last-updated', 'Telemetry unavailable. Verify /api/system/command_center.');
    _setText('cc-api-routes', '-');
    _setText('cc-ui-views', '-');
    _setText('cc-docs-count', '-');
    _setText('cc-runs-count', '-');
    _setText('cc-active-model', '-');
    _setText('cc-core-folders', '-');
    _setText('cc-footnote', 'Latest run: unavailable');
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
  const dashCard   = document.querySelector('.status-card');
  if (dashStatus && dashCard) {
    if (state === 'connected') {
      dashStatus.textContent = "All systems operational";
      dashCard.style.background = "#C5E0A5";
      dashCard.style.borderColor = "";
    } else if (state === 'listening') {
      dashStatus.textContent = "Listening…";
      dashCard.style.background = "#D0E8F0";
      dashCard.style.borderColor = "";
    } else {
      dashStatus.textContent = "System Offline — Start server";
      dashCard.style.background = "#F2CECE";
      dashCard.style.borderColor = "";
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

// ==================== ARIA LOCAL MODEL TOOLBAR ====================

async function _loadProviders() {
  // Load locally installed Ollama models — no external APIs
  try {
    const res = await fetch('/api/aria/models');
    if (!res.ok) return;
    const data = await res.json();
    _ariaModels    = data.models || [];
    _ariaProviders = _ariaModels;
    _ariaActiveModel = data.active_model || _ariaActiveModel;
    _ariaActiveProvider = _ariaActiveModel;
    _renderProviderPills();
    _setAriaStatusDot(true);
  } catch (_) {
    _setAriaStatusDot(false);
    // Show placeholder pills even if Ollama offline
    _renderProviderPills();
  }
}

function _renderProviderPills() {
  const container = document.getElementById('aria-provider-pills');
  if (!container) return;
  container.innerHTML = '';

  // If no models loaded, show single "Local" pill
  const models = _ariaModels.length > 0 ? _ariaModels : [{
    id:     _ariaActiveModel || 'llama3.2:1b',
    label:  _ariaActiveModel || 'llama3.2:1b',
    active: true,
  }];

  models.forEach(m => {
    const isActive = m.id === _ariaActiveModel || m.active;
    const pill = document.createElement('button');
    // Short label: use first 2 segments of model name
    const shortId = m.id.split(':')[0].replace('deepseek-r1','ds-r1').replace('codellama','code');
    const tag     = m.id.includes(':') ? m.id.split(':')[1] : '';
    pill.textContent = tag ? `${shortId} · ${tag}` : shortId;
    pill.title       = m.label || m.id;
    if (isActive) pill.classList.add('active-pill');
    pill.onclick = () => _setProvider(m.id);
    container.appendChild(pill);
  });

  // "+" hint if only one model (suggests pulling more)
  if (models.length === 1) {
    const hint = document.createElement('span');
    hint.style.cssText = 'font-size:9px;color:var(--txt-muted);margin-left:4px;';
    hint.textContent = '— pull more with ollama pull <model>';
    container.appendChild(hint);
  }
}

async function _setProvider(modelName) {
  try {
    const res = await fetch('/api/aria/set_model', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelName }),
    });
    if (!res.ok) return;
    _ariaActiveModel    = modelName;
    _ariaActiveProvider = modelName;
    localStorage.setItem('aria_model', modelName);
    // Update active pill styling
    document.querySelectorAll('#aria-provider-pills button').forEach(b => {
      b.classList.remove('active-pill');
    });
    _renderProviderPills();
    _addSystemNote(`Model: ${modelName}`);
  } catch (e) {
    console.warn('Model switch failed', e);
  }
}

function _setAriaStatusDot(online) {
  const dot = document.getElementById('aria-status-dot');
  if (dot) {
    dot.style.background = online ? '#4ade80' : '#f87171';
    dot.title = online ? 'ARIA online' : 'ARIA offline';
  }
}

function _updateLatencyBadge(provider, latencyMs) {
  const badge = document.getElementById('aria-latency-badge');
  if (!badge) return;
  if (provider && latencyMs != null) {
    const color = latencyMs < 500 ? '#4ade80' : latencyMs < 2000 ? '#f0a500' : '#f87171';
    badge.style.color = color;
    badge.textContent = `${provider} · ${latencyMs}ms`;
    badge.style.display = 'inline';
  }
}

function _addSystemNote(text) {
  const note = document.createElement('div');
  note.style.cssText = 'font-size:10px;color:var(--txt-muted);text-align:center;padding:4px 0;letter-spacing:.04em;';
  note.textContent = `— ${text} —`;
  chat.appendChild(note);
  chat.scrollTop = chat.scrollHeight;
}

// ==================== SLASH COMMAND HINTS ====================

function _onInputChange(e) {
  const val = e.target.value;
  const hints = document.getElementById('slash-hints');
  if (!hints) return;
  hints.style.display = val.startsWith('/') ? 'block' : 'none';
}

function _onInputKeyDown(e) {
  if (e.key === 'Tab' && input.value.startsWith('/')) {
    e.preventDefault();
    // Cycle through slash commands on Tab
    const cmds = ['/providers','/model ','/audit','/debug ','/review ','/help'];
    const cur = input.value;
    const match = cmds.find(c => c.startsWith(cur) && c !== cur);
    if (match) { input.value = match; input.dispatchEvent(new Event('input')); }
  }
}

function _selectSlash(cmd) {
  input.value = cmd;
  input.focus();
  const hints = document.getElementById('slash-hints');
  if (hints) hints.style.display = 'block';
}

// ==================== CHAT ====================

/**
 * Minimal markdown renderer for ARIA responses.
 * Handles: **bold**, `code`, # headers, - lists, | tables, line breaks.
 */
function _renderMarkdown(text) {
  if (!text) return '';
  // Escape HTML first
  let h = text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  // Code blocks (``` ... ```)
  h = h.replace(/```[\w]*\n?([\s\S]*?)```/g,
    '<pre style="background:#111;padding:8px;border-radius:6px;overflow-x:auto;font-size:11px;margin:6px 0;"><code>$1</code></pre>');
  // Inline code
  h = h.replace(/`([^`]+)`/g, '<code style="background:#222;padding:1px 4px;border-radius:3px;font-size:11px;">$1</code>');
  // Bold
  h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  // Italic
  h = h.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  // ### Headers
  h = h.replace(/^###\s+(.+)$/gm, '<div style="font-size:12px;font-weight:700;color:#f0a500;margin:8px 0 2px;">$1</div>');
  h = h.replace(/^##\s+(.+)$/gm,  '<div style="font-size:13px;font-weight:700;color:#ddd;margin:8px 0 2px;">$1</div>');
  h = h.replace(/^#\s+(.+)$/gm,   '<div style="font-size:14px;font-weight:700;color:#fff;margin:8px 0 2px;">$1</div>');
  // Tables (pipe-separated) — naive but functional
  h = h.replace(/(\|.+\|\n)((?:\|[-: ]+\|\n)+)((?:\|.+\|\n?)+)/g, (m) => {
    const rows = m.trim().split('\n').filter(r => r.trim() && !r.match(/^\|[-: |]+\|$/));
    if (rows.length < 2) return m;
    const toRow = (r, tag='td') =>
      '<tr>' + r.split('|').slice(1,-1).map(c =>
        `<${tag} style="padding:4px 8px;border:1px solid #333;">${c.trim()}</${tag}>`
      ).join('') + '</tr>';
    return `<table style="border-collapse:collapse;font-size:11px;margin:6px 0;">${toRow(rows[0],'th')}${rows.slice(1).map(r=>toRow(r)).join('')}</table>`;
  });
  // Checkboxes
  h = h.replace(/- \[ \] (.+)/g, '<div style="color:#666;">☐ $1</div>');
  h = h.replace(/- \[x\] (.+)/gi, '<div style="color:#4ade80;">☑ $1</div>');
  // Unordered lists
  h = h.replace(/^[-*•] (.+)$/gm, '<div style="padding-left:14px;">• $1</div>');
  // Numbered lists
  h = h.replace(/^\d+\. (.+)$/gm, '<div style="padding-left:14px;">$&</div>');
  // Horizontal rule
  h = h.replace(/^---+$/gm, '<hr style="border:none;border-top:1px solid #333;margin:8px 0;">');
  // Line breaks
  h = h.replace(/\n/g, '<br>');

  return h;
}

function addMessage(role, content, timestamp = null, metadata = null) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role}`;

  const contentDiv = document.createElement('div');
  if (role === 'assistant') {
    contentDiv.innerHTML = _renderMarkdown(content);
  } else {
    contentDiv.textContent = content;
  }

  const timeDiv = document.createElement('div');
  timeDiv.className = 'message-time';

  // Provider + latency badge for ARIA messages
  if (role === 'assistant' && metadata && metadata.provider && metadata.provider !== 'system') {
    const prov = metadata.provider;
    const lat  = metadata.latency_ms;
    const color = lat < 500 ? '#4ade80' : lat < 2000 ? '#f0a500' : '#f87171';
    const provBadge = document.createElement('span');
    provBadge.style.cssText = `
      font-size:9px; padding:1px 5px; border-radius:8px;
      background:#1a1a1a; color:${color}; border:1px solid #333;
      margin-right:5px; font-family:monospace;
    `;
    provBadge.textContent = `${prov} · ${lat}ms`;
    timeDiv.appendChild(provBadge);
  }

  const ts = document.createElement('span');
  ts.textContent = timestamp
    ? new Date(timestamp).toLocaleTimeString()
    : new Date().toLocaleTimeString();
  timeDiv.appendChild(ts);

  messageDiv.appendChild(contentDiv);
  messageDiv.appendChild(timeDiv);

  chat.appendChild(messageDiv);
  chat.scrollTop = chat.scrollHeight;
  return messageDiv;
}

async function sendMessage(text) {
  if (!text.trim()) return;

  // Clear input + hide slash hints
  input.value = '';
  const slashHints = document.getElementById('slash-hints');
  if (slashHints) slashHints.style.display = 'none';

  // Add user message
  addMessage('user', text);

  // Check connection
  if (!isConnected) {
    addMessage('assistant', '❌ Not connected to ARIA server. Please start the server.');
    return;
  }

  // Show loading indicator
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'message assistant';
  const modelShort = (_ariaActiveModel || 'ARIA').split(':')[0];
  loadingDiv.innerHTML = `<div class="loading"></div> <span style="color:var(--txt-muted);font-size:12px;">ARIA · ${modelShort}…</span>`;
  chat.appendChild(loadingDiv);
  chat.scrollTop = chat.scrollHeight;

  try {
    const response = await fetch(`${CONFIG.serverUrl}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message:    text,
        device_id:  CONFIG.deviceId,
        session_id: CONFIG.sessionId,
      }),
    });

    chat.removeChild(loadingDiv);

    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    const data = await response.json();

    // Update session ID
    CONFIG.sessionId = data.session_id;
    localStorage.setItem('aria_session_id', data.session_id);

    // Update latency badge in toolbar
    const modelUsed = data.provider || _ariaActiveModel || 'local';
    if (modelUsed !== 'system') {
      _updateLatencyBadge(modelUsed.split(':')[0], data.latency_ms);
    }

    // Add ARIA response with metadata badge
    addMessage('assistant', data.response, data.timestamp, {
      provider:   data.provider,
      latency_ms: data.latency_ms,
    });

  } catch (error) {
    if (chat.contains(loadingDiv)) chat.removeChild(loadingDiv);
    addMessage('assistant',
      `❌ Error: ${error.message}\n\nMake sure ARIA server is running:\npython run_atlas.py`
    );
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
