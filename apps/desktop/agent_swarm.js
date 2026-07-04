/**
 * agent_swarm.js — live Atlas OS swarm connector
 * Atlas v2026.04.27
 *
 * Bridges the desktop UI to the backend agent orchestrator via:
 *   • GET  /api/agents/status   — boot probe + periodic re-poll
 *   • GET  /api/agents/audit    — recent execution events (fallback / cold load)
 *   • WS   /ws/agents/{session} — live agent_start / agent_end stream
 *
 * Drives:
 *   • #swarm-pill / #swarm-pill-value (ARIA terminal "Swarm: …" chip)
 *   • #status-text   (chat connectivity strip — flips "Disconnected" → "Connected · N agents")
 *   • #status-dot    (red → green when both server + agent system are alive)
 *   • #aria-core-state briefly flashes ACTIVE on each agent_start, then back to IDLE
 *
 * Public API (window.AtlasSwarm):
 *   .start()     — kick off (called from app boot)
 *   .stop()      — cancel poll + close WS
 *   .status()    — synchronous snapshot { available, count, connected, lastEvent }
 *   .refresh()   — force-refresh status (used by agents.js, etc.)
 */

(function () {
  'use strict';

  // ── Config ─────────────────────────────────────────────────────────────────
  const SESSION_ID         = 'atlas-os';
  const STATUS_POLL_MS     = 30_000;
  const RECONNECT_BASE_MS  = 2_000;     // exponential backoff base
  const RECONNECT_MAX_MS   = 30_000;    // cap
  const PING_INTERVAL_MS   = 25_000;    // keep-alive ping
  const FLASH_HOLD_MS      = 1_500;     // how long ARIA Core stays ACTIVE per agent

  // ── State ──────────────────────────────────────────────────────────────────
  const state = {
    started:     false,
    connected:   false,         // WebSocket open
    available:   false,         // backend agent system available
    count:       0,             // # registered agents
    agents:      [],
    lastEvent:   null,
    inFlight:    new Set(),     // task_ids currently running
    flashTimer:  null,
    pollTimer:   null,
    ws:          null,
    wsAttempt:   0,             // reconnect attempt counter
    pingTimer:   null,
  };

  // ── DOM helpers ────────────────────────────────────────────────────────────
  function _el(id)  { return document.getElementById(id); }
  function _setText(el, txt) { if (el) el.textContent = txt; }

  function _serverUrl() {
    // Prefer the app's global CONFIG (set by app.js) so we always match the rest of the UI
    if (window.CONFIG && typeof window.CONFIG.serverUrl === 'string' && window.CONFIG.serverUrl) {
      return window.CONFIG.serverUrl;
    }
    if (window.location.protocol === 'file:') return 'http://localhost:8000';
    return window.location.origin;
  }

  function _wsUrl() {
    const base = _serverUrl();
    // Convert http(s) → ws(s)
    const wsBase = base.replace(/^http/i, 'ws');
    return `${wsBase}/ws/agents/${SESSION_ID}`;
  }

  function _apiBase() {
    // For relative-origin (browser load) we can use empty prefix; otherwise full URL
    const base = _serverUrl();
    if (window.location.origin && base === window.location.origin) return '';
    return base;
  }

  // ── Pill / status block painters ──────────────────────────────────────────
  function _paintSwarmPill() {
    const pill  = _el('swarm-pill');
    const value = _el('swarm-pill-value');
    if (!pill || !value) return;

    if (!state.available) {
      _setText(value, 'Offline');
      pill.style.borderColor = 'rgba(239,83,80,0.45)';
      pill.style.color       = '#ef9a9a';
      pill.title = 'Agent runtime offline. Start `python run_atlas.py` and reload.';
      return;
    }

    if (state.inFlight.size > 0) {
      _setText(value, `${state.inFlight.size} running…`);
      pill.style.borderColor = 'rgba(120,80,255,0.6)';
      pill.style.color       = '#c8b4ff';
      pill.title = `Live agent runs in flight. Click to open AI Agents panel.`;
      return;
    }

    const dot = state.connected ? '●' : '○';
    _setText(value, `${dot} ${state.count} ready`);
    pill.style.borderColor = state.connected
      ? 'rgba(0,230,118,0.45)'
      : 'rgba(243,156,18,0.45)';
    pill.style.color = state.connected ? '#7fffaa' : '#f1c277';
    pill.title = state.connected
      ? `${state.count} agents online · WebSocket live · click to open panel`
      : `${state.count} agents online · stream reconnecting · click to open panel`;
  }

  function _paintConnectivityStrip() {
    const txt = _el('status-text');
    const dot = _el('status-dot');
    const wrap = _el('status');
    if (!txt) return;

    if (state.available && state.count > 0) {
      _setText(txt, state.connected
        ? `Connected · ${state.count} agents · live`
        : `Connected · ${state.count} agents · polling`);
      if (dot) dot.style.background = state.connected ? '#2ecc71' : '#f39c12';
      // Reveal the strip briefly on first connect, then auto-hide
      if (wrap && wrap.style.display === 'none' && !wrap.dataset.revealed) {
        wrap.dataset.revealed = '1';
        wrap.style.display = '';
        wrap.style.opacity = '1';
        setTimeout(() => {
          wrap.style.transition = 'opacity 0.4s';
          wrap.style.opacity = '0';
          setTimeout(() => { wrap.style.display = 'none'; }, 450);
        }, 2_500);
      }
    } else {
      _setText(txt, 'Agent system offline');
      if (dot) dot.style.background = '#e74c3c';
    }
  }

  function _flashAriaCore(state_name = 'ACTIVE') {
    if (typeof window._ariaSetCoreState !== 'function') return;
    try { window._ariaSetCoreState(state_name); } catch (err) { console.warn('[AgentSwarm] set ARIA core state failed:', err.message); }

    if (state.flashTimer) clearTimeout(state.flashTimer);
    state.flashTimer = setTimeout(() => {
      // Only revert if no other agents are running
      if (state.inFlight.size === 0) {
        try { window._ariaSetCoreState('IDLE'); } catch (err) { console.warn('[AgentSwarm] reset ARIA core state failed:', err.message); }
      }
    }, FLASH_HOLD_MS);
  }

  function _repaint() {
    _paintSwarmPill();
    _paintConnectivityStrip();
  }

  // ── Status polling (REST fallback) ────────────────────────────────────────
  async function _pollStatus() {
    try {
      const res  = await fetch(`${_apiBase()}/api/agents/status`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      state.available = !!data.available;
      state.count     = data.agents_count || 0;
      state.agents    = data.agents || [];
    } catch (err) {
      state.available = false;
      state.count     = 0;
      state.agents    = [];
    }
    _repaint();
  }

  // ── WebSocket lifecycle ───────────────────────────────────────────────────
  function _connectWS() {
    if (state.ws) {
      try { state.ws.close(); } catch (err) { console.warn('[AgentSwarm] close existing websocket failed:', err.message); }
      state.ws = null;
    }

    let ws;
    try {
      ws = new WebSocket(_wsUrl());
    } catch (err) {
      console.warn('[swarm] ws construct failed:', err.message);
      _scheduleReconnect();
      return;
    }
    state.ws = ws;

    ws.addEventListener('open', () => {
      state.connected = true;
      state.wsAttempt = 0;
      _repaint();

      // Start keep-alive
      if (state.pingTimer) clearInterval(state.pingTimer);
      state.pingTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          try { ws.send(JSON.stringify({ type: 'ping' })); } catch (err) { console.warn('[AgentSwarm] websocket ping failed:', err.message); }
        }
      }, PING_INTERVAL_MS);
    });

    ws.addEventListener('message', (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch (err) { console.warn('[AgentSwarm] websocket message parse failed:', err.message); return; }
      _onEvent(msg);
    });

    ws.addEventListener('close', () => {
      state.connected = false;
      if (state.pingTimer) { clearInterval(state.pingTimer); state.pingTimer = null; }
      _repaint();
      if (state.started) _scheduleReconnect();
    });

    ws.addEventListener('error', () => {
      // Will trigger close — backoff handled there
    });
  }

  function _scheduleReconnect() {
    state.wsAttempt += 1;
    const delay = Math.min(
      RECONNECT_BASE_MS * Math.pow(2, Math.min(state.wsAttempt, 5)),
      RECONNECT_MAX_MS,
    );
    setTimeout(() => {
      if (state.started) _connectWS();
    }, delay);
  }

  // ── Event handler ─────────────────────────────────────────────────────────
  function _onEvent(evt) {
    state.lastEvent = evt;

    if (evt.type === 'hello') {
      state.available = !!evt.available;
      state.count     = evt.agents_count || 0;
      state.agents    = evt.agents || [];
      _repaint();
      return;
    }

    if (evt.type === 'agent_start') {
      if (evt.task_id) state.inFlight.add(evt.task_id);
      _flashAriaCore('ACTIVE');
      _repaint();
      return;
    }

    if (evt.type === 'agent_end') {
      if (evt.task_id) state.inFlight.delete(evt.task_id);
      // If error, briefly flash ALERT
      if (evt.status === 'error') _flashAriaCore('ALERT');
      _repaint();

      // Notify agents.js so it can refresh its own history list
      if (typeof window.AtlasAgents?.refresh === 'function') {
        try { window.AtlasAgents.refresh(); } catch (err) { console.warn('[AgentSwarm] refresh agents panel failed:', err.message); }
      }
      return;
    }

    if (evt.type === 'pong') return;
  }

  // ── Public API ────────────────────────────────────────────────────────────
  function start() {
    if (state.started) return;
    state.started = true;

    _pollStatus();
    if (state.pollTimer) clearInterval(state.pollTimer);
    state.pollTimer = setInterval(_pollStatus, STATUS_POLL_MS);

    _connectWS();
  }

  function stop() {
    state.started = false;
    if (state.pollTimer) { clearInterval(state.pollTimer); state.pollTimer = null; }
    if (state.pingTimer) { clearInterval(state.pingTimer); state.pingTimer = null; }
    if (state.ws) {
      try { state.ws.close(); } catch (err) { console.warn('[AgentSwarm] close websocket failed:', err.message); }
      state.ws = null;
    }
  }

  window.AtlasSwarm = {
    start,
    stop,
    refresh:  _pollStatus,
    status:   () => ({
      started:   state.started,
      available: state.available,
      connected: state.connected,
      count:     state.count,
      inFlight:  state.inFlight.size,
      lastEvent: state.lastEvent,
    }),
    version: '2026.04.27-v1',
  };

  // Auto-start
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    // Defer one tick so other modules (AriaCore, switchView) finish booting
    setTimeout(start, 50);
  }

})();
