/**
 * Market Brain — Unified ARIA Orchestrator
 *
 * Pulls signals from every analyzer module Atlas ships
 * (Trader composite · MMO quantum · Strategy consensus · Chaos · Volatility ·
 *  Signal composer · Fundamental/DCF · Analytics · Price prediction)
 * and asks ARIA to synthesize a single tradable plan.
 *
 * Two modes:
 *   · Single ticker — deep-dive on one symbol
 *   · Full portfolio — fan out across uploaded positions, aggregate to portfolio stance
 *
 * @module MarketBrain
 */
(function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════════════
     STATE
     ═══════════════════════════════════════════════════════════════ */
  let _mount = null;
  let _mode = 'ticker';           // 'ticker' | 'portfolio'
  let _currentTicker = 'SPY';
  let _latest = null;             // last full response (ticker or portfolio)
  let _busy = false;
  let _initialized = false;

  const MODULE_META = {
    quote:        { label: 'Live Quote',        icon: '●', color: '#9be7ff' },
    trader:       { label: 'Trader Composite',  icon: '⚡', color: '#ffd93d' },
    predict:      { label: 'Price Prediction',  icon: '⌖', color: '#ff9e66' },
    mmo:          { label: 'MMO Quantum',       icon: 'ψ', color: '#c084fc' },
    strategy:     { label: 'Strategy Consensus',icon: '⚙', color: '#50fa7b' },
    market_state: { label: 'Market Regime',     icon: '◈', color: '#4da6ff' },
    chaos:        { label: 'Chaos / Lyapunov',  icon: '≈', color: '#ff6b9d' },
    volatility:   { label: 'Volatility',        icon: '⇌', color: '#f97316' },
    signal:       { label: 'Signal Composer',   icon: '◉', color: '#a7f3d0' },
    analytics:    { label: 'Analytics',         icon: '∑', color: '#e0e0ff' },
    fundamental:  { label: 'Fundamental',       icon: '❈', color: '#ffb86c' },
    dcf:          { label: 'DCF Valuation',     icon: '$', color: '#7dd3fc' },
  };

  const VERDICT_STYLE = {
    BUY:  { color: '#00e5a0', bg: 'rgba(0,229,160,0.13)', border: 'rgba(0,229,160,0.40)' },
    SELL: { color: '#ff6b6b', bg: 'rgba(255,107,107,0.13)', border: 'rgba(255,107,107,0.40)' },
    HOLD: { color: '#9be7ff', bg: 'rgba(155,231,255,0.10)', border: 'rgba(155,231,255,0.35)' },
    WATCH:{ color: '#ffd93d', bg: 'rgba(255,217,61,0.12)', border: 'rgba(255,217,61,0.40)' },
  };

  /* ═══════════════════════════════════════════════════════════════
     HELPERS
     ═══════════════════════════════════════════════════════════════ */
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#039;');

  function _fmtNum(v, digits = 2) {
    if (v == null || v === '') return '—';
    const n = typeof v === 'number' ? v : parseFloat(v);
    if (!isFinite(n)) return '—';
    if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B';
    if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M';
    if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(2) + 'K';
    return n.toFixed(digits);
  }
  function _fmtPct(v) {
    if (v == null || v === '') return '—';
    const n = typeof v === 'number' ? v : parseFloat(v);
    if (!isFinite(n)) return '—';
    return (n >= 0 ? '+' : '') + n.toFixed(2) + '%';
  }
  function _fmtUSD(v) {
    if (v == null || v === '') return '—';
    const n = typeof v === 'number' ? v : parseFloat(v);
    if (!isFinite(n)) return '—';
    return '$' + n.toFixed(2);
  }
  function _markdown(src) {
    // Minimal md → html: headers (###), bold (**), bullets (- ), linebreaks
    if (!src) return '';
    let s = esc(src);
    s = s.replace(/^### (.+)$/gm, '<h4 class="brain-md-h">$1</h4>');
    s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    // bullets
    s = s.replace(/(^|\n)- (.+)/g, '$1<li>$2</li>');
    s = s.replace(/(<li>[\s\S]+?<\/li>(\n<li>[\s\S]+?<\/li>)*)/g, '<ul>$1</ul>');
    s = s.replace(/\n{2,}/g, '</p><p>');
    return '<p>' + s + '</p>';
  }
  function _verdictChip(v) {
    const key = String(v || 'HOLD').toUpperCase();
    const base = VERDICT_STYLE[key] || VERDICT_STYLE.HOLD;
    return `<span class="brain-chip" style="color:${base.color};background:${base.bg};border:1px solid ${base.border};">${esc(key)}</span>`;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER — SHELL
     ═══════════════════════════════════════════════════════════════ */
  function _renderShell() {
    if (!_mount) return;
    _mount.innerHTML = `
      <div class="brain-container">
        <div class="brain-header">
          <div class="brain-title-block">
            <div class="brain-title">
              <span class="brain-glyph">⌬</span>
              <span>Market Brain</span>
              <span class="brain-subtitle">Unified ARIA synthesis · every analyzer in one decision</span>
            </div>
          </div>
          <button class="btn link-btn" type="button" onclick="switchView('dashboard')">Home</button>
        </div>

        <div class="brain-controls">
          <div class="brain-mode-toggle">
            <button class="brain-mode-btn ${_mode === 'ticker' ? 'active' : ''}" id="brain-mode-ticker"
              onclick="MarketBrain.setMode('ticker')">Single Ticker</button>
            <button class="brain-mode-btn ${_mode === 'portfolio' ? 'active' : ''}" id="brain-mode-portfolio"
              onclick="MarketBrain.setMode('portfolio')">Full Portfolio</button>
          </div>

          <div class="brain-ticker-row" id="brain-ticker-row" style="${_mode === 'ticker' ? '' : 'display:none;'}">
            <input type="text" id="brain-ticker-input" class="brain-input" placeholder="TICKER"
              value="${esc(_currentTicker)}" maxlength="12"
              onkeydown="if(event.key==='Enter')MarketBrain.analyze()">
            <button class="brain-btn-primary" id="brain-analyze-btn" onclick="MarketBrain.analyze()">
              Synthesize
            </button>
          </div>

          <div class="brain-portfolio-row" id="brain-portfolio-row" style="${_mode === 'portfolio' ? '' : 'display:none;'}">
            <div class="brain-portfolio-hint">Runs brain on each uploaded position, aggregates to portfolio stance.</div>
            <button class="brain-btn-primary" id="brain-portfolio-btn" onclick="MarketBrain.analyzePortfolio()">
              Analyze Portfolio
            </button>
          </div>
        </div>

        <div id="brain-banner"></div>
        <div id="brain-result" class="brain-result"></div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER — SINGLE TICKER RESULT
     ═══════════════════════════════════════════════════════════════ */
  function _renderTickerResult(res) {
    const host = $('brain-result');
    if (!host) return;

    const summary  = res.summary  || {};
    const mech     = res.mechanical || {};
    const modules  = res.modules  || {};
    const aria     = res.aria     || {};
    const quality  = res.quality  || {};
    const last     = summary.last_price;
    const chgPct   = summary.change_pct;
    const setup    = summary.setup || {};
    const scores   = summary.scores || {};
    const regime   = summary.regime || '—';

    // Module status dots
    const moduleDots = Object.keys(MODULE_META).map((k) => {
      const m = modules[k] || { ok: false };
      const meta = MODULE_META[k];
      const ok = m.ok;
      const dotCol = ok ? meta.color : '#555';
      const title = ok ? `${meta.label} · OK` : `${meta.label} · ${esc(m.error || 'missing')}`;
      return `<div class="brain-mod-dot" title="${title}">
                <span class="brain-mod-dot-circle" style="color:${dotCol}">${meta.icon}</span>
                <span class="brain-mod-dot-label">${esc(meta.label)}</span>
              </div>`;
    }).join('');

    // Scoreboard (key numbers)
    const scoreboard = [
      { label: 'Last',          value: _fmtUSD(last) },
      { label: 'Change',        value: _fmtPct(chgPct) },
      { label: 'Composite',     value: _fmtNum(scores.composite_score, 1) },
      { label: 'MMO entropy',   value: _fmtNum(scores.mmo_entropy, 2) },
      { label: 'Strategy conf.',value: scores.strategy_confidence != null ? (scores.strategy_confidence * 100).toFixed(0) + '%' : '—' },
      { label: 'Engine agree.', value: scores.engine_agreement != null ? scores.engine_agreement + '/5' : '—' },
      { label: 'Realized vol',  value: scores.realized_vol != null ? _fmtPct(scores.realized_vol * 100) : '—' },
      { label: 'Regime',        value: esc(regime) },
    ].map((x) => `<div class="brain-score">
      <div class="brain-score-label">${esc(x.label)}</div>
      <div class="brain-score-value">${x.value}</div>
    </div>`).join('');

    // Per-module verdicts
    const verdictRows = Object.entries(summary.verdicts || {}).map(([k, v]) => `
      <div class="brain-verdict-row">
        <span class="brain-verdict-source">${esc(k)}</span>
        ${_verdictChip(v)}
      </div>
    `).join('') || '<div class="brain-empty">No module verdicts yet.</div>';

    // Setup block
    const setupBlock = `
      <div class="brain-setup">
        <div class="brain-setup-item"><div class="brain-setup-label">Entry</div><div class="brain-setup-value">${_fmtUSD(setup.entry)}</div></div>
        <div class="brain-setup-item"><div class="brain-setup-label">Stop</div><div class="brain-setup-value brain-stop">${_fmtUSD(setup.stop)}</div></div>
        <div class="brain-setup-item"><div class="brain-setup-label">Target</div><div class="brain-setup-value brain-target">${_fmtUSD(setup.target)}</div></div>
        <div class="brain-setup-item"><div class="brain-setup-label">R:R</div><div class="brain-setup-value">${setup.rr != null ? _fmtNum(setup.rr, 2) + ':1' : '—'}</div></div>
      </div>
    `;

    // Risk bullets
    const risks = summary.risks || {};
    const riskList = Object.keys(risks).length
      ? Object.entries(risks).map(([k, v]) => `<li><strong>${esc(k)}</strong>${v === true ? '' : ' · ' + esc(JSON.stringify(v))}</li>`).join('')
      : '<li style="color:var(--text-secondary)">No risk flags raised.</li>';

    host.innerHTML = `
      <div class="brain-hero">
        <div class="brain-hero-left">
          <div class="brain-hero-ticker">${esc(res.ticker)}</div>
          <div class="brain-hero-verdict">
            ${_verdictChip(mech.verdict)}
            <span class="brain-hero-conv">Mechanical conviction: <strong>${mech.conviction ?? '—'}%</strong></span>
            <span class="brain-hero-tally">
              ↑ ${mech.tally?.BUY || 0} &nbsp; ↓ ${mech.tally?.SELL || 0} &nbsp; = ${mech.tally?.HOLD || 0}
            </span>
          </div>
          <div class="brain-hero-meta">
            Generated ${esc((res.generated_at || '').split('T')[1]?.split('.')[0] || '')} ·
            ${res.elapsed_ms || 0} ms ·
            ARIA: <strong>${esc(aria.model || 'offline')}</strong> (${esc(aria.provider || 'none')})
            ${quality.modules_total ? ` · <span class="brain-quality-badge">${quality.modules_ok}/${quality.modules_total} analyzers · ${quality.verdicts_collected} verdicts</span>` : ''}
          </div>
        </div>
        <div class="brain-mod-dots">${moduleDots}</div>
      </div>

      <div class="brain-aria-card">
        <div class="brain-aria-header">
          <span class="brain-aria-glyph">✦</span>
          <span>ARIA Synthesis</span>
          <span class="brain-aria-provider">${esc(aria.provider || 'offline')} · ${aria.latency_ms || 0}ms</span>
        </div>
        <div class="brain-aria-body">${_markdown(aria.plan || '_No synthesis available._')}</div>
        ${aria.error ? `<div class="brain-aria-error">⚠ ${esc(aria.error)}</div>` : ''}
      </div>

      <div class="brain-grid">
        <div class="brain-panel">
          <div class="brain-panel-title">Signal Scoreboard</div>
          <div class="brain-scoreboard">${scoreboard}</div>
        </div>

        <div class="brain-panel">
          <div class="brain-panel-title">Module Verdicts</div>
          <div class="brain-verdicts">${verdictRows}</div>
        </div>

        <div class="brain-panel">
          <div class="brain-panel-title">Trade Setup</div>
          ${setupBlock}
        </div>

        <div class="brain-panel">
          <div class="brain-panel-title">Risk Flags</div>
          <ul class="brain-risks">${riskList}</ul>
        </div>
      </div>

      <div class="brain-panel brain-panel-wide">
        <div class="brain-panel-title">Raw Module Output <span class="brain-hint">— click to inspect</span></div>
        <div class="brain-modules-detail" id="brain-modules-detail">
          ${_renderModulesDetail(modules)}
        </div>
      </div>
    `;
  }

  function _renderModulesDetail(modules) {
    return Object.entries(MODULE_META).map(([k, meta]) => {
      const m = modules[k] || {};
      const ok = m.ok;
      const body = ok
        ? `<pre class="brain-module-pre">${esc(JSON.stringify(m.data, null, 2)).slice(0, 4000)}</pre>`
        : `<div class="brain-module-err">${esc(m.error || 'unavailable')}</div>`;
      return `
        <details class="brain-module-det">
          <summary>
            <span style="color:${meta.color}">${meta.icon}</span>
            <strong>${esc(meta.label)}</strong>
            <span class="brain-module-status ${ok ? 'ok' : 'bad'}">${ok ? 'OK' : 'FAIL'}</span>
          </summary>
          ${body}
        </details>
      `;
    }).join('');
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER — PORTFOLIO RESULT
     ═══════════════════════════════════════════════════════════════ */
  function _renderPortfolioResult(res) {
    const host = $('brain-result');
    if (!host) return;

    if (!res.has_portfolio) {
      host.innerHTML = `
        <div class="brain-empty-state">
          <h3>No portfolio uploaded</h3>
          <p>${esc(res.message || 'Upload a portfolio first (Finance tab).')}</p>
          <button class="brain-btn-primary" onclick="switchView('finance')">Go to Finance</button>
        </div>
      `;
      return;
    }

    const agg = res.aggregate || {};
    const aria = res.aria || {};
    const byCount  = agg.by_verdict || {};
    const byWeight = agg.weight_by_verdict || {};
    const concentration = agg.concentration_flags || [];

    // Positions table
    const posRows = (res.positions || []).map((p) => `
      <tr>
        <td class="brain-td-sym">${esc(p.symbol)}</td>
        <td>${_fmtNum(p.qty, 2)}</td>
        <td>${_fmtUSD(p.current_price)}</td>
        <td>${_fmtUSD(p.market_value)}</td>
        <td>${_fmtNum(p.weight_pct, 2)}%</td>
        <td class="${(p.pnl_pct || 0) >= 0 ? 'brain-pos' : 'brain-neg'}">${_fmtPct(p.pnl_pct)}</td>
        <td>${_verdictChip(p.verdict)}</td>
        <td>${p.conviction ?? '—'}%</td>
      </tr>
    `).join('');

    // Allocation bar (by verdict weight)
    const barB = Math.max(0, byWeight.BUY  || 0);
    const barH = Math.max(0, byWeight.HOLD || 0);
    const barS = Math.max(0, byWeight.SELL || 0);
    const barTotal = barB + barH + barS || 100;
    const pctB = (barB / barTotal * 100).toFixed(1);
    const pctH = (barH / barTotal * 100).toFixed(1);
    const pctS = (barS / barTotal * 100).toFixed(1);

    // Risk bullets
    const risks = agg.aggregate_risks || [];
    const riskList = risks.length
      ? risks.map((r) => `<li>${esc(r)}</li>`).join('')
      : '<li style="color:var(--text-secondary)">No aggregate risks raised.</li>';

    // Concentration flags
    const concList = concentration.length
      ? concentration.map((c) => `<li><strong>${esc(c.symbol)}</strong> · ${_fmtNum(c.weight_pct, 2)}%</li>`).join('')
      : '<li style="color:var(--text-secondary)">No single-name > 15%.</li>';

    host.innerHTML = `
      <div class="brain-hero">
        <div class="brain-hero-left">
          <div class="brain-hero-ticker">PORTFOLIO</div>
          <div class="brain-hero-meta">
            ${res.positions_analyzed || 0} positions ·
            Total equity ${_fmtUSD(res.total_equity)} ·
            ${res.elapsed_ms || 0} ms ·
            ARIA: <strong>${esc(aria.model || 'offline')}</strong>
          </div>
        </div>
      </div>

      <div class="brain-aria-card">
        <div class="brain-aria-header">
          <span class="brain-aria-glyph">✦</span>
          <span>ARIA Portfolio Plan</span>
          <span class="brain-aria-provider">${esc(aria.provider || 'offline')} · ${aria.latency_ms || 0}ms</span>
        </div>
        <div class="brain-aria-body">${_markdown(aria.plan || '_No synthesis._')}</div>
        ${aria.error ? `<div class="brain-aria-error">⚠ ${esc(aria.error)}</div>` : ''}
      </div>

      <div class="brain-grid">
        <div class="brain-panel">
          <div class="brain-panel-title">Verdict Distribution (by capital)</div>
          <div class="brain-bar">
            <div class="brain-bar-seg brain-bar-buy"  style="width:${pctB}%" title="BUY ${pctB}%">${pctB > 7 ? pctB + '%' : ''}</div>
            <div class="brain-bar-seg brain-bar-hold" style="width:${pctH}%" title="HOLD ${pctH}%">${pctH > 7 ? pctH + '%' : ''}</div>
            <div class="brain-bar-seg brain-bar-sell" style="width:${pctS}%" title="SELL ${pctS}%">${pctS > 7 ? pctS + '%' : ''}</div>
          </div>
          <div class="brain-bar-legend">
            <span><span class="brain-dot brain-dot-buy"></span> BUY ${byCount.BUY || 0} pos · ${_fmtNum(byWeight.BUY, 1)}%</span>
            <span><span class="brain-dot brain-dot-hold"></span> HOLD ${byCount.HOLD || 0} pos · ${_fmtNum(byWeight.HOLD, 1)}%</span>
            <span><span class="brain-dot brain-dot-sell"></span> SELL ${byCount.SELL || 0} pos · ${_fmtNum(byWeight.SELL, 1)}%</span>
          </div>
        </div>

        <div class="brain-panel">
          <div class="brain-panel-title">Concentration Flags (> 15%)</div>
          <ul class="brain-risks">${concList}</ul>
        </div>

        <div class="brain-panel brain-panel-wide">
          <div class="brain-panel-title">Aggregate Risk Flags</div>
          <ul class="brain-risks">${riskList}</ul>
        </div>
      </div>

      <div class="brain-panel brain-panel-wide">
        <div class="brain-panel-title">Positions</div>
        <div class="brain-table-wrap">
          <table class="brain-table">
            <thead><tr>
              <th>Symbol</th><th>Qty</th><th>Price</th><th>MV</th>
              <th>Weight</th><th>P&amp;L</th><th>Verdict</th><th>Conv.</th>
            </tr></thead>
            <tbody>${posRows}</tbody>
          </table>
        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════
     BANNER
     ═══════════════════════════════════════════════════════════════ */
  function _banner(msg, level) {
    const host = $('brain-banner');
    if (!host) return;
    if (!msg) { host.innerHTML = ''; return; }
    const palette = {
      info:  { bg: 'rgba(77,166,255,0.12)', border: 'rgba(77,166,255,0.45)', color: '#9be7ff' },
      warn:  { bg: 'rgba(255,217,61,0.12)', border: 'rgba(255,217,61,0.45)', color: '#ffd93d' },
      error: { bg: 'rgba(255,107,107,0.14)', border: 'rgba(255,107,107,0.50)', color: '#ff6b6b' },
      busy:  { bg: 'rgba(155,231,255,0.10)', border: 'rgba(155,231,255,0.35)', color: '#9be7ff' },
    };
    const p = palette[level] || palette.info;
    host.innerHTML = `<div class="brain-banner" style="background:${p.bg};border:1px solid ${p.border};color:${p.color}">${esc(msg)}</div>`;
  }

  /* ═══════════════════════════════════════════════════════════════
     API CALLS
     ═══════════════════════════════════════════════════════════════ */
  async function _fetchJSON(url) {
    const r = await fetch(url);
    if (!r.ok) {
      let detail = '';
      try { const j = await r.json(); detail = j.detail || JSON.stringify(j); } catch (err) { console.warn('[Brain] parse error response failed:', err.message); }
      throw new Error(`HTTP ${r.status}${detail ? ' — ' + detail : ''}`);
    }
    return await r.json();
  }

  /* ═══════════════════════════════════════════════════════════════
     PUBLIC ACTIONS
     ═══════════════════════════════════════════════════════════════ */
  function setMode(mode) {
    if (mode !== 'ticker' && mode !== 'portfolio') return;
    _mode = mode;
    _renderShell();
    const host = $('brain-result');
    if (host) host.innerHTML = '';
    _banner('');
  }

  async function analyze(ticker) {
    if (_busy) return;
    const input = $('brain-ticker-input');
    const sym = (ticker || (input ? input.value : _currentTicker) || 'SPY').trim().toUpperCase();
    if (!/^[A-Z0-9.\-]{1,12}$/.test(sym)) {
      _banner('Invalid ticker. Use 1–12 chars, letters/digits/./-.', 'error');
      return;
    }
    _currentTicker = sym;
    if (input) input.value = sym;
    _busy = true;
    const btn = $('brain-analyze-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Synthesizing...'; }
    _banner(`Querying ${Object.keys(MODULE_META).length} analyzers + ARIA for ${sym}...`, 'busy');

    try {
      const res = await _fetchJSON(`/api/brain/synthesize/${encodeURIComponent(sym)}`);
      _latest = res;
      _renderTickerResult(res);
      const failed = Object.entries(res.modules || {}).filter(([, v]) => !v.ok).map(([k]) => k);
      const qerr = res.aria?.error || '';
      if (qerr.startsWith('insufficient_data')) {
        _banner(`Too few analyzers responded for ${sym} — ARIA synthesis skipped. See module panel.`, 'error');
      } else if (failed.length >= 5) {
        _banner(`${failed.length} analyzers unavailable — synthesis is partial. Check /api/health.`, 'warn');
      } else if (qerr) {
        _banner(`ARIA unavailable: ${qerr}. Module signals shown raw.`, 'warn');
      } else {
        _banner('');
      }
    } catch (err) {
      _banner(`Brain synthesis failed: ${err.message}`, 'error');
      const host = $('brain-result');
      if (host) host.innerHTML = `<div class="brain-empty-state"><h3>Offline</h3><p>${esc(err.message)}</p></div>`;
    } finally {
      _busy = false;
      if (btn) { btn.disabled = false; btn.textContent = 'Synthesize'; }
    }
  }

  async function analyzePortfolio() {
    if (_busy) return;
    _busy = true;
    const btn = $('brain-portfolio-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Analyzing portfolio...'; }
    _banner('Running Market Brain on every holding — this can take 30–60s...', 'busy');

    try {
      const res = await _fetchJSON('/api/brain/portfolio');
      _latest = res;
      _renderPortfolioResult(res);
      if (res.has_portfolio && res.aria?.error) {
        _banner(`ARIA unavailable: ${res.aria.error}. Aggregate data shown raw.`, 'warn');
      } else {
        _banner('');
      }
    } catch (err) {
      _banner(`Portfolio brain failed: ${err.message}`, 'error');
      const host = $('brain-result');
      if (host) host.innerHTML = `<div class="brain-empty-state"><h3>Offline</h3><p>${esc(err.message)}</p></div>`;
    } finally {
      _busy = false;
      if (btn) { btn.disabled = false; btn.textContent = 'Analyze Portfolio'; }
    }
  }

  /* ═══════════════════════════════════════════════════════════════
     INIT
     ═══════════════════════════════════════════════════════════════ */
  function init() {
    _mount = $('view-brain');
    if (!_mount) return;
    if (!_initialized) {
      _initialized = true;
    }
    _renderShell();
    // Auto-run on first open if nothing loaded yet
    if (!_latest && _mode === 'ticker') {
      setTimeout(() => analyze(_currentTicker), 80);
    }
  }

  // Expose globally
  window.MarketBrain = { init, analyze, analyzePortfolio, setMode };
})();
