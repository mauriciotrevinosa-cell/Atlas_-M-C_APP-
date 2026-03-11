/**
 * MMO — Mau's Market Ontology
 * Multi-scale financial ecosystem viewed through physics lenses:
 *   · Quantum Layer  — superposition, wave collapse, Born rule, tunneling
 *   · Heisenberg     — uncertainty principle: Δp × Δx ≥ ℏ/2
 *   · Decoherence    — τ = time until wave function collapse
 *   · Entanglement   — inter-asset quantum correlation field
 *   · String Theory  — vibration amplitude, frequency, vertices, nodes
 *   · Energy Layer   — capital in motion, fatigue, bubble risk, cooling
 *   · Geology Layer  — being, essence, entanglement, structural stability
 *
 * 4-layer market model (deep → surface):
 *   GEOLOGY → SUBSURFACE → STATE → OBSERVABLE
 *
 * @module MMO
 */
(function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════════════
     STATE
     ═══════════════════════════════════════════════════════════════ */
  let _ticker = 'SPY';
  let _qState = null;      // latest quantum state
  let _waveAnimId = null;      // rAF id for wave canvas
  let _waveProbs = { BULL: 0.2, BEAR: 0.2, SIDEWAYS: 0.2, VOLATILE: 0.2, TRENDING: 0.2 };
  let _collapsed = false;     // wave function collapsed?
  let _collapseT = 0;         // collapse animation time
  let _scanCache = {};        // ticker → qState
  let _initialized = false;
  let _focusKey = 'surface';
  let _overlapMatrix = null;    // Phase 3B: quantum state overlap matrix (computed after scanner)

  const SCAN_TICKERS = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'GLD', 'BTC-USD'];

  /* ── State visual config ──────────────────────────────────────── */
  const STATES = {
    BULL: { color: '#00ff88', arrow: '▲', label: 'BULL' },
    BEAR: { color: '#ff4757', arrow: '▼', label: 'BEAR' },
    SIDEWAYS: { color: '#4da6ff', arrow: '→', label: 'SIDEWAYS' },
    VOLATILE: { color: '#ff9500', arrow: '◈', label: 'VOLATILE' },
    TRENDING: { color: '#cc99ff', arrow: '↗', label: 'TRENDING' },
  };

  const LAYER_CFG = [
    { id: 'structure', label: 'GEOLOGY', color: '#7b68ee', depth: 'FOUNDATION' },
    { id: 'energy', label: 'SUBSURFACE', color: '#ff6b35', depth: 'DEEP' },
    { id: 'thermal', label: 'STATE', color: '#00d4ff', depth: 'MID' },
    { id: 'surface', label: 'OBSERVABLE', color: '#50fa7b', depth: 'SHALLOW' },
  ];

  /* ── Market character profiles ────────────────────────────────── */
  const MARKET_CHARS = {
    'SPY': { trend: 0.62, vol: 0.15, basePrice: 575 },
    'QQQ': { trend: 0.65, vol: 0.20, basePrice: 490 },
    'AAPL': { trend: 0.60, vol: 0.22, basePrice: 230 },
    'MSFT': { trend: 0.63, vol: 0.19, basePrice: 420 },
    'NVDA': { trend: 0.70, vol: 0.35, basePrice: 850 },
    'TSLA': { trend: 0.50, vol: 0.45, basePrice: 285 },
    'GLD': { trend: 0.55, vol: 0.12, basePrice: 195 },
    'BTC-USD': { trend: 0.55, vol: 0.60, basePrice: 92000 },
  };

  /* ── Entanglement table (quantum correlation matrix) ──────────── */
  const ENTANGLE_TABLE = {
    'SPY': { 'QQQ': 0.92, 'AAPL': 0.75, 'MSFT': 0.78, 'NVDA': 0.65, 'TSLA': 0.52, 'GLD': -0.12, 'BTC-USD': 0.28 },
    'QQQ': { 'SPY': 0.92, 'AAPL': 0.85, 'MSFT': 0.82, 'NVDA': 0.78, 'TSLA': 0.62, 'GLD': -0.18, 'BTC-USD': 0.35 },
    'AAPL': { 'SPY': 0.75, 'QQQ': 0.85, 'MSFT': 0.72, 'NVDA': 0.55, 'TSLA': 0.45, 'GLD': -0.08, 'BTC-USD': 0.25 },
    'MSFT': { 'SPY': 0.78, 'QQQ': 0.82, 'AAPL': 0.72, 'NVDA': 0.62, 'TSLA': 0.42, 'GLD': -0.10, 'BTC-USD': 0.22 },
    'NVDA': { 'SPY': 0.65, 'QQQ': 0.78, 'AAPL': 0.55, 'MSFT': 0.62, 'TSLA': 0.58, 'GLD': -0.15, 'BTC-USD': 0.40 },
    'TSLA': { 'SPY': 0.52, 'QQQ': 0.62, 'AAPL': 0.45, 'MSFT': 0.42, 'NVDA': 0.58, 'GLD': -0.05, 'BTC-USD': 0.48 },
    'GLD': { 'SPY': -0.12, 'QQQ': -0.18, 'AAPL': -0.08, 'MSFT': -0.10, 'NVDA': -0.15, 'TSLA': -0.05, 'BTC-USD': 0.15 },
    'BTC-USD': { 'SPY': 0.28, 'QQQ': 0.35, 'AAPL': 0.25, 'MSFT': 0.22, 'NVDA': 0.40, 'TSLA': 0.48, 'GLD': 0.15 },
  };

  /* ── Tiny API helper ──────────────────────────────────────────── */
  const _api = {
    get: (path) => fetch(path).then(r => r.ok ? r.json() : null).catch(() => null),
  };

  function _clamp(value, min = 0, max = 1) {
    return Math.max(min, Math.min(max, value));
  }

  function _formatPct(value) {
    return typeof value === 'number' && Number.isFinite(value)
      ? `${Math.round(value * 100)}%`
      : '-';
  }

  function _formatMetric(value, digits = 3) {
    return typeof value === 'number' && Number.isFinite(value)
      ? value.toFixed(digits)
      : '-';
  }

  /* ═══════════════════════════════════════════════════════════════
     LOCAL QUANTUM STATE ENGINE
     Computes full quantum state offline — no API dependency.
     Uses deterministic pseudo-random seeded by ticker + day.
     ═══════════════════════════════════════════════════════════════ */
  function _computeLocalQuantumState(ticker) {
    const t = (ticker || 'SPY').toUpperCase();
    const seed = t.split('').reduce((a, c) => a + c.charCodeAt(0), 0) + new Date().getDate();
    const rng = (n) => {
      const x = Math.sin(seed * n + n * 1.618033988) * 10000;
      return x - Math.floor(x);
    };

    const char = MARKET_CHARS[t] || { trend: 0.55, vol: 0.25, basePrice: 100 };

    // ── Amplitudes (Born rule: prob = |amplitude|²) ──────────────
    const raw = {
      BULL: char.trend * (0.30 + rng(1) * 0.40),
      BEAR: (1 - char.trend) * (0.20 + rng(2) * 0.35),
      SIDEWAYS: 0.15 + rng(3) * 0.20,
      VOLATILE: char.vol * (0.20 + rng(4) * 0.30),
      TRENDING: char.trend * (0.20 + rng(5) * 0.25),
    };
    const total = Object.values(raw).reduce((a, b) => a + b, 0);
    const amps = {};
    Object.keys(raw).forEach(k => { amps[k] = raw[k] / total; });

    // ── Shannon entropy H = -Σpᵢlog(pᵢ)/log(5) ─────────────────
    const entropy = -Object.values(amps).reduce(
      (a, p) => a + (p > 0 ? p * Math.log(p) : 0), 0) / Math.log(5);

    // ── Dominant state ───────────────────────────────────────────
    let dom = 'BULL', domP = 0;
    Object.entries(amps).forEach(([s, p]) => { if (p > domP) { domP = p; dom = s; } });

    const collapse_prob = Math.min(0.99, 1 - entropy);
    const tunneling_risk = Math.min(0.9, char.vol * (0.3 + rng(6) * 0.4));

    // ── Quantum verdict ──────────────────────────────────────────
    let quantum_verdict = 'SUPERPOSED — WAIT';
    if (collapse_prob > 0.6 && dom === 'BULL') quantum_verdict = 'BUY';
    else if (collapse_prob > 0.6 && dom === 'BEAR') quantum_verdict = 'SELL';
    else if (dom === 'VOLATILE' || tunneling_risk > 0.25) quantum_verdict = 'HEDGE — VOLATILITY';
    else if (dom === 'TRENDING' && amps.TRENDING > 0.35) quantum_verdict = 'TREND FOLLOW';

    // ── Price data ───────────────────────────────────────────────
    const last_close = (char.basePrice * (0.95 + rng(7) * 0.10)).toFixed(2);
    const trend_pct = ((char.trend - 0.5) * 40 * (0.8 + rng(8) * 0.4)).toFixed(1);
    const annual_vol_pct = (char.vol * 100 * (0.9 + rng(9) * 0.2)).toFixed(1);

    // ── String theory ────────────────────────────────────────────
    const string = {
      amplitude: Math.min(1, 0.2 + char.vol * (0.5 + rng(10) * 0.5)),
      frequency: Math.min(1, 0.3 + char.trend * (0.5 + rng(11) * 0.4)),
      vertices_30d: Math.floor(3 + rng(12) * 10),
      nodes: [],
    };
    const base = parseFloat(last_close);
    if (rng(13) > 0.4) string.nodes.push({ level: (base * (1 - char.vol * 0.5)).toFixed(0), type: 'SUPPORT' });
    if (rng(14) > 0.4) string.nodes.push({ level: (base * (1 + char.vol * 0.5)).toFixed(0), type: 'RESISTANCE' });

    // ── Energy ───────────────────────────────────────────────────
    const energy = {
      score: Math.min(1, 0.3 + char.vol * 0.4 + char.trend * 0.2 + rng(15) * 0.15),
      fatigue: Math.min(1, rng(16) * (0.2 + (1 - char.trend) * 0.5)),
      bubble_risk: char.vol > 0.3 ? Math.min(1, 0.3 + rng(17) * 0.4) : Math.min(1, 0.05 + rng(17) * 0.2),
      cooling_adequacy: Math.min(1, 0.4 + (1 - char.vol) * 0.4 + rng(18) * 0.15),
    };

    // ── Ontology ─────────────────────────────────────────────────
    const beings = ['EXPANSION', 'CONTRACTION', 'TURBULENCE', 'STASIS', 'TRANSITION'];
    const being = char.trend > 0.6
      ? (rng(19) > 0.4 ? 'EXPANSION' : 'TRANSITION')
      : char.trend < 0.45
        ? (rng(19) > 0.4 ? 'CONTRACTION' : 'TURBULENCE')
        : beings[Math.floor(rng(19) * beings.length)];

    const ontology = {
      being,
      essence: dom.charAt(0) + dom.slice(1).toLowerCase() + ' Momentum Field',
      entanglement: t === 'SPY' ? 'BROAD MARKET' : t === 'GLD' ? 'INVERSE SPY' : 'SECTOR CORR',
      structural_stability: Math.min(1, 0.4 + (1 - char.vol) * 0.5 + rng(20) * 0.1),
    };

    // ── Layers ───────────────────────────────────────────────────
    const layers = [
      { id: 'structure', metric: `Stability ${(ontology.structural_stability * 100).toFixed(0)}%`, value: ontology.structural_stability, health: being },
      { id: 'energy', metric: `E=${energy.score.toFixed(2)}`, value: energy.score, health: energy.fatigue > 0.5 ? 'FATIGUED' : 'ACTIVE' },
      { id: 'thermal', metric: `Vol ${annual_vol_pct}%`, value: Math.min(1, char.vol * 2), health: dom },
      { id: 'surface', metric: `ψ=${amps[dom].toFixed(2)}`, value: amps[dom], health: quantum_verdict },
    ];

    // ── Heisenberg Uncertainty Principle ─────────────────────────
    // Δp = momentum uncertainty (proxy: volatility)
    // Δx = position uncertainty (proxy: inverse trend clarity)
    const delta_p = char.vol;
    const delta_x = 1 / Math.max(0.1, char.trend);
    const u_sys = delta_p * delta_x;
    const heisenberg = {
      delta_p,
      delta_x,
      product: u_sys,
      hbar_half: 0.5,
      compliant: u_sys >= 0.5,
      position_certainty: char.trend,
      momentum_certainty: Math.max(0, 1 - char.vol),
      sizing_suggested: `Size = [Capital × α] / √(${(u_sys || 1).toFixed(2)})`
    };

    // ── Decoherence time τ ────────────────────────────────────────
    // τ ∝ 1/(σ · H)  — high vol + high entropy → rapid collapse
    const tau = 1 / Math.max(0.01, char.vol * (1 + entropy));
    const decoherence = {
      tau,
      tau_normalized: Math.min(1, tau / 5),
      regime: tau < 0.5 ? 'RAPID COLLAPSE' : tau < 1.5 ? 'MODERATE DECAY' : 'STABLE SUPERPOSITION',
      noise_factor: Math.min(1, char.vol * (0.5 + entropy * 0.5)),
    };

    // ── Quantum Entanglement ──────────────────────────────────────
    const entanglement = ENTANGLE_TABLE[t] || {};

    return {
      ticker: t,
      amplitudes: amps,
      entropy,
      collapsed_state: collapse_prob > 0.75 ? dom : null,
      collapse_prob,
      tunneling_risk,
      quantum_verdict,
      last_close,
      trend_pct,
      annual_vol_pct,
      string,
      energy,
      ontology,
      layers,
      heisenberg,
      decoherence,
      entanglement,
      _local: true,
    };
  }

  /* ═══════════════════════════════════════════════════════════════
     BUILD VIEW HTML
     ═══════════════════════════════════════════════════════════════ */
  function _buildView() {
    const el = document.getElementById('view-mmo');
    if (!el || el.innerHTML.trim()) return;

    el.innerHTML = `
<div class="mmo-shell">

  <!-- HEADER -->
  <div class="mmo-header">
    <div class="mmo-brand">
      <span class="mmo-psi">⟨ψ⟩</span>
      <span class="mmo-title">MMO</span>
      <span class="mmo-sub">Mau's Market Ontology</span>
    </div>
    <div class="mmo-controls">
      <input id="mmo-ticker-input" class="mmo-input" value="SPY" maxlength="10"
             onkeydown="if(event.key==='Enter')MMO.analyze(this.value)" />
      <button class="mmo-btn-analyze"  onclick="MMO.analyze(document.getElementById('mmo-ticker-input').value)">⟩ Analyze</button>
      <button class="mmo-btn-collapse" onclick="MMO.collapse()">↯ Collapse</button>
      <button class="mmo-btn-reset"    onclick="MMO.reset()">⟳ Reset</button>
      <button class="mmo-btn-theory"   onclick="MMO.showTheory()">📖 Theory</button>
    </div>
  </div>

  <!-- LAYERED ECOSYSTEM PANEL -->
  <div class="mmo-layers-panel">
    <div class="mmo-layers-title">LAYERED ECOSYSTEM — Deep Structure → Observable Surface</div>
    <div class="mmo-layer-stack" id="mmo-layer-stack">
      ${LAYER_CFG.map(l => `
      <div class="mmo-layer-row layer-${l.id}" data-layer="${l.id}">
        <span class="mmo-layer-id">${l.label}</span>
        <span class="mmo-layer-metric" id="mmo-lm-${l.id}">—</span>
        <div class="mmo-layer-track">
          <div class="mmo-layer-fill" id="mmo-lf-${l.id}" style="width:50%"></div>
        </div>
        <span class="mmo-layer-health" id="mmo-lh-${l.id}">${l.depth}</span>
      </div>`).join('')}
    </div>
  </div>

  <!-- MAIN BODY GRID: Quantum HUD Observatory -->
  <div class="mmo-hud-container">
    
    <!-- LEFT PANEL: Quantum Observables -->
    <div class="mmo-hud-left">
      <div class="mmo-card mmo-energy-card">
        <div class="mmo-card-title" style="color:#ff6b35">THERMODYNAMICS &nbsp;|&nbsp; Energy & Fatigue</div>
        <div id="mmo-energy-display"><div style="font-size:9px;color:#3a3a5a">—</div></div>
      </div>
      <div class="mmo-card mmo-ontology-card">
        <div class="mmo-card-title" style="color:#7b68ee">MARKET ONTOLOGY</div>
        <div id="mmo-ontology-display"><div style="font-size:9px;color:#3a3a5a">—</div></div>
      </div>
      <div class="mmo-card mmo-entropy-card">
        <div class="mmo-card-title" style="color:#00d4ff">SUPERPOSITION ENTROPY</div>
        <div id="mmo-entropy-display"><div style="font-size:9px;color:#3a3a5a">—</div></div>
      </div>
    </div>

    <!-- CENTER PANEL: Vacuum Chamber (WebGL) & Waves -->
    <div class="mmo-hud-center">
      <div class="mmo-vacuum-title">⟨ψ⟩ SUPERPOSITION &nbsp;|&nbsp; QUANTUM TOPOLOGY</div>
      <div style="flex:1; display:flex; flex-direction:column; position:relative; padding-top:40px;">
        <!-- Top: 2D Wave Canvas -->
        <div style="flex:1; position:relative; overflow:hidden; border-bottom:1px solid rgba(124, 63, 228, 0.2);">
          <canvas id="mmo-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;"></canvas>
          <div style="position:absolute;top:10px;left:15px;font-size:10px;color:#9b8ee8;font-family:monospace;letter-spacing:1px;pointer-events:none;">
             WAVE FUNCTION | ψ(<span id="mmo-wave-ticker" style="color:#fff">SPY</span>)
          </div>
        </div>
        <!-- Bottom: 3D Vacuum Chamber -->
        <div id="mmo-three-mount" style="flex:1; position:relative; overflow:hidden;"></div>
      </div>
    </div>

    <!-- RIGHT PANEL: Collapse & Actionability -->
    <div class="mmo-hud-right">
      <div class="mmo-card mmo-heisenberg-card">
        <div class="mmo-card-title" style="color:#bd93f9">HEISENBERG SIZING &nbsp;|&nbsp; Δp × Δx</div>
        <div id="mmo-heisenberg-display"><div style="font-size:9px;color:#3a3a5a">—</div></div>
      </div>
      <div class="mmo-card mmo-decoherence-card">
        <div class="mmo-card-title" style="color:#ff79c6">DECOHERENCE τ &nbsp;|&nbsp; Wave Stability</div>
        <div id="mmo-decoherence-display"><div style="font-size:9px;color:#3a3a5a">—</div></div>
      </div>
      <div class="mmo-card mmo-action-card" style="flex:1;display:flex;flex-direction:column;">
        <div class="mmo-card-title" style="color:#00ff88">EXECUTION PROTOCOLS</div>
        <div id="mmo-action-display" style="padding:15px;flex:1;display:flex;flex-direction:column;justify-content:center;">
          <button class="mmo-btn-action mmo-btn-breakout" onclick="console.log('Breakout prepared')">[ PREPARE TUNNEL BREAKOUT ]</button>
          <button class="mmo-btn-action mmo-btn-hedge" onclick="console.log('Delta hedge initiated')">[ INITIATE DELTA HEDGE ]</button>
        </div>
      </div>
    </div>

  </div><!-- /mmo-hud-container -->

  <!-- BOTTOM BAR: String Theory & Scanner -->
  <div class="mmo-bottom-bar">
    <div class="mmo-card mmo-string-card">
      <div class="mmo-card-title" style="color:#6a3a5a">STRING THEORY &nbsp;|&nbsp; Probabilistic Paths</div>
      <div id="mmo-string-display"><div style="font-size:9px;color:#3a3a5a">—</div></div>
    </div>
    <div class="mmo-scanner-card mmo-card">
      <div class="mmo-card-title">QUANTUM SCANNER &nbsp;—&nbsp; Multi-Ticker Superposition</div>
      <div class="mmo-scanner-grid" id="mmo-scanner-grid">
        ${SCAN_TICKERS.map(t => `
        <div class="mmo-mini-card" onclick="MMO.analyze('${t}')" id="mmo-mini-${t.replace('-', '_')}">
          <div class="mmo-mini-ticker">${t}</div>
          <div class="mmo-mini-loading">loading…</div>
        </div>`).join('')}
      </div>
    </div>
  </div>

</div><!-- /mmo-shell -->
`;
    _startWaveCanvas();
    _startVacuumChamber();
    _loadScanner();
  }

  /* ═══════════════════════════════════════════════════════════════
     WAVE CANVAS ANIMATION
     ═══════════════════════════════════════════════════════════════ */
  function _startWaveCanvas() {
    if (_waveAnimId) cancelAnimationFrame(_waveAnimId);
    const canvas = document.getElementById('mmo-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let t = 0;
    let _tunnelingRisk = 0.1;

    function frame() {
      const W = canvas.offsetWidth;
      const H = canvas.offsetHeight || 150;
      canvas.width = W;
      canvas.height = H;

      ctx.clearRect(0, 0, W, H);

      // Subtle grid
      ctx.strokeStyle = 'rgba(255,255,255,0.03)';
      ctx.lineWidth = 1;
      for (let x = 0; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
      for (let y = 0; y < H; y += 30) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }


      // V(x) Potential Field Overlay (Phase 3A)
      if (_qState && _qState.potential_field && _qState.potential_field.length > 1) {
        const pf = _qState.potential_field;
        const prices = pf.map(p => p.price);
        const vvals  = pf.map(p => p.V);
        const pMin = Math.min(...prices), pMax = Math.max(...prices);
        const vMin = Math.min(...vvals),  vMax = Math.max(...vvals);
        const pRng = pMax - pMin || 1;
        const vRng = vMax - vMin || 1;
        const vH = H * 0.25;
        const vY0 = H - 2;
        ctx.save();
        ctx.globalAlpha = 0.45;
        ctx.beginPath();
        pf.forEach((pt, i) => {
          const x = (pt.price - pMin) / pRng * W;
          const y = vY0 - (pt.V - vMin) / vRng * vH;
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.lineTo(W, vY0); ctx.lineTo(0, vY0); ctx.closePath();
        const vGrad = ctx.createLinearGradient(0, vY0 - vH, 0, vY0);
        vGrad.addColorStop(0, 'rgba(255,149,0,0.6)');
        vGrad.addColorStop(1, 'rgba(255,149,0,0.05)');
        ctx.fillStyle = vGrad;
        ctx.fill();
        ctx.beginPath();
        pf.forEach((pt, i) => {
          const x = (pt.price - pMin) / pRng * W;
          const y = vY0 - (pt.V - vMin) / vRng * vH;
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.strokeStyle = 'rgba(255,149,0,0.7)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.globalAlpha = 1.0;
        ctx.restore();
        ctx.font = '8px monospace';
        ctx.fillStyle = 'rgba(255,149,0,0.5)';
        ctx.textAlign = 'left';
        ctx.fillText('V(x) potential', 4, vY0 - vH - 2);
      }

      const stateKeys = ['BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'TRENDING'];
      const freqs = [1.2, 0.9, 0.5, 2.1, 1.6];
      const phases = [0, 0.8, 1.5, 2.3, 0.3];
      const midY = H * 0.42;
      const maxAmp = H * 0.17;

      if (!_collapsed) {
        if (_tunnelingRisk > 0.05) {
          const barrierAlpha = Math.min(0.35, _tunnelingRisk);
          const barrierW = 4;
          const barrierTop = midY - maxAmp * 1.8;
          const barrierBot = midY + maxAmp * 1.8;

          ctx.fillStyle = `rgba(255, 149, 0, ${barrierAlpha * 0.6})`;
          ctx.fillRect(W * 0.22, barrierTop, barrierW, barrierBot - barrierTop);
          ctx.fillRect(W * 0.78, barrierTop, barrierW, barrierBot - barrierTop);

          ctx.shadowColor = '#ff9500';
          ctx.shadowBlur = 8;
          ctx.fillStyle = `rgba(255, 149, 0, ${_tunnelingRisk * 0.25})`;
          ctx.fillRect(W * 0.78 + barrierW, barrierTop, 20, barrierBot - barrierTop);
          ctx.shadowBlur = 0;

          ctx.font = '8px monospace';
          ctx.fillStyle = `rgba(255,149,0,0.5)`;
          ctx.textAlign = 'center';
          ctx.fillText('BARRIER', W * 0.22 + 2, barrierTop - 4);
          ctx.fillText(`T=${(_tunnelingRisk * 100).toFixed(0)}%`, W * 0.78 + barrierW + 12, barrierTop - 4);
        }

        stateKeys.forEach((s, i) => {
          const prob = _waveProbs[s] || 0.2;
          const amp = Math.sqrt(prob) * maxAmp;
          const col = STATES[s].color;

          ctx.beginPath();
          ctx.strokeStyle = col + '55';
          ctx.lineWidth = 1.5;
          for (let x = 0; x <= W; x += 2) {
            const nx = x / W * Math.PI * 4;
            const y = midY + Math.sin(nx * freqs[i] + t * (0.6 + i * 0.15) + phases[i]) * amp;
            if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          }
          ctx.stroke();
        });

        const sumY_arr = [];
        for (let x = 0; x <= W; x += 2) {
          const nx = x / W * Math.PI * 4;
          let sumY = 0;
          stateKeys.forEach((s, i) => {
            const prob = _waveProbs[s] || 0.2;
            const amp = Math.sqrt(prob) * maxAmp;
            sumY += Math.sin(nx * freqs[i] + t * (0.6 + i * 0.15) + phases[i]) * amp * 0.5;
          });
          sumY_arr.push(midY + sumY);
        }

        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255,255,255,0.30)';
        ctx.lineWidth = 2.5;
        sumY_arr.forEach((y, i) => { if (i === 0) ctx.moveTo(i * 2, y); else ctx.lineTo(i * 2, y); });
        ctx.stroke();

        const grad = ctx.createLinearGradient(0, midY - maxAmp * 1.5, 0, midY + maxAmp * 1.5);
        grad.addColorStop(0, 'rgba(124, 63, 228, 0.00)');
        grad.addColorStop(0.5, 'rgba(124, 63, 228, 0.08)');
        grad.addColorStop(1, 'rgba(124, 63, 228, 0.00)');

        ctx.beginPath();
        sumY_arr.forEach((y, i) => { if (i === 0) ctx.moveTo(i * 2, y); else ctx.lineTo(i * 2, y); });
        ctx.lineTo(W, midY);
        ctx.lineTo(0, midY);
        ctx.closePath();
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.font = '10px monospace';
        ctx.fillStyle = '#4a3a7a';
        ctx.textAlign = 'left';
        ctx.fillText('|ψ⟩ = SUPERPOSITION', 10, H - 10);
        ctx.fillStyle = '#2a2a5a';
        ctx.fillText('|ψ|² = probability density', 10, H - 22);

      } else {
        _collapseT += 0.05;
        const dominant = _qState && _qState.amplitudes ? _getDominantFromAmps(_qState.amplitudes) : 'BULL';
        const col = STATES[dominant] ? STATES[dominant].color : '#cc99ff';

        const ring = Math.abs(Math.sin(_collapseT * 3));
        for (let r = 10; r < 90; r += 20) {
          ctx.strokeStyle = col + Math.floor(ring * 50).toString(16).padStart(2, '0');
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(W / 2, midY, r * (1 + ring * 0.3), 0, Math.PI * 2);
          ctx.stroke();
        }

        const spikeH = maxAmp * 2.5;
        ctx.shadowColor = col;
        ctx.shadowBlur = 16;
        ctx.strokeStyle = col;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(W / 2, midY + 10);
        ctx.lineTo(W / 2, midY - spikeH);
        ctx.stroke();
        ctx.shadowBlur = 0;

        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.moveTo(W / 2, midY - spikeH);
        ctx.lineTo(W / 2 - 6, midY - spikeH + 12);
        ctx.lineTo(W / 2 + 6, midY - spikeH + 12);
        ctx.closePath();
        ctx.fill();

        ctx.font = 'bold 13px monospace';
        ctx.fillStyle = col;
        ctx.textAlign = 'center';
        ctx.shadowColor = col;
        ctx.shadowBlur = 8;
        ctx.fillText('⟩ COLLAPSED → ' + dominant, W / 2, H - 14);
        ctx.shadowBlur = 0;
      }

      ctx.strokeStyle = 'rgba(255,255,255,0.06)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(W, midY);
      ctx.stroke();

      t += 0.015;
      _waveAnimId = requestAnimationFrame(frame);
    }
    frame();

    _startWaveCanvas._setTunneling = (v) => { _tunnelingRisk = v; };
  }

  /* ═══════════════════════════════════════════════════════════════
     VACUUM CHAMBER W/ THREE.JS
     Shows: Entanglement Heatmap and Tunneling Risk in a 3D topology.
     ═══════════════════════════════════════════════════════════════ */
  let _vacuumAnimId = null;
  let _vacuumResizeObserver = null;
  let _vkRenderData = { tunnelingRisk: 0, amplitudes: null, vScene: null, focus: null, qState: null };

  function _startVacuumChamber() {
    if (_vacuumAnimId) cancelAnimationFrame(_vacuumAnimId);

    const mount = document.getElementById('mmo-three-mount');
    if (!mount || typeof THREE === 'undefined') return;
    mount.innerHTML = '';

    const W = mount.offsetWidth;
    const H = mount.offsetHeight;

    const scene = new THREE.Scene();
    scene.background = null; // transparent to show HUD dark bg
    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 1000);
    camera.position.set(0, 15, 65);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mount.appendChild(renderer.domElement);

    _vkRenderData.vScene = scene;

    // ── Topology Grid ──────────────────────────────────────────
    const gridGeo = new THREE.PlaneGeometry(200, 200, 40, 40);
    const gridMat = new THREE.MeshBasicMaterial({ color: 0x4a3a7a, wireframe: true, transparent: true, opacity: 0.15 });
    const grid = new THREE.Mesh(gridGeo, gridMat);
    grid.rotation.x = -Math.PI / 2;
    grid.position.y = -15;
    scene.add(grid);

    // ── Entanglement Spheres (Other assets) ────────────────────
    const nodes = [];
    const colors = [0x00ff88, 0x00d4ff, 0xff79c6, 0xffb86c, 0xbd93f9];
    for (let i = 0; i < 5; i++) {
      const geo = new THREE.SphereGeometry(1.5, 16, 16);
      const mat = new THREE.MeshBasicMaterial({ color: colors[i], transparent: true, opacity: 0.5 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set((Math.random() - 0.5) * 40, (Math.random() - 0.5) * 20, (Math.random() - 0.5) * 40);
      scene.add(mesh);

      // Entanglement Threads
      const lineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), mesh.position]);
      const lineMat = new THREE.LineBasicMaterial({ color: colors[i], transparent: true, opacity: 0.2 });
      const line = new THREE.Line(lineGeo, lineMat);
      scene.add(line);

      nodes.push({ mesh, line, basePos: mesh.position.clone(), speed: Math.random() * 0.02 + 0.01 });
    }

    // ── Primary Asset Core (The Ticker) ────────────────────────
    const coreGeo = new THREE.SphereGeometry(3, 32, 32);
    const coreMat = new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.8 });
    const core = new THREE.Mesh(coreGeo, coreMat);
    scene.add(core);

    const coreGlowGeo = new THREE.SphereGeometry(6, 32, 32);
    const coreGlowMat = new THREE.MeshBasicMaterial({ color: 0xbd93f9, transparent: true, opacity: 0.15, blending: THREE.AdditiveBlending, depthWrite: false });
    const coreGlow = new THREE.Mesh(coreGlowGeo, coreGlowMat);
    scene.add(coreGlow);

    // ── Tunneling Membrane (Resistance Plane) ──────────────────
    const membraneGeo = new THREE.PlaneGeometry(60, 40, 20, 20);
    const membraneMat = new THREE.MeshBasicMaterial({ color: 0xff9500, wireframe: true, transparent: true, opacity: 0.05, side: THREE.DoubleSide });
    const membrane = new THREE.Mesh(membraneGeo, membraneMat);
    membrane.position.z = -15;
    scene.add(membrane);

    // ── Floating Particles (Energy Flux) ───────────────────────
    const partGeo = new THREE.BufferGeometry();
    const partCount = 400;
    const posInit = new Float32Array(partCount * 3);
    for (let i = 0; i < partCount * 3; i++) posInit[i] = (Math.random() - 0.5) * 80;
    partGeo.setAttribute('position', new THREE.BufferAttribute(posInit, 3));
    const partMat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.3, transparent: true, opacity: 0.4 });
    const particles = new THREE.Points(partGeo, partMat);
    scene.add(particles);

    let t = 0;
    function animate() {
      _vacuumAnimId = requestAnimationFrame(animate);
      t += 0.01;

      const risk = _vkRenderData.tunnelingRisk || 0;

      // Pulse Core
      core.rotation.y += 0.01;
      core.rotation.x += 0.005;
      const pulse = 1 + Math.sin(t * 5) * 0.1;
      core.scale.set(pulse, pulse, pulse);

      // Update Nodes
      nodes.forEach((n, idx) => {
        n.mesh.position.y = n.basePos.y + Math.sin(t * 3 + idx) * 5;
        const posCopy = n.mesh.position.clone();
        n.line.geometry.setFromPoints([core.position, posCopy]);
        n.line.material.opacity = 0.1 + Math.sin(t * 2 + idx) * 0.1;
      });

      // Tunneling Membrane Activity
      if (risk > 0.05) {
        membrane.material.opacity = 0.1 + risk * 0.4;
        membrane.material.color.setHex(0xff3300);
        membrane.position.z = -15 + Math.sin(t * 10) * risk * 5;
        const positions = partGeo.attributes.position.array;
        for (let i = 0; i < partCount; i++) {
          positions[i * 3 + 2] -= (0.5 + risk * 2); // Particles fly towards membrane
          if (positions[i * 3 + 2] < -20) {
            positions[i * 3] = (Math.random() - 0.5) * 80;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 40;
            positions[i * 3 + 2] = 20;
          }
        }
        partGeo.attributes.position.needsUpdate = true;
      } else {
        membrane.material.opacity = 0.05;
        membrane.material.color.setHex(0x4a3a7a);
        membrane.position.z = -25;
        const positions = partGeo.attributes.position.array;
        for (let i = 0; i < partCount; i++) {
          positions[i * 3 + 2] -= 0.2;
          if (positions[i * 3 + 2] < -40) positions[i * 3 + 2] = 40;
        }
        partGeo.attributes.position.needsUpdate = true;
      }

      // Camera Orbit
      camera.position.x = Math.sin(t * 0.2) * 30;
      camera.position.z = 60 + Math.cos(t * 0.2) * 10;
      camera.lookAt(core.position);

      renderer.render(scene, camera);
    }
    animate();

    // Resize observer
    const ro = new ResizeObserver(() => {
      if (!mount || !renderer) return;
      renderer.setSize(mount.offsetWidth, mount.offsetHeight);
      camera.aspect = mount.offsetWidth / mount.offsetHeight;
      camera.updateProjectionMatrix();
    });
    ro.observe(mount);
  }

  function _getDominantState() {
    if (!_qState) return 'BULL';
    let best = 'BULL', bestP = 0;
    Object.entries(_qState.amplitudes || {}).forEach(([s, p]) => { if (p > bestP) { bestP = p; best = s; } });
    return best;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: AMPLITUDE BARS
     ═══════════════════════════════════════════════════════════════ */
  function _renderAmplitudes(amplitudes) {
    const el = document.getElementById('mmo-amplitudes');
    if (!el || !amplitudes) return;

    const order = ['BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'TRENDING'];
    el.innerHTML = order.map(s => {
      const p = amplitudes[s] || 0;
      const pct = Math.round(p * 100);
      const col = STATES[s].color;
      const arr = STATES[s].arrow;
      const css = s.toLowerCase();
      return `
<div class="mmo-amp-row">
  <span class="mmo-amp-label mmo-state-${css}">${s}</span>
  <div class="mmo-amp-track">
    <div class="mmo-amp-fill" style="width:${pct}%;background:${col};box-shadow:0 0 6px ${col}55"></div>
  </div>
  <span class="mmo-amp-pct" style="color:${col}">${pct}%</span>
  <span class="mmo-amp-arrow" style="color:${col}">${arr}</span>
</div>`;
    }).join('');
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: QUANTUM STATE PANEL
     ═══════════════════════════════════════════════════════════════ */
  function _renderQuantumState(qs) {
    const el = document.getElementById('mmo-state-display');
    if (!el || !qs) return;

    const verdict = qs.quantum_verdict || 'SUPERPOSED — WAIT';
    const colProb = Math.round((qs.collapse_prob || 0) * 100);
    const tunnPct = Math.round((qs.tunneling_risk || 0) * 100);
    const isCollapsed = !!qs.collapsed_state;

    let verdictClass = 'mmo-verdict-wait';
    if (verdict === 'BUY') verdictClass = 'mmo-verdict-buy';
    else if (verdict === 'SELL') verdictClass = 'mmo-verdict-sell';
    else if (verdict.includes('TREND')) verdictClass = 'mmo-verdict-trend';
    else if (verdict.includes('HEDGE')) verdictClass = 'mmo-verdict-hedge';

    let tunnClass = 'mmo-tunnel-low';
    if (tunnPct > 12) tunnClass = 'mmo-tunnel-high';
    else if (tunnPct > 6) tunnClass = 'mmo-tunnel-mod';

    el.innerHTML = `
${isCollapsed
        ? `<div class="mmo-collapsed-badge">⟩ WAVE COLLAPSED</div>`
        : `<div class="mmo-superposed-label">|ψ⟩ = Σ αᵢ|stateᵢ⟩</div>`}

<div class="mmo-verdict ${verdictClass}">${verdict}</div>

<div class="mmo-collapse-meter">
  <div class="mmo-meter-label">Collapse Probability</div>
  <div class="mmo-meter-track">
    <div class="mmo-meter-fill" style="width:${colProb}%"></div>
  </div>
  <div class="mmo-meter-val">${colProb}%</div>
</div>

<div class="mmo-tunnel-row">
  <span class="mmo-tunnel-label">Tunneling Risk</span>
  <span class="mmo-tunnel-val ${tunnClass}">
    ${tunnPct < 4 ? 'LOW' : tunnPct < 10 ? 'MODERATE' : 'HIGH'} &nbsp;${tunnPct}%
  </span>
</div>
${qs.last_close ? `
<div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(108,63,200,0.1);font-size:9px;color:#4a4a6a">
  <span style="color:#7a6a9a">LAST CLOSE</span>
  &nbsp;<span style="color:#cc99ff;font-weight:700">$${qs.last_close}</span>
  &nbsp;&nbsp;
  <span style="color:#7a6a9a">6MO TREND</span>
  &nbsp;<span style="color:${(qs.trend_pct || 0) >= 0 ? '#00ff88' : '#ff4757'};font-weight:700">
    ${(qs.trend_pct || 0) >= 0 ? '+' : ''}${qs.trend_pct}%
  </span>
  &nbsp;&nbsp;
  <span style="color:#7a6a9a">VOL</span>
  &nbsp;<span style="color:#ffaa00;font-weight:700">${qs.annual_vol_pct}%</span>
</div>` : ''}
${qs._local ? '<div style="margin-top:6px;font-size:8px;color:#2a2a4a">⚙ computed locally</div>' : ''}
`;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: STRING THEORY PANEL
     ═══════════════════════════════════════════════════════════════ */
  function _renderString(d) {
    const el = document.getElementById('mmo-string-display');
    if (!el) return;
    const s = d.string || {};
    const nodes = s.nodes || [];
    const tNodes = d.tunneling_nodes || [];
    const ampColor = s.amplitude > 0.6 ? '#ff4757' : s.amplitude > 0.3 ? '#f1c40f' : '#00d4ff';
    const freqColor = s.frequency > 0.6 ? '#ff9500' : '#bd93f9';
    const nodeHTML = nodes.map(n => {
      const T = n.T_wkb != null ? n.T_wkb : 0.5;
      const tColor = T > 0.5 ? '#ff4757' : T > 0.2 ? '#f1c40f' : '#00ff88';
      const typeColor = n.type === 'RESISTANCE' ? '#ff4757' : '#00ff88';
      return `<div class="mmo-node-row">
        <span style="color:${typeColor};font-size:9px;min-width:24px;">${n.type === 'RESISTANCE' ? 'RES' : 'SUP'}</span>
        <span style="font-family:monospace;font-size:11px;color:#eee;flex:1;">$${n.level}</span>
        <span style="font-size:9px;color:#667;">T_WKB:</span>
        <span style="font-family:monospace;font-size:11px;color:${tColor};min-width:42px;text-align:right;">${T.toFixed(3)}</span>
        <div style="width:40px;height:4px;background:rgba(255,255,255,0.06);border-radius:2px;margin-left:4px;">
          <div style="width:${T*100}%;height:100%;background:${tColor};border-radius:2px;"></div>
        </div>
      </div>`;
    }).join('');
    const extraNodes = tNodes.filter(n => !nodes.some(nn => Math.abs(nn.level - n.level) < 1)).slice(0, 3);
    const extraHTML = extraNodes.map(n => {
      const tColor = n.T_wkb > 0.5 ? '#ff4757' : n.T_wkb > 0.2 ? '#f1c40f' : '#00ff88';
      const typeColor = n.type === 'RESISTANCE' ? '#ff4757' : '#00ff88';
      return `<div class="mmo-node-row">
        <span style="color:${typeColor};font-size:9px;min-width:24px;opacity:0.7;">${n.type === 'RESISTANCE' ? 'RES' : 'SUP'}</span>
        <span style="font-family:monospace;font-size:11px;color:#aaa;flex:1;">$${n.level}</span>
        <span style="font-size:9px;color:#667;">T:</span>
        <span style="font-family:monospace;font-size:11px;color:${tColor};min-width:42px;text-align:right;">${n.T_wkb.toFixed(3)}</span>
        <div style="width:40px;height:4px;background:rgba(255,255,255,0.06);border-radius:2px;margin-left:4px;">
          <div style="width:${n.T_wkb*100}%;height:100%;background:${tColor};border-radius:2px;"></div>
        </div>
      </div>`;
    }).join('');
    el.innerHTML = `
      <div style="display:flex;gap:16px;margin-bottom:10px;">
        <div class="mmo-heis-kpi" style="flex:1;">
          <div class="mmo-heis-val" style="color:${ampColor}">${s.amplitude?.toFixed(3) || '—'}</div>
          <div class="mmo-heis-label">Amplitude A</div>
        </div>
        <div class="mmo-heis-kpi" style="flex:1;">
          <div class="mmo-heis-val" style="color:${freqColor}">${s.frequency?.toFixed(3) || '—'}</div>
          <div class="mmo-heis-label">Frequency ω</div>
        </div>
        <div class="mmo-heis-kpi" style="flex:1;">
          <div class="mmo-heis-val" style="color:#f1fa8c">${s.vertices_30d ?? '—'}</div>
          <div class="mmo-heis-label">Vertices 30d</div>
        </div>
      </div>
      ${nodes.length || extraNodes.length ? `
      <div style="font-size:9px;color:#556;margin-bottom:5px;font-family:monospace;text-transform:uppercase;">
        Potential Nodes V(x) — WKB Tunneling T = e^(−2κa)
      </div>
      <div style="display:flex;flex-direction:column;gap:3px;">
        ${nodeHTML}${extraHTML}
      </div>
      <div style="font-size:9px;color:#334;margin-top:5px;">T→1: barrier breakout likely · T→0: wall holds</div>` : ''}
      ${_renderPathIntegral(d.path_integral)}
    `;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: ENERGY PANEL
     ═══════════════════════════════════════════════════════════════ */
  function _renderEnergy(energy) {
    const el = document.getElementById('mmo-energy-display');
    if (!el || !energy) return;

    const score = energy.score || 0;
    const fatigue = energy.fatigue || 0;
    const bubble = energy.bubble_risk || 0;
    const cooling = energy.cooling_adequacy || 0;

    function _bar(val, col) {
      return `<div class="mmo-bar-track">
        <div class="mmo-bar-fill" style="width:${Math.round(val * 100)}%;background:${col};box-shadow:0 0 5px ${col}44"></div>
      </div>`;
    }

    el.innerHTML = `
<div class="mmo-metric-row">
  <span class="mmo-metric-label">ENERGY SCORE</span>
  ${_bar(score, '#ff6b35')}
  <span class="mmo-metric-val" style="color:#ff6b35">${score.toFixed(2)}</span>
</div>
<div class="mmo-metric-row">
  <span class="mmo-metric-label">FATIGUE</span>
  ${_bar(fatigue, '#f1fa8c')}
  <span class="mmo-metric-val" style="color:#f1fa8c">${fatigue.toFixed(2)}</span>
</div>
<div class="mmo-metric-row">
  <span class="mmo-metric-label">BUBBLE RISK</span>
  ${_bar(bubble, '#ff4757')}
  <span class="mmo-metric-val" style="color:#ff4757">${bubble.toFixed(2)}</span>
</div>
<div class="mmo-metric-row">
  <span class="mmo-metric-label">COOLING</span>
  ${_bar(cooling, '#50fa7b')}
  <span class="mmo-metric-val" style="color:#50fa7b">${cooling.toFixed(2)}</span>
</div>
<div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,107,53,0.1);font-size:9px;color:#2a2a4a;font-style:italic">
  E = f(capital flow, leverage, credit) &nbsp;·&nbsp; dP/dE → 0 signals fatigue
</div>
`;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: ONTOLOGY PANEL
     ═══════════════════════════════════════════════════════════════ */
  function _renderOntology(onto) {
    const el = document.getElementById('mmo-ontology-display');
    if (!el || !onto) return;

    const rows = [
      { key: 'BEING', val: onto.being || '—' },
      { key: 'ESSENCE', val: onto.essence || '—' },
      { key: 'ENTANGLEMENT', val: onto.entanglement || '—' },
      {
        key: 'STABILITY', val: typeof onto.structural_stability === 'number'
          ? (onto.structural_stability * 100).toFixed(0) + '%' : '—'
      },
    ];

    const beingColor = {
      EXPANSION: '#00ff88', CONTRACTION: '#ff4757', TURBULENCE: '#ff9500',
      STASIS: '#4da6ff', TRANSITION: '#cc99ff', UNKNOWN: '#4a4a6a',
    }[onto.being] || '#cc99ff';

    el.innerHTML = rows.map(r => `
<div class="mmo-onto-row">
  <span class="mmo-onto-key">${r.key}</span>
  <span class="mmo-onto-val" style="${r.key === 'BEING' ? 'color:' + beingColor : ''}">${r.val}</span>
</div>`).join('');
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: ENTROPY GAUGE
     ═══════════════════════════════════════════════════════════════ */
  function _renderEntropy(entropy) {
    const el = document.getElementById('mmo-entropy-display');
    if (!el) return;

    const H = typeof entropy === 'number' ? entropy : 1.0;
    const pct = Math.round(H * 100);

    let level, desc, col, cls;
    if (H < 0.25) {
      level = 'CERTAIN'; desc = 'Collapse imminent — strong signal'; col = '#00ff88'; cls = 'entropy-certain';
    } else if (H < 0.50) {
      level = 'LOW'; desc = 'Directional signal present'; col = '#00d4ff'; cls = 'entropy-low';
    } else if (H < 0.75) {
      level = 'MODERATE'; desc = 'Mixed signals — wait for clarity'; col = '#f1fa8c'; cls = 'entropy-moderate';
    } else {
      level = 'CHAOTIC'; desc = 'High dispersion — system fragile'; col = '#ff4757'; cls = 'entropy-chaotic';
    }

    el.innerHTML = `
<div class="mmo-entropy-gauge-wrap">
  <div class="mmo-entropy-track">
    <div class="mmo-entropy-fill" style="width:${pct}%;background:linear-gradient(90deg,#7c3fe4,${col})"></div>
  </div>
  <div class="mmo-entropy-ticks">
    <span>0 CERTAIN</span><span>0.25</span><span>0.5</span><span>0.75</span><span>CHAOTIC 1</span>
  </div>
</div>
<div class="mmo-entropy-level ${cls}">${level}</div>
<div class="mmo-entropy-desc">${desc}</div>
<div style="margin-top:12px;font-size:9px;color:#2a2a4a;text-align:center;font-style:italic">
  H = ${H.toFixed(3)} &nbsp;·&nbsp; H = −Σ pᵢ log(pᵢ) / log(5)
</div>
`;
  }

  /* ═══════════════════════════════════════════════════════════════
     HELPER: PROBABILITY CURRENT FLOW CHAIN
     Renders a state-chain diagram showing the 4 inter-state
     probability currents from the j_flows array:
       BEAR →[J₀]→ SIDEWAYS →[J₁]→ VOLATILE →[J₂]→ TRENDING →[J₃]→ BULL
     Arrow thickness and color encode magnitude and direction.
     ═══════════════════════════════════════════════════════════════ */
  function _renderJFlowsChain(jFlows) {
    if (!jFlows || jFlows.length < 4) return '';

    const CHAIN = ['BEAR', 'SIDEW', 'VOLAT', 'TREND', 'BULL'];
    const CHAIN_COLORS = ['#ff4757', '#4da6ff', '#ff9500', '#cc99ff', '#00ff88'];
    const maxJ = Math.max(...jFlows.map(j => Math.abs(j)), 0.01);

    const cells = [];
    CHAIN.forEach((label, i) => {
      // State node
      cells.push(`<div class="mmo-jflow-node" style="color:${CHAIN_COLORS[i]};">${label}</div>`);
      // Arrow between nodes
      if (i < 4) {
        const j = jFlows[i];
        const norm = Math.abs(j) / maxJ;
        const h = Math.max(2, Math.round(norm * 8));          // 2–8 px height
        const col = j > 0 ? '#00ff88' : j < 0 ? '#ff4757' : '#333';
        const dir = j > 0 ? '→' : j < 0 ? '←' : '·';
        cells.push(`
          <div class="mmo-jflow-arrow" title="J${i}=${j.toFixed(4)}">
            <div class="mmo-jflow-bar" style="height:${h}px;background:${col};box-shadow:0 0 4px ${col}55;"></div>
            <span class="mmo-jflow-dir" style="color:${col};">${dir}</span>
            <span class="mmo-jflow-val">${Math.abs(j).toFixed(3)}</span>
          </div>`);
      }
    });

    return `
      <div style="margin-top:8px;">
        <div style="font-size:8px;color:#445;font-family:monospace;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">
          State Transition Currents J_{n→n+1}
        </div>
        <div class="mmo-jflow-chain">${cells.join('')}</div>
      </div>`;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: HEISENBERG UNCERTAINTY PRINCIPLE
     Δp = momentum uncertainty (proxy: volatility)
     Δx = position uncertainty (proxy: 1/trend_clarity)
     Uncertainty principle: Δp × Δx ≥ ℏ/2 = 0.5 (normalized)
     ═══════════════════════════════════════════════════════════════ */
  function _renderHeisenberg(d) {
    const el = document.getElementById('mmo-heisenberg-display');
    if (!el) return;
    const h = d.heisenberg || {};
    const qfi = d.quantum_fisher_info || {};
    const jDir = d.j_directional || 'NEUTRAL';
    const jTotal = d.probability_current_J || 0;
    const jColor = jDir === 'BULL_FLOW' ? '#00ff88' : jDir === 'BEAR_FLOW' ? '#ff4757' : '#aaa';
    const jArrow = jDir === 'BULL_FLOW' ? '▲' : jDir === 'BEAR_FLOW' ? '▼' : '→';
    const comply = h.compliant;
    const cpColor = comply ? '#00ff88' : '#ff4757';
    const qfiColor = qfi.signal_clarity === 'HIGH' ? '#00ff88' : qfi.signal_clarity === 'MEDIUM' ? '#f1c40f' : '#ff9500';
    el.innerHTML = `
      <div class="mmo-heis-grid">
        <div class="mmo-heis-kpi">
          <div class="mmo-heis-val" style="color:#bd93f9">${(h.delta_p || 0).toFixed(3)}</div>
          <div class="mmo-heis-label">Δp momentum</div>
        </div>
        <div class="mmo-heis-kpi">
          <div class="mmo-heis-val" style="color:#8be9fd">${(h.delta_x || 0).toFixed(3)}</div>
          <div class="mmo-heis-label">Δx position</div>
        </div>
        <div class="mmo-heis-kpi">
          <div class="mmo-heis-val" style="color:${cpColor}">${(h.product || 0).toFixed(3)}</div>
          <div class="mmo-heis-label">Δp·Δx ${comply ? '≥ℏ/2 ✓' : '< ℏ/2 ⚠'}</div>
        </div>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.06);margin:8px 0;padding-top:8px;">
        <div style="font-size:9px;color:#556;margin-bottom:5px;font-family:monospace;text-transform:uppercase;">Quantum Fisher Info</div>
        <div class="mmo-heis-grid">
          <div class="mmo-heis-kpi">
            <div class="mmo-heis-val" style="color:${qfiColor}">${(qfi.F_Q || 0).toFixed(3)}</div>
            <div class="mmo-heis-label">F_Q Fisher</div>
          </div>
          <div class="mmo-heis-kpi">
            <div class="mmo-heis-val" style="color:#f1fa8c">${(qfi.cramer_rao_bound || 0).toFixed(3)}</div>
            <div class="mmo-heis-label">σ_min C-R</div>
          </div>
          <div class="mmo-heis-kpi">
            <div class="mmo-heis-val" style="color:${qfiColor}">${qfi.signal_clarity || '—'}</div>
            <div class="mmo-heis-label">Clarity</div>
          </div>
        </div>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.06);margin:8px 0;padding-top:8px;">
        <div style="font-size:9px;color:#556;margin-bottom:5px;font-family:monospace;text-transform:uppercase;">Probability Current J</div>
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="font-size:20px;color:${jColor};">${jArrow}</span>
          <div>
            <div style="font-size:13px;font-weight:700;color:${jColor};font-family:monospace;">${jDir.replace('_',' ')}</div>
            <div style="font-size:10px;color:#667;">J_total = ${jTotal.toFixed(4)}</div>
          </div>
          <div style="flex:1;height:4px;background:rgba(255,255,255,0.05);border-radius:2px;margin-left:8px;">
            <div style="height:100%;width:${Math.min(Math.abs(jTotal)*200,100)}%;background:${jColor};border-radius:2px;transition:width 0.5s;"></div>
          </div>
        </div>
        ${_renderJFlowsChain(d.j_flows)}
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.06);margin:8px 0;padding-top:8px;">
        <div style="font-size:9px;color:#556;margin-bottom:4px;font-family:monospace;text-transform:uppercase;">QFI-Adjusted Position Sizing</div>
        <div style="font-size:11px;color:#bd93f9;font-family:monospace;">${h.qfi_sizing || '—'}</div>
        <div style="font-size:9px;color:#556;margin-top:3px;">ψ_survival = ${(h.psi_survival || 0).toFixed(4)} · σ_CR = ${(h.cramer_rao || 0).toFixed(4)}</div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: DECOHERENCE CLOCK
     τ = 1/(σ · H)  — time until superposition collapses
     High vol + high entropy → τ → 0 (rapid collapse)
     Low vol + low entropy → τ → ∞ (stable superposition)
     ═══════════════════════════════════════════════════════════════ */
  function _renderDecoherence(d) {
    const el = document.getElementById('mmo-decoherence-display');
    if (!el) return;
    const tau     = d.decoherence_tau      || 0;
    const thermal = d.thermal               || {};
    const cirTemp = thermal.cir_temperature || 0;
    const beta    = thermal.beta_thermal    || 0;
    const tauNorm = Math.min(1, tau / 5);
    const tauColor = tau < 0.5 ? '#ff4757' : tau < 1.5 ? '#f1c40f' : '#00ff88';
    const regime  = tau < 0.5 ? 'RAPID COLLAPSE' : tau < 1.5 ? 'MODERATE DECAY' : 'STABLE SUPERPOSITION';
    // Pulse speed: fast (0.35s) when τ near 0, slow (2.5s) when τ stable
    const pulseSpeed = tau < 0.5 ? '0.35s' : tau < 1.5 ? '0.9s' : '2.5s';
    const glowShadow = tau < 0.5 ? `0 0 14px ${tauColor}` : tau < 1.5 ? `0 0 8px ${tauColor}88` : 'none';
    const urgencyBadge = tau < 0.5
      ? `<span style="font-size:9px;background:#ff475722;border:1px solid #ff475744;color:#ff4757;padding:1px 6px;border-radius:4px;font-family:monospace;margin-left:6px;">⚠ COLLAPSING</span>`
      : tau < 1.5
      ? `<span style="font-size:9px;background:#f1c40f22;border:1px solid #f1c40f44;color:#f1c40f;padding:1px 6px;border-radius:4px;font-family:monospace;margin-left:6px;">DECAYING</span>`
      : `<span style="font-size:9px;background:#00ff8822;border:1px solid #00ff8844;color:#00ff88;padding:1px 6px;border-radius:4px;font-family:monospace;margin-left:6px;">STABLE</span>`;
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
        <div style="text-align:center;position:relative;">
          <div style="
            font-size:26px;font-weight:900;color:${tauColor};font-family:monospace;
            animation: mmo-deco-pulse ${pulseSpeed} ease-in-out infinite;
            text-shadow:${glowShadow};
            display:inline-block;
          ">${tau.toFixed(2)}</div>
          <div style="font-size:9px;color:#556;">τ (trading days)</div>
        </div>
        <div style="flex:1;">
          <div style="display:flex;align-items:center;margin-bottom:4px;">
            <div style="font-size:11px;font-weight:700;color:${tauColor};">${regime}</div>
            ${urgencyBadge}
          </div>
          <div style="height:5px;background:rgba(255,255,255,0.07);border-radius:3px;overflow:hidden;">
            <div style="height:100%;width:${tauNorm*100}%;background:${tauColor};border-radius:3px;transition:width 0.6s;box-shadow:0 0 6px ${tauColor}55;"></div>
          </div>
          <div style="font-size:9px;color:#445;margin-top:4px;font-family:monospace;">
            τ = 1/(σ_CIR × H) · Signal expires in ~${tau < 1 ? (tau * 6.5).toFixed(1) + 'h' : tau.toFixed(1) + ' days'}
          </div>
        </div>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
        <div style="font-size:9px;color:#556;margin-bottom:5px;font-family:monospace;text-transform:uppercase;">CIR Thermal State</div>
        <div class="mmo-heis-grid">
          <div class="mmo-heis-kpi">
            <div class="mmo-heis-val" style="color:#ff79c6">${cirTemp.toFixed(4)}</div>
            <div class="mmo-heis-label">T_CIR vol</div>
          </div>
          <div class="mmo-heis-kpi">
            <div class="mmo-heis-val" style="color:#f1fa8c">${beta.toFixed(2)}</div>
            <div class="mmo-heis-label">β = 1/T</div>
          </div>
          <div class="mmo-heis-kpi">
            <div class="mmo-heis-val" style="color:#8be9fd">${(d.cir_drift || 0).toFixed(4)}</div>
            <div class="mmo-heis-label">dr_CIR</div>
          </div>
        </div>
        <div style="font-size:9px;color:#445;margin-top:6px;">τ ∝ 1/(T_CIR · H) — Phase 3A coupled</div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: NON-HERMITIAN HAMILTONIAN H_eff (Phase 3C)
     H_eff = H − iΓ/2  (open quantum system)
     ε_k = E_k − iΓ_k/2  (complex eigenvalues)
     Exceptional point: eigenvalues coalesce → ε_A → ε_B
     ═══════════════════════════════════════════════════════════════ */
  function _renderNonHermitian(qs) {
    const el = document.getElementById('mmo-nh-display');
    if (!el) return;
    const nh = qs.non_hermitian;
    if (!nh) { el.innerHTML = '<div style="font-size:9px;color:#3a3a5a">—</div>'; return; }

    const P_NH    = typeof nh.P_NH    === 'number' ? nh.P_NH    : 0;
    const P_loss  = typeof nh.P_loss  === 'number' ? nh.P_loss  : 0;
    const ep_gap  = typeof nh.ep_gap  === 'number' ? nh.ep_gap  : 1;
    const near_ep = nh.near_ep || ep_gap < 0.05;
    const gamma_g = typeof nh.gamma_global === 'number' ? nh.gamma_global : 0;

    // Survival color: green = stable, yellow = decaying, red = rapid loss
    const survColor = P_NH > 0.7 ? '#00ff88' : P_NH > 0.4 ? '#f1c40f' : '#ff4757';
    // EP gap color: danger when gap is tiny (eigenvalues coalescing)
    const epColor   = near_ep ? '#ff4757' : ep_gap < 0.15 ? '#f1c40f' : '#00d4ff';

    const epBadge = near_ep
      ? `<span class="mmo-nh-ep-warning">⚡ NEAR EXCEPTIONAL POINT</span>`
      : ep_gap < 0.15
      ? `<span class="mmo-nh-ep-warning mmo-nh-ep-caution">⚠ EP PROXIMITY</span>`
      : `<span class="mmo-nh-ep-badge">EIGENVALUE SPLIT</span>`;

    // Eigenvalue rows (top 4 by probability)
    const evRows = (nh.eigenvalues || [])
      .sort((a, b) => b.p - a.p)
      .slice(0, 4)
      .map(ev => {
        const eCol = ev.E > 0.08 ? '#00ff88' : ev.E < -0.08 ? '#ff4757' : '#8be9fd';
        const gCol = ev.Gamma > 0.5 ? '#ff4757' : ev.Gamma > 0.2 ? '#f1c40f' : '#44f';
        const survPct = Math.round((ev.survival || 0) * 100);
        return `
<div class="mmo-nh-ev-row">
  <span class="mmo-nh-state" style="color:${eCol}">${ev.state}</span>
  <span class="mmo-nh-val" style="color:${eCol}" title="Real energy E_k">${ev.E >= 0 ? '+' : ''}${ev.E.toFixed(3)}</span>
  <span class="mmo-nh-val" style="color:${gCol}" title="Decay rate Γ_k">Γ=${ev.Gamma.toFixed(3)}</span>
  <span class="mmo-nh-val" style="color:#bd93f9" title="Im(ε) = -Γ/2">${ev.eps_im.toFixed(3)}i</span>
  <div class="mmo-nh-surv-track" title="Survival probability">
    <div class="mmo-nh-surv-fill" style="width:${survPct}%;background:${eCol};"></div>
  </div>
  <span class="mmo-nh-pct" style="color:${eCol}">${survPct}%</span>
</div>`;
      }).join('');

    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:9px;">
        <div style="text-align:center;">
          <div style="font-size:22px;font-weight:900;color:${survColor};font-family:monospace;
            text-shadow:0 0 10px ${survColor}88;">${(P_NH * 100).toFixed(1)}%</div>
          <div style="font-size:8px;color:#556;font-family:monospace;">P_NH survival</div>
        </div>
        <div style="flex:1;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px;">
            <div style="font-size:10px;font-weight:700;color:${survColor};">
              ${P_NH > 0.7 ? 'COHERENT' : P_NH > 0.4 ? 'LEAKING' : 'DISSIPATING'}
            </div>
            ${epBadge}
          </div>
          <div style="height:4px;background:rgba(255,255,255,0.07);border-radius:3px;overflow:hidden;">
            <div style="height:100%;width:${P_NH*100}%;background:${survColor};border-radius:3px;
              transition:width 0.6s;box-shadow:0 0 5px ${survColor}66;"></div>
          </div>
          <div style="font-size:8px;color:#445;margin-top:3px;font-family:monospace;">
            P_loss=${(P_loss*100).toFixed(1)}% · Γ_global=${gamma_g.toFixed(3)} · EP gap=${ep_gap.toFixed(4)}
          </div>
        </div>
        <div style="text-align:center;">
          <div style="font-size:16px;font-weight:700;color:${epColor};font-family:monospace;">${ep_gap.toFixed(4)}</div>
          <div style="font-size:8px;color:#556;">EP gap |Δε|</div>
        </div>
      </div>
      <div style="font-size:8px;color:#445;text-transform:uppercase;font-family:monospace;margin-bottom:4px;">
        H_eff eigenvalues — ε_k = E_k − iΓ_k/2
      </div>
      <div class="mmo-nh-ev-table">${evRows}</div>
      <div style="font-size:8px;color:#334;margin-top:5px;font-family:monospace;">
        Open system: env. coupling Γ leaks probability — Phase 3C
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: QUANTUM ENTANGLEMENT MATRIX
     Shows inter-asset correlation as quantum entanglement strength.
     Positive correlation = entangled (⊕), negative = anti-entangled (⊗)
     ═══════════════════════════════════════════════════════════════ */
  function _renderEntanglement(ticker, entanglement) {
    const el = document.getElementById('mmo-entanglement-display');
    if (!el || !entanglement) return;

    const others = Object.keys(entanglement);
    if (!others.length) {
      el.innerHTML = '<div style="font-size:9px;color:#3a3a5a;text-align:center;padding:12px">No entanglement data</div>';
      return;
    }

    const rows = others.map(other => {
      const corr = entanglement[other];
      const absPct = Math.round(Math.abs(corr) * 100);
      const isNeg = corr < 0;
      const col = isNeg
        ? '#ff4757'
        : (absPct > 70 ? '#00ff88' : absPct > 40 ? '#00d4ff' : '#f1fa8c');
      const entLevel = absPct > 80 ? 'STRONG' : absPct > 50 ? 'MOD' : absPct > 20 ? 'WEAK' : 'NONE';
      const icon = isNeg ? '⊗' : (absPct > 70 ? '⊕' : '∿');

      return `
<div class="mmo-entangle-row">
  <span class="mmo-entangle-pair">${ticker} ${icon} ${other}</span>
  <div class="mmo-entangle-track">
    <div class="mmo-entangle-fill"
         style="width:${absPct}%;background:${col};box-shadow:0 0 4px ${col}44;
                ${isNeg ? 'margin-left:auto' : ''}"></div>
  </div>
  <span class="mmo-entangle-val" style="color:${col}">${corr.toFixed(2)}</span>
  <span class="mmo-entangle-level" style="color:${col}">${entLevel}</span>
</div>`;
    }).join('');

    // ── Phase 3B: quantum state overlap |⟨ψ_A|ψ_B⟩|² ───────────────
    let overlapHtml = '';
    if (_overlapMatrix && ticker && _overlapMatrix[ticker]) {
      const overlaps = Object.entries(_overlapMatrix[ticker])
        .filter(([k]) => k !== ticker)
        .sort((a, b) => b[1] - a[1]);
      if (overlaps.length) {
        const overlapRows = overlaps.map(([other, ov]) => {
          const pct = Math.round(ov * 100);
          const col = ov > 0.85 ? '#00ff88' : ov > 0.70 ? '#00d4ff' : ov > 0.50 ? '#f1fa8c' : '#ff9500';
          return `<div class="mmo-entangle-row">
            <span class="mmo-entangle-pair" style="color:${col}">${ticker} ⊙ ${other}</span>
            <div class="mmo-entangle-track">
              <div class="mmo-entangle-fill" style="width:${pct}%;background:${col};box-shadow:0 0 4px ${col}44;"></div>
            </div>
            <span class="mmo-entangle-val" style="color:${col}">${ov.toFixed(3)}</span>
          </div>`;
        }).join('');
        overlapHtml = `
          <div style="border-top:1px solid rgba(255,255,255,0.06);margin:8px 0;padding-top:8px;">
            <div style="font-size:9px;color:#556;margin-bottom:5px;font-family:monospace;text-transform:uppercase;">
              State Fidelity |⟨ψ_A|ψ_B⟩|² — Phase 3B Quantum Overlap
            </div>
            ${overlapRows}
            <div style="margin-top:5px;font-size:9px;color:#2a2a4a;font-style:italic;">
              (Σ√(p_as·p_bs))² — 1.0=identical states · 0=orthogonal
            </div>
          </div>
        `;
      }
    }

    el.innerHTML = `
<div class="mmo-entangle-legend">
  ρ(A,B) = quantum correlation &nbsp;·&nbsp;
  ⊕ entangled &nbsp;·&nbsp; ⊗ anti-entangled &nbsp;·&nbsp; |ρ|>0.7 = STRONG
</div>
${rows}
<div style="margin-top:10px;font-size:9px;color:#2a2a4a;font-style:italic">
  Entangled pairs move together — diversification reduces entanglement energy
</div>
${overlapHtml}
`;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: 4-LAYER ECOSYSTEM
     ═══════════════════════════════════════════════════════════════ */
  function _renderLayers(layers) {
    if (!layers || !layers.length) return;
    layers.forEach(layer => {
      const fill = document.getElementById('mmo-lf-' + layer.id);
      const metric = document.getElementById('mmo-lm-' + layer.id);
      const health = document.getElementById('mmo-lh-' + layer.id);
      if (fill) fill.style.width = Math.round((layer.value || 0.5) * 100) + '%';
      if (metric) metric.textContent = layer.metric || '';
      if (health) health.textContent = layer.health || '';
    });
  }

  /* ═══════════════════════════════════════════════════════════════
     SCANNER
     ═══════════════════════════════════════════════════════════════ */
  function _loadScanner() {
    let remaining = SCAN_TICKERS.length;
    const _done = () => { if (--remaining === 0) _onAllScansLoaded(); };
    SCAN_TICKERS.forEach(t => {
      if (_scanCache[t]) {
        _renderMiniCard(t, _scanCache[t]);
        _done();
        return;
      }
      // Try API first, fall back to local computation
      _api.get('/api/mmo/quantum_state/' + t).then(d => {
        const state = _normalizeQuantumState(d, t);
        _scanCache[t] = state;
        _renderMiniCard(t, state);
        _done();
      });
    });
  }

  function _renderMiniCard(ticker, qs) {
    const id = 'mmo-mini-' + ticker.replace('-', '_');
    const el = document.getElementById(id);
    if (!el) return;

    const dominant = qs.collapsed_state || _getDominantFromAmps(qs.amplitudes);
    const verdict = qs.quantum_verdict || '?';
    const entropy = qs.entropy || 0.5;

    let vCol = '#ffaa00';
    if (verdict === 'BUY') vCol = '#00ff88';
    else if (verdict === 'SELL') vCol = '#ff4757';
    else if (verdict.includes('TREND')) vCol = '#cc99ff';
    else if (verdict.includes('HEDGE')) vCol = '#ff9500';

    const entFill = Math.round(entropy * 100);
    const entCol = entropy < 0.25 ? '#00ff88' : entropy < 0.5 ? '#00d4ff' : entropy < 0.75 ? '#f1fa8c' : '#ff4757';

    // 5-bar amplitude histogram (BULL / BEAR / SIDEWAYS / VOLATILE / TRENDING)
    const STATE_ORDER = ['BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'TRENDING'];
    const ampBars = STATE_ORDER.map(s => {
      const p = (qs.amplitudes || {})[s] || 0;
      const col = STATES[s] ? STATES[s].color : '#556';
      const h = Math.max(2, Math.round(p * 28));  // 2–28 px tall
      return `<div title="${s} ${(p*100).toFixed(0)}%" style="flex:1;height:${h}px;background:${col};border-radius:1px 1px 0 0;opacity:0.85;align-self:flex-end;"></div>`;
    }).join('');

    el.innerHTML = `
<div class="mmo-mini-ticker">${ticker}</div>
<div class="mmo-mini-state" style="color:${STATES[dominant] ? STATES[dominant].color : '#cc99ff'}">${dominant}</div>
<div class="mmo-mini-verdict" style="color:${vCol}">${verdict.replace('SUPERPOSED — ', '')}</div>
<div style="display:flex;align-items:flex-end;gap:1px;height:30px;margin:4px 0 2px;border-bottom:1px solid rgba(255,255,255,0.06);">
  ${ampBars}
</div>
<div class="mmo-mini-entropy">
  <div class="mmo-mini-entropy-fill" style="width:${entFill}%;background:${entCol}"></div>
</div>
`;
  }

  function _getDominantFromAmps(amps) {
    if (!amps) return 'BULL';
    let best = 'BULL', bestP = 0;
    Object.entries(amps).forEach(([s, p]) => { if (p > bestP) { bestP = p; best = s; } });
    return best;
  }

  /* ═══════════════════════════════════════════════════════════════
     PHASE 3B — BERRY PHASE RENDER
     Geometric phase γ acquired by |ψ⟩ as parameters (T_CIR, trend)
     traverse a closed loop in market-parameter space.
     Detects cyclical regime patterns: BULL_LOOP / BEAR_LOOP / NEUTRAL
     ═══════════════════════════════════════════════════════════════ */
  function _renderBerry(qs) {
    const el = document.getElementById('mmo-berry-display');
    if (!el || !qs) return;
    const bp = qs.berry_phase;
    if (!bp) {
      el.innerHTML = '<div style="font-size:9px;color:#3a3a5a">Berry phase requires local quantum state</div>';
      return;
    }
    const gamma    = bp.gamma;
    const gamma_pi = bp.gamma_pi;
    const cycle    = bp.regime_cycle;
    const topo     = bp.topological;
    const winding  = bp.winding;
    const cycleCol = cycle === 'BULL_LOOP' ? '#00ff88' : cycle === 'BEAR_LOOP' ? '#ff4757' : '#8be9fd';
    const cycleCls = cycle === 'BULL_LOOP' ? 'mmo-berry-cycle-bull' : cycle === 'BEAR_LOOP' ? 'mmo-berry-cycle-bear' : 'mmo-berry-cycle-neutral';
    // gauge: 0% = −π, 50% = 0, 100% = +π
    const gaugePct = Math.round(((gamma + Math.PI) / (2 * Math.PI)) * 100);
    const topoLabel = topo
      ? '<span class="mmo-berry-topo-badge">⟲ TOPOLOGICAL</span>'
      : '';
    const cycleDesc = cycle === 'BULL_LOOP'
      ? '▲ Forward rotation — regime cycling toward BULL'
      : cycle === 'BEAR_LOOP'
      ? '▼ Reverse rotation — regime cycling toward BEAR'
      : '→ No dominant rotation — neutral topology';
    el.innerHTML = `
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
        <div style="text-align:center;min-width:52px;">
          <div style="font-size:26px;font-weight:900;font-family:monospace;color:${cycleCol};">${gamma_pi >= 0 ? '+' : ''}${gamma_pi}π</div>
          <div style="font-size:8px;color:#556;letter-spacing:0.5px;text-transform:uppercase;">Berry γ</div>
        </div>
        <div style="flex:1;">
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
            <span class="mmo-berry-cycle-badge ${cycleCls}">${cycle.replace('_', ' ')}</span>
            ${topoLabel}
          </div>
          <div style="height:5px;background:rgba(255,255,255,0.07);border-radius:3px;position:relative;overflow:visible;">
            <div style="height:100%;width:${gaugePct}%;background:linear-gradient(90deg,#ff4757,${cycleCol});border-radius:3px;transition:width 0.6s;"></div>
            <div style="position:absolute;top:-3px;left:50%;transform:translateX(-50%);width:1px;height:11px;background:rgba(255,255,255,0.18);"></div>
          </div>
          <div style="display:flex;justify-content:space-between;font-size:8px;color:#334;margin-top:2px;font-family:monospace;">
            <span>−π</span><span>0</span><span>+π</span>
          </div>
        </div>
      </div>
      <div style="border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
        <div class="mmo-heis-grid">
          <div class="mmo-heis-kpi">
            <div class="mmo-heis-val" style="color:${cycleCol}">${gamma.toFixed(4)}</div>
            <div class="mmo-heis-label">γ (rad)</div>
          </div>
          <div class="mmo-heis-kpi">
            <div class="mmo-heis-val" style="color:#bd93f9">${gamma_pi >= 0 ? '+' : ''}${gamma_pi}π</div>
            <div class="mmo-heis-label">γ / π</div>
          </div>
          <div class="mmo-heis-kpi">
            <div class="mmo-heis-val" style="color:#f1fa8c">${winding >= 0 ? '+' : ''}${winding}</div>
            <div class="mmo-heis-label">Winding #</div>
          </div>
        </div>
      </div>
      <div style="margin-top:8px;font-size:9px;color:#2a2a4a;font-style:italic;">
        γ = Im log ∏⟨ψₖ|ψₖ₊₁⟩ — loop in (T_CIR, trend) space
      </div>
      <div style="margin-top:4px;font-size:9px;color:#334;">${cycleDesc}</div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════
     PHASE 3B — PATH INTEGRAL DISTRIBUTION HELPER
     Returns HTML for the Feynman K(R) return distribution bars.
     K(R) ∝ Σ_paths exp(−S/ℏ_eff) · δ(ΣΔP − R)
     S = Σ_steps (ΔP)²/(2σ²)   [Euclidean action]
     ═══════════════════════════════════════════════════════════════ */
  function _renderPathIntegral(pi) {
    if (!pi || !pi.distribution || !pi.distribution.length) return '';
    const nBins  = pi.distribution.length;
    const center = nBins / 2;
    const bars = pi.distribution.map((h, i) => {
      const dist = Math.abs(i - center) / center;
      const col  = dist < 0.25 ? '#00ff88' : dist < 0.50 ? '#00d4ff' : dist < 0.75 ? '#bd93f9' : '#ff4757';
      const ht   = Math.max(1, Math.round(h * 28));
      return `<div class="mmo-pi-bar" title="${Math.round(h*100)}%" style="height:${ht}px;background:${col};opacity:${(0.45 + h * 0.55).toFixed(2)};"></div>`;
    }).join('');
    const rangePct = (pi.range * 100).toFixed(1);
    return `
      <div style="margin-top:10px;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;">
        <div style="font-size:9px;color:#556;margin-bottom:4px;font-family:monospace;text-transform:uppercase;">
          Path Integral K(R) — Feynman Amplitude Distribution
        </div>
        <div class="mmo-pi-bars">${bars}</div>
        <div style="display:flex;justify-content:space-between;font-size:8px;color:#334;font-family:monospace;">
          <span>−${rangePct}%</span><span>Return</span><span>+${rangePct}%</span>
        </div>
        <div style="font-size:9px;color:#2a2a4a;margin-top:4px;font-style:italic;">
          K(R) = Σ exp(−S/ℏ_eff), S=Σ(ΔP)²/2σ² · ℏ=${pi.hbar_eff}
        </div>
      </div>
    `;
  }

  /* ═══════════════════════════════════════════════════════════════
     PHASE 3B — QUANTUM OVERLAP MATRIX
     |⟨ψ_A|ψ_B⟩|² = (Σ_s √(p_As · p_Bs))² for all scanner pairs.
     Higher overlap → more similar quantum state distribution.
     Computed once after all scanner states are loaded.
     ═══════════════════════════════════════════════════════════════ */
  function _computeOverlapMatrix() {
    const tickers = Object.keys(_scanCache).filter(t => _scanCache[t] && _scanCache[t].amplitudes);
    if (tickers.length < 2) return null;
    const SK = ['BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'TRENDING'];
    const matrix = {};
    tickers.forEach(A => {
      matrix[A] = {};
      const aA = _scanCache[A].amplitudes;
      tickers.forEach(B => {
        if (A === B) { matrix[A][B] = 1.000; return; }
        const aB = _scanCache[B].amplitudes;
        const ov = SK.reduce((s, k) => s + Math.sqrt((aA[k] || 0) * (aB[k] || 0)), 0);
        matrix[A][B] = Number((ov * ov).toFixed(3));
      });
    });
    return matrix;
  }

  /* Called once all scanner tickers have been loaded/cached. */
  function _onAllScansLoaded() {
    _overlapMatrix = _computeOverlapMatrix();
    if (_qState) _renderEntanglement(_qState.ticker, _qState.entanglement);
  }

  /* ═══════════════════════════════════════════════════════════════
     PHYSICS AUGMENTATION
     When the API returns real data it lacks heisenberg/decoherence/
     entanglement. Compute them from the available vol/trend fields.
     ═══════════════════════════════════════════════════════════════ */
  function _augmentWithPhysics(qs) {
    if (!qs) return qs;

    // Derive vol/trend proxies from API response fields
    const vol = typeof qs.annual_vol_pct === 'number' ? qs.annual_vol_pct / 100 : 0.20;
    const trend = typeof qs.trend_pct === 'number'
      ? Math.max(0.1, Math.min(0.9, 0.5 + qs.trend_pct / 100))
      : 0.55;

    // Heisenberg Sizing
    if (!qs.heisenberg) {
      // delta_p (momentum uncertainty) ∝ CIR stochastic drift or thermal temperature
      const delta_p = typeof qs.thermal?.temperature === 'number' ? qs.thermal.temperature : vol;

      // delta_x (position uncertainty) ∝ 1 / Probability Current |J|
      let delta_x = 1 / Math.max(0.1, trend);
      if (typeof qs.probability_current_J === 'number') {
        delta_x = qs.probability_current_J === 0 ? 5.0 : Math.min(5.0, 1.0 / Math.max(0.01, Math.abs(qs.probability_current_J * 10)));
      }

      const u_sys = delta_p * delta_x;
      qs.heisenberg = {
        delta_p,
        delta_x,
        product: u_sys,
        hbar_half: 0.5,
        compliant: u_sys >= 0.5,
        position_certainty: trend,
        momentum_certainty: Math.max(0, 1 - vol),
        sizing_suggested: `Size = [Capital × α] / √(${(u_sys || 1).toFixed(2)})`
      };
    }

    // Decoherence
    if (!qs.decoherence) {
      const entropy = typeof qs.entropy === 'number' ? qs.entropy : 0.6;
      let tau = 1 / Math.max(0.01, vol * (1 + entropy));
      if (typeof qs.decoherence_tau === 'number') tau = qs.decoherence_tau;

      let noiseFactor = Math.min(1, vol * (0.5 + entropy * 0.5));
      if (typeof qs.cir_drift === 'number') noiseFactor = Math.min(1, Math.abs(qs.cir_drift) * 10);

      qs.decoherence = {
        tau,
        tau_normalized: Math.min(1, tau / 5),
        regime: tau < 0.5 ? 'RAPID COLLAPSE' : tau < 1.5 ? 'MODERATE DECAY' : 'STABLE SUPERPOSITION',
        noise_factor: noiseFactor,
      };
    }

    // Entanglement
    if (!qs.entanglement) {
      qs.entanglement = ENTANGLE_TABLE[qs.ticker] || {};
    }

    // Phase 3B + 3C: Berry phase, path integral, Non-Hermitian — always run locally from API data
    if (!qs.berry_phase || !qs.path_integral || !qs.non_hermitian) {
      const localAugment = _computeLocalQuantumState(qs.ticker || 'SPY');
      if (!qs.berry_phase)    qs.berry_phase    = localAugment.berry_phase;
      if (!qs.path_integral)  qs.path_integral  = localAugment.path_integral;
      if (!qs.non_hermitian)  qs.non_hermitian  = localAugment.non_hermitian;
    }

    return qs;
  }

  /* ═══════════════════════════════════════════════════════════════
     FULL RENDER — called after analyze()
     ═══════════════════════════════════════════════════════════════ */
  function _renderAll(qs) {
    if (!qs) return;

    // Update wave ticker label
    const wt = document.getElementById('mmo-wave-ticker');
    if (wt) wt.textContent = qs.ticker || _ticker;

    // Update ticker input
    const inp = document.getElementById('mmo-ticker-input');
    if (inp) inp.value = qs.ticker || _ticker;

    // Update wave animation probs + tunneling
    if (qs.amplitudes && typeof _waveProbs !== 'undefined') {
      Object.assign(_waveProbs, qs.amplitudes);
    }

    // Update all panels
    _renderAmplitudes(qs.amplitudes);
    _renderQuantumState(qs);
    _renderString(qs);
    _renderEnergy(qs.energy);
    _renderOntology(qs.ontology);
    _renderEntropy(qs.entropy);
    _renderLayers(qs.layers);
    _renderHeisenberg(qs);
    _renderDecoherence(qs);
    _renderEntanglement(qs.ticker, qs.entanglement);
    _renderBerry(qs);
    _renderNonHermitian(qs);
    _renderFocusDetail(qs);

    // Update Vacuum Chamber data
    _vkRenderData.qState = qs;
    _vkRenderData.amplitudes = qs.amplitudes || null;
    if (typeof qs.tunneling_risk === 'number') {
      _vkRenderData.tunnelingRisk = qs.tunneling_risk;
      if (typeof _startWaveCanvas._setTunneling === 'function') {
        _startWaveCanvas._setTunneling(qs.tunneling_risk);
      }
    }
    if (typeof _startVacuumChamber._syncNodes === 'function') {
      _startVacuumChamber._syncNodes();
    }

    // Auto-collapse if wave already collapsed
    if (qs.collapsed_state && !_collapsed) {
      setTimeout(() => { _collapsed = true; _collapseT = 0; }, 600);
    }
  }

  /* ═══════════════════════════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════════════════════════ */

  /**
   * Analyze a ticker — try API, fall back to local quantum engine.
   */
  function analyze(ticker) {
    _ticker = (ticker || 'SPY').toUpperCase().trim();
    _collapsed = false;
    _collapseT = 0;

    // Show loading state
    const stateEl = document.getElementById('mmo-state-display');
    if (stateEl) stateEl.innerHTML = `<div class="mmo-superposed-label" style="color:#3a3a6a">Loading ψ(${_ticker})…</div>`;

    _api.get('/api/mmo/quantum_state/' + _ticker).then(qs => {
      const state = _normalizeQuantumState(qs, _ticker);
      _qState = state;
      _renderAll(state);
    });
  }

  /**
   * Force wave function collapse to dominant state.
   */
  function collapse() {
    if (!_qState) {
      // If no analysis yet, compute locally and collapse immediately
      _qState = _computeLocalQuantumState(_ticker);
      _renderAll(_qState);
    }
    _collapsed = true;
    _collapseT = 0;
    _renderQuantumState(Object.assign({}, _qState, {
      collapsed_state: _qState.collapsed_state || _getDominantState(),
      quantum_verdict: _qState.quantum_verdict,
    }));
  }

  /**
   * Reset to superposition.
   */
  function reset() {
    _collapsed = false;
    _collapseT = 0;
    if (_qState) {
      _renderQuantumState(Object.assign({}, _qState, { collapsed_state: null }));
    } else {
      const el = document.getElementById('mmo-state-display');
      if (el) el.innerHTML = `<div class="mmo-superposed-label">|ψ⟩ = Σ αᵢ|stateᵢ⟩</div>`;
    }
    // Reset vacuum chamber to uniform
    _vkRenderData.tunnelingRisk = 0.1;
    _renderFocusDetail(_qState);
  }

  /* ═══════════════════════════════════════════════════════════════
     INIT
     ═══════════════════════════════════════════════════════════════ */
  function _computeLocalQuantumState(ticker) {
    const t = (ticker || 'SPY').toUpperCase();
    const seed = t.split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0) + new Date().getDate();
    const rng = (n) => {
      const x = Math.sin(seed * n + n * 1.618033988) * 10000;
      return x - Math.floor(x);
    };
    const complex = (mag, phase) => ({ re: mag * Math.cos(phase), im: mag * Math.sin(phase) });
    const char = MARKET_CHARS[t] || { trend: 0.55, vol: 0.25, basePrice: 100 };
    const raw = {
      BULL: char.trend * (0.30 + rng(1) * 0.40),
      BEAR: (1 - char.trend) * (0.20 + rng(2) * 0.35),
      SIDEWAYS: 0.15 + rng(3) * 0.20,
      VOLATILE: char.vol * (0.20 + rng(4) * 0.30),
      TRENDING: char.trend * (0.20 + rng(5) * 0.25),
    };
    const total = Object.values(raw).reduce((acc, value) => acc + value, 0);
    const amps = {};
    Object.keys(raw).forEach(key => { amps[key] = raw[key] / total; });
    const entropy = -Object.values(amps).reduce((acc, prob) => acc + (prob > 0 ? prob * Math.log(prob) : 0), 0) / Math.log(5);

    let dom = 'BULL';
    let domP = 0;
    Object.entries(amps).forEach(([state, prob]) => {
      if (prob > domP) {
        dom = state;
        domP = prob;
      }
    });

    const last_close = Number((char.basePrice * (0.95 + rng(7) * 0.10)).toFixed(2));
    const trend_pct = Number((((char.trend - 0.5) * 40) * (0.8 + rng(8) * 0.4)).toFixed(1));
    const annual_vol_pct = Number((char.vol * 100 * (0.9 + rng(9) * 0.2)).toFixed(1));
    const cir_temperature = Number(_clamp(char.vol * (0.85 + rng(21) * 0.45), 0.01, 0.95).toFixed(4));
    const beta_thermal = Number((1 / Math.max(cir_temperature, 0.01)).toFixed(4));
    const cir_drift = Number((((rng(22) - 0.5) * char.vol * 0.18)).toFixed(4));

    const basePhases = [
      char.trend * 2.6,
      -char.trend * 2.2,
      (rng(23) - 0.5) * 0.8,
      char.vol * Math.PI * 1.3,
      Math.abs(char.trend - 0.5) * 4.2,
    ];
    const thermalFrequencies = [0.8, 0.6, 0.2, 1.2, 1.0];
    const phases = basePhases.map((phase, index) => phase + beta_thermal * thermalFrequencies[index] * 0.12);
    const stateOrder = ['BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'TRENDING'];
    const psiVec = stateOrder.map((state, index) => complex(Math.sqrt(amps[state]), phases[index]));
    const orderedStates = ['BEAR', 'SIDEWAYS', 'VOLATILE', 'TRENDING', 'BULL'];
    const orderedPsi = orderedStates.map(state => psiVec[stateOrder.indexOf(state)]);
    const probability_current_J = orderedPsi.slice(0, -1).reduce((acc, current, index) => {
      const next = orderedPsi[index + 1];
      return acc + ((current.re * next.im) - (current.im * next.re)) / 0.5;
    }, 0);
    const j_directional = probability_current_J > 0.02 ? 'BULL_FLOW' : probability_current_J < -0.02 ? 'BEAR_FLOW' : 'NEUTRAL';
    const j_flows = orderedPsi.slice(0, -1).map((psi_n, i) => {
      const psi_next = orderedPsi[i + 1];
      return Number(((psi_n.re * psi_next.im) - (psi_n.im * psi_next.re)) / 0.5);
    });

    // ── Berry Phase γ (Phase 3B) ─────────────────────────────────────
    // Geometric phase acquired by |ψ⟩ as parameters (T_CIR, trend) trace
    // a closed loop in market-parameter space. γ = Im log ∏_k ⟨ψ_k|ψ_{k+1}⟩
    // BULL_LOOP → γ > 0 (regime cycling toward bull)
    // BEAR_LOOP → γ < 0 (regime cycling toward bear)
    const _berryN   = 8;                               // loop waypoints
    const _berryRT  = cir_temperature * 0.28;           // T oscillation radius
    const _berryRtr = Math.min(char.trend * 0.18, 0.10); // trend osc. radius
    let _gRe = 1.0, _gIm = 0.0;                        // accumulator ∏⟨ψ_k|ψ_{k+1}⟩
    for (let bk = 0; bk < _berryN; bk++) {
      const _mkPsi = (theta) => {
        const T_b   = Math.max(0.01, cir_temperature + _berryRT  * Math.sin(theta));
        const tr_b  = Math.min(0.99, Math.max(0.01, char.trend   + _berryRtr * Math.cos(theta)));
        const beta_b = 1 / T_b;
        const rB = {
          BULL: tr_b * (0.30 + rng(1) * 0.40),
          BEAR: (1 - tr_b) * (0.20 + rng(2) * 0.35),
          SIDEWAYS: 0.15 + rng(3) * 0.20,
          VOLATILE: (T_b / 0.6) * (0.20 + rng(4) * 0.30),
          TRENDING: tr_b * (0.20 + rng(5) * 0.25),
        };
        const totB = Object.values(rB).reduce((a, v) => a + v, 0);
        const phB  = basePhases.map((phi0, i) => phi0 + beta_b * thermalFrequencies[i] * 0.12);
        return stateOrder.map((s, i) => {
          const mag = Math.sqrt((rB[s] || 0.001) / totB);
          return { re: mag * Math.cos(phB[i]), im: mag * Math.sin(phB[i]) };
        });
      };
      const th_k   = (2 * Math.PI * bk)       / _berryN;
      const th_kp1 = (2 * Math.PI * (bk + 1)) / _berryN;
      const pk  = _mkPsi(th_k);
      const pkp = _mkPsi(th_kp1);
      let ovRe = 0, ovIm = 0;
      pk.forEach((a, i) => {
        const b = pkp[i];
        ovRe += a.re * b.re + a.im * b.im;   // Re(⟨ψ_k|ψ_{k+1}⟩)
        ovIm += a.re * b.im - a.im * b.re;   // Im(⟨ψ_k|ψ_{k+1}⟩)
      });
      const nR = _gRe * ovRe - _gIm * ovIm;
      const nI = _gRe * ovIm + _gIm * ovRe;
      _gRe = nR; _gIm = nI;
    }
    const berry_gamma = Math.atan2(_gIm, _gRe);
    const berry_phase = {
      gamma:        Number(berry_gamma.toFixed(4)),
      gamma_pi:     Number((berry_gamma / Math.PI).toFixed(3)),
      regime_cycle: berry_gamma > 0.3 ? 'BULL_LOOP' : berry_gamma < -0.3 ? 'BEAR_LOOP' : 'NEUTRAL',
      topological:  Math.abs(berry_gamma) > Math.PI / 2,
      winding:      Number((berry_gamma / (2 * Math.PI)).toFixed(3)),
    };

    // ── Path Integral Distribution K(R) (Phase 3B) ──────────────────
    // K(R) ∝ Σ_paths exp(−S/ℏ_eff) · δ(Σ ΔP − R)
    // S = Σ_steps (ΔP)²/(2σ²)  [Euclidean / Wick-rotated action]
    const _piSteps = 5, _piPaths = 60, _piBins = 12, _piHbar = 0.2;
    const _piSigma = Math.max(0.02, char.vol / Math.sqrt(252));  // daily σ
    const _piRange = _piSigma * _piSteps * 2.8;
    const _piDist  = new Array(_piBins).fill(0);
    for (let p = 0; p < _piPaths; p++) {
      let totalR = 0, action = 0;
      for (let st = 0; st < _piSteps; st++) {
        const dP  = (rng(120 + p * _piSteps + st) - 0.5) * _piSigma * 4.4;
        action   += (dP * dP) / (2 * _piSigma * _piSigma);
        totalR   += dP;
      }
      const w   = Math.exp(-action / _piHbar);
      const bin = Math.min(_piBins - 1, Math.max(0, Math.floor((totalR + _piRange) / (2 * _piRange) * _piBins)));
      _piDist[bin] += w;
    }
    const _piMax = Math.max(..._piDist, 0.001);
    const path_integral = {
      distribution: _piDist.map(d => Number((d / _piMax).toFixed(3))),
      hbar_eff:     _piHbar,
      sigma_daily:  Number(_piSigma.toFixed(5)),
      range:        Number(_piRange.toFixed(5)),
    };

    const observableAxis = [-1, -0.5, 0, 0.5, 1];
    const meanObservable = stateOrder.reduce((acc, state, index) => acc + amps[state] * observableAxis[index], 0);
    const varianceObservable = stateOrder.reduce((acc, state, index) => {
      const delta = observableAxis[index] - meanObservable;
      return acc + amps[state] * delta * delta;
    }, 0);
    const F_Q = Number((4 * varianceObservable).toFixed(4));
    const cramer_rao_bound = Number((1 / Math.sqrt(Math.max(F_Q, 1e-6))).toFixed(4));
    const signal_clarity = F_Q > 0.5 ? 'HIGH' : F_Q > 0.2 ? 'MEDIUM' : 'LOW';
    const collapse_prob = Number(_clamp(1 - entropy + rng(24) * 0.04, 0.12, 0.99).toFixed(4));

    let quantum_verdict = 'SUPERPOSED — WAIT';
    if (collapse_prob > 0.6 && dom === 'BULL') quantum_verdict = 'BUY';
    else if (collapse_prob > 0.6 && dom === 'BEAR') quantum_verdict = 'SELL';
    else if (dom === 'VOLATILE') quantum_verdict = 'HEDGE — VOLATILITY';
    else if (dom === 'TRENDING' && amps.TRENDING > 0.30) quantum_verdict = 'TREND FOLLOW';

    const string = {
      amplitude: Number(_clamp(0.2 + char.vol * (0.5 + rng(10) * 0.5), 0, 1).toFixed(3)),
      frequency: Number(_clamp(0.3 + char.trend * (0.5 + rng(11) * 0.4), 0, 1).toFixed(3)),
      vertices_30d: Math.floor(3 + rng(12) * 10),
      nodes: [],
    };
    const basePrice = last_close;
    if (rng(13) > 0.25) string.nodes.push({ level: Number((basePrice * (1 - char.vol * 0.35)).toFixed(2)), type: 'SUPPORT' });
    if (rng(14) > 0.25) string.nodes.push({ level: Number((basePrice * (1 + char.vol * 0.35)).toFixed(2)), type: 'RESISTANCE' });
    if (!string.nodes.length) string.nodes.push({ level: Number(basePrice.toFixed(2)), type: 'SUPPORT' });

    const tunneling_nodes = string.nodes.map((node, index) => {
      const distance = Math.abs(basePrice - node.level) / Math.max(basePrice, 1);
      const barrierHeight = _clamp(0.35 + char.vol * 0.45 + rng(40 + index) * 0.25, 0.15, 0.98);
      const T_wkb = _clamp(0.85 - distance * 3.2 + char.trend * 0.15 + rng(50 + index) * 0.08, 0.05, 0.95);
      return { level: node.level, type: node.type, T_wkb: Number(T_wkb.toFixed(4)), V0: Number(barrierHeight.toFixed(3)) };
    });
    const tunneling_risk = Number(_clamp(Math.max(...tunneling_nodes.map(node => node.T_wkb), char.vol * (0.3 + rng(6) * 0.4)), 0.05, 0.98).toFixed(4));
    string.nodes = string.nodes.map(node => {
      const match = tunneling_nodes.find(candidate => candidate.level === node.level && candidate.type === node.type);
      return match ? Object.assign({}, node, { T_wkb: match.T_wkb }) : node;
    });

    const fieldStart = basePrice * (1 - char.vol * 0.9);
    const fieldEnd = basePrice * (1 + char.vol * 0.9);
    const potential_field = Array.from({ length: 36 }, (_, index) => {
      const price = fieldStart + (((fieldEnd - fieldStart) / 35) * index);
      let barrier = 0.12 + char.vol * 0.25;
      tunneling_nodes.forEach(node => {
        const width = Math.max(basePrice * Math.max(char.vol, 0.12) * 0.18, 1);
        const scaledDistance = (price - node.level) / width;
        barrier += node.V0 * Math.exp(-0.5 * scaledDistance * scaledDistance) * 0.6;
      });
      return { price: Number(price.toFixed(2)), V: Number(_clamp(barrier, 0, 1.25).toFixed(3)) };
    });

    const energy = {
      score: Number(_clamp(0.3 + char.vol * 0.4 + char.trend * 0.2 + rng(15) * 0.15, 0, 1).toFixed(3)),
      fatigue: Number(_clamp(rng(16) * (0.2 + (1 - char.trend) * 0.5), 0, 1).toFixed(3)),
      bubble_risk: Number(_clamp(char.vol > 0.3 ? 0.3 + rng(17) * 0.4 : 0.05 + rng(17) * 0.2, 0, 1).toFixed(3)),
      cooling_adequacy: Number(_clamp(0.4 + (1 - char.vol) * 0.4 + rng(18) * 0.15, 0, 1).toFixed(3)),
    };

    const beings = ['EXPANSION', 'CONTRACTION', 'TURBULENCE', 'STASIS', 'TRANSITION'];
    const being = char.trend > 0.6 ? (rng(19) > 0.4 ? 'EXPANSION' : 'TRANSITION') : char.trend < 0.45 ? (rng(19) > 0.4 ? 'CONTRACTION' : 'TURBULENCE') : beings[Math.floor(rng(19) * beings.length)];
    const structural_stability = Number(_clamp(0.4 + (1 - char.vol) * 0.5 + rng(20) * 0.1, 0, 1).toFixed(3));
    const ontology = {
      being,
      essence: `${dom.charAt(0) + dom.slice(1).toLowerCase()} Momentum Field`,
      entanglement: t === 'SPY' ? 'BROAD MARKET' : t === 'GLD' ? 'INVERSE SPY' : 'SECTOR CORR',
      structural_stability,
    };

    const tau = Number((1 / Math.max(0.01, cir_temperature * Math.max(entropy, 0.08))).toFixed(4));
    const thermal = {
      temperature: Number(_clamp(cir_temperature / 0.6, 0, 1).toFixed(3)),
      cir_temperature,
      beta_thermal,
      overheating: cir_temperature > 0.55 && trend_pct > 2,
      phase: cir_temperature < 0.18 ? 'COLD' : cir_temperature < 0.32 ? 'WARM' : cir_temperature < 0.5 ? 'HOT' : trend_pct > 2 ? 'OVERHEATING' : 'TURBULENT',
    };
    const decoherence = {
      tau,
      tau_normalized: Number(_clamp(tau / 5, 0, 1).toFixed(3)),
      regime: tau < 0.5 ? 'RAPID COLLAPSE' : tau < 1.5 ? 'MODERATE DECAY' : 'STABLE SUPERPOSITION',
      noise_factor: Number(_clamp(char.vol * (0.5 + entropy * 0.5), 0, 1).toFixed(3)),
    };

    // ── Non-Hermitian Hamiltonian H_eff (Phase 3C) ───────────────────
    // H_eff = H − iΓ/2  (open quantum system: environment coupling)
    // Complex eigenvalues: ε_k = E_k − iΓ_k/2
    //   E_k  = real energy (state momentum/return proxy)
    //   Γ_k  = state-specific decay rate (less probable → decays faster)
    // Non-Hermitian survival: P_NH(τ) = Σ_k p_k · exp(−Γ_k · τ)
    // Exceptional point: eigenvalues coalesce when |ε_A − ε_B| → 0
    const _nhE0 = { BULL: 0.20, BEAR: -0.20, SIDEWAYS: 0.00, VOLATILE: 0.10, TRENDING: 0.15 };
    const _nhGamma = decoherence.noise_factor;  // global Γ from CIR+entropy coupling
    const nh_eigenvalues = stateOrder.map(s => {
      const E_k     = _nhE0[s] || 0;
      const p_k     = amps[s]  || 0;
      const Gamma_k = Number(_clamp(_nhGamma * (1.2 - p_k), 0.01, 2.0).toFixed(4));
      const surv_k  = Number((p_k * Math.exp(-Gamma_k * tau)).toFixed(5));
      return { state: s, E: Number(E_k.toFixed(4)), Gamma: Gamma_k, eps_im: Number((-Gamma_k / 2).toFixed(4)), p: Number(p_k.toFixed(4)), survival: surv_k };
    });
    const P_NH = Number(nh_eigenvalues.reduce((s, ev) => s + ev.survival, 0).toFixed(4));
    // Exceptional point gap: distance between two dominant eigenvalue pairs
    const _nhSorted = [...nh_eigenvalues].sort((a, b) => b.p - a.p);
    const ep_gap = _nhSorted.length >= 2
      ? Number(Math.sqrt((_nhSorted[0].E - _nhSorted[1].E) ** 2 + (_nhSorted[0].Gamma - _nhSorted[1].Gamma) ** 2).toFixed(4))
      : 1.0;
    const non_hermitian = {
      gamma_global: Number(_nhGamma.toFixed(4)),
      eigenvalues:  nh_eigenvalues,
      P_NH,                                          // prob. remaining in system
      P_loss: Number((1 - P_NH).toFixed(4)),         // prob. leaked to environment
      ep_gap,                                        // exceptional point gap
      near_ep: ep_gap < 0.05,                        // coalescence warning
    };

    const delta_p = Number(char.vol.toFixed(3));
    const delta_x = Number(Math.min(5, 1 / Math.max(0.18, Math.abs(probability_current_J) * 6 + char.trend)).toFixed(3));
    const u_sys = Number((delta_p * delta_x).toFixed(3));
    const psi_survival = Number((Math.exp(-1 / Math.max(tau, 0.01))).toFixed(4));
    const sizeFactor = psi_survival / (1 + u_sys + cramer_rao_bound);
    const heisenberg = {
      delta_p,
      delta_x,
      product: u_sys,
      hbar_half: 0.5,
      compliant: u_sys >= 0.5,
      position_certainty: Number(char.trend.toFixed(3)),
      momentum_certainty: Number(Math.max(0, 1 - char.vol).toFixed(3)),
      qfi_sizing: `S = C x alpha x ${sizeFactor.toFixed(3)}`,
      psi_survival,
      cramer_rao: cramer_rao_bound,
      sizing_suggested: `Size = [Capital x alpha] / sqrt(${(u_sys || 1).toFixed(2)})`,
    };

    const layers = [
      { id: 'structure', metric: `Stability ${Math.round(structural_stability * 100)}%`, value: structural_stability, health: being },
      { id: 'energy', metric: `E=${energy.score.toFixed(2)}`, value: energy.score, health: energy.fatigue > 0.5 ? 'FATIGUED' : 'ACTIVE' },
      { id: 'thermal', metric: `T_CIR ${cir_temperature.toFixed(2)}`, value: thermal.temperature, health: thermal.phase },
      { id: 'surface', metric: `psi=${amps[dom].toFixed(2)}`, value: amps[dom], health: quantum_verdict },
    ];

    return {
      ticker: t,
      amplitudes: amps,
      entropy: Number(entropy.toFixed(4)),
      collapsed_state: collapse_prob > 0.75 ? dom : null,
      collapse_prob,
      tunneling_risk,
      quantum_verdict,
      last_close,
      trend_pct,
      annual_vol_pct,
      string,
      tunneling_nodes,
      potential_field,
      energy,
      thermal,
      ontology,
      layers,
      heisenberg,
      quantum_fisher_info: { F_Q, cramer_rao_bound, signal_clarity },
      probability_current_J: Number(probability_current_J.toFixed(4)),
      j_flows: j_flows.map(j => Number(j.toFixed(4))),
      j_directional,
      decoherence_tau: tau,
      cir_drift,
      decoherence,
      entanglement: ENTANGLE_TABLE[t] || {},
      berry_phase,
      path_integral,
      non_hermitian,
      confidence: Number((1 - entropy).toFixed(3)),
      _local: true,
    };
  }

  function _normalizeQuantumState(qs, ticker) {
    if (!qs || qs.error || !qs.last_close || !qs.amplitudes) {
      const local = _computeLocalQuantumState(ticker);
      if (qs && qs.error) local._notice = `API fallback: ${qs.error}`;
      return local;
    }
    return _augmentWithPhysics(qs);
  }

  function _buildFocusCatalog(qs) {
    const current = qs || _qState || _computeLocalQuantumState(_ticker);
    const structureLayer = (current.layers || []).find(layer => layer.id === 'structure') || {};
    const energyLayer = (current.layers || []).find(layer => layer.id === 'energy') || {};
    const thermalLayer = (current.layers || []).find(layer => layer.id === 'thermal') || {};
    const dominant = current.collapsed_state || _getDominantFromAmps(current.amplitudes || {});
    const topNode = (current.tunneling_nodes || []).slice().sort((a, b) => (b.T_wkb || 0) - (a.T_wkb || 0))[0];
    return {
      structure: {
        key: 'structure',
        accent: '#7b68ee',
        vizMode: 'structure',
        kicker: 'Layer 01 / Foundation',
        title: 'Geology / Structural Stability',
        description: 'Deep structure constrains everything above it. Stability is the bedrock score for the current ontology state.',
        facts: [
          { label: 'Stability', value: _formatPct(current.ontology?.structural_stability), accent: '#d6c7ff' },
          { label: 'Being', value: current.ontology?.being || '-', accent: '#7b68ee' },
          { label: 'Essence', value: current.ontology?.essence || '-', accent: '#bfa5ff' },
          { label: 'Health', value: structureLayer.health || '-', accent: '#8be9fd' },
        ],
        note: 'The mini-universe raises geological pillars by structural stability. Low stability means a fractured base.'
      },
      energy: {
        key: 'energy',
        accent: '#ff6b35',
        vizMode: 'energy',
        kicker: 'Layer 02 / Deep Flow',
        title: 'Subsurface / Capital Energy',
        description: 'Energy is money in motion. Fatigue, cooling, and bubble pressure determine whether the system can keep transferring force.',
        facts: [
          { label: 'Energy', value: _formatMetric(current.energy?.score), accent: '#ff8b5d' },
          { label: 'Fatigue', value: _formatMetric(current.energy?.fatigue), accent: '#f1fa8c' },
          { label: 'Cooling', value: _formatMetric(current.energy?.cooling_adequacy), accent: '#50fa7b' },
          { label: 'Bubble', value: _formatMetric(current.energy?.bubble_risk), accent: '#ff4757' },
        ],
        note: 'Particles accelerate with energy score. Bubble risk saturates the field toward red and stretches the flow membrane.'
      },
      thermal: {
        key: 'thermal',
        accent: '#00d4ff',
        vizMode: 'thermal',
        kicker: 'Layer 03 / State',
        title: 'State / Thermal Regime',
        description: 'The thermal layer couples CIR temperature into the market wave. Heat changes phase stability and collapse speed.',
        facts: [
          { label: 'Phase', value: current.thermal?.phase || '-', accent: '#8be9fd' },
          { label: 'T_CIR', value: _formatMetric(current.thermal?.cir_temperature, 4), accent: '#00d4ff' },
          { label: 'Beta', value: _formatMetric(current.thermal?.beta_thermal, 2), accent: '#f1fa8c' },
          { label: 'Tau', value: _formatMetric(current.decoherence_tau || current.decoherence?.tau, 2), accent: '#ff79c6' },
        ],
        note: 'The thermal shell twists faster in hot regimes. Short tau means faster decoherence and a more unstable wave.'
      },
      surface: {
        key: 'surface',
        accent: '#50fa7b',
        vizMode: 'surface',
        kicker: 'Layer 04 / Observable',
        title: 'Observable / Wave Collapse',
        description: 'The observable layer is the projection of the state vector. Collapse probability, current flow, and verdict sit on the surface.',
        facts: [
          { label: 'Verdict', value: current.quantum_verdict || '-', accent: '#50fa7b' },
          { label: 'Collapse', value: _formatPct(current.collapse_prob), accent: '#bd93f9' },
          { label: 'Dominant', value: dominant || '-', accent: '#ffffff' },
          { label: 'Current J', value: _formatMetric(current.probability_current_J, 4), accent: '#8be9fd' },
        ],
        note: 'The lower chamber draws the surface wave ring from amplitudes. Collapse probability expands the observable orbit.'
      },
      nodes: {
        key: 'nodes',
        accent: '#ff9500',
        vizMode: 'nodes',
        kicker: 'Barrier / WKB',
        title: 'Potential Nodes / Tunneling',
        description: 'Potential wells define support and resistance barriers. WKB transmission estimates which wall is most likely to break.',
        facts: [
          { label: 'Tunneling', value: _formatPct(current.tunneling_risk), accent: '#ff9500' },
          { label: 'Best Node', value: topNode ? `${topNode.type} ${topNode.level}` : '-', accent: '#f1fa8c' },
          { label: 'Best T', value: topNode ? _formatMetric(topNode.T_wkb, 3) : '-', accent: '#ff79c6' },
          { label: 'Vertices', value: String(current.string?.vertices_30d ?? '-'), accent: '#8be9fd' },
        ],
        note: 'Barrier spheres orbit the core. High T_wkb pulls them closer to the breach plane and brightens the membrane.'
      },
    };
  }

  function _highlightFocusControls() {
    document.querySelectorAll('.mmo-layer-row').forEach(row => {
      row.classList.toggle('is-focus', row.dataset.layer === _focusKey);
    });
    document.querySelectorAll('.mmo-example-btn').forEach(btn => {
      btn.classList.toggle('is-active', btn.dataset.focus === _focusKey);
    });
  }

  function _renderFocusDetail(qs) {
    const catalog = _buildFocusCatalog(qs);
    const focus = catalog[_focusKey] || catalog.surface;
    const detailEl = document.getElementById('mmo-layer-detail');
    if (detailEl) {
      detailEl.innerHTML = `
        <div class="mmo-detail-kicker" style="color:${focus.accent}">${focus.kicker}</div>
        <div class="mmo-detail-title">${focus.title}</div>
        <div class="mmo-detail-desc">${focus.description}</div>
        <div class="mmo-detail-facts">
          ${focus.facts.map(item => `
            <div class="mmo-detail-fact">
              <div class="mmo-detail-fact-label">${item.label}</div>
              <div class="mmo-detail-fact-value" style="color:${item.accent || focus.accent}">${item.value}</div>
            </div>
          `).join('')}
        </div>
        <div class="mmo-detail-note">${focus.note}</div>
      `;
    }
    const titleEl = document.getElementById('mmo-universe-title');
    const readoutEl = document.getElementById('mmo-universe-readout');
    if (titleEl) titleEl.textContent = focus.title;
    if (readoutEl) {
      readoutEl.innerHTML = focus.facts.map(item => `<span class="mmo-universe-chip"><strong>${item.label}</strong>${item.value}</span>`).join('');
    }
    _vkRenderData.focus = focus;
    _highlightFocusControls();
  }

  function focus(key) {
    _focusKey = ['structure', 'energy', 'thermal', 'surface', 'nodes'].includes(key) ? key : 'surface';
    _renderFocusDetail(_qState);
  }

  function launchViz(vizKey) {
    if (window.VizLab && typeof window.VizLab.launch === 'function') {
      window.__MMO_CURRENT_TICKER__ = _ticker;
      window.VizLab.launch(vizKey === 'blackhole' ? 'blackhole' : 'galaxy3d');
      return;
    }
    focus(vizKey === 'blackhole' ? 'nodes' : 'surface');
  }

  function _buildView() {
    const el = document.getElementById('view-mmo');
    if (!el || el.innerHTML.trim()) return;

    el.innerHTML = `
<div class="mmo-shell">
  <div class="mmo-header">
    <div class="mmo-brand">
      <span class="mmo-psi">psi</span>
      <span class="mmo-title">MMO</span>
      <span class="mmo-sub">Mau's Market Ontology</span>
    </div>
    <div class="mmo-controls">
      <input id="mmo-ticker-input" class="mmo-input" value="SPY" maxlength="10"
             onkeydown="if(event.key==='Enter')MMO.analyze(this.value)" />
      <button class="mmo-btn-analyze" onclick="MMO.analyze(document.getElementById('mmo-ticker-input').value)">Analyze</button>
      <button class="mmo-btn-collapse" onclick="MMO.collapse()">Collapse</button>
      <button class="mmo-btn-reset" onclick="MMO.reset()">Reset</button>
      <button class="mmo-btn-theory" onclick="MMO.showTheory()">Theory</button>
    </div>
  </div>

  <div class="mmo-layers-panel">
    <div class="mmo-layers-title">LAYERED ECOSYSTEM - Deep Structure to Observable Surface</div>
    <div class="mmo-layer-stack" id="mmo-layer-stack">
      ${LAYER_CFG.map(layer => `
      <div class="mmo-layer-row layer-${layer.id}" data-layer="${layer.id}" onclick="MMO.focus('${layer.id}')">
        <span class="mmo-layer-id">${layer.label}</span>
        <span class="mmo-layer-metric" id="mmo-lm-${layer.id}">-</span>
        <div class="mmo-layer-track">
          <div class="mmo-layer-fill" id="mmo-lf-${layer.id}" style="width:50%"></div>
        </div>
        <span class="mmo-layer-health" id="mmo-lh-${layer.id}">${layer.depth}</span>
      </div>`).join('')}
    </div>
  </div>

  <div class="mmo-hud-container">
    <div class="mmo-hud-left">
      <div class="mmo-card mmo-layer-detail-card">
        <div class="mmo-card-title" style="color:#9b8ee8">Interactive Layer Explorer</div>
        <div id="mmo-layer-detail"><div style="font-size:10px;color:#55606f;">Select a layer or example to inspect the current ontology.</div></div>
      </div>
      <div class="mmo-card mmo-energy-card">
        <div class="mmo-card-title" style="color:#ff6b35">Thermodynamics | Energy & Fatigue</div>
        <div id="mmo-energy-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
      </div>
      <div class="mmo-card mmo-ontology-card">
        <div class="mmo-card-title" style="color:#7b68ee">Market Ontology</div>
        <div id="mmo-ontology-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
      </div>
      <div class="mmo-card mmo-entropy-card">
        <div class="mmo-card-title" style="color:#00d4ff">Superposition Entropy</div>
        <div id="mmo-entropy-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
      </div>
    </div>

    <div class="mmo-hud-center">
      <div class="mmo-vacuum-title">Mini Universe | Wave and Topology</div>
      <div style="flex:1; display:flex; flex-direction:column; position:relative; padding-top:40px;">
        <div style="flex:1; position:relative; overflow:hidden; border-bottom:1px solid rgba(124, 63, 228, 0.2);">
          <canvas id="mmo-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;"></canvas>
          <div style="position:absolute;top:10px;left:15px;font-size:10px;color:#9b8ee8;font-family:monospace;letter-spacing:1px;pointer-events:none;">
             WAVE FUNCTION | psi(<span id="mmo-wave-ticker" style="color:#fff">SPY</span>)
          </div>
        </div>
        <div id="mmo-three-mount" style="flex:1; position:relative; overflow:hidden;">
          <div id="mmo-universe-hud" class="mmo-universe-hud">
            <div id="mmo-universe-title">Observable / Wave Collapse</div>
            <div id="mmo-universe-readout"></div>
          </div>
        </div>
      </div>
    </div>

    <div class="mmo-hud-right">
      <div class="mmo-card mmo-state-card">
        <div class="mmo-card-title" style="color:#50fa7b">Observable | Quantum State</div>
        <div id="mmo-state-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
        <div id="mmo-amplitudes" style="margin-top:14px;"><div style="font-size:9px;color:#3a3a5a">-</div></div>
      </div>
      <div class="mmo-card mmo-heisenberg-card">
        <div class="mmo-card-title" style="color:#bd93f9">Heisenberg Sizing | dp x dx</div>
        <div id="mmo-heisenberg-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
      </div>
      <div class="mmo-card mmo-decoherence-card">
        <div class="mmo-card-title" style="color:#ff79c6">Decoherence tau | Wave Stability</div>
        <div id="mmo-decoherence-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
      </div>
      <div class="mmo-card mmo-action-card" style="flex:1;display:flex;flex-direction:column;">
        <div class="mmo-card-title" style="color:#00ff88">Examples and 3D Launchers</div>
        <div class="mmo-example-grid">
          <button class="mmo-example-btn" data-focus="structure" onclick="MMO.focus('structure')">Geology Stability</button>
          <button class="mmo-example-btn" data-focus="energy" onclick="MMO.focus('energy')">Subsurface Energy</button>
          <button class="mmo-example-btn" data-focus="thermal" onclick="MMO.focus('thermal')">State Temperature</button>
          <button class="mmo-example-btn" data-focus="surface" onclick="MMO.focus('surface')">Observable Collapse</button>
          <button class="mmo-example-btn" data-focus="nodes" onclick="MMO.focus('nodes')">Barrier Nodes</button>
          <button class="mmo-example-btn" data-focus="surface" onclick="MMO.analyze(document.getElementById('mmo-ticker-input').value)">Refresh Data</button>
        </div>
        <div id="mmo-action-display" style="padding:0;flex:1;display:flex;flex-direction:column;justify-content:center;">
          <button class="mmo-btn-action mmo-btn-breakout" onclick="MMO.launchViz('blackhole')">[ LIQUIDITY BLACK HOLE ]</button>
          <button class="mmo-btn-action mmo-btn-hedge" onclick="MMO.launchViz('galaxy3d')">[ MARKET GALAXY 3D ]</button>
        </div>
      </div>
    </div>
  </div>

  <div class="mmo-bottom-bar">
    <div class="mmo-card mmo-string-card">
      <div class="mmo-card-title" style="color:#ff79c6">String Theory | Paths &amp; Integral</div>
      <div id="mmo-string-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
    </div>
    <div class="mmo-card mmo-berry-card">
      <div class="mmo-card-title" style="color:#bd93f9">Berry Phase γ &nbsp;|&nbsp; Regime Topology</div>
      <div id="mmo-berry-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
    </div>
    <div class="mmo-card mmo-nh-card">
      <div class="mmo-card-title" style="color:#ff5555">H<sub>eff</sub> Non-Hermitian &nbsp;|&nbsp; Open System</div>
      <div id="mmo-nh-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
    </div>
    <div class="mmo-card mmo-entanglement-card">
      <div class="mmo-card-title" style="color:#8be9fd">Entanglement Matrix &amp; Overlap</div>
      <div id="mmo-entanglement-display"><div style="font-size:9px;color:#3a3a5a">-</div></div>
    </div>
  </div>

  <div class="mmo-scanner-card mmo-card">
    <div class="mmo-card-title">Quantum Scanner - Multi-Ticker Superposition</div>
    <div class="mmo-scanner-grid" id="mmo-scanner-grid">
      ${SCAN_TICKERS.map(ticker => `
      <div class="mmo-mini-card" onclick="MMO.analyze('${ticker}')" id="mmo-mini-${ticker.replace('-', '_')}">
        <div class="mmo-mini-ticker">${ticker}</div>
        <div class="mmo-mini-loading">loading...</div>
      </div>`).join('')}
    </div>
  </div>
</div>`;

    _startWaveCanvas();
    _startVacuumChamber();
    _loadScanner();
    _renderFocusDetail(_qState);
  }

  function _startVacuumChamber() {
    if (_vacuumAnimId) cancelAnimationFrame(_vacuumAnimId);
    if (_vacuumResizeObserver) {
      _vacuumResizeObserver.disconnect();
      _vacuumResizeObserver = null;
    }

    const mount = document.getElementById('mmo-three-mount');
    if (!mount || typeof THREE === 'undefined') return;
    Array.from(mount.children).forEach(child => {
      if (child.id !== 'mmo-universe-hud') child.remove();
    });

    const W = mount.offsetWidth || 640;
    const H = mount.offsetHeight || 320;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 1000);
    camera.position.set(0, 12, 48);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.domElement.style.position = 'absolute';
    renderer.domElement.style.inset = '0';
    mount.prepend(renderer.domElement);

    _vkRenderData.vScene = scene;

    const grid = new THREE.Mesh(
      new THREE.PlaneGeometry(200, 200, 32, 32),
      new THREE.MeshBasicMaterial({ color: 0x4a3a7a, wireframe: true, transparent: true, opacity: 0.14 })
    );
    grid.rotation.x = -Math.PI / 2;
    grid.position.y = -12;
    scene.add(grid);

    const coreMat = new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.88 });
    const core = new THREE.Mesh(new THREE.IcosahedronGeometry(4.5, 1), coreMat);
    scene.add(core);

    const coreGlowMat = new THREE.MeshBasicMaterial({ color: 0xbd93f9, transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending, depthWrite: false });
    const coreGlow = new THREE.Mesh(new THREE.SphereGeometry(7.2, 28, 28), coreGlowMat);
    scene.add(coreGlow);

    const structureGroup = new THREE.Group();
    for (let i = 0; i < 12; i++) {
      const pillar = new THREE.Mesh(
        new THREE.CylinderGeometry(0.6, 0.9, 10, 6),
        new THREE.MeshBasicMaterial({ color: 0x7b68ee, transparent: true, opacity: 0.32, wireframe: true })
      );
      const angle = (Math.PI * 2 * i) / 12;
      pillar.position.set(Math.cos(angle) * 16, -7, Math.sin(angle) * 16);
      pillar.userData = { angle };
      structureGroup.add(pillar);
    }
    scene.add(structureGroup);

    const thermalShell = new THREE.Mesh(
      new THREE.TorusKnotGeometry(9, 1.5, 128, 12),
      new THREE.MeshBasicMaterial({ color: 0x00d4ff, wireframe: true, transparent: true, opacity: 0.28 })
    );
    scene.add(thermalShell);

    const membrane = new THREE.Mesh(
      new THREE.PlaneGeometry(50, 30, 18, 18),
      new THREE.MeshBasicMaterial({ color: 0xff9500, wireframe: true, transparent: true, opacity: 0.12, side: THREE.DoubleSide })
    );
    membrane.position.z = -12;
    scene.add(membrane);

    const waveSegments = 72;
    const wavePositions = new Float32Array(waveSegments * 3);
    const waveGeometry = new THREE.BufferGeometry();
    waveGeometry.setAttribute('position', new THREE.BufferAttribute(wavePositions, 3));
    const observableRing = new THREE.LineLoop(
      waveGeometry,
      new THREE.LineBasicMaterial({ color: 0x50fa7b, transparent: true, opacity: 0.85 })
    );
    scene.add(observableRing);

    const particlesGeometry = new THREE.BufferGeometry();
    const particleCount = 420;
    const particlePositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount * 3; i++) {
      particlePositions[i] = (Math.random() - 0.5) * 80;
    }
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particleMaterial = new THREE.PointsMaterial({ color: 0xffffff, size: 0.36, transparent: true, opacity: 0.42 });
    const particles = new THREE.Points(particlesGeometry, particleMaterial);
    scene.add(particles);

    const nodeGroup = new THREE.Group();
    scene.add(nodeGroup);

    const entanglementNodes = [];
    for (let i = 0; i < 5; i++) {
      const mesh = new THREE.Mesh(
        new THREE.SphereGeometry(1.4, 16, 16),
        new THREE.MeshBasicMaterial({ color: 0x8be9fd, transparent: true, opacity: 0.5 })
      );
      const line = new THREE.Line(
        new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, 0)]),
        new THREE.LineBasicMaterial({ color: 0x8be9fd, transparent: true, opacity: 0.16 })
      );
      mesh.userData = { phase: i * 1.26, radius: 20 + i * 2.6 };
      scene.add(mesh);
      scene.add(line);
      entanglementNodes.push({ mesh, line });
    }

    function clearGroup(group) {
      while (group.children.length) {
        const child = group.children.pop();
        group.remove(child);
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach(mat => mat.dispose());
          else child.material.dispose();
        }
      }
    }

    function syncNodes() {
      clearGroup(nodeGroup);
      const nodes = (_vkRenderData.qState?.tunneling_nodes || []).slice(0, 6);
      nodes.forEach((node, index) => {
        const breach = node.T_wkb || 0.15;
        const material = new THREE.MeshBasicMaterial({
          color: node.type === 'RESISTANCE' ? 0xff4757 : 0x50fa7b,
          transparent: true,
          opacity: 0.35 + breach * 0.4,
          wireframe: true,
        });
        const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.9 + breach * 1.1, 12, 12), material);
        sphere.userData = {
          radius: 12 + index * 2.2,
          phase: index * 1.1,
          baseY: node.type === 'RESISTANCE' ? 5 + breach * 7 : -5 - breach * 4,
        };
        nodeGroup.add(sphere);
      });
    }
    _startVacuumChamber._syncNodes = syncNodes;
    syncNodes();

    const cameraTargets = {
      structure: new THREE.Vector3(0, 16, 54),
      energy: new THREE.Vector3(22, 10, 50),
      thermal: new THREE.Vector3(-18, 16, 48),
      surface: new THREE.Vector3(0, 10, 44),
      nodes: new THREE.Vector3(12, 8, 40),
    };

    let tick = 0;
    function animate() {
      _vacuumAnimId = requestAnimationFrame(animate);
      tick += 0.01;
      const qs = _vkRenderData.qState || _qState || _computeLocalQuantumState(_ticker);
      const focusState = _vkRenderData.focus || _buildFocusCatalog(qs).surface;
      const focusMode = focusState.vizMode || 'surface';
      const stability = qs.ontology?.structural_stability ?? 0.5;
      const energyScore = qs.energy?.score ?? 0.5;
      const temperature = qs.thermal?.temperature ?? 0.5;
      const collapseProb = qs.collapse_prob ?? 0.5;
      const risk = qs.tunneling_risk ?? 0.1;
      const entEntries = Object.entries(qs.entanglement || {}).slice(0, entanglementNodes.length);

      core.rotation.x += 0.005;
      core.rotation.y += 0.007;
      const pulse = 1 + Math.sin(tick * 4.5) * 0.06;
      core.scale.set(pulse, pulse, pulse);
      coreGlow.scale.setScalar(1 + Math.sin(tick * 2.2) * 0.03 + collapseProb * 0.14);
      coreGlowMat.color.setStyle(focusState.accent || '#bd93f9');

      structureGroup.visible = focusMode === 'structure';
      structureGroup.children.forEach((pillar, index) => {
        const heightScale = 0.55 + stability * 2.4 + Math.sin(tick * 2 + index) * 0.06;
        pillar.scale.y = heightScale;
        pillar.position.y = -12 + (heightScale * 2.1);
      });

      thermalShell.visible = focusMode === 'thermal';
      thermalShell.rotation.x += 0.006 + temperature * 0.012;
      thermalShell.rotation.y -= 0.004 + temperature * 0.008;
      thermalShell.scale.setScalar(0.95 + temperature * 0.35 + Math.sin(tick * 3.5) * 0.04);
      thermalShell.material.opacity = 0.18 + temperature * 0.36;

      observableRing.visible = focusMode === 'surface' || focusMode === 'nodes';
      const waveBuffer = waveGeometry.attributes.position.array;
      const ampValues = [qs.amplitudes?.BULL || 0.2, qs.amplitudes?.BEAR || 0.2, qs.amplitudes?.SIDEWAYS || 0.2, qs.amplitudes?.VOLATILE || 0.2, qs.amplitudes?.TRENDING || 0.2];
      for (let i = 0; i < waveSegments; i++) {
        const angle = (Math.PI * 2 * i) / waveSegments;
        const amp = ampValues[i % ampValues.length];
        const radius = 10 + collapseProb * 7 + Math.sin(angle * 3 + tick * 2.4) * (1.2 + amp * 4);
        waveBuffer[i * 3] = Math.cos(angle) * radius;
        waveBuffer[i * 3 + 1] = Math.sin(angle * 4 + tick * 3.2) * (0.8 + amp * 4);
        waveBuffer[i * 3 + 2] = Math.sin(angle) * radius;
      }
      waveGeometry.attributes.position.needsUpdate = true;

      membrane.visible = focusMode !== 'structure';
      membrane.position.z = focusMode === 'nodes' ? -7 + Math.sin(tick * 6) * 2.2 : -12 + Math.sin(tick * 5) * risk * 4;
      membrane.material.opacity = 0.08 + risk * 0.26 + (focusMode === 'energy' ? 0.08 : 0);
      membrane.material.color.setStyle(focusMode === 'energy' ? '#ff6b35' : focusMode === 'nodes' ? '#ff9500' : '#7c3fe4');

      const positions = particlesGeometry.attributes.position.array;
      const speed = 0.16 + energyScore * 0.4 + temperature * 0.26;
      particleMaterial.color.setStyle(focusMode === 'energy' ? '#ff6b35' : focusMode === 'thermal' ? '#00d4ff' : '#ffffff');
      for (let i = 0; i < particleCount; i++) {
        positions[i * 3 + 2] -= speed;
        if (positions[i * 3 + 2] < -42) {
          positions[i * 3] = (Math.random() - 0.5) * 80;
          positions[i * 3 + 1] = (Math.random() - 0.5) * 42;
          positions[i * 3 + 2] = 42;
        }
      }
      particlesGeometry.attributes.position.needsUpdate = true;

      nodeGroup.visible = focusMode === 'nodes';
      nodeGroup.children.forEach((sphere, index) => {
        const phase = sphere.userData.phase + tick * (0.4 + risk * 0.9);
        sphere.position.x = Math.cos(phase) * sphere.userData.radius;
        sphere.position.z = Math.sin(phase) * sphere.userData.radius - 8;
        sphere.position.y = sphere.userData.baseY + Math.sin(tick * 3 + index) * 0.9;
      });

      entanglementNodes.forEach((entry, index) => {
        const corr = Math.abs(entEntries[index]?.[1] ?? 0.35);
        const isInverse = (entEntries[index]?.[1] ?? 0) < 0;
        entry.mesh.userData.phase += 0.003 + corr * 0.01;
        entry.mesh.position.x = Math.cos(entry.mesh.userData.phase) * entry.mesh.userData.radius;
        entry.mesh.position.y = Math.sin(tick * 2 + index) * (2 + corr * 4);
        entry.mesh.position.z = Math.sin(entry.mesh.userData.phase) * entry.mesh.userData.radius;
        entry.mesh.scale.setScalar(0.65 + corr * 1.3);
        entry.mesh.material.color.setStyle(isInverse ? '#ff4757' : '#8be9fd');
        entry.line.geometry.setFromPoints([core.position, entry.mesh.position.clone()]);
        entry.line.material.opacity = 0.08 + corr * 0.14;
      });

      const target = cameraTargets[focusMode] || cameraTargets.surface;
      camera.position.lerp(target, 0.03);
      camera.lookAt(0, focusMode === 'structure' ? 2 : 0, 0);
      renderer.render(scene, camera);
    }
    animate();

    _vacuumResizeObserver = new ResizeObserver(() => {
      const width = mount.offsetWidth || 640;
      const height = mount.offsetHeight || 320;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    });
    _vacuumResizeObserver.observe(mount);
  }

  function _init() {
    if (_initialized) return;
    _initialized = true;
    _buildView();

    // Hook into Atlas view switcher
    const origSwitch = window.switchView;
    if (typeof origSwitch === 'function') {
      window.switchView = function (name) {
        origSwitch(name);
        if (name === 'mmo') {
          setTimeout(() => {
            _buildView();
            if (!_qState) analyze('SPY');
          }, 50);
        }
      };
    }
  }

  // Theory Modal
  function showTheory() {
    let modal = document.getElementById('mmo-theory-modal');
    if (modal) { modal.style.display = 'flex'; return; }
    modal = document.createElement('div');
    modal.id = 'mmo-theory-modal';
    modal.className = 'mmo-theory-overlay';
    modal.innerHTML = `
      <div class="mmo-theory-panel">
        <div class="mmo-theory-header">
          <span class="mmo-theory-title">⟨ψ⟩ MMO — Física Cuántica Aplicada a Mercados</span>
          <button class="mmo-theory-close" onclick="document.getElementById('mmo-theory-modal').style.display='none'">✕</button>
        </div>
        <div class="mmo-theory-body">

          <div class="mmo-theory-section">
            <div class="mmo-theory-section-title">§1 · Amplitudes Complejas y Regla de Born</div>
            <div class="mmo-theory-formula">|ψ⟩ = ψ_BULL + ψ_BEAR + ψ_SIDEWAYS + ψ_VOLATILE + ψ_TRENDING</div>
            <div class="mmo-theory-text">
              Cada componente: <code>ψᵢ = Aᵢ · e^(iφᵢ)</code>. Regla de Born: P_i = |ψᵢ|²
            </div>
          </div>

          <div class="mmo-theory-section">
            <div class="mmo-theory-section-title">§2 · Acoplamiento Térmico CIR → Fases (Phase 3A)</div>
            <div class="mmo-theory-formula">dr = k(θ − r)dt + σ√r · dW</div>
            <div class="mmo-theory-formula">φᵢ(T) = φ₀ᵢ + β · ωᵢ · dt · 2π</div>
            <div class="mmo-theory-text">β = 1/T_CIR. Mercados calientes → β pequeño → fases más estáticas.</div>
          </div>

          <div class="mmo-theory-section">
            <div class="mmo-theory-section-title">§3 · Corriente de Probabilidad J</div>
            <div class="mmo-theory-formula">J = (iℏ/2m)(ψ∇ψ* − ψ*∇ψ)</div>
            <div class="mmo-theory-formula">J_{n→n+1} = Im(ψₙ* · ψₙ₊₁) / ℏ_market</div>
            <div class="mmo-theory-text">J_total &gt; 0: flujo hacia BULL · J_total &lt; 0: flujo hacia BEAR</div>
          </div>

          <div class="mmo-theory-section">
            <div class="mmo-theory-section-title">§4 · Pozos de Potencial V(x) y Tunneling WKB</div>
            <div class="mmo-theory-formula">T = exp(−2κa)   κ = √(2m_eff(V₀ − E)) / ℏ_eff</div>
            <div class="mmo-theory-text">ℏ_eff = ATR(14)/2 · m_eff = 1/(1+T_CIR) · E = ½·trend²/σ<br>T→1: breakout inminente · T→0: nivel sólido</div>
          </div>

          <div class="mmo-theory-section">
            <div class="mmo-theory-section-title">§5 · Información de Fisher Cuántica y Cramér-Rao</div>
            <div class="mmo-theory-formula">F_Q = 4(⟨Â²⟩ − ⟨Â⟩²)   σ_min = 1/√F_Q</div>
            <div class="mmo-theory-formula">S = Capital × α × ψ_survival / (1 + Δp·Δx + σ_CR)</div>
          </div>

          <div class="mmo-theory-section">
            <div class="mmo-theory-section-title">§6 · Decoherencia τ y Reloj de Colapso</div>
            <div class="mmo-theory-formula">τ ∝ 1/(T_CIR · H)   H = entropía de Shannon normalizada</div>
            <div class="mmo-theory-text">Cuando τ &lt; 0.5 días: prepararse para movimiento fuerte.</div>
          </div>

          <div class="mmo-theory-section">
            <div class="mmo-theory-section-title">§7 · Principio de Incerteza de Heisenberg</div>
            <div class="mmo-theory-formula">Δp · Δx ≥ ℏ/2</div>
            <div class="mmo-theory-text">Δp = σ_anual · Δx = 1/ADX_proxy<br>Si Δp·Δx &lt; 0.5: inconsistencia, reducir posición.</div>
          </div>

          <div class="mmo-theory-section">
            <div class="mmo-theory-section-title">§8 · Mapa de Capas — Deep Structure → Observable</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;">
              <div class="mmo-theory-layer-card" style="border-color:#7b68ee33">
                <div style="color:#7b68ee;font-weight:700;margin-bottom:4px;">GEOLOGY (Foundation)</div>
                <div style="font-size:10px;color:#889;">Tendencia largo plazo. Semanas/meses.</div>
              </div>
              <div class="mmo-theory-layer-card" style="border-color:#ff6b3533">
                <div style="color:#ff6b35;font-weight:700;margin-bottom:4px;">SUBSURFACE (Energy)</div>
                <div style="font-size:10px;color:#889;">Flujo de capital, fatiga, burbuja. Días.</div>
              </div>
              <div class="mmo-theory-layer-card" style="border-color:#00d4ff33">
                <div style="color:#00d4ff;font-weight:700;margin-bottom:4px;">STATE (Thermal)</div>
                <div style="font-size:10px;color:#889;">T_CIR: COLD/WARM/HOT/OVERHEATING.</div>
              </div>
              <div class="mmo-theory-layer-card" style="border-color:#50fa7b33">
                <div style="color:#50fa7b;font-weight:700;margin-bottom:4px;">OBSERVABLE (Surface)</div>
                <div style="font-size:10px;color:#889;">Función de onda colapsada. Tiempo real.</div>
              </div>
            </div>
          </div>

        </div>
      </div>
    `;
    document.body.appendChild(modal);
    modal.style.display = 'flex';
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
  }

    // Expose globally
  window.MMO = { analyze, collapse, reset, showTheory, focus, launchViz };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }

})();
