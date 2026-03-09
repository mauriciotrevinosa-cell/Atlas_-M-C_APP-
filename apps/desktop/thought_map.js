/**
 * Atlas Thought Map
 * Visual connectivity map + high-level ARIA reasoning trace.
 */

window.AtlasThoughtMap = (() => {
  'use strict';

  const POLL_MS = 30_000;
  let _initialized = false;
  let _pollHandle = null;

  function init() {
    const root = document.getElementById('view-thought');
    if (!root) return;
    if (!_initialized) {
      _build(root);
      _bind();
      _initialized = true;
    }
    refresh();
    _startPolling();
  }

  function refresh() {
    const stamp = document.getElementById('thought-generated');
    if (stamp) stamp.textContent = 'Refreshing telemetry...';

    fetch('/api/system/thought_map')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => _render(data))
      .catch((err) => _renderError(err));
  }

  function _build(root) {
    root.innerHTML = `
      <div class="section-header-row">
        <div class="section-header">Thought Map</div>
        <div style="display:flex; gap:8px;">
          <button class="btn secondary" type="button" id="thought-refresh-btn">Refresh</button>
          <button class="btn link-btn" type="button" onclick="switchView('dashboard')">Home</button>
        </div>
      </div>

      <div class="thought-shell">
        <div class="thought-grid">
          <div class="scenario-card thought-overview">
            <div class="thought-title-row">
              <h3 style="margin:0;">Atlas Visibility</h3>
              <span id="thought-status-chip" class="thought-status-chip">DEGRADED</span>
            </div>
            <div class="thought-subline">
              <span id="thought-pulse">Pulse 0/100</span>
              <span id="thought-generated">Waiting for data...</span>
            </div>
            <div class="thought-kpi-grid">
              <div class="thought-kpi">
                <span>Connectivity</span>
                <strong id="thought-connect-ratio">0/0</strong>
              </div>
              <div class="thought-kpi">
                <span>API Routes</span>
                <strong id="thought-api-count">0</strong>
              </div>
              <div class="thought-kpi">
                <span>Desktop Views</span>
                <strong id="thought-view-count">0</strong>
              </div>
              <div class="thought-kpi">
                <span>JS Modules</span>
                <strong id="thought-js-count">0</strong>
              </div>
              <div class="thought-kpi">
                <span>Active Model</span>
                <strong id="thought-model">n/a</strong>
              </div>
              <div class="thought-kpi">
                <span>Latest Run</span>
                <strong id="thought-run-latest">none</strong>
              </div>
            </div>
          </div>

          <div class="scenario-card thought-graph-card">
            <h3 style="margin:0;">System Graph</h3>
            <div class="thought-graph-wrap">
              <svg id="thought-graph-svg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet"></svg>
            </div>
          </div>
        </div>

        <div class="thought-grid thought-grid-bottom">
          <div class="scenario-card thought-connect-card">
            <h3 style="margin:0;">Connectivity Checks</h3>
            <div id="thought-connectivity-list" class="thought-connectivity-list"></div>
          </div>
          <div class="scenario-card thought-trace-card">
            <h3 style="margin:0;">Reasoning Trace (Audit)</h3>
            <div id="thought-trace-list" class="thought-trace-list"></div>
          </div>
        </div>

        <div class="scenario-card thought-registry-card">
          <div class="thought-title-row">
            <h3 style="margin:0;">Module Registry</h3>
            <span id="thought-module-summary" class="thought-module-summary">Visualized 0/0</span>
          </div>
          <div id="thought-module-list" class="thought-module-list"></div>
        </div>
      </div>
    `;
  }

  function _bind() {
    const btn = document.getElementById('thought-refresh-btn');
    if (btn) btn.addEventListener('click', refresh);
  }

  function _render(payload) {
    const cc = payload.command_center || {};
    const runtime = cc.runtime || {};
    const project = cc.project || {};
    const aria = cc.aria || {};
    const visibility = payload.visibility || {};
    const connectivity = payload.connectivity || {};

    _setText('thought-pulse', `Pulse ${payload.pulse_score || 0}/100`);
    _setText('thought-generated', _fmtDate(payload.generated_at));
    _setText(
      'thought-connect-ratio',
      `${connectivity.connected || 0}/${connectivity.total || 0}`
    );
    _setText('thought-api-count', String(runtime.api_routes || 0));
    _setText('thought-view-count', String(visibility.desktop_views || project.desktop_views || 0));
    _setText(
      'thought-js-count',
      String(visibility.desktop_js_modules || project.desktop_js_modules || 0)
    );
    _setText('thought-model', String(aria.active_model || 'n/a'));
    _setText('thought-run-latest', String(visibility.latest_run_id || 'none'));

    _applyStatusChip(String(payload.status || 'degraded'));
    _renderChecks(connectivity.checks || []);
    _renderTrace(payload.thinking_trace || []);
    _renderGraph(payload.graph || {});
    _renderRegistry(payload.module_registry || {});
  }

  function _renderError(err) {
    _applyStatusChip('critical');
    _setText('thought-generated', `Telemetry offline (${err.message || 'error'})`);
    _setText('thought-connect-ratio', '0/0');
    _setText('thought-api-count', '-');
    _setText('thought-view-count', '-');
    _setText('thought-js-count', '-');
    _setText('thought-model', '-');
    _setText('thought-run-latest', 'unavailable');
    _setHtml(
      'thought-connectivity-list',
      '<div class="thought-check thought-bad">Unable to load /api/system/thought_map</div>'
    );
    _setHtml(
      'thought-trace-list',
      '<div class="thought-trace-row thought-bad">Reasoning trace unavailable</div>'
    );
    _setText('thought-module-summary', 'Visualized 0/0');
    _setHtml(
      'thought-module-list',
      '<div class="thought-module-row thought-bad">Module registry unavailable</div>'
    );
    _setHtml('thought-graph-svg', '');
  }

  function _renderChecks(checks) {
    const body = checks
      .map((check) => {
        const ok = Boolean(check.connected);
        return `
          <div class="thought-check ${ok ? 'thought-ok' : 'thought-bad'}">
            <div>
              <div class="thought-check-label">${_esc(check.label || check.id || 'check')}</div>
              <div class="thought-check-kind">${_esc(check.kind || 'unknown')}</div>
            </div>
            <code>${_esc(check.target || '')}</code>
          </div>
        `;
      })
      .join('');

    _setHtml(
      'thought-connectivity-list',
      body || '<div class="thought-check thought-bad">No connectivity checks available</div>'
    );
  }

  function _renderTrace(trace) {
    if (!Array.isArray(trace) || trace.length === 0) {
      _setHtml(
        'thought-trace-list',
        '<div class="thought-trace-row">No audit events yet. Send a message to ARIA to build trace data.</div>'
      );
      return;
    }

    const html = trace
      .map((row) => {
        const ok = Boolean(row.success);
        return `
          <div class="thought-trace-row ${ok ? 'thought-ok' : 'thought-bad'}">
            <div class="thought-trace-head">
              <span>${_esc(_fmtTime(row.ts))}</span>
              <span>${_esc(row.stage || 'unknown')}</span>
            </div>
            <div class="thought-trace-label">${_esc(row.label || 'event')}</div>
          </div>
        `;
      })
      .join('');

    _setHtml('thought-trace-list', html);
  }

  function _renderGraph(graph) {
    const svg = document.getElementById('thought-graph-svg');
    if (!svg) return;

    const nodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    const edges = Array.isArray(graph.edges) ? graph.edges : [];
    if (nodes.length === 0) {
      svg.innerHTML = '';
      return;
    }

    const lookup = Object.fromEntries(nodes.map((n) => [n.id, n]));
    const lines = edges
      .map((edge) => {
        const from = lookup[edge.source];
        const to = lookup[edge.target];
        if (!from || !to) return '';
        return `
          <line
            x1="${_num(from.x)}"
            y1="${_num(from.y)}"
            x2="${_num(to.x)}"
            y2="${_num(to.y)}"
            stroke="${_statusColor(edge.status)}"
            stroke-width="1.7"
            stroke-opacity="0.85"
          />
        `;
      })
      .join('');

    const points = nodes
      .map((node) => {
        const color = _statusColor(node.status);
        return `
          <g transform="translate(${_num(node.x)}, ${_num(node.y)})">
            <circle r="3.7" fill="${color}" stroke="#ffffff" stroke-width="0.6"></circle>
            <text x="0" y="-5.5" text-anchor="middle" class="thought-node-label">${_esc(node.label || node.id)}</text>
            <text x="0" y="8" text-anchor="middle" class="thought-node-meta">${_esc(node.meta || '')}</text>
          </g>
        `;
      })
      .join('');

    svg.innerHTML = `${lines}${points}`;
  }

  function _renderRegistry(registry) {
    const entries = Array.isArray(registry.entries) ? registry.entries : [];
    const total = Number(registry.total || entries.length || 0);
    const visualized = Number(registry.visualized || 0);
    const pending = Number(registry.pending || Math.max(total - visualized, 0));
    _setText('thought-module-summary', `Visualized ${visualized}/${total} · Pending ${pending}`);

    if (entries.length === 0) {
      _setHtml(
        'thought-module-list',
        '<div class="thought-module-row">No module metadata available.</div>'
      );
      return;
    }

    const rows = entries
      .map((entry) => {
        const status = String(entry.status || 'pending').toLowerCase();
        const viewToken = _viewToken(entry.suggested_view);
        const openBtn = viewToken
          ? `<button class="btn link-btn thought-open-btn" type="button" onclick="switchView('${viewToken}')">Open</button>`
          : '<span class="thought-module-pill thought-pill-pending">Pending</span>';
        return `
          <div class="thought-module-row thought-module-${status}">
            <div>
              <div class="thought-module-name">${_esc(entry.module || 'module')}</div>
              <div class="thought-module-note">${_esc(entry.note || '')}</div>
            </div>
            <div class="thought-module-meta">
              <span class="thought-module-pill">${_esc(entry.suggested_view || 'no-view')}</span>
              ${openBtn}
            </div>
          </div>
        `;
      })
      .join('');

    _setHtml('thought-module-list', rows);
  }

  function _applyStatusChip(statusRaw) {
    const chip = document.getElementById('thought-status-chip');
    if (!chip) return;
    const status = String(statusRaw || 'degraded').toLowerCase();
    chip.classList.remove('thought-state-nominal', 'thought-state-degraded', 'thought-state-critical');
    if (status === 'nominal') chip.classList.add('thought-state-nominal');
    else if (status === 'critical') chip.classList.add('thought-state-critical');
    else chip.classList.add('thought-state-degraded');
    chip.textContent = status.toUpperCase();
  }

  function _startPolling() {
    if (_pollHandle) return;
    _pollHandle = setInterval(() => {
      if (_isVisible()) refresh();
    }, POLL_MS);
  }

  function _isVisible() {
    const root = document.getElementById('view-thought');
    return Boolean(root && root.classList.contains('active'));
  }

  function _fmtDate(value) {
    if (!value) return 'n/a';
    try {
      return new Date(value).toLocaleString();
    } catch (_) {
      return String(value);
    }
  }

  function _fmtTime(value) {
    if (!value) return 'n/a';
    try {
      return new Date(value).toLocaleTimeString();
    } catch (_) {
      return String(value);
    }
  }

  function _statusColor(state) {
    const key = String(state || '').toLowerCase();
    if (key === 'online' || key === 'nominal') return '#2ecc71';
    if (key === 'critical' || key === 'error') return '#e74c3c';
    return '#f39c12';
  }

  function _setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function _setHtml(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = value;
  }

  function _num(v) {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  }

  function _esc(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function _viewToken(value) {
    if (!value) return '';
    const token = String(value).trim();
    return /^[a-zA-Z0-9_-]+$/.test(token) ? token : '';
  }

  return { init, refresh };
})();
