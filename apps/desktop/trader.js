/**
 * ARIA Trader — Quantitative Learning Machine
 * Elite composite scoring + prediction sheets + universe screener
 *
 * Fuses: Technical (35%) + Factor (25%) + Fundamental (20%)
 *        + Momentum (10%) + Regime (10%)
 * Output: composite_score (-100..+100), verdict, prediction, insights
 */

const AriaTrader = (() => {
  'use strict';

  // ─── State ────────────────────────────────────────────────────────────────
  let _currentTicker   = 'AAPL';
  let _currentResult   = null;
  let _screenResults   = [];
  let _scoreGaugeAnim  = null;
  let _radarChart      = null;    // Chart.js radar
  let _equityChart     = null;    // backtest line

  // Default watchlist
  const DEFAULT_WATCH = ['AAPL','MSFT','NVDA','GOOGL','TSLA','AMZN','META','JPM','V','AMD'];

  // Verdict colours
  const VERDICT_STYLE = {
    'STRONG BUY':  { bg: '#1a3d2b', border: '#2ecc71', text: '#2ecc71', icon: '🚀' },
    'BUY':         { bg: '#1a2f3d', border: '#3498db', text: '#3498db', icon: '📈' },
    'HOLD':        { bg: '#2d2d1a', border: '#f39c12', text: '#f1c40f', icon: '⚖' },
    'AVOID':       { bg: '#2d1a1a', border: '#e67e22', text: '#e67e22', icon: '⚠' },
    'STRONG SELL': { bg: '#3d1a1a', border: '#e74c3c', text: '#e74c3c', icon: '🔴' },
  };

  // ─── Init ─────────────────────────────────────────────────────────────────
  function init() {
    _buildView();
    _bindEvents();
    // Load AAPL on first visit
    setTimeout(() => analyze('AAPL'), 400);
  }

  // ─── HTML builder ─────────────────────────────────────────────────────────
  function _buildView() {
    const el = document.getElementById('view-trader');
    if (!el) return;
    el.innerHTML = `
<!-- ═══════════════════════  ARIA TRADER  ═══════════════════════ -->
<div class="trader-shell">

  <!-- Header bar -->
  <div class="trader-header">
    <div class="trader-brand">
      <span class="trader-logo">⚡</span>
      <div>
        <div class="trader-title">ARIA Trader</div>
        <div class="trader-subtitle">Quantitative Learning Machine · v2.0</div>
      </div>
    </div>

    <div class="trader-search-bar">
      <input id="trader-ticker-input" type="text" value="AAPL"
             placeholder="Ticker…" autocomplete="off"
             onkeydown="if(event.key==='Enter') AriaTrader.analyze(this.value.toUpperCase())"/>
      <button class="trader-btn-primary" onclick="AriaTrader.analyze(document.getElementById('trader-ticker-input').value.toUpperCase())">
        Analyze
      </button>
      <button class="trader-btn-secondary" onclick="AriaTrader.openScreener()">
        🔭 Screen Universe
      </button>
    </div>
  </div>

  <!-- Main layout: left panel + right panel -->
  <div class="trader-body">

    <!-- LEFT: Score + Prediction + Components -->
    <div class="trader-left">

      <!-- Score gauge card -->
      <div class="trader-card" id="trader-score-card">
        <div class="trader-card-loading" id="trader-loading">
          <div class="trader-spinner"></div>
          <span>Analysing…</span>
        </div>
        <div id="trader-score-content" style="display:none;">
          <!-- Ticker + price row -->
          <div class="trader-ticker-row">
            <div class="trader-ticker-name" id="t-ticker-label">—</div>
            <div class="trader-price-chip" id="t-price-chip">$—</div>
          </div>

          <!-- Gauge + Verdict side by side -->
          <div class="trader-gauge-row">
            <div class="trader-gauge-wrap">
              <canvas id="trader-gauge-canvas" width="220" height="130"></canvas>
              <div class="trader-gauge-score" id="t-gauge-score">0</div>
              <div class="trader-gauge-label">Composite Score</div>
            </div>
            <div class="trader-verdict-wrap">
              <div class="trader-verdict-badge" id="t-verdict-badge">—</div>
              <div class="trader-confidence-bar-wrap">
                <div class="trader-conf-label">Confidence</div>
                <div class="trader-confidence-bar">
                  <div class="trader-confidence-fill" id="t-conf-fill"></div>
                </div>
                <div class="trader-conf-pct" id="t-conf-pct">0%</div>
              </div>
            </div>
          </div>

          <!-- Component bars -->
          <div class="trader-components" id="t-components"></div>
        </div>
      </div>

      <!-- Prediction card -->
      <div class="trader-card" id="trader-predict-card" style="display:none;">
        <div class="trader-card-title">📊 Trade Setup</div>
        <div class="trader-predict-grid" id="t-predict-grid"></div>
        <div class="trader-predict-bar-wrap">
          <div class="trader-predict-bar">
            <div class="trader-pbar-stop" id="t-pbar-stop"></div>
            <div class="trader-pbar-entry" id="t-pbar-entry"></div>
            <div class="trader-pbar-t1" id="t-pbar-t1"></div>
            <div class="trader-pbar-t2" id="t-pbar-t2"></div>
          </div>
          <div class="trader-pbar-labels" id="t-pbar-labels"></div>
        </div>
      </div>

      <!-- Insights card -->
      <div class="trader-card" id="trader-insights-card" style="display:none;">
        <div class="trader-card-title" style="display:flex;justify-content:space-between;align-items:center;">
          <span>💡 Key Insights</span>
          <button class="trader-btn-mini" onclick="AriaTrader.askARIA()" style="background:rgba(52,152,219,0.15); border-color:rgba(52,152,219,0.4); color:#3498db;">
            🧠 Ask ARIA
          </button>
        </div>
        <div id="t-insights-list"></div>
        <div id="t-risk-flags"></div>
      </div>

      <!-- Backtest equity curve -->
      <div class="trader-card" id="trader-backtest-card" style="display:none;">
        <div class="trader-card-title" style="display:flex;justify-content:space-between;align-items:center;">
          <span>📉 Strategy Backtest (1Y Walk-Forward)</span>
          <div id="t-bt-stats" style="display:flex;gap:14px;font-size:11px;font-family:monospace;color:#667;"></div>
        </div>
        <canvas id="trader-equity-canvas" height="110" style="width:100%;display:block;"></canvas>
      </div>

      <!-- Factor Heatmap card -->
      <div class="trader-card" id="trader-factors-card" style="display:none;">
        <div class="trader-card-title">🔭 Alpha Factor Heatmap</div>
        <div id="t-factor-heatmap"></div>
      </div>

    </div>

    <!-- RIGHT: Radar + Watchlist + Screener -->
    <div class="trader-right">

      <!-- Radar chart card -->
      <div class="trader-card">
        <div class="trader-card-title">🕸 Signal Radar</div>
        <div class="trader-radar-wrap">
          <canvas id="trader-radar" width="260" height="260"></canvas>
        </div>
      </div>

      <!-- Watchlist card -->
      <div class="trader-card">
        <div class="trader-card-title" style="display:flex; justify-content:space-between; align-items:center;">
          <span>📋 Watchlist</span>
          <button class="trader-btn-mini" onclick="AriaTrader.loadWatchlist()">↻ Refresh</button>
        </div>
        <div id="t-watchlist-grid"></div>
      </div>

      <!-- Screener results (hidden until opened) -->
      <div class="trader-card" id="trader-screener-card" style="display:none;">
        <div class="trader-card-title" style="display:flex; justify-content:space-between;">
          <span>🔭 Universe Screener</span>
          <div style="display:flex;gap:6px;">
            <input id="screener-custom-tickers" type="text" placeholder="AAPL,MSFT,TSLA…"
                   class="trader-input-sm" style="width:160px;"/>
            <button class="trader-btn-mini" onclick="AriaTrader.runScreener()">Run</button>
          </div>
        </div>
        <div id="t-screener-loading" style="display:none;" class="trader-loading-row">
          <div class="trader-spinner-sm"></div> Screening universe…
        </div>
        <div id="t-screener-results"></div>
      </div>

    </div>
  </div><!-- /.trader-body -->

</div><!-- /.trader-shell -->
    `;

    // Build watchlist cards
    _buildWatchlistCards(DEFAULT_WATCH);
  }

  function _bindEvents() {
    // Re-init if view is switched back
    document.addEventListener('click', (e) => {
      if (e.target.id === 'nav-trader') {
        if (!_currentResult) analyze(_currentTicker);
      }
    });
  }

  // ─── Analyze ──────────────────────────────────────────────────────────────
  async function analyze(ticker) {
    if (!ticker) return;
    ticker = ticker.toUpperCase().trim();
    _currentTicker = ticker;

    const input = document.getElementById('trader-ticker-input');
    if (input) input.value = ticker;

    _setLoading(true);
    _hideResult();

    try {
      const resp = await fetch(`${CONFIG.serverUrl}/api/trader/analyze/${ticker}?period=1y`);
      if (!resp.ok) throw new Error(`API ${resp.status}`);
      const data = await resp.json();
      _currentResult = data;
      _renderResult(data);

      // Fire parallel enrichment calls (non-blocking)
      _loadBacktest(ticker);
      _loadFactorHeatmap(ticker);
    } catch (err) {
      _showError(ticker, err.message);
    } finally {
      _setLoading(false);
    }
  }

  // ─── Render Result ────────────────────────────────────────────────────────
  function _renderResult(d) {
    document.getElementById('trader-score-content').style.display = 'block';
    document.getElementById('trader-predict-card').style.display = 'block';
    document.getElementById('trader-insights-card').style.display = 'block';

    // Ticker + price
    document.getElementById('t-ticker-label').textContent = d.ticker;
    document.getElementById('t-price-chip').textContent = `$${_fmt(d.last_close)}`;

    // Gauge animation
    _animateGauge(d.composite_score);

    // Verdict badge
    const vs = VERDICT_STYLE[d.verdict] || VERDICT_STYLE['HOLD'];
    const badge = document.getElementById('t-verdict-badge');
    badge.textContent = `${vs.icon} ${d.verdict}`;
    badge.style.cssText = `background:${vs.bg}; border-color:${vs.border}; color:${vs.text};`;

    // Confidence bar
    const confPct = Math.round(d.confidence * 100);
    document.getElementById('t-conf-fill').style.width = confPct + '%';
    document.getElementById('t-conf-fill').style.background = _scoreColor(d.composite_score);
    document.getElementById('t-conf-pct').textContent = confPct + '%';

    // Component bars
    _renderComponents(d.components);

    // Prediction
    if (d.prediction) _renderPrediction(d.prediction, d.composite_score);

    // Insights + Risks
    _renderInsights(d.insights, d.risk_flags);

    // Radar
    _renderRadar(d.components);
  }

  // ─── Gauge ────────────────────────────────────────────────────────────────
  function _animateGauge(targetScore) {
    const canvas = document.getElementById('trader-gauge-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let current = 0;
    cancelAnimationFrame(_scoreGaugeAnim);

    const label = document.getElementById('t-gauge-score');

    function draw(score) {
      const W = 220, H = 130;
      ctx.clearRect(0, 0, W, H);

      const cx = W / 2, cy = H - 10;
      const r = 90;

      // Background arc (grey)
      ctx.beginPath();
      ctx.arc(cx, cy, r, Math.PI, 0, false);
      ctx.lineWidth = 18;
      ctx.strokeStyle = 'rgba(255,255,255,0.08)';
      ctx.stroke();

      // Score arc
      const norm = (score + 100) / 200;          // 0..1
      const startAngle = Math.PI;
      const endAngle   = Math.PI + norm * Math.PI;
      const color      = _scoreColor(score);

      // Gradient
      const grad = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
      grad.addColorStop(0, '#e74c3c');
      grad.addColorStop(0.4, '#f39c12');
      grad.addColorStop(0.5, '#f1c40f');
      grad.addColorStop(0.7, '#3498db');
      grad.addColorStop(1.0, '#2ecc71');

      ctx.beginPath();
      ctx.arc(cx, cy, r, startAngle, endAngle, false);
      ctx.lineWidth = 18;
      ctx.strokeStyle = grad;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Needle
      const angle = startAngle + norm * Math.PI;
      const nx = cx + (r - 5) * Math.cos(angle);
      const ny = cy + (r - 5) * Math.sin(angle);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(nx, ny);
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2.5;
      ctx.lineCap = 'round';
      ctx.stroke();

      // Center dot
      ctx.beginPath();
      ctx.arc(cx, cy, 5, 0, Math.PI * 2);
      ctx.fillStyle = '#fff';
      ctx.fill();

      // Labels
      ctx.font = '10px monospace';
      ctx.fillStyle = '#666';
      ctx.textAlign = 'left';
      ctx.fillText('-100', 10, cy + 4);
      ctx.textAlign = 'right';
      ctx.fillText('+100', W - 10, cy + 4);
      ctx.textAlign = 'center';
      ctx.fillText('0', cx, cy + 4);
    }

    function step() {
      const diff = targetScore - current;
      current += diff * 0.12;
      if (Math.abs(diff) < 0.5) current = targetScore;
      draw(current);
      label.textContent = (current >= 0 ? '+' : '') + Math.round(current);
      label.style.color = _scoreColor(current);
      if (Math.abs(diff) > 0.3) {
        _scoreGaugeAnim = requestAnimationFrame(step);
      }
    }
    step();
  }

  // ─── Component Bars ───────────────────────────────────────────────────────
  function _renderComponents(components) {
    const el = document.getElementById('t-components');
    if (!el) return;

    const labels = {
      technical:   'Technical',
      factor:      'Alpha Factor',
      fundamental: 'Fundamental',
      momentum:    'Momentum',
      regime:      'Market Regime',
    };
    const icons = {
      technical: '⚙', factor: '🔭', fundamental: '💰', momentum: '📈', regime: '🌊'
    };

    el.innerHTML = components.map(c => {
      const pct = Math.round(c.score);          // -100..+100
      const barPct = Math.abs(pct) / 2;         // 0..50 (half-bar)
      const isPos = pct >= 0;
      const color = _scoreColor(c.score);
      const name = labels[c.name] || c.name;
      const icon = icons[c.name] || '◆';

      return `
      <div class="trader-comp-row">
        <div class="trader-comp-label">${icon} ${name}</div>
        <div class="trader-comp-bar-wrap">
          <div class="trader-comp-bar-inner">
            <!-- Left half -->
            <div class="trader-comp-half-left">
              ${!isPos ? `<div class="trader-comp-fill" style="width:${barPct}%; background:${color}; margin-left:auto;"></div>` : ''}
            </div>
            <!-- Centre line -->
            <div class="trader-comp-center-line"></div>
            <!-- Right half -->
            <div class="trader-comp-half-right">
              ${isPos ? `<div class="trader-comp-fill" style="width:${barPct}%; background:${color};"></div>` : ''}
            </div>
          </div>
        </div>
        <div class="trader-comp-score" style="color:${color}">${pct > 0 ? '+' : ''}${pct}</div>
        <div class="trader-comp-weight">${Math.round(c.weight * 100)}%</div>
      </div>`;
    }).join('');
  }

  // ─── Prediction ───────────────────────────────────────────────────────────
  function _renderPrediction(p, score) {
    const grid = document.getElementById('t-predict-grid');
    if (!grid) return;

    const isLong = score >= 0;
    const retSign = p.expected_return_pct >= 0 ? '+' : '';

    grid.innerHTML = `
      <div class="trader-pred-cell">
        <div class="trader-pred-label">Entry</div>
        <div class="trader-pred-val">$${_fmt(p.entry)}</div>
      </div>
      <div class="trader-pred-cell warn">
        <div class="trader-pred-label">Stop Loss</div>
        <div class="trader-pred-val" style="color:#e74c3c;">$${_fmt(p.stop_loss)}</div>
      </div>
      <div class="trader-pred-cell good">
        <div class="trader-pred-label">Target 1</div>
        <div class="trader-pred-val" style="color:#2ecc71;">$${_fmt(p.target_1)}</div>
      </div>
      <div class="trader-pred-cell good2">
        <div class="trader-pred-label">Target 2</div>
        <div class="trader-pred-val" style="color:#1abc9c;">$${_fmt(p.target_2)}</div>
      </div>
      <div class="trader-pred-cell">
        <div class="trader-pred-label">R:R Ratio</div>
        <div class="trader-pred-val" style="color:#f1c40f;">${p.rr_ratio}x</div>
      </div>
      <div class="trader-pred-cell">
        <div class="trader-pred-label">Exp. Return</div>
        <div class="trader-pred-val" style="color:${p.expected_return_pct>=0?'#2ecc71':'#e74c3c'}">${retSign}${p.expected_return_pct}%</div>
      </div>
      <div class="trader-pred-cell">
        <div class="trader-pred-label">Horizon</div>
        <div class="trader-pred-val">${p.horizon_days}d</div>
      </div>
      <div class="trader-pred-cell">
        <div class="trader-pred-label">ATR(14)</div>
        <div class="trader-pred-val">$${_fmt(p.atr)}</div>
      </div>
    `;

    // Price bar visualisation
    const all = [p.stop_loss, p.entry, p.target_1, p.target_2];
    const minP = Math.min(...all);
    const maxP = Math.max(...all);
    const rng = maxP - minP || 1;
    const pct = v => ((v - minP) / rng * 100).toFixed(1);

    document.getElementById('t-pbar-stop').style.left = pct(p.stop_loss) + '%';
    document.getElementById('t-pbar-entry').style.left = pct(p.entry) + '%';
    document.getElementById('t-pbar-t1').style.left = pct(p.target_1) + '%';
    document.getElementById('t-pbar-t2').style.left = pct(p.target_2) + '%';

    document.getElementById('t-pbar-labels').innerHTML = `
      <span style="position:absolute; left:${pct(p.stop_loss)}%; transform:translateX(-50%); color:#e74c3c; font-size:9px; white-space:nowrap;">Stop</span>
      <span style="position:absolute; left:${pct(p.entry)}%; transform:translateX(-50%); color:#aaa; font-size:9px; white-space:nowrap;">Entry</span>
      <span style="position:absolute; left:${pct(p.target_1)}%; transform:translateX(-50%); color:#2ecc71; font-size:9px; white-space:nowrap;">T1</span>
      <span style="position:absolute; left:${pct(p.target_2)}%; transform:translateX(-50%); color:#1abc9c; font-size:9px; white-space:nowrap;">T2</span>
    `;
  }

  // ─── Insights ─────────────────────────────────────────────────────────────
  function _renderInsights(insights, risks) {
    const el = document.getElementById('t-insights-list');
    const rf = document.getElementById('t-risk-flags');
    if (!el || !rf) return;

    el.innerHTML = insights.map(i => `
      <div class="trader-insight-row">
        <span class="trader-insight-dot"></span>
        <span>${i}</span>
      </div>`).join('');

    rf.innerHTML = risks.length ? risks.map(r => `
      <div class="trader-risk-row">${r}</div>`).join('') : '';
  }

  // ─── Radar Chart ──────────────────────────────────────────────────────────
  function _renderRadar(components) {
    const canvas = document.getElementById('trader-radar');
    if (!canvas) return;

    const labels = components.map(c => ({
      technical:   'Technical',
      factor:      'Alpha',
      fundamental: 'Fundamental',
      momentum:    'Momentum',
      regime:      'Regime',
    }[c.name] || c.name));

    // Convert -100..+100 → 0..100 for radar display
    const values = components.map(c => Math.round((c.score + 100) / 2));

    // Draw with raw canvas (no Chart.js dependency)
    const ctx = canvas.getContext('2d');
    const W = 260, H = 260;
    const cx = W / 2, cy = H / 2;
    const r = 95;
    const n = labels.length;

    ctx.clearRect(0, 0, W, H);

    // Background webs
    for (let ring = 1; ring <= 4; ring++) {
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
        const pr = r * ring / 4;
        const x = cx + pr * Math.cos(angle);
        const y = cy + pr * Math.sin(angle);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.strokeStyle = 'rgba(255,255,255,0.07)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Spokes
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + r * Math.cos(angle), cy + r * Math.sin(angle));
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // Data polygon
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
      const pr = r * (values[i] / 100);
      const x = cx + pr * Math.cos(angle);
      const y = cy + pr * Math.sin(angle);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.closePath();

    // Fill gradient
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
    grad.addColorStop(0, 'rgba(52, 152, 219, 0.5)');
    grad.addColorStop(1, 'rgba(46, 204, 113, 0.15)');
    ctx.fillStyle = grad;
    ctx.fill();
    ctx.strokeStyle = '#3498db';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Data dots + labels
    for (let i = 0; i < n; i++) {
      const angle = (Math.PI * 2 * i / n) - Math.PI / 2;
      const pr = r * (values[i] / 100);
      const x = cx + pr * Math.cos(angle);
      const y = cy + pr * Math.sin(angle);
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#3498db';
      ctx.fill();

      // Label
      const lx = cx + (r + 16) * Math.cos(angle);
      const ly = cy + (r + 16) * Math.sin(angle);
      ctx.font = '10px monospace';
      ctx.fillStyle = '#aaa';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(labels[i], lx, ly);
    }

    // Centre score
    if (_currentResult) {
      ctx.font = 'bold 20px monospace';
      ctx.fillStyle = _scoreColor(_currentResult.composite_score);
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      const sc = _currentResult.composite_score;
      ctx.fillText((sc >= 0 ? '+' : '') + Math.round(sc), cx, cy);
    }
  }

  // ─── Watchlist ────────────────────────────────────────────────────────────
  function _buildWatchlistCards(tickers) {
    const el = document.getElementById('t-watchlist-grid');
    if (!el) return;
    el.innerHTML = tickers.map(t => `
      <div class="trader-watch-card" id="wcard-${t}" onclick="AriaTrader.analyze('${t}')">
        <div class="trader-watch-ticker">${t}</div>
        <div class="trader-watch-score" id="wscore-${t}">—</div>
        <div class="trader-watch-verdict" id="wverdict-${t}">—</div>
      </div>
    `).join('');
  }

  async function loadWatchlist() {
    const tickers = DEFAULT_WATCH.join(',');
    try {
      const resp = await fetch(`${CONFIG.serverUrl}/api/trader/batch?tickers=${tickers}&period=6mo`);
      if (!resp.ok) return;
      const data = await resp.json();
      (data.results || []).forEach(r => {
        const sc = document.getElementById(`wscore-${r.ticker}`);
        const vr = document.getElementById(`wverdict-${r.ticker}`);
        const card = document.getElementById(`wcard-${r.ticker}`);
        if (!sc || !vr) return;
        const s = r.composite_score;
        const vs = VERDICT_STYLE[r.verdict] || VERDICT_STYLE['HOLD'];
        sc.textContent = (s >= 0 ? '+' : '') + Math.round(s);
        sc.style.color = _scoreColor(s);
        vr.textContent = r.verdict || '—';
        vr.style.color = vs.text;
        if (card) card.style.borderColor = vs.border + '66';
      });
    } catch (e) {
      console.warn('Watchlist load error:', e);
    }
  }

  // ─── Screener ─────────────────────────────────────────────────────────────
  function openScreener() {
    const card = document.getElementById('trader-screener-card');
    if (!card) return;
    card.style.display = 'block';
    card.scrollIntoView({ behavior: 'smooth' });
  }

  async function runScreener() {
    const customInput = document.getElementById('screener-custom-tickers');
    const custom = customInput ? customInput.value.trim() : '';
    const loadEl = document.getElementById('t-screener-loading');
    const resEl = document.getElementById('t-screener-results');

    if (loadEl) loadEl.style.display = 'flex';
    if (resEl) resEl.innerHTML = '';

    try {
      const url = custom
        ? `${CONFIG.serverUrl}/api/trader/screen?tickers=${encodeURIComponent(custom)}&period=6mo&top_n=10`
        : `${CONFIG.serverUrl}/api/trader/screen?period=6mo&top_n=10`;

      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`API ${resp.status}`);
      const data = await resp.json();
      _renderScreener(data, resEl);
    } catch (e) {
      if (resEl) resEl.innerHTML = `<div style="color:#e74c3c;padding:12px;">Error: ${e.message}</div>`;
    } finally {
      if (loadEl) loadEl.style.display = 'none';
    }
  }

  function _renderScreener(data, el) {
    if (!el) return;
    const list = data.full_ranking || [];
    if (!list.length) {
      el.innerHTML = '<div style="padding:12px;color:#888;">No results</div>';
      return;
    }

    el.innerHTML = `
      <div class="trader-screener-table">
        <div class="trader-scr-head">
          <span>Ticker</span><span>Score</span><span>Verdict</span><span>Confidence</span><span>Action</span>
        </div>
        ${list.map(r => {
          const vs = VERDICT_STYLE[r.verdict] || VERDICT_STYLE['HOLD'];
          const s = r.composite_score;
          return `
          <div class="trader-scr-row" onclick="AriaTrader.analyze('${r.ticker}')">
            <span class="trader-scr-ticker">${r.ticker}</span>
            <span style="color:${_scoreColor(s)};font-family:monospace;">${s>=0?'+':''}${Math.round(s)}</span>
            <span style="color:${vs.text};">${vs.icon} ${r.verdict}</span>
            <span>${Math.round(r.confidence * 100)}%</span>
            <span class="trader-scr-action">▶ Analyse</span>
          </div>`;
        }).join('')}
      </div>
    `;
  }

  // ─── Backtest Chart ───────────────────────────────────────────────────────
  async function _loadBacktest(ticker) {
    const card = document.getElementById('trader-backtest-card');
    const statsEl = document.getElementById('t-bt-stats');
    if (!card) return;
    card.style.display = 'block';

    try {
      const resp = await fetch(`${CONFIG.serverUrl}/api/strategy/backtest/${ticker}?period=1y`);
      if (!resp.ok) return;
      const d = await resp.json();
      if (!d.equity_curve || !d.equity_curve.length) return;

      // Stats
      if (statsEl) {
        const tr = d.total_return >= 0 ? `+${(d.total_return*100).toFixed(1)}%` : `${(d.total_return*100).toFixed(1)}%`;
        const col = d.total_return >= 0 ? '#2ecc71' : '#e74c3c';
        statsEl.innerHTML = `
          <span style="color:${col};font-weight:700;">${tr}</span>
          <span>Sharpe: <b style="color:#f1c40f">${(d.sharpe||0).toFixed(2)}</b></span>
          <span>MaxDD: <b style="color:#e74c3c">${(d.max_drawdown*100).toFixed(1)}%</b></span>
          <span>Trades: <b style="color:#aab">${d.n_trades}</b></span>
        `;
      }

      _renderEquityCurve(d.equity_curve, d.trades || []);
    } catch (e) {
      console.warn('Backtest load error:', e);
    }
  }

  function _renderEquityCurve(curve, trades) {
    const canvas = document.getElementById('trader-equity-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.offsetWidth || 600;
    const H = 110;
    canvas.width  = W;
    canvas.height = H;
    ctx.clearRect(0, 0, W, H);

    const equities = curve.map(p => p.equity);
    const minE = Math.min(...equities);
    const maxE = Math.max(...equities);
    const rng  = maxE - minE || 1;
    const pad  = { t: 8, r: 12, b: 20, l: 52 };
    const cw   = W - pad.l - pad.r;
    const ch   = H - pad.t - pad.b;

    const px = (i) => pad.l + (i / (curve.length - 1)) * cw;
    const py = (e) => pad.t + (1 - (e - minE) / rng) * ch;

    // Grid lines
    for (let y = 0; y <= 4; y++) {
      const yy = pad.t + (y / 4) * ch;
      ctx.beginPath();
      ctx.moveTo(pad.l, yy); ctx.lineTo(pad.l + cw, yy);
      ctx.strokeStyle = 'rgba(255,255,255,0.05)';
      ctx.lineWidth = 1;
      ctx.stroke();
      const val = maxE - (y / 4) * rng;
      ctx.font = '9px monospace';
      ctx.fillStyle = '#445';
      ctx.textAlign = 'right';
      ctx.fillText('$' + val.toFixed(0), pad.l - 4, yy + 3);
    }

    // Gradient fill
    const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + ch);
    const lastE = equities[equities.length - 1];
    const isUp = lastE >= equities[0];
    grad.addColorStop(0, isUp ? 'rgba(46,204,113,0.35)' : 'rgba(231,76,60,0.35)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');

    ctx.beginPath();
    ctx.moveTo(px(0), py(equities[0]));
    for (let i = 1; i < curve.length; i++) ctx.lineTo(px(i), py(equities[i]));
    ctx.lineTo(px(curve.length - 1), H - pad.b);
    ctx.lineTo(px(0), H - pad.b);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.moveTo(px(0), py(equities[0]));
    for (let i = 1; i < curve.length; i++) ctx.lineTo(px(i), py(equities[i]));
    ctx.strokeStyle = isUp ? '#2ecc71' : '#e74c3c';
    ctx.lineWidth = 1.8;
    ctx.stroke();

    // Trade markers
    trades.slice(0, 80).forEach(t => {
      if (t.bar >= curve.length) return;
      const x = px(t.bar);
      const y = py(equities[t.bar] || equities[equities.length - 1]);
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = t.action === 'BUY' ? '#3498db' : '#e67e22';
      ctx.fill();
    });

    // X-axis labels (3 dates)
    if (curve.length > 2) {
      ctx.font = '9px monospace';
      ctx.fillStyle = '#445';
      ctx.textAlign = 'center';
      [0, Math.floor(curve.length / 2), curve.length - 1].forEach(i => {
        const date = (curve[i].date || '').slice(0, 10);
        ctx.fillText(date, px(i), H - 4);
      });
    }
  }

  // ─── Factor Heatmap ───────────────────────────────────────────────────────
  async function _loadFactorHeatmap(ticker) {
    const card = document.getElementById('trader-factors-card');
    const el   = document.getElementById('t-factor-heatmap');
    if (!card || !el) return;
    card.style.display = 'block';

    try {
      const resp = await fetch(`${CONFIG.serverUrl}/api/factors/${ticker}`);
      if (!resp.ok) return;
      const d = await resp.json();
      _renderFactorHeatmap(d, el);
    } catch (e) {
      console.warn('Factor load error:', e);
    }
  }

  function _renderFactorHeatmap(d, el) {
    // d.group_scores = { MOMENTUM: 0.3, VOLUME: -0.1, ... }
    // d.top_factors  = [{ factor: 'mom20', score: 0.72, group: 'MOMENTUM' }, ...]
    const groups  = d.group_scores || {};
    const topFacs = d.top_factors  || [];

    const GROUP_ICONS = {
      MOMENTUM: '📈', VOLUME: '📊', VOLATILITY: '〰',
      QUALITY: '⭐', TECHNICAL: '⚙', MICRO: '🔬',
    };

    // Group bars row
    const groupBars = Object.entries(groups).map(([g, v]) => {
      const pct = Math.round(v * 100);
      const color = pct >= 20 ? '#2ecc71' : pct >= 0 ? '#3498db' : pct >= -20 ? '#f1c40f' : '#e74c3c';
      const barW  = Math.round(Math.abs(pct) / 2);  // 0..50px
      return `
        <div class="tfactor-group-row">
          <span class="tfactor-group-name">${GROUP_ICONS[g]||'◆'} ${g}</span>
          <div class="tfactor-bar-bg">
            <div class="tfactor-bar-fill" style="width:${barW}px; background:${color};
              ${pct < 0 ? 'margin-left:auto;' : ''}"></div>
          </div>
          <span class="tfactor-group-val" style="color:${color};">${pct>0?'+':''}${pct}</span>
        </div>
      `;
    }).join('');

    // Top factors mini-grid
    const topGrid = topFacs.slice(0, 12).map(f => {
      const pct = Math.round((f.score || 0) * 100);
      const color = pct >= 30 ? '#2ecc71' : pct >= 0 ? '#3498db' : pct >= -30 ? '#f39c12' : '#e74c3c';
      return `
        <div class="tfactor-chip" style="border-color:${color}33; background:${color}11;">
          <div class="tfactor-chip-name">${f.factor}</div>
          <div class="tfactor-chip-val" style="color:${color};">${pct>0?'+':''}${pct}</div>
        </div>
      `;
    }).join('');

    el.innerHTML = `
      <div class="tfactor-groups">${groupBars}</div>
      ${topFacs.length ? `
        <div class="tfactor-top-label">Top Signals</div>
        <div class="tfactor-top-grid">${topGrid}</div>
      ` : ''}
    `;
  }

  // ─── Utilities ────────────────────────────────────────────────────────────
  function _setLoading(on) {
    const ld = document.getElementById('trader-loading');
    const sc = document.getElementById('trader-score-content');
    if (!ld || !sc) return;
    ld.style.display = on ? 'flex' : 'none';
    if (on) sc.style.display = 'none';
  }

  function _hideResult() {
    ['trader-predict-card','trader-insights-card'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });
  }

  function _showError(ticker, msg) {
    const ld = document.getElementById('trader-loading');
    if (ld) ld.innerHTML = `<div style="color:#e74c3c;text-align:center;"><div style="font-size:20px;">⚠</div><div>${ticker}: ${msg}</div></div>`;
  }

  function _scoreColor(score) {
    if (score >= 50)  return '#2ecc71';
    if (score >= 20)  return '#3498db';
    if (score >= -15) return '#f1c40f';
    if (score >= -50) return '#e67e22';
    return '#e74c3c';
  }

  function _fmt(v) {
    if (v == null) return '—';
    const n = parseFloat(v);
    if (isNaN(n)) return '—';
    if (n >= 1000) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return n.toFixed(2);
  }

  // ─── Ask ARIA ─────────────────────────────────────────────────────────────
  function askARIA() {
    if (!_currentResult) return;
    const d = _currentResult;
    const pred = d.prediction;

    // Build a rich context message
    const lines = [
      `[ARIA Trader Context — ${d.ticker}]`,
      `• Composite Score: ${d.composite_score > 0 ? '+' : ''}${d.composite_score} / 100`,
      `• Verdict: ${d.verdict}  (Confidence: ${Math.round(d.confidence * 100)}%)`,
      `• Last Close: $${_fmt(d.last_close)}`,
      `• Components:`,
      ...(d.components || []).map(c => `  – ${c.name}: ${c.score > 0 ? '+' : ''}${c.score}/100 (${Math.round(c.weight*100)}%)`),
    ];
    if (pred) {
      lines.push(
        `• Trade Setup: Entry $${_fmt(pred.entry)} | Stop $${_fmt(pred.stop_loss)} | T1 $${_fmt(pred.target_1)} | R:R ${pred.rr_ratio}x`,
        `• Expected Return: ${pred.expected_return_pct > 0 ? '+' : ''}${pred.expected_return_pct}% over ${pred.horizon_days} days`
      );
    }
    if (d.insights && d.insights.length) {
      lines.push('• Key Insights:', ...d.insights.map(i => `  • ${i}`));
    }
    if (d.risk_flags && d.risk_flags.length) {
      lines.push('• Risk Flags:', ...d.risk_flags.map(r => `  ${r}`));
    }
    lines.push(`\nBased on this quantitative analysis, what is your deeper qualitative view on ${d.ticker}? Should I act on this signal?`);

    const prompt = lines.join('\n');

    // Store globally so ARIA can reference it
    window._ariaTraderContext = prompt;

    // Switch to chat and pre-fill
    if (typeof switchView === 'function') switchView('chat');
    setTimeout(() => {
      const inp = document.getElementById('input');
      if (inp) {
        inp.value = prompt;
        inp.focus();
        inp.dispatchEvent(new Event('input'));
      }
    }, 300);
  }

  // ─── Public API ───────────────────────────────────────────────────────────
  return { init, analyze, loadWatchlist, openScreener, runScreener, askARIA };
})();

// Auto-init when DOM ready, but only if view exists
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('view-trader')) {
    AriaTrader.init();
    // Lazy-load watchlist after a small delay
    setTimeout(() => AriaTrader.loadWatchlist(), 1200);
  }
});
