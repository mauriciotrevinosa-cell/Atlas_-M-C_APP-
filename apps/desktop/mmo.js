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
  let _ticker       = 'SPY';
  let _qState       = null;      // latest quantum state
  let _waveAnimId   = null;      // rAF id for wave canvas
  let _collapsed    = false;     // wave function collapsed?
  let _collapseT    = 0;         // collapse animation time
  let _scanCache    = {};        // ticker → qState
  let _initialized  = false;

  const SCAN_TICKERS = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'TSLA', 'GLD', 'BTC-USD'];

  /* ── State visual config ──────────────────────────────────────── */
  const STATES = {
    BULL:      { color: '#00ff88', arrow: '▲', label: 'BULL' },
    BEAR:      { color: '#ff4757', arrow: '▼', label: 'BEAR' },
    SIDEWAYS:  { color: '#4da6ff', arrow: '→', label: 'SIDEWAYS' },
    VOLATILE:  { color: '#ff9500', arrow: '◈', label: 'VOLATILE' },
    TRENDING:  { color: '#cc99ff', arrow: '↗', label: 'TRENDING' },
  };

  const LAYER_CFG = [
    { id: 'structure', label: 'GEOLOGY',    color: '#7b68ee', depth: 'FOUNDATION' },
    { id: 'energy',    label: 'SUBSURFACE', color: '#ff6b35', depth: 'DEEP' },
    { id: 'thermal',   label: 'STATE',      color: '#00d4ff', depth: 'MID' },
    { id: 'surface',   label: 'OBSERVABLE', color: '#50fa7b', depth: 'SHALLOW' },
  ];

  /* ── Market character profiles ────────────────────────────────── */
  const MARKET_CHARS = {
    'SPY':     { trend: 0.62, vol: 0.15, basePrice: 575 },
    'QQQ':     { trend: 0.65, vol: 0.20, basePrice: 490 },
    'AAPL':    { trend: 0.60, vol: 0.22, basePrice: 230 },
    'MSFT':    { trend: 0.63, vol: 0.19, basePrice: 420 },
    'NVDA':    { trend: 0.70, vol: 0.35, basePrice: 850 },
    'TSLA':    { trend: 0.50, vol: 0.45, basePrice: 285 },
    'GLD':     { trend: 0.55, vol: 0.12, basePrice: 195 },
    'BTC-USD': { trend: 0.55, vol: 0.60, basePrice: 92000 },
  };

  /* ── Entanglement table (quantum correlation matrix) ──────────── */
  const ENTANGLE_TABLE = {
    'SPY':     { 'QQQ': 0.92, 'AAPL': 0.75, 'MSFT': 0.78, 'NVDA': 0.65, 'TSLA': 0.52, 'GLD': -0.12, 'BTC-USD': 0.28 },
    'QQQ':     { 'SPY': 0.92, 'AAPL': 0.85, 'MSFT': 0.82, 'NVDA': 0.78, 'TSLA': 0.62, 'GLD': -0.18, 'BTC-USD': 0.35 },
    'AAPL':    { 'SPY': 0.75, 'QQQ': 0.85, 'MSFT': 0.72, 'NVDA': 0.55, 'TSLA': 0.45, 'GLD': -0.08, 'BTC-USD': 0.25 },
    'MSFT':    { 'SPY': 0.78, 'QQQ': 0.82, 'AAPL': 0.72, 'NVDA': 0.62, 'TSLA': 0.42, 'GLD': -0.10, 'BTC-USD': 0.22 },
    'NVDA':    { 'SPY': 0.65, 'QQQ': 0.78, 'AAPL': 0.55, 'MSFT': 0.62, 'TSLA': 0.58, 'GLD': -0.15, 'BTC-USD': 0.40 },
    'TSLA':    { 'SPY': 0.52, 'QQQ': 0.62, 'AAPL': 0.45, 'MSFT': 0.42, 'NVDA': 0.58, 'GLD': -0.05, 'BTC-USD': 0.48 },
    'GLD':     { 'SPY': -0.12, 'QQQ': -0.18, 'AAPL': -0.08, 'MSFT': -0.10, 'NVDA': -0.15, 'TSLA': -0.05, 'BTC-USD': 0.15 },
    'BTC-USD': { 'SPY': 0.28, 'QQQ': 0.35, 'AAPL': 0.25, 'MSFT': 0.22, 'NVDA': 0.40, 'TSLA': 0.48, 'GLD': 0.15 },
  };

  /* ── Tiny API helper ──────────────────────────────────────────── */
  const _api = {
    get: (path) => fetch(path).then(r => r.ok ? r.json() : null).catch(() => null),
  };

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
      BULL:     char.trend * (0.30 + rng(1) * 0.40),
      BEAR:     (1 - char.trend) * (0.20 + rng(2) * 0.35),
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

    const collapse_prob  = Math.min(0.99, 1 - entropy);
    const tunneling_risk = Math.min(0.9, char.vol * (0.3 + rng(6) * 0.4));

    // ── Quantum verdict ──────────────────────────────────────────
    let quantum_verdict = 'SUPERPOSED — WAIT';
    if (collapse_prob > 0.6 && dom === 'BULL')                    quantum_verdict = 'BUY';
    else if (collapse_prob > 0.6 && dom === 'BEAR')               quantum_verdict = 'SELL';
    else if (dom === 'VOLATILE' || tunneling_risk > 0.25)          quantum_verdict = 'HEDGE — VOLATILITY';
    else if (dom === 'TRENDING' && amps.TRENDING > 0.35)           quantum_verdict = 'TREND FOLLOW';

    // ── Price data ───────────────────────────────────────────────
    const last_close   = (char.basePrice * (0.95 + rng(7) * 0.10)).toFixed(2);
    const trend_pct    = ((char.trend - 0.5) * 40 * (0.8 + rng(8) * 0.4)).toFixed(1);
    const annual_vol_pct = (char.vol * 100 * (0.9 + rng(9) * 0.2)).toFixed(1);

    // ── String theory ────────────────────────────────────────────
    const string = {
      amplitude:   Math.min(1, 0.2 + char.vol * (0.5 + rng(10) * 0.5)),
      frequency:   Math.min(1, 0.3 + char.trend * (0.5 + rng(11) * 0.4)),
      vertices_30d: Math.floor(3 + rng(12) * 10),
      nodes: [],
    };
    const base = parseFloat(last_close);
    if (rng(13) > 0.4) string.nodes.push({ level: (base * (1 - char.vol * 0.5)).toFixed(0), type: 'SUPPORT' });
    if (rng(14) > 0.4) string.nodes.push({ level: (base * (1 + char.vol * 0.5)).toFixed(0), type: 'RESISTANCE' });

    // ── Energy ───────────────────────────────────────────────────
    const energy = {
      score:             Math.min(1, 0.3 + char.vol * 0.4 + char.trend * 0.2 + rng(15) * 0.15),
      fatigue:           Math.min(1, rng(16) * (0.2 + (1 - char.trend) * 0.5)),
      bubble_risk:       char.vol > 0.3 ? Math.min(1, 0.3 + rng(17) * 0.4) : Math.min(1, 0.05 + rng(17) * 0.2),
      cooling_adequacy:  Math.min(1, 0.4 + (1 - char.vol) * 0.4 + rng(18) * 0.15),
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
      essence:              dom.charAt(0) + dom.slice(1).toLowerCase() + ' Momentum Field',
      entanglement:         t === 'SPY' ? 'BROAD MARKET' : t === 'GLD' ? 'INVERSE SPY' : 'SECTOR CORR',
      structural_stability: Math.min(1, 0.4 + (1 - char.vol) * 0.5 + rng(20) * 0.1),
    };

    // ── Layers ───────────────────────────────────────────────────
    const layers = [
      { id: 'structure', metric: `Stability ${(ontology.structural_stability * 100).toFixed(0)}%`, value: ontology.structural_stability, health: being },
      { id: 'energy',    metric: `E=${energy.score.toFixed(2)}`,  value: energy.score,           health: energy.fatigue > 0.5 ? 'FATIGUED' : 'ACTIVE' },
      { id: 'thermal',   metric: `Vol ${annual_vol_pct}%`,        value: Math.min(1, char.vol * 2), health: dom },
      { id: 'surface',   metric: `ψ=${amps[dom].toFixed(2)}`,     value: amps[dom],              health: quantum_verdict },
    ];

    // ── Heisenberg Uncertainty Principle ─────────────────────────
    // Δp = momentum uncertainty (proxy: volatility)
    // Δx = position uncertainty (proxy: inverse trend clarity)
    const delta_p = char.vol;
    const delta_x = 1 / Math.max(0.1, char.trend);
    const heisenberg = {
      delta_p,
      delta_x,
      product:            delta_p * delta_x,
      hbar_half:          0.5,
      compliant:          (delta_p * delta_x) >= 0.5,
      position_certainty: char.trend,
      momentum_certainty: Math.max(0, 1 - char.vol),
    };

    // ── Decoherence time τ ────────────────────────────────────────
    // τ ∝ 1/(σ · H)  — high vol + high entropy → rapid collapse
    const tau = 1 / Math.max(0.01, char.vol * (1 + entropy));
    const decoherence = {
      tau,
      tau_normalized:  Math.min(1, tau / 5),
      regime:          tau < 0.5 ? 'RAPID COLLAPSE' : tau < 1.5 ? 'MODERATE DECAY' : 'STABLE SUPERPOSITION',
      noise_factor:    Math.min(1, char.vol * (0.5 + entropy * 0.5)),
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

  <!-- MAIN BODY GRID -->
  <div class="mmo-body">

    <!-- ── LEFT COL, ROW 1: Wave function ── -->
    <div class="mmo-card mmo-wave-card">
      <div class="mmo-card-title">QUANTUM WAVE FUNCTION &nbsp;|&nbsp; ψ(<span id="mmo-wave-ticker">SPY</span>)
        <span style="float:right;font-size:9px;color:#3a3a5a">Click canvas to collapse</span>
      </div>
      <canvas id="mmo-canvas" onclick="MMO.collapse()"></canvas>
      <div id="mmo-amplitudes"></div>
    </div>

    <!-- ── RIGHT COL, ROW 1: Quantum State ── -->
    <div class="mmo-card mmo-state-card">
      <div class="mmo-card-title">QUANTUM STATE</div>
      <div id="mmo-state-display">
        <div class="mmo-superposed-label">|ψ⟩ = Σ αᵢ|stateᵢ⟩</div>
        <div style="font-size:9px;color:#3a3a5a;text-align:center;margin-top:8px">Awaiting analysis…</div>
      </div>
    </div>

    <!-- ── LEFT COL, ROW 2: String Theory ── -->
    <div class="mmo-card mmo-string-card">
      <div class="mmo-card-title" style="color:#6a3a5a">STRING THEORY &nbsp;|&nbsp; Price as Vibration</div>
      <div id="mmo-string-display">
        <div style="font-size:9px;color:#3a3a5a">—</div>
      </div>
    </div>

    <!-- ── RIGHT COL, ROW 2: Ontology ── -->
    <div class="mmo-card mmo-ontology-card">
      <div class="mmo-card-title">MARKET ONTOLOGY &nbsp;<span style="color:#2a2a4a;font-size:9px">GEOLOGY LAYER</span></div>
      <div id="mmo-ontology-display">
        <div style="font-size:9px;color:#3a3a5a">—</div>
      </div>
    </div>

    <!-- ── LEFT COL, ROW 3: Energy ── -->
    <div class="mmo-card mmo-energy-card">
      <div class="mmo-card-title" style="color:#6a4a2a">ENERGY &amp; ENTROPY &nbsp;|&nbsp; Capital in Motion</div>
      <div id="mmo-energy-display">
        <div style="font-size:9px;color:#3a3a5a">—</div>
      </div>
    </div>

    <!-- ── RIGHT COL, ROW 3: Entropy gauge ── -->
    <div class="mmo-card mmo-entropy-card">
      <div class="mmo-card-title">SUPERPOSITION ENTROPY</div>
      <div id="mmo-entropy-display">
        <div style="font-size:9px;color:#3a3a5a">—</div>
      </div>
    </div>

    <!-- ── LEFT COL, ROW 4: Heisenberg Uncertainty ── -->
    <div class="mmo-card mmo-heisenberg-card">
      <div class="mmo-card-title" style="color:#bd93f9">HEISENBERG UNCERTAINTY &nbsp;|&nbsp; Δp × Δx ≥ ℏ/2</div>
      <div id="mmo-heisenberg-display">
        <div style="font-size:9px;color:#3a3a5a">—</div>
      </div>
    </div>

    <!-- ── RIGHT COL, ROW 4: Decoherence Clock ── -->
    <div class="mmo-card mmo-decoherence-card">
      <div class="mmo-card-title" style="color:#ff79c6">DECOHERENCE &nbsp;|&nbsp; Wave Stability τ</div>
      <div id="mmo-decoherence-display">
        <div style="font-size:9px;color:#3a3a5a">—</div>
      </div>
    </div>

  </div><!-- /mmo-body -->

  <!-- QUANTUM SCANNER -->
  <div class="mmo-scanner-card mmo-card">
    <div class="mmo-card-title">QUANTUM SCANNER &nbsp;—&nbsp; Multi-Ticker Superposition</div>
    <div class="mmo-scanner-grid" id="mmo-scanner-grid">
      ${SCAN_TICKERS.map(t => `
      <div class="mmo-mini-card" onclick="MMO.analyze('${t}')" id="mmo-mini-${t.replace('-','_')}">
        <div class="mmo-mini-ticker">${t}</div>
        <div class="mmo-mini-loading">loading…</div>
      </div>`).join('')}
    </div>
  </div>

  <!-- QUANTUM ENTANGLEMENT MATRIX -->
  <div class="mmo-card mmo-entanglement-card">
    <div class="mmo-card-title" style="color:#8be9fd">QUANTUM ENTANGLEMENT &nbsp;—&nbsp; Inter-Asset Correlation Field</div>
    <div id="mmo-entanglement-display">
      <div style="font-size:9px;color:#3a3a5a;text-align:center;padding:16px 0">
        Run analysis on any ticker to reveal entanglement field…
      </div>
    </div>
  </div>

</div><!-- /mmo-shell -->
`;

    _startWaveCanvas();
    _loadScanner();
  }

  /* ═══════════════════════════════════════════════════════════════
     WAVE CANVAS ANIMATION
     Shows: individual state waves, superposition sum, |ψ|² density,
     tunneling barrier visualization, collapse Dirac delta.
     ═══════════════════════════════════════════════════════════════ */
  let _waveProbs = { BULL: 0.2, BEAR: 0.2, SIDEWAYS: 0.2, VOLATILE: 0.2, TRENDING: 0.2 };

  function _startWaveCanvas() {
    if (_waveAnimId) cancelAnimationFrame(_waveAnimId);
    const canvas = document.getElementById('mmo-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let t = 0;
    let _tunnelingRisk = 0.1;  // will update from state

    function frame() {
      const W = canvas.offsetWidth;
      const H = 190;
      canvas.width  = W;
      canvas.height = H;

      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#050611';
      ctx.fillRect(0, 0, W, H);

      // Subtle grid
      ctx.strokeStyle = 'rgba(255,255,255,0.03)';
      ctx.lineWidth = 1;
      for (let x = 0; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
      for (let y = 0; y < H; y += 30) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

      const stateKeys = ['BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'TRENDING'];
      const freqs     = [1.2, 0.9, 0.5, 2.1, 1.6];
      const phases    = [0, 0.8, 1.5, 2.3, 0.3];
      const midY      = H * 0.42;
      const maxAmp    = H * 0.17;

      if (!_collapsed) {
        // ── Tunneling barrier (±1σ walls) ───────────────────────
        if (_tunnelingRisk > 0.05) {
          const barrierAlpha = Math.min(0.35, _tunnelingRisk);
          const barrierW = 4;
          const barrierTop = midY - maxAmp * 1.8;
          const barrierBot = midY + maxAmp * 1.8;

          // Left barrier
          ctx.fillStyle = `rgba(255, 149, 0, ${barrierAlpha * 0.6})`;
          ctx.fillRect(W * 0.22, barrierTop, barrierW, barrierBot - barrierTop);
          // Right barrier
          ctx.fillRect(W * 0.78, barrierTop, barrierW, barrierBot - barrierTop);

          // Tunneling leak glow
          const glowR = Math.floor(_tunnelingRisk * 255).toString(16).padStart(2,'0');
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

        // ── Individual state waves ───────────────────────────────
        stateKeys.forEach((s, i) => {
          const prob = _waveProbs[s] || 0.2;
          const amp  = Math.sqrt(prob) * maxAmp;
          const col  = STATES[s].color;

          ctx.beginPath();
          ctx.strokeStyle = col + '55';
          ctx.lineWidth = 1.5;
          for (let x = 0; x <= W; x += 2) {
            const nx = x / W * Math.PI * 4;
            const y  = midY + Math.sin(nx * freqs[i] + t * (0.6 + i * 0.15) + phases[i]) * amp;
            if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          }
          ctx.stroke();
        });

        // ── Superposition sum wave (interference) ───────────────
        const sumY_arr = [];
        for (let x = 0; x <= W; x += 2) {
          const nx = x / W * Math.PI * 4;
          let sumY = 0;
          stateKeys.forEach((s, i) => {
            const prob = _waveProbs[s] || 0.2;
            const amp  = Math.sqrt(prob) * maxAmp;
            sumY += Math.sin(nx * freqs[i] + t * (0.6 + i * 0.15) + phases[i]) * amp * 0.5;
          });
          sumY_arr.push(midY + sumY);
        }

        ctx.beginPath();
        ctx.strokeStyle = 'rgba(255,255,255,0.30)';
        ctx.lineWidth = 2.5;
        sumY_arr.forEach((y, i) => { if (i === 0) ctx.moveTo(i * 2, y); else ctx.lineTo(i * 2, y); });
        ctx.stroke();

        // ── |ψ|² probability density shading ───────────────────
        // Fill between wave and axis with gradient based on amplitude
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

        // ── Label ────────────────────────────────────────────────
        ctx.font = '10px monospace';
        ctx.fillStyle = '#4a3a7a';
        ctx.textAlign = 'left';
        ctx.fillText('|ψ⟩ = SUPERPOSITION', 10, H - 10);
        ctx.fillStyle = '#2a2a5a';
        ctx.fillText('|ψ|² = probability density', 10, H - 22);

      } else {
        // ── COLLAPSED — Dirac delta spike ────────────────────────
        _collapseT += 0.05;
        const dominant = _getDominantState();
        const col = STATES[dominant] ? STATES[dominant].color : '#cc99ff';

        // Expanding rings (measurement disturbance)
        const ring = Math.abs(Math.sin(_collapseT * 3));
        for (let r = 10; r < 90; r += 20) {
          ctx.strokeStyle = col + Math.floor(ring * 50).toString(16).padStart(2, '0');
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.arc(W / 2, midY, r * (1 + ring * 0.3), 0, Math.PI * 2);
          ctx.stroke();
        }

        // Delta spike with glow
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

        // Arrowhead at tip
        ctx.fillStyle = col;
        ctx.beginPath();
        ctx.moveTo(W / 2,    midY - spikeH);
        ctx.lineTo(W / 2 - 6, midY - spikeH + 12);
        ctx.lineTo(W / 2 + 6, midY - spikeH + 12);
        ctx.closePath();
        ctx.fill();

        // Collapsed label
        ctx.font = 'bold 13px monospace';
        ctx.fillStyle = col;
        ctx.textAlign = 'center';
        ctx.shadowColor = col;
        ctx.shadowBlur = 8;
        ctx.fillText('⟩ COLLAPSED → ' + dominant, W / 2, H - 14);
        ctx.shadowBlur = 0;

        ctx.font = '9px monospace';
        ctx.fillStyle = '#4a3a7a';
        ctx.fillText('δ(state − ' + dominant + ')', W / 2, H - 26);
        ctx.textAlign = 'left';
      }

      // Axis line
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

    // Allow external update of tunneling risk
    _startWaveCanvas._setTunneling = (v) => { _tunnelingRisk = v; };
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
      const p   = amplitudes[s] || 0;
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

    const verdict  = qs.quantum_verdict || 'SUPERPOSED — WAIT';
    const colProb  = Math.round((qs.collapse_prob || 0) * 100);
    const tunnPct  = Math.round((qs.tunneling_risk || 0) * 100);
    const isCollapsed = !!qs.collapsed_state;

    let verdictClass = 'mmo-verdict-wait';
    if (verdict === 'BUY')                verdictClass = 'mmo-verdict-buy';
    else if (verdict === 'SELL')          verdictClass = 'mmo-verdict-sell';
    else if (verdict.includes('TREND'))   verdictClass = 'mmo-verdict-trend';
    else if (verdict.includes('HEDGE'))   verdictClass = 'mmo-verdict-hedge';

    let tunnClass = 'mmo-tunnel-low';
    if (tunnPct > 12)     tunnClass = 'mmo-tunnel-high';
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
  &nbsp;<span style="color:${(qs.trend_pct||0) >= 0 ? '#00ff88' : '#ff4757'};font-weight:700">
    ${(qs.trend_pct||0) >= 0 ? '+' : ''}${qs.trend_pct}%
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
  function _renderString(str) {
    const el = document.getElementById('mmo-string-display');
    if (!el || !str) return;

    const amp   = str.amplitude || 0;
    const freq  = str.frequency || 0;
    const verts = str.vertices_30d || 0;
    const nodes = str.nodes || [];

    const nodeHtml = nodes.length > 0
      ? `<div class="mmo-nodes-row">
          <span style="font-size:9px;color:#4a3a7a;margin-right:4px">NODES</span>
          ${nodes.map(n => `
          <span class="mmo-node-pill mmo-node-${n.type.toLowerCase()}">
            $${n.level}&nbsp;&nbsp;${n.type}
          </span>`).join('')}
        </div>`
      : '';

    el.innerHTML = `
<div class="mmo-metric-row">
  <span class="mmo-metric-label">AMPLITUDE</span>
  <div class="mmo-bar-track">
    <div class="mmo-bar-fill" style="width:${Math.round(amp*100)}%;background:#ff79c6;box-shadow:0 0 6px #ff79c644"></div>
  </div>
  <span class="mmo-metric-val" style="color:#ff79c6">${amp.toFixed(2)}</span>
</div>
<div class="mmo-metric-row">
  <span class="mmo-metric-label">FREQUENCY</span>
  <div class="mmo-bar-track">
    <div class="mmo-bar-fill" style="width:${Math.round(freq*100)}%;background:#9b8ee8;box-shadow:0 0 6px #9b8ee844"></div>
  </div>
  <span class="mmo-metric-val" style="color:#9b8ee8">${freq.toFixed(2)}</span>
</div>
<div style="margin-top:10px;display:flex;align-items:center;gap:10px">
  <span style="font-size:9px;color:#4a3a7a;text-transform:uppercase;letter-spacing:.07em">Vertices (30d)</span>
  <span class="mmo-vertex-badge">⚡ ${verts} event${verts !== 1 ? 's' : ''}</span>
  <span style="font-size:9px;color:#2a2a4a;margin-left:4px">energy transfer points</span>
</div>
${nodeHtml}
<div style="margin-top:10px;font-size:9px;color:#2a2a4a;font-style:italic">
  charts = projection(vibration) &nbsp;·&nbsp; trend = interference pattern
</div>
`;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: ENERGY PANEL
     ═══════════════════════════════════════════════════════════════ */
  function _renderEnergy(energy) {
    const el = document.getElementById('mmo-energy-display');
    if (!el || !energy) return;

    const score   = energy.score           || 0;
    const fatigue = energy.fatigue         || 0;
    const bubble  = energy.bubble_risk     || 0;
    const cooling = energy.cooling_adequacy|| 0;

    function _bar(val, col) {
      return `<div class="mmo-bar-track">
        <div class="mmo-bar-fill" style="width:${Math.round(val*100)}%;background:${col};box-shadow:0 0 5px ${col}44"></div>
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
      { key: 'BEING',        val: onto.being       || '—' },
      { key: 'ESSENCE',      val: onto.essence     || '—' },
      { key: 'ENTANGLEMENT', val: onto.entanglement|| '—' },
      { key: 'STABILITY',    val: typeof onto.structural_stability === 'number'
                                   ? (onto.structural_stability * 100).toFixed(0) + '%' : '—' },
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
      level = 'CERTAIN';  desc = 'Collapse imminent — strong signal';   col = '#00ff88'; cls = 'entropy-certain';
    } else if (H < 0.50) {
      level = 'LOW';      desc = 'Directional signal present';          col = '#00d4ff'; cls = 'entropy-low';
    } else if (H < 0.75) {
      level = 'MODERATE'; desc = 'Mixed signals — wait for clarity';    col = '#f1fa8c'; cls = 'entropy-moderate';
    } else {
      level = 'CHAOTIC';  desc = 'High dispersion — system fragile';   col = '#ff4757'; cls = 'entropy-chaotic';
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
     RENDER: HEISENBERG UNCERTAINTY PRINCIPLE
     Δp = momentum uncertainty (proxy: volatility)
     Δx = position uncertainty (proxy: 1/trend_clarity)
     Uncertainty principle: Δp × Δx ≥ ℏ/2 = 0.5 (normalized)
     ═══════════════════════════════════════════════════════════════ */
  function _renderHeisenberg(h) {
    const el = document.getElementById('mmo-heisenberg-display');
    if (!el || !h) return;

    const dpPct   = Math.min(100, Math.round(h.delta_p * 100));
    const dxPct   = Math.min(100, Math.round(Math.min(1, h.delta_x / 5) * 100));
    const prodPct = Math.min(100, Math.round(h.product * 100));
    const compliantCol = h.compliant ? '#00ff88' : '#ff4757';
    const compliantLabel = h.compliant ? 'PRINCIPLE SATISFIED ✓' : 'VIOLATION DETECTED ✗';

    el.innerHTML = `
<div class="mmo-heisenberg-desc">
  Δp = momentum uncertainty (volatility) &nbsp;·&nbsp; Δx = position uncertainty (1/trend)
</div>
<div class="mmo-metric-row">
  <span class="mmo-metric-label">Δp (momentum unc.)</span>
  <div class="mmo-bar-track">
    <div class="mmo-bar-fill" style="width:${dpPct}%;background:#bd93f9;box-shadow:0 0 5px #bd93f944"></div>
  </div>
  <span class="mmo-metric-val" style="color:#bd93f9">${h.delta_p.toFixed(3)}</span>
</div>
<div class="mmo-metric-row">
  <span class="mmo-metric-label">Δx (position unc.)</span>
  <div class="mmo-bar-track">
    <div class="mmo-bar-fill" style="width:${dxPct}%;background:#ff79c6;box-shadow:0 0 5px #ff79c644"></div>
  </div>
  <span class="mmo-metric-val" style="color:#ff79c6">${h.delta_x.toFixed(3)}</span>
</div>
<div class="mmo-metric-row">
  <span class="mmo-metric-label">Δp × Δx</span>
  <div class="mmo-bar-track">
    <div class="mmo-bar-fill" style="width:${prodPct}%;background:${compliantCol};box-shadow:0 0 5px ${compliantCol}44"></div>
  </div>
  <span class="mmo-metric-val" style="color:${compliantCol}">${h.product.toFixed(3)}</span>
</div>
<div class="mmo-heisenberg-badge" style="border-color:${compliantCol}44;background:${compliantCol}08">
  <span style="font-size:11px;color:${compliantCol};font-weight:700">${compliantLabel}</span>
  <span style="font-size:9px;color:#4a4a6a">ℏ/2 = 0.500</span>
  <div>
    <div style="font-size:9px;color:#4a3a7a">position certainty: <span style="color:#cc99ff">${(h.position_certainty * 100).toFixed(0)}%</span></div>
    <div style="font-size:9px;color:#4a3a7a">momentum certainty: <span style="color:#cc99ff">${(h.momentum_certainty * 100).toFixed(0)}%</span></div>
  </div>
</div>
<div style="margin-top:8px;font-size:9px;color:#2a2a4a;font-style:italic">
  Trading insight: you can't know BOTH direction AND timing simultaneously
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
    if (!el || !d) return;

    const tauPct  = Math.round(d.tau_normalized * 100);
    let regimeCol = '#00ff88';
    if (d.regime === 'RAPID COLLAPSE')        regimeCol = '#ff4757';
    else if (d.regime === 'MODERATE DECAY')   regimeCol = '#f1fa8c';

    const noisePct = Math.round(d.noise_factor * 100);

    el.innerHTML = `
<div style="text-align:center;margin-bottom:12px">
  <div class="mmo-tau-display" style="color:${regimeCol};text-shadow:0 0 20px ${regimeCol}44">
    τ = ${d.tau.toFixed(3)}
  </div>
  <div style="font-size:9px;color:#4a3a7a;margin-top:3px">decoherence time (inverse-vol-entropy)</div>
</div>
<div class="mmo-metric-row">
  <span class="mmo-metric-label">τ STABILITY</span>
  <div class="mmo-bar-track">
    <div class="mmo-bar-fill" style="width:${tauPct}%;background:${regimeCol};box-shadow:0 0 6px ${regimeCol}44"></div>
  </div>
  <span class="mmo-metric-val" style="color:${regimeCol}">${tauPct}%</span>
</div>
<div class="mmo-metric-row">
  <span class="mmo-metric-label">NOISE FACTOR</span>
  <div class="mmo-bar-track">
    <div class="mmo-bar-fill" style="width:${noisePct}%;background:#ff79c6;box-shadow:0 0 5px #ff79c644"></div>
  </div>
  <span class="mmo-metric-val" style="color:#ff79c6">${d.noise_factor.toFixed(3)}</span>
</div>
<div style="margin-top:10px;padding:8px 12px;border:1px solid ${regimeCol}33;border-radius:4px;text-align:center;background:${regimeCol}06">
  <span style="font-size:11px;font-weight:700;color:${regimeCol}">${d.regime}</span>
</div>
<div style="margin-top:8px;font-size:9px;color:#2a2a4a;font-style:italic;text-align:center">
  τ ∝ 1/(σ·H) &nbsp;·&nbsp; low τ → state collapses → direction resolved
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
      const corr    = entanglement[other];
      const absPct  = Math.round(Math.abs(corr) * 100);
      const isNeg   = corr < 0;
      const col     = isNeg
        ? '#ff4757'
        : (absPct > 70 ? '#00ff88' : absPct > 40 ? '#00d4ff' : '#f1fa8c');
      const entLevel = absPct > 80 ? 'STRONG' : absPct > 50 ? 'MOD' : absPct > 20 ? 'WEAK' : 'NONE';
      const icon     = isNeg ? '⊗' : (absPct > 70 ? '⊕' : '∿');

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

    el.innerHTML = `
<div class="mmo-entangle-legend">
  ρ(A,B) = quantum correlation &nbsp;·&nbsp;
  ⊕ entangled &nbsp;·&nbsp; ⊗ anti-entangled &nbsp;·&nbsp; |ρ|>0.7 = STRONG
</div>
${rows}
<div style="margin-top:10px;font-size:9px;color:#2a2a4a;font-style:italic">
  Entangled pairs move together — diversification reduces entanglement energy
</div>
`;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: 4-LAYER ECOSYSTEM
     ═══════════════════════════════════════════════════════════════ */
  function _renderLayers(layers) {
    if (!layers || !layers.length) return;
    layers.forEach(layer => {
      const fill   = document.getElementById('mmo-lf-' + layer.id);
      const metric = document.getElementById('mmo-lm-' + layer.id);
      const health = document.getElementById('mmo-lh-' + layer.id);
      if (fill)   fill.style.width   = Math.round((layer.value || 0.5) * 100) + '%';
      if (metric) metric.textContent = layer.metric || '';
      if (health) health.textContent = layer.health || '';
    });
  }

  /* ═══════════════════════════════════════════════════════════════
     SCANNER
     ═══════════════════════════════════════════════════════════════ */
  function _loadScanner() {
    SCAN_TICKERS.forEach(t => {
      if (_scanCache[t]) {
        _renderMiniCard(t, _scanCache[t]);
        return;
      }
      // Try API first, fall back to local computation
      _api.get('/api/mmo/quantum_state/' + t).then(d => {
        const state = d || _computeLocalQuantumState(t);
        _scanCache[t] = state;
        _renderMiniCard(t, state);
      });
    });
  }

  function _renderMiniCard(ticker, qs) {
    const id = 'mmo-mini-' + ticker.replace('-', '_');
    const el = document.getElementById(id);
    if (!el) return;

    const dominant = qs.collapsed_state || _getDominantFromAmps(qs.amplitudes);
    const verdict  = qs.quantum_verdict || '?';
    const entropy  = qs.entropy || 0.5;

    let vCol = '#ffaa00';
    if (verdict === 'BUY')              vCol = '#00ff88';
    else if (verdict === 'SELL')        vCol = '#ff4757';
    else if (verdict.includes('TREND')) vCol = '#cc99ff';
    else if (verdict.includes('HEDGE')) vCol = '#ff9500';

    const entFill = Math.round(entropy * 100);
    const entCol  = entropy < 0.25 ? '#00ff88' : entropy < 0.5 ? '#00d4ff' : entropy < 0.75 ? '#f1fa8c' : '#ff4757';

    el.innerHTML = `
<div class="mmo-mini-ticker">${ticker}</div>
<div class="mmo-mini-state" style="color:${STATES[dominant] ? STATES[dominant].color : '#cc99ff'}">${dominant}</div>
<div class="mmo-mini-verdict" style="color:${vCol}">${verdict.replace('SUPERPOSED — ', '')}</div>
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
     PHYSICS AUGMENTATION
     When the API returns real data it lacks heisenberg/decoherence/
     entanglement. Compute them from the available vol/trend fields.
     ═══════════════════════════════════════════════════════════════ */
  function _augmentWithPhysics(qs) {
    if (!qs) return qs;

    // Derive vol/trend proxies from API response fields
    const vol   = typeof qs.annual_vol_pct === 'number' ? qs.annual_vol_pct / 100 : 0.20;
    const trend = typeof qs.trend_pct      === 'number'
      ? Math.max(0.1, Math.min(0.9, 0.5 + qs.trend_pct / 100))
      : 0.55;

    // Heisenberg
    if (!qs.heisenberg) {
      const delta_p = vol;
      const delta_x = 1 / Math.max(0.1, trend);
      qs.heisenberg = {
        delta_p,
        delta_x,
        product:            delta_p * delta_x,
        hbar_half:          0.5,
        compliant:          (delta_p * delta_x) >= 0.5,
        position_certainty: trend,
        momentum_certainty: Math.max(0, 1 - vol),
      };
    }

    // Decoherence
    if (!qs.decoherence) {
      const entropy = typeof qs.entropy === 'number' ? qs.entropy : 0.6;
      const tau     = 1 / Math.max(0.01, vol * (1 + entropy));
      qs.decoherence = {
        tau,
        tau_normalized:  Math.min(1, tau / 5),
        regime:          tau < 0.5 ? 'RAPID COLLAPSE' : tau < 1.5 ? 'MODERATE DECAY' : 'STABLE SUPERPOSITION',
        noise_factor:    Math.min(1, vol * (0.5 + entropy * 0.5)),
      };
    }

    // Entanglement
    if (!qs.entanglement) {
      qs.entanglement = ENTANGLE_TABLE[qs.ticker] || {};
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

    // Update all panels
    _renderAmplitudes(qs.amplitudes);
    _renderQuantumState(qs);
    _renderString(qs.string);
    _renderEnergy(qs.energy);
    _renderOntology(qs.ontology);
    _renderEntropy(qs.entropy);
    _renderLayers(qs.layers);
    _renderHeisenberg(qs.heisenberg);
    _renderDecoherence(qs.decoherence);
    _renderEntanglement(qs.ticker, qs.entanglement);

    // Update wave animation probs + tunneling
    if (qs.amplitudes) {
      Object.assign(_waveProbs, qs.amplitudes);
    }
    if (_startWaveCanvas._setTunneling && typeof qs.tunneling_risk === 'number') {
      _startWaveCanvas._setTunneling(qs.tunneling_risk);
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
      // Fallback: compute locally if API unavailable
      const state = qs ? _augmentWithPhysics(qs) : _computeLocalQuantumState(_ticker);
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
      quantum_verdict:  _qState.quantum_verdict,
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
    // Reset wave probs to uniform
    Object.keys(_waveProbs).forEach(k => { _waveProbs[k] = 0.2; });
    if (_startWaveCanvas._setTunneling) _startWaveCanvas._setTunneling(0.1);
  }

  /* ═══════════════════════════════════════════════════════════════
     INIT
     ═══════════════════════════════════════════════════════════════ */
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

  // Expose globally
  window.MMO = { analyze, collapse, reset };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }

})();
