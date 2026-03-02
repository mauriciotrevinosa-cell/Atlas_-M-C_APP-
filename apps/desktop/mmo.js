/**
 * MMO — Mau's Market Ontology
 * Multi-scale financial ecosystem viewed through physics lenses:
 *   · Quantum Layer  — superposition, wave collapse, Born rule, tunneling
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
  let _qState       = null;      // latest API response
  let _waveAnimId   = null;      // rAF id for wave canvas
  let _layerAnimId  = null;      // rAF id for layer panel
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

  /* ── Tiny API helper ──────────────────────────────────────────── */
  const _api = {
    get: (path) => fetch(path).then(r => r.ok ? r.json() : null).catch(() => null),
  };

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
      <button class="mmo-btn-analyze" onclick="MMO.analyze(document.getElementById('mmo-ticker-input').value)">⟩ Analyze</button>
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

</div><!-- /mmo-shell -->
`;

    _startWaveCanvas();
    _loadScanner();
  }

  /* ═══════════════════════════════════════════════════════════════
     WAVE CANVAS ANIMATION
     ═══════════════════════════════════════════════════════════════ */
  let _waveProbs = { BULL: 0.2, BEAR: 0.2, SIDEWAYS: 0.2, VOLATILE: 0.2, TRENDING: 0.2 };

  function _startWaveCanvas() {
    if (_waveAnimId) cancelAnimationFrame(_waveAnimId);
    const canvas = document.getElementById('mmo-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let t = 0;
    function frame() {
      const W = canvas.offsetWidth;
      const H = 180;
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
        // Draw individual state waves
        stateKeys.forEach((s, i) => {
          const prob = _waveProbs[s] || 0.2;
          const amp  = Math.sqrt(prob) * maxAmp;  // Born rule inverse
          const col  = STATES[s].color;

          ctx.beginPath();
          ctx.strokeStyle = col + '60';
          ctx.lineWidth = 1.5;
          for (let x = 0; x <= W; x += 2) {
            const nx = x / W * Math.PI * 4;
            const y  = midY + Math.sin(nx * freqs[i] + t * (0.6 + i * 0.15) + phases[i]) * amp;
            if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
          }
          ctx.stroke();
        });

        // Superposition / interference sum wave
        ctx.beginPath();
        ctx.strokeStyle = '#ffffff22';
        ctx.lineWidth = 2.5;
        for (let x = 0; x <= W; x += 2) {
          const nx = x / W * Math.PI * 4;
          let sumY = 0;
          stateKeys.forEach((s, i) => {
            const prob = _waveProbs[s] || 0.2;
            const amp  = Math.sqrt(prob) * maxAmp;
            sumY += Math.sin(nx * freqs[i] + t * (0.6 + i * 0.15) + phases[i]) * amp * 0.5;
          });
          const y = midY + sumY;
          if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.stroke();

        // Probability cloud (alpha fill under sum)
        ctx.beginPath();
        for (let x = 0; x <= W; x += 2) {
          const nx = x / W * Math.PI * 4;
          let sumY = 0;
          stateKeys.forEach((s, i) => {
            const prob = _waveProbs[s] || 0.2;
            const amp  = Math.sqrt(prob) * maxAmp;
            sumY += Math.sin(nx * freqs[i] + t * (0.6 + i * 0.15) + phases[i]) * amp * 0.5;
          });
          const y = midY + sumY;
          if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.lineTo(W, midY); ctx.lineTo(0, midY); ctx.closePath();
        ctx.fillStyle = 'rgba(124,63,228,0.04)';
        ctx.fill();

        // Label
        ctx.font = '10px monospace';
        ctx.fillStyle = '#4a3a7a';
        ctx.textAlign = 'left';
        ctx.fillText('|ψ⟩ = SUPERPOSITION', 10, H - 10);

      } else {
        // COLLAPSED — Dirac delta spike
        _collapseT += 0.05;
        const dominant = _getDominantState();
        const col = STATES[dominant] ? STATES[dominant].color : '#cc99ff';

        // Fade rings
        const ring = Math.abs(Math.sin(_collapseT * 3));
        ctx.strokeStyle = col + Math.floor(ring * 60).toString(16).padStart(2, '0');
        ctx.lineWidth = 1;
        for (let r = 10; r < 80; r += 20) {
          ctx.beginPath();
          ctx.arc(W / 2, midY, r * (1 + ring * 0.3), 0, Math.PI * 2);
          ctx.stroke();
        }

        // Delta spike
        const spikeH = maxAmp * 2.5;
        ctx.strokeStyle = col;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(W / 2, midY + 10);
        ctx.lineTo(W / 2, midY - spikeH);
        ctx.stroke();

        // Collapsed label
        ctx.font = 'bold 13px monospace';
        ctx.fillStyle = col;
        ctx.textAlign = 'center';
        ctx.fillText('COLLAPSED → ' + dominant, W / 2, H - 14);

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
    if (verdict === 'BUY')           verdictClass = 'mmo-verdict-buy';
    else if (verdict === 'SELL')     verdictClass = 'mmo-verdict-sell';
    else if (verdict.includes('TREND')) verdictClass = 'mmo-verdict-trend';
    else if (verdict.includes('HEDGE')) verdictClass = 'mmo-verdict-hedge';

    let tunnClass = 'mmo-tunnel-low';
    if (tunnPct > 12)      tunnClass = 'mmo-tunnel-high';
    else if (tunnPct > 6)  tunnClass = 'mmo-tunnel-mod';

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
`;
  }

  /* ═══════════════════════════════════════════════════════════════
     RENDER: STRING THEORY PANEL
     ═══════════════════════════════════════════════════════════════ */
  function _renderString(str) {
    const el = document.getElementById('mmo-string-display');
    if (!el || !str) return;

    const amp  = str.amplitude || 0;
    const freq = str.frequency || 0;
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
      { key: 'BEING',       val: onto.being       || '—' },
      { key: 'ESSENCE',     val: onto.essence     || '—' },
      { key: 'ENTANGLEMENT', val: onto.entanglement || '—' },
      { key: 'STABILITY',   val: typeof onto.structural_stability === 'number'
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
      _api.get('/api/mmo/quantum_state/' + t).then(d => {
        if (!d) return;
        _scanCache[t] = d;
        _renderMiniCard(t, d);
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
    if (verdict === 'BUY')         vCol = '#00ff88';
    else if (verdict === 'SELL')   vCol = '#ff4757';
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

    // Update wave animation probs
    if (qs.amplitudes) {
      Object.assign(_waveProbs, qs.amplitudes);
    }

    // Auto-collapse if wave collapsed
    if (qs.collapsed_state && !_collapsed) {
      setTimeout(() => { _collapsed = true; _collapseT = 0; }, 600);
    }
  }

  /* ═══════════════════════════════════════════════════════════════
     PUBLIC API
     ═══════════════════════════════════════════════════════════════ */

  /**
   * Analyze a ticker — fetch full quantum state and render.
   */
  function analyze(ticker) {
    _ticker = (ticker || 'SPY').toUpperCase().trim();
    _collapsed = false;
    _collapseT = 0;

    // Show loading state
    const stateEl = document.getElementById('mmo-state-display');
    if (stateEl) stateEl.innerHTML = `<div class="mmo-superposed-label" style="color:#3a3a6a">Loading ψ(${_ticker})…</div>`;

    _api.get('/api/mmo/quantum_state/' + _ticker).then(qs => {
      if (!qs) {
        if (stateEl) stateEl.innerHTML = `<div style="font-size:9px;color:#ff4757">API error — check server</div>`;
        return;
      }
      _qState = qs;
      _renderAll(qs);
    });
  }

  /**
   * Force wave function collapse to dominant state.
   */
  function collapse() {
    if (!_qState) return;
    _collapsed = true;
    _collapseT = 0;
    // Re-render state panel with collapsed view
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
    // Reset wave probs to uniform
    Object.keys(_waveProbs).forEach(k => { _waveProbs[k] = 0.2; });
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
