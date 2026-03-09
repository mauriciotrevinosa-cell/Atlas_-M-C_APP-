/**
 * agents.js — AI Agent System UI
 * Atlas v2026.03.07
 *
 * Provides a frontend panel to interact with the Atlas AI Agent System:
 * PlannerAgent, ReviewerAgent, TestDesignAgent, ContextCuratorAgent,
 * CodeBuilderAgent, RepoScoutAgent, IngestionAgent, DocsAgent.
 *
 * API endpoints used:
 *   GET  /api/agents         → list agents
 *   GET  /api/agents/status  → system status
 *   POST /api/agents/run     → execute a task
 */

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────────────────────
  let _initialized = false;
  let _agentsList  = [];
  let _running     = false;
  let _history     = [];   // local run history (last 20)

  // Agent display names + icons
  const AGENT_META = {
    planner_agent:         { label: 'Planner',          icon: '🗺️',  color: '#4da6ff', hint: 'Converts a goal into a step-by-step execution plan' },
    reviewer_agent:        { label: 'Reviewer',         icon: '🔍',  color: '#f39c12', hint: 'Reviews code or diffs and returns a structured verdict' },
    test_agent:            { label: 'Test Designer',    icon: '🧪',  color: '#00e676', hint: 'Designs pytest test suites: nominal, edge, error cases' },
    context_curator_agent: { label: 'Context Curator',  icon: '✂️',  color: '#26c6da', hint: 'Filters and compacts context for LLM consumption' },
    code_builder_agent:    { label: 'Code Builder',     icon: '⚒️',  color: '#ab47bc', hint: 'Proposes clean code implementations (draft only)' },
    repo_scout_agent:      { label: 'Repo Scout',       icon: '🔭',  color: '#ef5350', hint: 'Researches GitHub patterns and solutions' },
    ingestion_agent:       { label: 'Ingestion',        icon: '📥',  color: '#66bb6a', hint: 'Converts docs/URLs into structured knowledge packs' },
    docs_agent:            { label: 'Docs',             icon: '📝',  color: '#7850ff', hint: 'Generates ADRs, changelogs, module specs, READMEs' },
  };

  const DOC_TYPES = ['module_spec', 'adr', 'changelog', 'readme', 'api_doc'];

  // ── Mount ─────────────────────────────────────────────────────────────────
  function initAgents() {
    const root = document.getElementById('view-agents');
    if (!root) return false;
    if (_initialized) return true;

    try {
      root.innerHTML = _buildShell();
      _attachEvents();
      _loadStatus();
      _initialized = true;
      root.dataset.agentsReady = '1';
      return true;
    } catch (err) {
      _initialized = false;
      root.innerHTML = `
        <div class="scenario-card" style="margin-top:18px;">
          <h3 style="margin:0 0 8px;">AI Agents failed to load</h3>
          <div style="font-size:12px;color:#888;line-height:1.5;">
            Open DevTools Console and check errors from <code>agents.js</code>.
          </div>
        </div>
      `;
      console.error('AtlasAgents init failed:', err);
      return false;
    }
  }

  // ── HTML Shell ────────────────────────────────────────────────────────────
  function _buildShell() {
    const agentOptions = Object.entries(AGENT_META)
      .map(([id, m]) => `<option value="${id}">${m.icon} ${m.label}</option>`)
      .join('');

    const docTypeOptions = DOC_TYPES
      .map(t => `<option value="${t}">${t}</option>`)
      .join('');

    return `
<div class="agents-root" style="
  padding:20px 24px 40px;
  max-width:980px;
  margin:0 auto;
  font-family:'SF Mono',monospace;
  color:#e0e0e0;
">

  <!-- Header -->
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:24px;">
    <button class="btn link-btn" onclick="switchView('dashboard')" style="font-size:12px;padding:4px 10px;">← Home</button>
    <div>
      <h2 style="margin:0;font-size:22px;color:#fff;letter-spacing:0.5px;">🤖 AI Agent System</h2>
      <p style="margin:4px 0 0;font-size:12px;color:#666;">
        n8n-style agent orchestration · stub mode (no LLM required)
      </p>
    </div>
    <div id="agents-status-badge" style="margin-left:auto;padding:4px 12px;border-radius:20px;
      font-size:11px;background:#111;border:1px solid #333;color:#888;">
      checking...
    </div>
  </div>

  <!-- Agent Selector Cards -->
  <div style="margin-bottom:20px;">
    <div style="font-size:11px;color:#555;letter-spacing:1px;margin-bottom:10px;">SELECT AGENT</div>
    <div id="agent-card-grid" style="
      display:grid;
      grid-template-columns:repeat(auto-fill,minmax(180px,1fr));
      gap:10px;
    ">
      ${Object.entries(AGENT_META).map(([id, m]) => `
        <div class="agent-card" data-agent="${id}" onclick="window._agentsSelectAgent('${id}')" style="
          background:#0a0a0f;
          border:1px solid #222;
          border-radius:10px;
          padding:12px 14px;
          cursor:pointer;
          transition:border-color 0.15s,background 0.15s;
        ">
          <div style="font-size:20px;margin-bottom:6px;">${m.icon}</div>
          <div style="font-size:13px;font-weight:600;color:#ddd;">${m.label}</div>
          <div style="font-size:10px;color:#555;margin-top:3px;line-height:1.4;">${m.hint}</div>
        </div>
      `).join('')}
    </div>
  </div>

  <!-- Task Form -->
  <div style="background:#090912;border:1px solid #1e1e2e;border-radius:12px;padding:20px;margin-bottom:20px;">
    <div style="font-size:11px;color:#555;letter-spacing:1px;margin-bottom:14px;">TASK CONFIGURATION</div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;">

      <div>
        <label style="font-size:11px;color:#666;">Agent</label>
        <select id="agents-agent-sel" style="
          width:100%;margin-top:4px;background:#0f0f1a;
          border:1px solid #333;border-radius:6px;
          color:#e0e0e0;padding:8px 10px;font-size:13px;
        ">${agentOptions}</select>
      </div>

      <div>
        <label style="font-size:11px;color:#666;">Risk Level</label>
        <select id="agents-risk-sel" style="
          width:100%;margin-top:4px;background:#0f0f1a;
          border:1px solid #333;border-radius:6px;
          color:#e0e0e0;padding:8px 10px;font-size:13px;
        ">
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
          <option value="critical">critical</option>
        </select>
      </div>
    </div>

    <div style="margin-bottom:14px;">
      <label style="font-size:11px;color:#666;">Objective <span style="color:#444;">(required)</span></label>
      <input id="agents-objective" type="text"
        placeholder="e.g. Implement RBAC system for Atlas modules"
        style="
          width:100%;margin-top:4px;background:#0f0f1a;
          border:1px solid #333;border-radius:6px;
          color:#e0e0e0;padding:8px 10px;font-size:13px;
          box-sizing:border-box;
        "
      />
    </div>

    <!-- Doc type (only visible for docs_agent) -->
    <div id="agents-doctype-row" style="margin-bottom:14px;display:none;">
      <label style="font-size:11px;color:#666;">Document Type</label>
      <select id="agents-doctype-sel" style="
        width:100%;margin-top:4px;background:#0f0f1a;
        border:1px solid #333;border-radius:6px;
        color:#e0e0e0;padding:8px 10px;font-size:13px;
      ">${docTypeOptions}</select>
    </div>

    <!-- Code input (only visible for relevant agents) -->
    <div id="agents-code-row" style="margin-bottom:14px;display:none;">
      <label style="font-size:11px;color:#666;">Code / Content <span style="color:#444;">(optional)</span></label>
      <textarea id="agents-code-input" rows="5"
        placeholder="Paste code, diff, or document content here..."
        style="
          width:100%;margin-top:4px;background:#0f0f1a;
          border:1px solid #333;border-radius:6px;
          color:#ccc;padding:8px 10px;font-size:12px;
          box-sizing:border-box;resize:vertical;
          font-family:'SF Mono',monospace;
        "
      ></textarea>
    </div>

    <div style="margin-bottom:14px;">
      <label style="font-size:11px;color:#666;">Module / Context <span style="color:#444;">(optional)</span></label>
      <input id="agents-module" type="text"
        placeholder="e.g. auth, api_gateway, payments"
        style="
          width:100%;margin-top:4px;background:#0f0f1a;
          border:1px solid #333;border-radius:6px;
          color:#e0e0e0;padding:8px 10px;font-size:13px;
          box-sizing:border-box;
        "
      />
    </div>

    <button id="agents-run-btn" onclick="window._agentsRun()" style="
      background:linear-gradient(135deg,#1a0f3a,#0f0820);
      border:1px solid rgba(120,80,255,0.5);
      color:#c8b4ff;
      padding:10px 24px;
      border-radius:8px;
      font-size:13px;
      cursor:pointer;
      transition:all 0.15s;
      font-family:'SF Mono',monospace;
    ">▶ Run Agent</button>

    <span id="agents-spinner" style="display:none;margin-left:12px;font-size:12px;color:#555;">
      ⏳ running...
    </span>
  </div>

  <!-- Result Panel -->
  <div id="agents-result-panel" style="display:none;
    background:#060612;border:1px solid #1e1e2e;border-radius:12px;padding:20px;margin-bottom:20px;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;">
      <div style="font-size:11px;color:#555;letter-spacing:1px;">RESULT</div>
      <div id="agents-result-status" style="padding:2px 10px;border-radius:12px;font-size:11px;"></div>
      <div id="agents-result-agent" style="color:#555;font-size:11px;"></div>
      <div id="agents-result-ms" style="margin-left:auto;color:#444;font-size:11px;"></div>
    </div>

    <div id="agents-result-summary" style="
      font-size:13px;color:#aaa;margin-bottom:14px;
      padding:10px 14px;background:#0a0a14;border-radius:6px;border-left:3px solid #7850ff;
    "></div>

    <div id="agents-result-body" style="
      font-size:12px;color:#ccc;white-space:pre-wrap;
      background:#050510;padding:14px;border-radius:8px;
      max-height:420px;overflow-y:auto;
      font-family:'SF Mono',monospace;line-height:1.6;
    "></div>

    <div id="agents-result-errors" style="display:none;
      margin-top:10px;padding:10px 14px;background:#1a0808;
      border:1px solid rgba(255,80,80,0.3);border-radius:6px;
      font-size:11px;color:#ff8080;
    "></div>
  </div>

  <!-- History -->
  <div id="agents-history" style="display:none;">
    <div style="font-size:11px;color:#555;letter-spacing:1px;margin-bottom:10px;">RECENT RUNS</div>
    <div id="agents-history-list" style="display:flex;flex-direction:column;gap:8px;"></div>
  </div>

</div>`;
  }

  // ── Events ────────────────────────────────────────────────────────────────
  function _attachEvents() {
    const agentSel = document.getElementById('agents-agent-sel');
    if (agentSel) agentSel.addEventListener('change', _onAgentChange);
  }

  function _onAgentChange() {
    const agent = document.getElementById('agents-agent-sel')?.value;
    _updateFormForAgent(agent);
    // Sync card highlight
    document.querySelectorAll('.agent-card').forEach(c => {
      const isActive = c.dataset.agent === agent;
      const m = AGENT_META[c.dataset.agent] || {};
      c.style.borderColor = isActive ? (m.color || '#7850ff') : '#222';
      c.style.background  = isActive ? '#0f0f1a' : '#0a0a0f';
    });
  }

  function _updateFormForAgent(agent) {
    const needsCode    = ['reviewer_agent', 'test_agent', 'code_builder_agent'].includes(agent);
    const needsDocType = agent === 'docs_agent';

    document.getElementById('agents-code-row').style.display    = needsCode ? '' : 'none';
    document.getElementById('agents-doctype-row').style.display = needsDocType ? '' : 'none';
  }

  // Public — called by card onclick
  window._agentsSelectAgent = function (agentId) {
    const sel = document.getElementById('agents-agent-sel');
    if (sel) { sel.value = agentId; _onAgentChange(); }
  };

  // ── Run ───────────────────────────────────────────────────────────────────
  window._agentsRun = async function () {
    if (_running) return;

    const agentName = document.getElementById('agents-agent-sel')?.value;
    const objective = (document.getElementById('agents-objective')?.value || '').trim();
    const riskLevel = document.getElementById('agents-risk-sel')?.value || 'low';
    const module    = (document.getElementById('agents-module')?.value || '').trim();
    const code      = (document.getElementById('agents-code-input')?.value || '').trim();
    const docType   = document.getElementById('agents-doctype-sel')?.value || 'module_spec';

    if (!objective) {
      _flash('agents-objective', '#ff5050');
      return;
    }

    _running = true;
    document.getElementById('agents-run-btn').disabled  = true;
    document.getElementById('agents-spinner').style.display = '';
    document.getElementById('agents-result-panel').style.display = 'none';

    const body = {
      agent_name: agentName,
      objective,
      risk_level: riskLevel,
      context: module ? { module } : {},
      inputs:  {},
    };

    if (agentName === 'docs_agent') body.inputs.document_type = docType;
    if (code) {
      if (agentName === 'reviewer_agent') body.inputs.code = code;
      else if (agentName === 'test_agent') body.inputs.code = code;
      else if (agentName === 'code_builder_agent') body.inputs.description = code;
      else if (agentName === 'docs_agent') body.inputs.content = code;
      else body.inputs.code = code;
    }

    const t0 = Date.now();
    try {
      const res  = await fetch('/api/agents/run', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}: ${res.statusText}`);
      const data = await res.json();
      const ms   = Date.now() - t0;
      _showResult(data, agentName, ms);
      _addHistory(agentName, objective, data.status, ms);
    } catch (err) {
      _showResult({ status: 'error', errors: [err.message], summary: 'Network error', result: {} }, agentName, Date.now() - t0);
    } finally {
      _running = false;
      document.getElementById('agents-run-btn').disabled  = false;
      document.getElementById('agents-spinner').style.display = 'none';
    }
  };

  // ── Result display ────────────────────────────────────────────────────────
  function _showResult(data, agentName, ms) {
    const panel   = document.getElementById('agents-result-panel');
    const status  = document.getElementById('agents-result-status');
    const summary = document.getElementById('agents-result-summary');
    const body    = document.getElementById('agents-result-body');
    const errors  = document.getElementById('agents-result-errors');
    const agentEl = document.getElementById('agents-result-agent');
    const msEl    = document.getElementById('agents-result-ms');

    panel.style.display = '';

    // Status badge
    const colors = { success: '#00e676', partial: '#f39c12', error: '#ef5350' };
    status.textContent   = data.status || 'unknown';
    status.style.background = (colors[data.status] || '#555') + '22';
    status.style.color      = colors[data.status] || '#aaa';
    status.style.border     = `1px solid ${colors[data.status] || '#555'}44`;

    const m = AGENT_META[agentName] || {};
    agentEl.textContent = `${m.icon || ''} ${m.label || agentName}`;
    msEl.textContent    = `${ms}ms`;

    summary.textContent = data.summary || '—';

    // Pretty-print result
    const result = data.result || {};
    let bodyText = '';

    // If docs agent — show content nicely
    if (result.content) {
      bodyText = result.content;
    } else if (result.steps && Array.isArray(result.steps)) {
      bodyText = result.steps.map((s, i) => `${i + 1}. ${s}`).join('\n');
      if (result.files_to_touch?.length) bodyText += '\n\nFiles to touch:\n' + result.files_to_touch.map(f => `  • ${f}`).join('\n');
      if (result.tests_required?.length) bodyText += '\n\nTests required:\n' + result.tests_required.map(t => `  • ${t}`).join('\n');
    } else if (result.verdict) {
      bodyText = `Verdict: ${result.verdict}\n`;
      if (result.merge_recommendation) bodyText += `Merge: ${result.merge_recommendation}\n`;
      if (result.critical_findings?.length) bodyText += '\nCritical:\n' + result.critical_findings.map(f => `  ⚠ ${f}`).join('\n');
      if (result.important_findings?.length) bodyText += '\nImportant:\n' + result.important_findings.map(f => `  • ${f}`).join('\n');
      if (result.concrete_fixes?.length) bodyText += '\nFixes:\n' + result.concrete_fixes.map(f => `  → ${f}`).join('\n');
    } else if (result.pytest_starter_code) {
      bodyText = result.pytest_starter_code;
      if (result.nominal_cases?.length) {
        bodyText = `Nominal cases (${result.nominal_cases.length}):\n` +
          result.nominal_cases.map(c => `  ✓ ${c.name} — ${c.description}`).join('\n') + '\n\n' + bodyText;
      }
    } else {
      bodyText = JSON.stringify(result, null, 2);
    }

    body.textContent = bodyText || '(empty result)';

    // Errors
    if (data.errors?.length) {
      errors.style.display = '';
      errors.textContent = '⚠ ' + data.errors.join('\n⚠ ');
    } else {
      errors.style.display = 'none';
    }

    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // ── History ───────────────────────────────────────────────────────────────
  function _addHistory(agentName, objective, status, ms) {
    const m = AGENT_META[agentName] || {};
    _history.unshift({ agentName, objective, status, ms, ts: new Date().toLocaleTimeString() });
    if (_history.length > 20) _history.pop();

    const histContainer = document.getElementById('agents-history');
    const histList      = document.getElementById('agents-history-list');
    if (!histContainer || !histList) return;

    histContainer.style.display = '';
    histList.innerHTML = _history.map(h => {
      const hm     = AGENT_META[h.agentName] || {};
      const colors = { success: '#00e676', partial: '#f39c12', error: '#ef5350' };
      return `
        <div style="display:flex;align-items:center;gap:10px;
          padding:8px 12px;background:#090912;border-radius:6px;border:1px solid #1a1a24;
          font-size:11px;color:#666;cursor:pointer;"
          onclick="window._agentsSelectAgent('${h.agentName}')">
          <span>${hm.icon || '🤖'}</span>
          <span style="color:${hm.color || '#999'};min-width:100px;">${hm.label || h.agentName}</span>
          <span style="color:#888;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${h.objective}</span>
          <span style="color:${colors[h.status] || '#555'};min-width:50px;">${h.status}</span>
          <span style="min-width:50px;text-align:right;">${h.ms}ms</span>
          <span style="color:#444;">${h.ts}</span>
        </div>
      `;
    }).join('');
  }

  // ── Status check ──────────────────────────────────────────────────────────
  async function _loadStatus() {
    const badge = document.getElementById('agents-status-badge');
    try {
      const res  = await fetch('/api/agents/status');
      if (!res.ok) throw new Error(`agents/status ${res.status}`);
      const data = await res.json();
      if (data.available) {
        badge.textContent   = `✓ ${data.agents_count} agents ready`;
        badge.style.color   = '#00e676';
        badge.style.borderColor = '#00e67633';
        _agentsList = data.agents || [];
      } else {
        badge.textContent = '⚠ stub mode';
        badge.style.color = '#f39c12';
      }
    } catch {
      badge.textContent = '● offline';
      badge.style.color = '#ef5350';
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────
  function _flash(id, color) {
    const el = document.getElementById(id);
    if (!el) return;
    const orig = el.style.borderColor;
    el.style.borderColor = color;
    setTimeout(() => { el.style.borderColor = orig; }, 800);
  }

  // ── switchView hook ───────────────────────────────────────────────────────
  function _hookSwitchView() {
    if (window.__atlasAgentsSwitchHooked) return true;
    const origSwitch = window.switchView;
    if (typeof origSwitch !== 'function') return false;

    window.__atlasAgentsSwitchHooked = true;
    window.switchView = function (view) {
      origSwitch(view);
      if (view === 'agents') initAgents();
    };
    return true;
  }

  function _boot() {
    // Expose explicit init so index.html can call it directly as fallback.
    window.AtlasAgents = {
      init: initAgents,
      refresh: _loadStatus,
      isReady: () => _initialized,
      version: '2026.03.08-v3',
    };

    if (!_hookSwitchView()) {
      let attempts = 0;
      const timer = setInterval(() => {
        attempts += 1;
        if (_hookSwitchView() || attempts >= 30) clearInterval(timer);
      }, 100);
    }

    // Eager init to ensure the Agents panel is visible even if view hooks fail.
    setTimeout(() => {
      if (!_initialized) initAgents();
    }, 40);

    if (document.getElementById('view-agents')?.classList.contains('active')) {
      initAgents();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _boot);
  } else {
    _boot();
  }

})();
