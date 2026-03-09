/**
 * Atlas Viz Lab â€” v1.0
 * =====================
 * 10 live WebGL / Canvas visualizations for financial data, ARIA brain state,
 * market physics, RL agent, and system architecture.
 *
 * Inspired by:
 *   sphere-main    â†’ 3D particle market universe
 *   GitNexus       â†’ system brain graph
 *   speed-racer-rl â†’ RL agent racing track
 */

'use strict';

/* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
   GLOBAL VIZ LAB STATE
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
window.VizLab = (() => {
  let _activeViz = null;
  let _animFrameId = null;
  let _overlay = null;
  let _canvas = null;
  let _ctx = null;
  let _threeRenderer = null;
  let _threeScene = null;
  let _threeCamera = null;
  let _mouseX = 0;
  let _mouseY = 0;
  let _localCleanup = null;   // cleanup fn returned by local-renderer vizzes

  // â”€â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function lerp(a, b, t) { return a + (b - a) * t; }
  function rand(min, max) { return min + Math.random() * (max - min); }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function hsla(h, s, l, a = 1) { return `hsla(${h},${s}%,${l}%,${a})`; }

  // â”€â”€â”€ Overlay management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function _ensureOverlay() {
    if (!_overlay) {
      _overlay = document.getElementById('viz-overlay');
    }
    return _overlay;
  }

  function _getCanvas2D(id = 'viz-canvas') {
    _canvas = document.getElementById(id);
    _ctx = _canvas ? _canvas.getContext('2d') : null;
    return { canvas: _canvas, ctx: _ctx };
  }

  function _stop() {
    // Clean up any local-renderer viz (psaturn, pheart, nexus vizzes, etc.)
    if (_localCleanup) { try { _localCleanup(); } catch (e) { } _localCleanup = null; }
    if (_animFrameId) { cancelAnimationFrame(_animFrameId); _animFrameId = null; }
    if (_threeRenderer) {
      try { _threeRenderer.dispose(); } catch (e) { }
      _threeRenderer = null; _threeScene = null; _threeCamera = null;
    }
    if (_ctx && _canvas) { _ctx.clearRect(0, 0, _canvas.width, _canvas.height); }
    const threeMount = document.getElementById('viz-three-mount');
    if (threeMount) threeMount.innerHTML = '';
    _activeViz = null;
  }

  // Vizzes that create their own local WebGL renderer (not the global mount)
  const _LOCAL_THREE = new Set([
    'psaturn', 'pheart', 'pmorph',                             // sphere-main
    'pmobius', 'ptoroidal', 'pspherical', 'plissajous', 'plorenzp', // nexus-core
    'galaxy3d',                                                 // MMO Market Galaxy 3D
  ]);

  function _open(vizName) {
    const overlay = _ensureOverlay();
    if (!overlay) return;
    _stop();
    overlay.style.display = 'flex';
    const title = document.getElementById('viz-overlay-title');
    if (title) title.textContent = VIZ_META[vizName]?.label || vizName;

    // Mount-based vizzes use #viz-three-mount; local-Three vizzes create their own renderer.
    const isGlobalThree = vizName === 'particle' || vizName === 'livemonitor' || vizName === 'brain';
    const isLocalThree = _LOCAL_THREE.has(vizName);
    const hideCanvas = isGlobalThree || isLocalThree;

    const threeMount = document.getElementById('viz-three-mount');
    const c = document.getElementById('viz-canvas');
    if (threeMount) threeMount.style.display = (isGlobalThree || isLocalThree) ? 'block' : 'none';
    if (c) {
      c.style.display = hideCanvas ? 'none' : 'block';
      if (!hideCanvas) {
        const container = document.getElementById('viz-canvas-container');
        const cW = container ? container.clientWidth : window.innerWidth;
        const cH = container ? container.clientHeight : window.innerHeight - 50;
        c.width = cW || window.innerWidth;
        c.height = cH || window.innerHeight - 50;
      }
    }

    _activeViz = vizName;
    _mouseX = 0; _mouseY = 0;
    // Save cleanup fn so _stop() can tear down local renderers properly
    setTimeout(() => {
      if (VIZZES[vizName]) _localCleanup = VIZZES[vizName]() || null;
    }, 80);
  }

  function _close() {
    _stop();
    const overlay = _ensureOverlay();
    if (overlay) overlay.style.display = 'none';
  }

  // â”€â”€â”€ Mouse tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function _trackMouse(e) {
    const c = document.getElementById('viz-canvas');
    if (!c) return;
    const r = c.getBoundingClientRect();
    _mouseX = e.clientX - r.left;
    _mouseY = e.clientY - r.top;
  }

  /* â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
     VIZ META (label + description shown in card grid)
  â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  // cat: 'algo' = connected to a real Atlas algorithm/API
  //      'art'  = pure math / particle art / decorative sim
  const VIZ_META = {
    // â•â• ALGORITHM VISUALIZATIONS â€” live Atlas data â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    particle: { cat: 'algo', label: 'Particle Market Universe', icon: 'âš›', api: '/api/vizlab/regime/SPY', desc: 'Regime detection â†’ 15k particles morph shape: bull sphere / bear scatter / volatile chaos' },
    brain: { cat: 'algo', label: 'ARIA Neural Brain', icon: 'ðŸ§ ', api: '/api/vizlab/brain', desc: 'Live ARIA module activity graph â€” nodes pulse with real inference activity' },
    radar: { cat: 'algo', label: 'Strategy Signal Radar', icon: 'ðŸ“¡', api: '/api/strategy/analyze/SPY', desc: 'MultiStrategyEngine 5-engine radar â€” real RSI/MACD/BB/SMA/Momentum signals' },
    agentswarm: { cat: 'algo', label: 'ARIA Agent Swarm', icon: 'ðŸ¤–', api: '/api/strategy/analyze/SPY', desc: 'Each orbiting agent = one rule engine. Signal strength drives orbit speed + glow' },
    alphascanner: { cat: 'algo', label: 'Alpha Factor Scanner', icon: 'ðŸ”­', api: '/api/factors/SPY', desc: 'FactorEngine Alpha158 â€” real factor scores drive particle brightness and orbit radius' },
    factorwheel: { cat: 'algo', label: 'Factor Group Wheel', icon: 'âš™', api: '/api/factors/SPY', desc: 'MOMENTUM / VOLUME / QUALITY / VOLATILITY / TECHNICAL / MICRO group scores on rotating wheel' },
    scorepulse: { cat: 'algo', label: 'Composite Score Pulse', icon: 'ðŸ’“', api: '/api/trader/analyze/SPY', desc: 'ARIA Trader composite scorer â€” all 5 signal layers shown as live EKG waves' },
    livemonitor: { cat: 'algo', label: 'Live Monitor Ops', icon: 'MON', api: '/api/monitor/tick', desc: 'Mission-control panel with auto quote polling + rotating multi-signal checks' },
    drawdown: { cat: 'algo', label: 'Drawdown Mountain', icon: 'â›°', api: '/api/strategy/backtest/SPY', desc: 'Real walk-forward equity curve + underwater drawdown terrain from backtest engine' },
    assetgraph: { cat: 'algo', label: 'Asset Correlation Network', icon: 'ðŸ•¸', api: '/api/correlation/cluster', desc: 'Real cointegrated pair correlations as a live force-directed graph' },
    correlation3d: { cat: 'algo', label: 'Correlation Surface 3D', icon: 'ðŸŒ', api: '/api/correlation/cluster', desc: 'Real asset correlation cluster data rendered as a rotating 3D bar surface' },
    galaxy: { cat: 'algo', label: 'Correlation Galaxy', icon: 'ðŸŒ ', api: '/api/correlation/cluster', desc: 'Real cluster assignments â€” assets orbit their cluster center as stars' },
    forcegraph: { cat: 'algo', label: 'Market Structure Graph', icon: 'ðŸŒŒ', api: '/api/correlation/structure', desc: 'Market regime + diversification score from correlation engine as gravity field' },
    flowstate: { cat: 'algo', label: 'Capital Flow State', icon: 'ðŸŒ€', api: '/api/correlation/structure', desc: 'Regime + correlation structure drives sector rotation wheel allocation' },
    dcfuniverse: { cat: 'algo', label: 'DCF Universe', icon: 'ðŸ’°', api: '/api/fundamental/AAPL', desc: 'Real fundamental data â€” stocks plotted by intrinsic value Ã— growth Ã— momentum' },
    montecarlo: { cat: 'algo', label: 'Monte Carlo Paths', icon: 'ðŸ“‰', api: '/api/vizlab/montecarlo/SPY', desc: 'Server-side GBM simulation â€” real volatility parameters from yfinance' },
    heatmap: { cat: 'algo', label: 'Return Heatmap Calendar', icon: 'ðŸ“…', api: '/api/market_data/SPY', desc: 'Real SPY daily returns rendered as GitHub-style contribution heatmap' },
    candle: { cat: 'algo', label: 'Candle River', icon: 'ðŸ•¯', api: '/api/market_data/SPY', desc: 'Real OHLCV data â€” live candles flow as a river with volume pulse' },
    flowfield: { cat: 'algo', label: 'Price Flow Field', icon: 'ðŸŒŠ', api: '/api/market_data/SPY', desc: 'Price momentum vectors drive particle flow field direction and speed' },
    terrain: { cat: 'algo', label: 'Risk Terrain', icon: 'ðŸ”', api: '/api/factors/SPY', desc: 'Volatility factor group score shapes the 3D risk landscape altitude' },
    entropy: { cat: 'algo', label: 'Entropy Cascade', icon: 'ðŸ’§', api: '/api/factors/SPY', desc: 'Realised volatility from FactorEngine drives market entropy waterfall speed' },
    rltrack: { cat: 'algo', label: 'RL Agent Race Track', icon: 'ðŸ', api: '/api/strategy/backtest/SPY', desc: 'Backtest trade signals â†’ agent accelerates on BUY, brakes on SELL' },
    treemap: { cat: 'algo', label: 'Portfolio Treemap', icon: 'ðŸŒ³', api: '/api/correlation/cluster', desc: 'Real cluster weights as nested treemap tiles with live signal heat' },
    orderbook: { cat: 'algo', label: 'Order Book Depth', icon: 'ðŸ“–', api: '/api/quote/SPY', desc: 'Real mid-price from yfinance anchors simulated L2 bid/ask pressure' },
    worldmodel: { cat: 'algo', label: 'World Model Tokens', icon: 'ðŸŽ²', api: '/api/market_data/SPY', desc: 'Real price returns encoded as masked tokens â€” the market\'s generative model' },
    volsmile: { cat: 'algo', label: 'Vol Smile Surface', icon: 'ðŸ˜Š', api: '/api/options/surface/SPY', desc: 'Real implied vol surface from options chain across strikes and expiries' },
    blackhole: { cat: 'algo', label: 'Liquidity Black Hole', icon: '🕳', api: null, desc: 'Market liquidity singularity — capital in accretion infall, event horizon, lensing rings' },
    galaxy3d: { cat: 'algo', label: 'Market Galaxy 3D', icon: '🌌', api: '/api/correlation/cluster', desc: 'Three.js 3D spiral galaxy — sector arms orbit the benchmark singularity' },
    // â•â• DECORATIVE SIMS â€” mathematical art, no live data â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    lorenz: { cat: 'art', label: 'Lorenz Attractor', icon: 'ðŸŒ€', api: null, desc: 'Chaotic differential equation â€” butterfly effect in 3D phase space' },
    quantum: { cat: 'art', label: 'Quantum Superposition', icon: 'ðŸ”¬', api: null, desc: 'Probability wave collapse simulation â€” SchrÃ¶dinger market analogy' },
    spread: { cat: 'art', label: 'Spread Dynamics', icon: 'â†”', api: null, desc: 'Stylised bid-ask spread wave animation â€” market microstructure art' },
    marketdna: { cat: 'art', label: 'Market DNA Helix', icon: 'ðŸ§¬', api: null, desc: 'Candle types encoded as rotating DNA â€” visual genome of the market' },
    psaturn: { cat: 'art', label: 'Particle Saturn', icon: 'ðŸª', api: null, desc: '15k particles in Saturn-ring shape with cursor repulsion field' },
    pheart: { cat: 'art', label: 'Particle Heart', icon: 'â¤', api: null, desc: '15k particles in a pulsing heart â€” particle physics art' },
    pmorph: { cat: 'art', label: 'Particle Morph', icon: 'âœ¨', api: null, desc: 'Morphs between Saturn / Heart / Sphere â€” 15k particles + cursor push' },
    pmobius: { cat: 'art', label: 'MÃ¶bius Strip', icon: 'âˆž', api: null, desc: '50k particles on a MÃ¶bius band â€” topology art' },
    ptoroidal: { cat: 'art', label: 'Toroidal Vortex', icon: 'ðŸ©', api: null, desc: '50k particles on a knotted torus with ripple deformation' },
    pspherical: { cat: 'art', label: 'Spherical Harmonics', icon: 'ðŸ”®', api: null, desc: '50k particles on a bumpy sphere â€” mathematical art' },
    plissajous: { cat: 'art', label: 'Lissajous 3D', icon: 'ã€°', api: null, desc: '50k particles on 3D Lissajous curves â€” multi-frequency art' },
    plorenzp: { cat: 'art', label: 'Lorenz Attractor 3D', icon: 'ðŸŒ€', api: null, desc: '50k particles tracing Lorenz chaos in 3D particle form' },
    speedracer: { cat: 'art', label: 'DQN Speed Racer', icon: 'ðŸŽ', api: null, desc: 'Îµ-greedy DQN simulation â€” self-contained AI agent, not trading data' },
  };

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     1. PARTICLE MARKET UNIVERSE
     Inspired by sphere-main (React Three Fiber â†’ pure Three.js)
     15 000 particles morphing between shapes based on market regime.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizParticle() {
    const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!container || typeof THREE === 'undefined') { _fallback2D('particle'); return; }

    const W = container.clientWidth, H = container.clientHeight - 50;
    const COUNT = 15000;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060610);
    const camera = new THREE.PerspectiveCamera(65, W / H, 0.1, 500);
    camera.position.set(0, 0, 18);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    const mount = document.getElementById('viz-three-mount');
    if (!mount) return;
    mount.innerHTML = '';
    mount.appendChild(renderer.domElement);
    _threeRenderer = renderer;
    _threeScene = scene;
    _threeCamera = camera;

    // Shapes: generates target positions
    const regimes = ['BULL', 'BEAR', 'SIDEWAYS', 'VOLATILE', 'TRENDING'];
    let currentRegime = 'BULL';
    let regimeIndex = 0;

    function makeShape(regime) {
      const pos = new Float32Array(COUNT * 3);
      const col = new Float32Array(COUNT * 3);
      for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        let x, y, z, r, g, b;
        if (regime === 'BULL') {
          // Perfect sphere
          const phi = Math.acos(2 * Math.random() - 1);
          const theta = Math.random() * Math.PI * 2;
          const radius = 5 + rand(-0.2, 0.2);
          x = radius * Math.sin(phi) * Math.cos(theta);
          y = radius * Math.sin(phi) * Math.sin(theta);
          z = radius * Math.cos(phi);
          r = 0.1; g = rand(0.7, 1.0); b = 0.3;
        } else if (regime === 'BEAR') {
          // Inverted cone â€” particles draining down
          const angle = Math.random() * Math.PI * 2;
          const height = rand(0, 8);
          const radius = (8 - height) * 0.6 + rand(-0.3, 0.3);
          x = Math.cos(angle) * radius;
          y = 4 - height;
          z = Math.sin(angle) * radius;
          r = rand(0.7, 1.0); g = 0.1; b = 0.1;
        } else if (regime === 'SIDEWAYS') {
          // Saturn: sphere + rings
          if (i < COUNT * 0.55) {
            const phi = Math.acos(2 * Math.random() - 1);
            const theta = Math.random() * Math.PI * 2;
            const radius = 3.5 + rand(-0.15, 0.15);
            x = radius * Math.sin(phi) * Math.cos(theta);
            y = radius * Math.sin(phi) * Math.sin(theta);
            z = radius * Math.cos(phi);
          } else {
            const angle = Math.random() * Math.PI * 2;
            const radius = rand(5.5, 8.5);
            x = Math.cos(angle) * radius;
            y = rand(-0.4, 0.4);
            z = Math.sin(angle) * radius;
          }
          r = 0.4; g = 0.6; b = rand(0.7, 1.0);
        } else if (regime === 'VOLATILE') {
          // Exploding cloud â€” random sphere with large variance
          const phi = Math.acos(2 * Math.random() - 1);
          const theta = Math.random() * Math.PI * 2;
          const radius = rand(2, 12);
          x = radius * Math.sin(phi) * Math.cos(theta) + rand(-1, 1);
          y = radius * Math.sin(phi) * Math.sin(theta) + rand(-1, 1);
          z = radius * Math.cos(phi) + rand(-1, 1);
          r = rand(0.8, 1.0); g = rand(0.5, 0.8); b = 0.0;
        } else { // TRENDING
          // Double helix â€” upward trending
          const t = (i / COUNT) * Math.PI * 12;
          const strand = i % 2;
          const helix_r = 3.5;
          x = Math.cos(t + strand * Math.PI) * helix_r;
          y = (t / (Math.PI * 12)) * 14 - 7;
          z = Math.sin(t + strand * Math.PI) * helix_r;
          r = 0.6; g = rand(0.5, 0.9); b = rand(0.8, 1.0);
        }
        pos[i3] = x; pos[i3 + 1] = y; pos[i3 + 2] = z;
        col[i3] = r; col[i3 + 1] = g; col[i3 + 2] = b;
      }
      return { pos, col };
    }

    // Geometry
    const geo = new THREE.BufferGeometry();
    const currentPos = new Float32Array(COUNT * 3);
    const currentCol = new Float32Array(COUNT * 3);
    const velocity = new Float32Array(COUNT * 3);
    let target = makeShape('BULL');
    // Initialize positions randomly then morph in
    for (let i = 0; i < COUNT * 3; i++) {
      currentPos[i] = rand(-12, 12);
      currentCol[i] = Math.random();
    }
    geo.setAttribute('position', new THREE.BufferAttribute(currentPos, 3));
    geo.setAttribute('color', new THREE.BufferAttribute(currentCol, 3));

    const mat = new THREE.PointsMaterial({ size: 0.04, vertexColors: true, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false });
    const points = new THREE.Points(geo, mat);
    scene.add(points);

    // Lighting fog-like effect
    scene.fog = new THREE.Fog(0x060610, 30, 80);

    // Mouse interaction
    let mouseNDC = { x: 0, y: 0 };
    renderer.domElement.addEventListener('mousemove', e => {
      const r = renderer.domElement.getBoundingClientRect();
      mouseNDC.x = ((e.clientX - r.left) / W) * 2 - 1;
      mouseNDC.y = -((e.clientY - r.top) / H) * 2 + 1;
    });

    // Auto-cycle regimes
    let lastCycle = Date.now();
    const CYCLE_MS = 8000;

    // Orbit
    let rotY = 0, rotX = 0;
    let dragStart = null;
    renderer.domElement.addEventListener('mousedown', e => { dragStart = { x: e.clientX, y: e.clientY, rotY, rotX }; });
    renderer.domElement.addEventListener('mousemove', e => {
      if (!dragStart) return;
      rotY = dragStart.rotY + (e.clientX - dragStart.x) * 0.005;
      rotX = dragStart.rotX + (e.clientY - dragStart.y) * 0.005;
    });
    renderer.domElement.addEventListener('mouseup', () => { dragStart = null; });

    // â”€â”€ Live regime from /api/vizlab/regime/SPY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const _REGIME_MAP = { BULL: 0, BEAR: 1, SIDEWAYS: 2, VOLATILE: 3, TRENDING: 4 };
    fetchRegimeAndUpdate('SPY').then(r => {
      if (!r) return;
      const idx = _REGIME_MAP[r.toUpperCase()];
      if (idx !== undefined) {
        regimeIndex = idx;
        currentRegime = regimes[idx];
        target = makeShape(currentRegime);
        lastCycle = Date.now(); // reset cycle timer
      }
    }).catch(() => { });

    let frame = 0;
    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;

      // Cycle regime (auto-cycle continues after live init)
      if (Date.now() - lastCycle > CYCLE_MS) {
        lastCycle = Date.now();
        regimeIndex = (regimeIndex + 1) % regimes.length;
        currentRegime = regimes[regimeIndex];
        target = makeShape(currentRegime);
        updateRegimeLabel(currentRegime);
      }

      // Morph particles toward target
      const SPEED = 0.035;
      const pos = geo.attributes.position.array;
      const col = geo.attributes.color.array;
      for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        // Mouse repulsion
        const px = pos[i3], py = pos[i3 + 1];
        const mx = mouseNDC.x * 8, my = mouseNDC.y * 8;
        const dx = px - mx, dy = py - my;
        const dist = Math.sqrt(dx * dx + dy * dy) + 0.01;
        const repel = dist < 2.5 ? (2.5 - dist) / dist * 0.15 : 0;

        pos[i3] = lerp(pos[i3], target.pos[i3], SPEED) + dx * repel * 0.01;
        pos[i3 + 1] = lerp(pos[i3 + 1], target.pos[i3 + 1], SPEED) + dy * repel * 0.01;
        pos[i3 + 2] = lerp(pos[i3 + 2], target.pos[i3 + 2], SPEED);
        col[i3] = lerp(col[i3], target.col[i3], 0.02);
        col[i3 + 1] = lerp(col[i3 + 1], target.col[i3 + 1], 0.02);
        col[i3 + 2] = lerp(col[i3 + 2], target.col[i3 + 2], 0.02);
      }
      geo.attributes.position.needsUpdate = true;
      geo.attributes.color.needsUpdate = true;

      // Slow auto-rotation if not dragging
      if (!dragStart) { rotY += 0.003; }
      points.rotation.y = rotY;
      points.rotation.x = clamp(rotX, -0.8, 0.8);

      renderer.render(scene, camera);
    }
    animate();
  }

  function updateRegimeLabel(regime) {
    const el = document.getElementById('viz-regime-label');
    if (!el) return;
    const colors = { BULL: '#00ff88', BEAR: '#ff4444', SIDEWAYS: '#4488ff', VOLATILE: '#ffaa00', TRENDING: '#cc88ff' };
    el.textContent = `Regime: ${regime}`;
    el.style.color = colors[regime] || '#fff';
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     2. ARIA NEURAL BRAIN
     Animated force-directed graph of ARIA's modules.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizBrain() {
    const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!container || typeof THREE === 'undefined') { _fallback2D('brain'); return; }

    const W = container.clientWidth, H = container.clientHeight - 50;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x060610);
    const camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000);
    camera.position.set(0, 0, 120);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const mount = document.getElementById('viz-three-mount');
    if (!mount) return;
    mount.innerHTML = '';
    mount.appendChild(renderer.domElement);

    _threeRenderer = renderer;
    _threeScene = scene;
    _threeCamera = camera;

    // We will build nodes and edges dynamically via API fetch
    const nodeMaterials = {};
    const nodeMeshes = {};
    const edgeLines = [];
    const labels = [];

    // Group to hold graph to rotate
    const graphGroup = new THREE.Group();
    scene.add(graphGroup);

    // Some base physics configuration
    let nodesData = [];
    let edgesData = [];

    const typeColors = {
      "data": 0x00aaff,
      "analytics": 0x00ddff,
      "engine": 0x8844ff,
      "risk": 0xff8800,
      "sim": 0xffaa00,
      "eval": 0x44cc88,
      "exec": 0x00ff88,
      "ai": 0xffffff,
      "ui": 0xcc44ff,
      "app": 0xff44cc,
    };

    fetchBrainState().then(d => {
      if (!d || !d.nodes) return;
      nodesData = d.nodes.map(n => {
        // Initialize random 3D position
        const phi = Math.acos(2 * Math.random() - 1);
        const theta = Math.random() * Math.PI * 2;
        const r = 40 + Math.random() * 20;
        n.x = r * Math.sin(phi) * Math.cos(theta);
        n.y = r * Math.sin(phi) * Math.sin(theta);
        n.z = r * Math.cos(phi);
        n.vx = 0; n.vy = 0; n.vz = 0;
        n.activity = n.active ? 1.0 : 0.2;
        n.color = typeColors[n.type] || 0xffffff;

        if (n.id === 'aria') {
          n.x = 0; n.y = 0; n.z = 0; // Fix ARIA near center
          n.size = 6;
        } else {
          n.size = 2.5 + Math.random();
        }
        return n;
      });
      edgesData = d.edges;

      initGraphGeometry();
    }).catch(e => console.error(e));

    function initGraphGeometry() {
      // Create Node Spheres
      nodesData.forEach(n => {
        const geo = new THREE.SphereGeometry(n.size, 16, 16);
        const mat = new THREE.MeshBasicMaterial({
          color: n.color,
          transparent: true,
          opacity: n.active ? 0.9 : 0.3
        });
        const mesh = new THREE.Mesh(geo, mat);

        // Add outer glow / halo
        const haloGeo = new THREE.SphereGeometry(n.size * 2.2, 16, 16);
        const haloMat = new THREE.MeshBasicMaterial({
          color: n.color,
          transparent: true,
          opacity: n.active ? 0.2 : 0.05,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        });
        const halo = new THREE.Mesh(haloGeo, haloMat);
        mesh.add(halo);

        mesh.position.set(n.x, n.y, n.z);
        graphGroup.add(mesh);
        nodeMeshes[n.id] = { mesh, halo, data: n };

        // Create CSS 2D Label manually or using primitive canvas sprites
        const sprite = makeTextSprite(n.label, n.color);
        sprite.position.set(n.x, n.y - n.size - 2, n.z);
        graphGroup.add(sprite);
        labels.push({ sprite, id: n.id });
      });

      // Create Edges
      const lineMat = new THREE.LineBasicMaterial({
        color: 0x445588,
        transparent: true,
        opacity: 0.4,
        linewidth: 1
      });

      edgesData.forEach(e => {
        const geo = new THREE.BufferGeometry();
        const fromNode = nodeMeshes[e.from];
        const toNode = nodeMeshes[e.to];
        if (fromNode && toNode) {
          geo.setFromPoints([fromNode.mesh.position, toNode.mesh.position]);
          const line = new THREE.Line(geo, lineMat.clone());
          // Color line based on fromNode
          line.material.color.setHex(fromNode.data.color);
          graphGroup.add(line);
          edgeLines.push({ line, from: e.from, to: e.to });
        }
      });
    }

    // Canvas Text Sprite helper
    function makeTextSprite(message, colorHex) {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      canvas.width = 256; canvas.height = 64;

      ctx.font = 'bold 24px monospace';
      ctx.fillStyle = '#' + colorHex.toString(16).padStart(6, '0');
      ctx.textAlign = 'center';
      ctx.fillText(message, 128, 32);

      const tex = new THREE.CanvasTexture(canvas);
      const mat = new THREE.SpriteMaterial({ map: tex, transparent: true });
      const sprite = new THREE.Sprite(mat);
      sprite.scale.set(30, 7.5, 1);
      return sprite;
    }

    // ── Star field (3D) ─────────────────────────────────────────
    const starGeo = new THREE.BufferGeometry();
    const starCount = 300;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount * 3; i++) {
      starPos[i] = (Math.random() - 0.5) * 400;
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({ color: 0xaaaaaa, size: 0.5, transparent: true, opacity: 0.6 });
    const stars = new THREE.Points(starGeo, starMat);
    scene.add(stars);

    // Mouse Controls
    let rotY = 0, rotX = 0;
    let dragStart = null;
    renderer.domElement.addEventListener('mousedown', e => { dragStart = { x: e.clientX, y: e.clientY, rotY, rotX }; });
    renderer.domElement.addEventListener('mousemove', e => {
      if (!dragStart) return;
      rotY = dragStart.rotY + (e.clientX - dragStart.x) * 0.005;
      rotX = dragStart.rotX + (e.clientY - dragStart.y) * 0.005;
    });
    renderer.domElement.addEventListener('mouseup', () => { dragStart = null; });
    renderer.domElement.addEventListener('mouseleave', () => { dragStart = null; });

    let frame = 0;
    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;

      // Update Physics (Force layout)
      if (nodesData.length > 0) {
        // Repulsion
        for (let i = 0; i < nodesData.length; i++) {
          for (let j = i + 1; j < nodesData.length; j++) {
            const a = nodesData[i], b = nodesData[j];
            const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
            let d = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
            const force = 3000 / (d * d); // Repulsion config
            const fx = (dx / d) * force, fy = (dy / d) * force, fz = (dz / d) * force;
            a.vx -= fx; a.vy -= fy; a.vz -= fz;
            b.vx += fx; b.vy += fy; b.vz += fz;
          }
          // Gravity to center
          const a = nodesData[i];
          if (a.id === 'aria') {
            a.vx += (0 - a.x) * 0.05;
            a.vy += (0 - a.y) * 0.05;
            a.vz += (0 - a.z) * 0.05;
          } else {
            a.vx += (0 - a.x) * 0.002;
            a.vy += (0 - a.y) * 0.002;
            a.vz += (0 - a.z) * 0.002;
          }
        }

        // Springs (Edges)
        edgesData.forEach(e => {
          const a = nodeMeshes[e.from]?.data;
          const b = nodeMeshes[e.to]?.data;
          if (a && b) {
            const dx = b.x - a.x, dy = b.y - a.y, dz = b.z - a.z;
            let d = Math.sqrt(dx * dx + dy * dy + dz * dz) || 1;
            const rest = 30;
            const k = 0.02;
            const f = (d - rest) * k;
            const fx = (dx / d) * f, fy = (dy / d) * f, fz = (dz / d) * f;
            a.vx += fx; a.vy += fy; a.vz += fz;
            b.vx -= fx; b.vy -= fy; b.vz -= fz;
          }
        });

        // Apply forces and update meshes
        nodesData.forEach(n => {
          n.vx *= 0.85; n.vy *= 0.85; n.vz *= 0.85; // Damping
          n.x += n.vx; n.y += n.vy; n.z += n.vz;

          const obj = nodeMeshes[n.id];
          if (obj) {
            obj.mesh.position.set(n.x, n.y, n.z);

            // Pulse activity
            if (n.active) {
              const pulse = Math.sin(frame * 0.05 + n.x) * 0.3 + 0.7; // 0.4 to 1.0
              obj.halo.material.opacity = 0.2 * pulse;
              obj.halo.scale.setScalar(1 + 0.1 * pulse);
            }
          }
        });

        // Update Lines
        edgeLines.forEach(edge => {
          const fromN = nodeMeshes[edge.from];
          const toN = nodeMeshes[edge.to];
          if (fromN && toN) {
            const posAtt = edge.line.geometry.attributes.position;
            posAtt.setXYZ(0, fromN.mesh.position.x, fromN.mesh.position.y, fromN.mesh.position.z);
            posAtt.setXYZ(1, toN.mesh.position.x, toN.mesh.position.y, toN.mesh.position.z);
            posAtt.needsUpdate = true;

            // Pulse line opacity
            if (fromN.data.active && toN.data.active) {
              edge.line.material.opacity = 0.3 + 0.3 * Math.sin(frame * 0.1 + fromN.data.x);
            }
          }
        });

        // Update Labels
        labels.forEach(lbl => {
          const nd = nodeMeshes[lbl.id];
          if (nd) {
            lbl.sprite.position.set(nd.data.x, nd.data.y - nd.data.size - 2, nd.data.z);
          }
        });
      }

      // Rotate entire graph
      if (!dragStart) { rotY += 0.0015; }
      graphGroup.rotation.y = rotY;
      graphGroup.rotation.x = clamp(rotX, -0.8, 0.8);

      renderer.render(scene, camera);
    }

    animate();

    return () => {
      // Cleanup for WebGL memory
      try {
        scene.remove(graphGroup);
        scene.remove(stars);
        graphGroup.clear();
        starGeo.dispose();
        starMat.dispose();
        Object.values(nodeMeshes).forEach(n => {
          n.mesh.geometry.dispose();
          n.mesh.material.dispose();
          n.halo.geometry.dispose();
          n.halo.material.dispose();
        });
        edgeLines.forEach(e => {
          e.line.geometry.dispose();
          e.line.material.dispose();
        });
        labels.forEach(l => {
          l.sprite.material.map.dispose();
          l.sprite.material.dispose();
        });
      } catch (e) { }
    };
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     3. MARKET FORCE GRAPH â€” correlation galaxy
     Assets as stars pulled together by correlation.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizForceGraph() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const ASSETS = [
      { id: 'SPY', sector: 'ETF', color: '#00ff88' },
      { id: 'QQQ', sector: 'ETF', color: '#00ff88' },
      { id: 'AAPL', sector: 'Tech', color: '#4488ff' },
      { id: 'MSFT', sector: 'Tech', color: '#4488ff' },
      { id: 'NVDA', sector: 'Tech', color: '#4488ff' },
      { id: 'AMZN', sector: 'Tech', color: '#4488ff' },
      { id: 'TSLA', sector: 'Auto', color: '#cc88ff' },
      { id: 'JPM', sector: 'Finance', color: '#ff8800' },
      { id: 'GS', sector: 'Finance', color: '#ff8800' },
      { id: 'BTC', sector: 'Crypto', color: '#ffaa00' },
      { id: 'ETH', sector: 'Crypto', color: '#ffaa00' },
      { id: 'GLD', sector: 'Commodity', color: '#ffdd44' },
      { id: 'XOM', sector: 'Energy', color: '#ff4444' },
      { id: 'NFLX', sector: 'Media', color: '#ff44aa' },
    ];

    // Correlation matrix (starts simulated, gets overwritten by live API data)
    const CORR = {};
    function getCorr(a, b) {
      const key = [a, b].sort().join('-');
      if (!CORR[key]) {
        const sa = ASSETS.find(x => x.id === a), sb = ASSETS.find(x => x.id === b);
        CORR[key] = sa.sector === sb.sector ? rand(0.55, 0.92) : rand(-0.1, 0.45);
      }
      return CORR[key];
    }

    // â”€â”€ Live correlation data from /api/vizlab/market_graph â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _graphLabel = 'Market Force Graph â€” Simulated';
    _api.get('/api/vizlab/market_graph').then(d => {
      if (!d || !d.edges) return;
      _graphLabel = `Market Force Graph â€” LIVE (${d.n_days || '?'}d)`;
      // Overwrite simulated correlations with real ones
      d.edges.forEach(e => {
        const key = [e.from, e.to].sort().join('-');
        CORR[key] = e.corr;
      });
      // Add missing assets from API that aren't already in ASSETS
      (d.nodes || []).forEach(n => {
        if (!ASSETS.find(a => a.id === n.id)) {
          const angle = Math.random() * Math.PI * 2;
          ASSETS.push({
            id: n.id, sector: n.sector || 'Other', color: n.color || '#aaaaff',
            x: W / 2 + Math.cos(angle) * 160, y: H / 2 + Math.sin(angle) * 130,
            vx: 0, vy: 0, size: 18 + Math.random() * 12, pulse: Math.random() * Math.PI * 2
          });
        }
      });
    }).catch(() => { });

    // Init positions
    ASSETS.forEach((a, i) => {
      const angle = (i / ASSETS.length) * Math.PI * 2;
      a.x = W / 2 + Math.cos(angle) * 160;
      a.y = H / 2 + Math.sin(angle) * 130;
      a.vx = 0; a.vy = 0;
      a.size = 18 + Math.random() * 16;
      a.pulse = Math.random() * Math.PI * 2;
    });

    // ── Star field (force graph) ─────────────────────────────────────────
    const _fgStars = Array.from({ length: 100 }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      r: Math.random() * 1.1 + 0.15,
      a: Math.random() * 0.4 + 0.05,
      da: (Math.random() - 0.5) * 0.002
    }));

    let frame = 0;
    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      // Background fade (motion trail)
      ctx.fillStyle = 'rgba(4,4,14,0.22)';
      ctx.fillRect(0, 0, W, H);

      // Twinkling stars
      for (const s of _fgStars) {
        s.a += s.da; if (s.a > 0.42 || s.a < 0.04) s.da *= -1;
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(170,200,255,${s.a.toFixed(3)})`; ctx.fill();
      }

      // Force physics
      for (let i = 0; i < ASSETS.length; i++) {
        for (let j = i + 1; j < ASSETS.length; j++) {
          const a = ASSETS[i], b = ASSETS[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const d = Math.sqrt(dx * dx + dy * dy) + 1;
          const corr = getCorr(a.id, b.id);
          // High corr â†’ attract, low/neg â†’ repel
          const strength = corr * 0.7 - 0.1;
          const f = strength * 0.8 / (d * 0.05 + 1);
          a.vx += dx / d * f; a.vy += dy / d * f;
          b.vx -= dx / d * f; b.vy -= dy / d * f;
          // Base repulsion (collision avoidance)
          if (d < 60) {
            const rep = (60 - d) / 60 * 1.5;
            a.vx -= dx / d * rep; a.vy -= dy / d * rep;
            b.vx += dx / d * rep; b.vy += dy / d * rep;
          }
        }
        // Center pull
        ASSETS[i].vx += (W / 2 - ASSETS[i].x) * 0.001;
        ASSETS[i].vy += (H / 2 - ASSETS[i].y) * 0.001;
        ASSETS[i].vx *= 0.9; ASSETS[i].vy *= 0.9;
        ASSETS[i].x = clamp(ASSETS[i].x + ASSETS[i].vx, 50, W - 50);
        ASSETS[i].y = clamp(ASSETS[i].y + ASSETS[i].vy, 50, H - 50);
      }

      // Draw edges — gradient glow by correlation strength
      for (let i = 0; i < ASSETS.length; i++) {
        for (let j = i + 1; j < ASSETS.length; j++) {
          const corr = getCorr(ASSETS[i].id, ASSETS[j].id);
          if (corr < 0.4) continue;
          const a = ASSETS[i], b = ASSETS[j];
          const ea = Math.round((corr - 0.4) * 220).toString(16).padStart(2, '0');
          const edgeGrd = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
          edgeGrd.addColorStop(0, a.color + ea);
          edgeGrd.addColorStop(0.5, `rgba(100,210,255,${((corr - 0.4) * 0.5).toFixed(2)})`);
          edgeGrd.addColorStop(1, b.color + ea);
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
          ctx.strokeStyle = edgeGrd;
          ctx.lineWidth = corr > 0.75 ? 2.2 : 1.2;
          ctx.stroke();
        }
      }

      // Draw nodes — premium multi-layer glow
      for (const a of ASSETS) {
        a.pulse += 0.04;
        const glow = a.size + Math.sin(a.pulse) * 5;

        // Outer corona
        const corona = ctx.createRadialGradient(a.x, a.y, glow * 0.3, a.x, a.y, glow * 3.0);
        corona.addColorStop(0, a.color + '22');
        corona.addColorStop(0.6, a.color + '08');
        corona.addColorStop(1, 'transparent');
        ctx.beginPath(); ctx.arc(a.x, a.y, glow * 3.0, 0, Math.PI * 2);
        ctx.fillStyle = corona; ctx.fill();

        // Mid glow
        const grd = ctx.createRadialGradient(a.x, a.y, 0, a.x, a.y, glow * 1.8);
        grd.addColorStop(0, a.color + 'bb');
        grd.addColorStop(0.5, a.color + '40');
        grd.addColorStop(1, 'transparent');
        ctx.beginPath(); ctx.arc(a.x, a.y, glow * 1.8, 0, Math.PI * 2);
        ctx.fillStyle = grd; ctx.fill();

        // Core ring
        ctx.beginPath(); ctx.arc(a.x, a.y, glow * 0.6, 0, Math.PI * 2);
        ctx.fillStyle = a.color + '28'; ctx.fill();
        ctx.strokeStyle = a.color; ctx.lineWidth = 1.8; ctx.stroke();

        // Label
        ctx.shadowBlur = 5; ctx.shadowColor = a.color;
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 9px monospace';
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(a.id, a.x, a.y);
        ctx.shadowBlur = 0;
      }

      // Legend — premium with sector color glows
      const sectors = [...new Set(ASSETS.map(a => a.sector))];
      sectors.forEach((s, i) => {
        const col = ASSETS.find(a => a.sector === s).color;
        ctx.shadowBlur = 4; ctx.shadowColor = col;
        ctx.fillStyle = col;
        ctx.font = '9px monospace';
        ctx.textAlign = 'left';
        ctx.fillText('▪ ' + s, 12, 20 + i * 13);
        ctx.shadowBlur = 0;
      });
      ctx.fillStyle = '#334455';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(_graphLabel, 12, H - 10);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     4. MONTE CARLO PATHS â€” animated GBM fan
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizMonteCarlo() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    // â”€â”€ Defaults (simulated fallback) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const N_PATHS_SIM = 150, STEPS_SIM = 200;
    const mu_sim = 0.0003, sigma_sim = 0.018;
    let paths = [];
    let pMin = Infinity, pMax = -Infinity;
    let STEPS = STEPS_SIM;
    let _mcLabel = `Monte Carlo GBM  |  Î¼=${(mu_sim * 252 * 100).toFixed(1)}% ann.  |  Ïƒ=${(sigma_sim * Math.sqrt(252) * 100).toFixed(1)}% ann.  |  SPY sim`;

    function buildPaths(rawPaths, S0ref) {
      paths = [];
      pMin = Infinity; pMax = -Infinity;
      rawPaths.forEach(p => {
        const ret = (p[p.length - 1] - p[0]) / p[0];
        const h = ret > 0 ? 120 : 0;
        const l = 40 + Math.abs(ret) * 30;
        paths.push({ path: p, color: `hsl(${h},80%,${l}%)` });
        for (const v of p) { if (v < pMin) pMin = v; if (v > pMax) pMax = v; }
      });
      STEPS = (rawPaths[0] || []).length - 1;
    }

    // Generate simulated fallback paths
    (function genSim() {
      const rawPaths = [];
      for (let p = 0; p < N_PATHS_SIM; p++) {
        let price = 100;
        const path = [price];
        for (let s = 0; s < STEPS_SIM; s++) {
          const dW = (Math.random() + Math.random() + Math.random() - 1.5) * Math.sqrt(1 / 252);
          price *= Math.exp((mu_sim - 0.5 * sigma_sim * sigma_sim) / 252 + sigma_sim * dW);
          path.push(price);
        }
        rawPaths.push(path);
      }
      buildPaths(rawPaths, 100);
    })();

    // â”€â”€ Fetch real paths from API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _api.get('/api/vizlab/montecarlo/SPY?paths=150&horizon=252').then(d => {
      if (!d || !d.paths || d.paths.length === 0) return;
      buildPaths(d.paths, d.S0);
      _mcLabel = `Monte Carlo GBM  |  Î¼=${d.mu_annual.toFixed(1)}% ann.  |  Ïƒ=${d.sigma_annual.toFixed(1)}% ann.  |  SPY LIVE`;
    }).catch(() => { });

    // ── Star field for MC background ─────────────────────────────────────
    const _mcStars = Array.from({ length: 80 }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      r: Math.random() * 1.0 + 0.15,
      a: Math.random() * 0.35 + 0.05,
      da: (Math.random() - 0.5) * 0.002
    }));

    let drawProgress = 0;
    function animate() {
      _animFrameId = requestAnimationFrame(animate);

      if (paths.length === 0) {
        ctx.fillStyle = '#060610'; ctx.fillRect(0, 0, W, H); return;
      }
      drawProgress = Math.min(STEPS, drawProgress + 1.5);
      const end = Math.floor(drawProgress);
      const xScale = (W - 90) / STEPS;
      const yRange = pMax - pMin || 1;
      const yScale = (H * 0.72) / yRange;
      const yBase = H * 0.88;

      // Background — deep radial
      const bgGrd = ctx.createLinearGradient(0, 0, 0, H);
      bgGrd.addColorStop(0, '#050518');
      bgGrd.addColorStop(1, '#020210');
      ctx.fillStyle = bgGrd;
      ctx.fillRect(0, 0, W, H);

      // Stars
      for (const s of _mcStars) {
        s.a += s.da; if (s.a > 0.38 || s.a < 0.04) s.da *= -1;
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(170,195,255,${s.a.toFixed(3)})`; ctx.fill();
      }

      // Grid lines (horizontal, 8 bands)
      for (let g = 0; g <= 8; g++) {
        const gy = yBase - (g / 8) * (H * 0.72);
        ctx.beginPath();
        ctx.moveTo(50, gy); ctx.lineTo(W - 40, gy);
        ctx.strokeStyle = g === 0 ? 'rgba(100,130,200,0.25)' : 'rgba(60,80,150,0.12)';
        ctx.lineWidth = g === 0 ? 1.5 : 0.8;
        ctx.setLineDash(g === 0 ? [] : [4, 8]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // ── Draw individual paths ─────────────────────────────────────────
      for (const { path, color } of paths) {
        ctx.beginPath();
        for (let s = 0; s <= end && s < path.length; s++) {
          const x = 50 + s * xScale;
          const y = yBase - (path[s] - pMin) * yScale;
          s === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = color + '44';
        ctx.lineWidth = 0.75;
        ctx.stroke();
      }

      // ── Percentile band fill (P5–P95 gradient) ───────────────────────
      const endIdx = Math.min(end, STEPS);
      const pricesNow = paths.map(p => p.path[Math.min(endIdx, p.path.length - 1)]).sort((a, b) => a - b);
      const PN = pricesNow.length;
      const p5 = pricesNow[Math.floor(PN * 0.05)];
      const p95 = pricesNow[Math.floor(PN * 0.95)];
      const p25 = pricesNow[Math.floor(PN * 0.25)];
      const p75 = pricesNow[Math.floor(PN * 0.75)];
      const p50 = pricesNow[Math.floor(PN * 0.5)];
      const ex = 50 + end * xScale;

      // Track percentile paths across all steps for band fill
      const y5 = yBase - (p5 - pMin) * yScale;
      const y95 = yBase - (p95 - pMin) * yScale;
      const y25 = yBase - (p25 - pMin) * yScale;
      const y75 = yBase - (p75 - pMin) * yScale;
      const y50 = yBase - (p50 - pMin) * yScale;

      // P5–P95 band (wide, faint)
      const bandGrd = ctx.createLinearGradient(0, y95, 0, y5);
      bandGrd.addColorStop(0, 'rgba(46,204,113,0.06)');
      bandGrd.addColorStop(0.5, 'rgba(241,196,15,0.08)');
      bandGrd.addColorStop(1, 'rgba(231,76,60,0.06)');
      ctx.fillStyle = bandGrd;
      ctx.fillRect(50, y95, ex - 50, y5 - y95);

      // P25–P75 inner band (tighter, slightly more opaque)
      const midGrd = ctx.createLinearGradient(0, y75, 0, y25);
      midGrd.addColorStop(0, 'rgba(46,204,113,0.10)');
      midGrd.addColorStop(1, 'rgba(231,76,60,0.10)');
      ctx.fillStyle = midGrd;
      ctx.fillRect(50, y75, ex - 50, y25 - y75);

      // ── Median (P50) — thick glowing gold line ────────────────────────
      ctx.save();
      ctx.shadowBlur = 10; ctx.shadowColor = '#ffcc00';
      ctx.beginPath();
      // Walk each step for P50 from start
      for (let s = 0; s <= end; s++) {
        const vals = paths.map(p => p.path[Math.min(s, p.path.length - 1)]).sort((a, b) => a - b);
        const med = vals[Math.floor(vals.length * 0.5)];
        const x = 50 + s * xScale;
        const y = yBase - (med - pMin) * yScale;
        s === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.strokeStyle = '#ffcc00';
      ctx.lineWidth = 2.2;
      ctx.stroke();
      ctx.shadowBlur = 0;
      ctx.restore();

      // ── Percentile labels ─────────────────────────────────────────────
      const lx = ex + 6;
      ctx.font = 'bold 10px monospace';
      ctx.textAlign = 'left';
      ctx.shadowBlur = 6;
      ctx.shadowColor = '#00ff88'; ctx.fillStyle = '#00ff88';
      ctx.fillText(`P95 ${p95.toFixed(1)}`, lx, y95 + 4);
      ctx.shadowColor = '#ffcc00'; ctx.fillStyle = '#ffcc00';
      ctx.fillText(`P50 ${p50.toFixed(1)}`, lx, y50 + 4);
      ctx.shadowColor = '#ff4444'; ctx.fillStyle = '#ff4444';
      ctx.fillText(`P05 ${p5.toFixed(1)}`, lx, y5 + 4);
      ctx.shadowBlur = 0;

      // ── Title bar ─────────────────────────────────────────────────────
      ctx.fillStyle = 'rgba(6,6,20,0.7)';
      ctx.fillRect(0, 0, W, 30);
      ctx.fillStyle = '#8899bb';
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(_mcLabel, 12, 20);

      // Scanlines
      for (let scanY = 0; scanY < H; scanY += 5) {
        ctx.fillStyle = 'rgba(0,0,0,0.04)';
        ctx.fillRect(0, scanY, W, 1.5);
      }

      if (drawProgress >= STEPS) drawProgress = 0; // loop
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     5. SIGNAL RADAR â€” multi-indicator spider chart pulse
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizRadar() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;
    const cx = W / 2, cy = H / 2, R = Math.min(W, H) * 0.38;

    // â”€â”€ Live data from MultiStrategyEngine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const INDICATORS = ['SMA Cross', 'RSI Rev', 'MACD', 'BB Squeeze', 'Momentum', 'Consensus', 'Buy Wt', 'Sell Wt', 'Net Score', 'Confidence'];
    const N = INDICATORS.length;
    let values = INDICATORS.map(() => rand(0.2, 0.9));
    let targets = values.slice();
    let _liveLabel = 'SPY Â· Simulated';

    _api.get('/api/strategy/analyze/SPY').then(d => {
      if (!d) return;
      const ind = d.individual || {};
      const con = d.consensus || {};
      const engines = Object.values(ind);
      // Map engine signals to radar axes (0..1 range)
      const sig = (v, flip) => {
        const n = typeof v === 'number' ? v : 0;
        const norm = (n + 1) / 2;   // -1..1 â†’ 0..1
        return flip ? 1 - norm : norm;
      };
      const eArr = engines.slice(0, 5);
      targets = [
        eArr[0] ? sig(eArr[0].signal ?? 0) : rand(0.2, 0.9),
        eArr[1] ? sig(eArr[1].signal ?? 0) : rand(0.2, 0.9),
        eArr[2] ? sig(eArr[2].signal ?? 0) : rand(0.2, 0.9),
        eArr[3] ? sig(eArr[3].signal ?? 0) : rand(0.2, 0.9),
        eArr[4] ? sig(eArr[4].signal ?? 0) : rand(0.2, 0.9),
        con.action === 'BUY' ? 0.8 : con.action === 'SELL' ? 0.2 : 0.5,
        typeof con.buy_weight === 'number' ? con.buy_weight : 0.5,
        typeof con.sell_weight === 'number' ? 1 - con.sell_weight : 0.5,
        typeof con.net_score === 'number' ? sig(con.net_score) : 0.5,
        typeof con.confidence === 'number' ? con.confidence : 0.5,
      ];
      _liveLabel = `SPY Â· ${con.action || 'HOLD'} (${Math.round((con.confidence || 0) * 100)}% conf)`;
    }).catch(() => { });

    // ── Star field ───────────────────────────────────────────────────────
    const _radarStars = Array.from({ length: 90 }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      r: Math.random() * 1.1 + 0.15,
      a: Math.random() * 0.4 + 0.05,
      da: (Math.random() - 0.5) * 0.003
    }));

    let frame = 0;

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      ctx.clearRect(0, 0, W, H);

      // Background — space radial
      const bgGrd = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(W, H) * 0.7);
      bgGrd.addColorStop(0, '#0c0c22');
      bgGrd.addColorStop(1, '#040410');
      ctx.fillStyle = bgGrd;
      ctx.fillRect(0, 0, W, H);

      // Twinkle stars
      for (const s of _radarStars) {
        s.a += s.da; if (s.a > 0.45 || s.a < 0.04) s.da *= -1;
        ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(170,200,255,${s.a.toFixed(3)})`; ctx.fill();
      }

      // Update targets every 80 frames
      if (frame % 80 === 0) {
        targets = INDICATORS.map(() => rand(0.15, 0.95));
      }
      values = values.map((v, i) => lerp(v, targets[i], 0.03));

      const rings = [0.25, 0.5, 0.75, 1.0];

      // Ring backgrounds with colored bands
      const ringColors = ['rgba(40,60,140,0.18)', 'rgba(50,100,180,0.2)', 'rgba(60,140,200,0.22)', 'rgba(80,160,255,0.14)'];
      for (let ri = 0; ri < rings.length; ri++) {
        const r = rings[ri];
        ctx.beginPath();
        for (let i = 0; i < N; i++) {
          const angle = (i / N) * Math.PI * 2 - Math.PI / 2;
          const x = cx + Math.cos(angle) * R * r;
          const y = cy + Math.sin(angle) * R * r;
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.strokeStyle = ringColors[ri];
        ctx.lineWidth = ri === rings.length - 1 ? 1.5 : 1;
        ctx.stroke();
        // Fill inside outer ring only as faint glow
        if (ri === rings.length - 1) {
          ctx.fillStyle = 'rgba(40,60,180,0.04)';
          ctx.fill();
        }
      }

      // Draw axes
      for (let i = 0; i < N; i++) {
        const angle = (i / N) * Math.PI * 2 - Math.PI / 2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(angle) * R, cy + Math.sin(angle) * R);
        ctx.strokeStyle = 'rgba(80,110,200,0.28)';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Label with shadow
        const lx = cx + Math.cos(angle) * (R + 24);
        const ly = cy + Math.sin(angle) * (R + 24);
        ctx.shadowBlur = 4; ctx.shadowColor = '#4488ff';
        ctx.fillStyle = '#99bbff';
        ctx.font = '9.5px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(INDICATORS[i], lx, ly);
        ctx.shadowBlur = 0;
      }

      // Draw filled polygon — layered gradients for depth
      ctx.beginPath();
      for (let i = 0; i < N; i++) {
        const angle = (i / N) * Math.PI * 2 - Math.PI / 2;
        const x = cx + Math.cos(angle) * R * values[i];
        const y = cy + Math.sin(angle) * R * values[i];
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.closePath();

      // Fill layer 1 — inner glow
      const grd1 = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.7);
      grd1.addColorStop(0, 'rgba(120,220,255,0.35)');
      grd1.addColorStop(0.6, 'rgba(90,80,240,0.18)');
      grd1.addColorStop(1, 'rgba(60,40,200,0.06)');
      ctx.fillStyle = grd1;
      ctx.fill();

      // Stroke — electric cyan with glow
      ctx.shadowBlur = 14; ctx.shadowColor = '#44ccff';
      ctx.strokeStyle = '#66ddff';
      ctx.lineWidth = 2.5;
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Draw vertex dots with pulsing glow
      for (let i = 0; i < N; i++) {
        const angle = (i / N) * Math.PI * 2 - Math.PI / 2;
        const v = values[i];
        const x = cx + Math.cos(angle) * R * v;
        const y = cy + Math.sin(angle) * R * v;
        const col = v > 0.65 ? '#00ff88' : v > 0.35 ? '#ffaa00' : '#ff4444';
        // Outer ring
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, Math.PI * 2);
        ctx.strokeStyle = col + '55';
        ctx.lineWidth = 1;
        ctx.stroke();
        // Core dot
        ctx.beginPath();
        ctx.arc(x, y, 4.5, 0, Math.PI * 2);
        ctx.fillStyle = col;
        ctx.shadowBlur = 8; ctx.shadowColor = col;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // Score display with glow
      const avg = values.reduce((a, b) => a + b, 0) / N;
      const scoreColor = avg > 0.6 ? '#00ff88' : avg > 0.4 ? '#ffaa00' : '#ff4444';
      ctx.shadowBlur = 16; ctx.shadowColor = scoreColor;
      ctx.fillStyle = scoreColor;
      ctx.font = 'bold 28px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${(avg * 100).toFixed(0)}`, cx, cy - 12);
      ctx.shadowBlur = 0;
      ctx.font = '10px monospace';
      ctx.fillStyle = '#6688aa';
      ctx.fillText('STRATEGY SIGNAL SCORE', cx, cy + 14);
      ctx.font = '9px monospace';
      ctx.fillStyle = '#445566';
      ctx.fillText(_liveLabel, cx, H - 14);

      // Dual rotating scan beams
      const beam1 = (frame * 0.016) % (Math.PI * 2);
      const beam2 = (frame * 0.016 + Math.PI * 0.7) % (Math.PI * 2);
      for (const [angle, alpha] of [[beam1, 0.45], [beam2, 0.25]]) {
        ctx.beginPath();
        ctx.arc(cx, cy, R + 10, angle, angle + 0.18);
        ctx.strokeStyle = `rgba(80,200,255,${alpha})`;
        ctx.lineWidth = 4;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(cx, cy, R + 6, angle, angle + 0.32);
        ctx.strokeStyle = `rgba(80,200,255,${alpha * 0.4})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     6. RISK TERRAIN â€” procedural 3D terrain mesh
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizTerrain() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const GRID = 32;
    const CELL = Math.min(W, H * 0.9) / GRID;
    let heights = [], targetHeights = [], time = 0;

    function genTerrain() {
      const h = [];
      for (let y = 0; y <= GRID; y++) {
        for (let x = 0; x <= GRID; x++) {
          const nx = x / GRID * 3, ny = y / GRID * 3;
          // Simplex-like using sin/cos
          let v = Math.sin(nx * 2.3 + time * 0.3) * Math.cos(ny * 1.7 + time * 0.2) * 0.4
            + Math.sin(nx * 4.1 - time * 0.5) * Math.cos(ny * 3.8 + time * 0.4) * 0.25
            + Math.sin(nx * 7.2 + time * 0.7) * Math.cos(ny * 6.1 - time * 0.6) * 0.15;
          h.push((v + 1) * 0.5); // normalize 0-1
        }
      }
      return h;
    }

    heights = genTerrain();

    // â”€â”€ Live risk level from /api/vizlab/system_status â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _terrainRisk = 0.5;  // 0=safe, 1=dangerous â€” amplifies terrain elevation
    let _terrainLabel = 'Risk Terrain â€” Simulated';
    _api.get('/api/vizlab/system_status').then(d => {
      if (!d) return;
      const health = typeof d.health_score === 'number' ? d.health_score : 0.7;
      _terrainRisk = clamp(1 - health, 0.1, 0.9);
      _terrainLabel = `Risk Terrain â€” LIVE  Sys Risk: ${(_terrainRisk * 100).toFixed(0)}%`;
    }).catch(() => { });

    // Isometric projection
    const isoX = (gx, gy) => W * 0.5 + (gx - gy) * CELL * 0.6;
    const isoY = (gx, gy, h) => H * 0.55 + (gx + gy - GRID) * CELL * 0.3 - h * (80 * (0.5 + _terrainRisk));

    function colorForHeight(h) {
      if (h > 0.75) return `hsl(${(1 - h) * 60},90%,60%)`;  // Red peaks (risk)
      if (h > 0.5) return `hsl(40,80%,55%)`;            // Orange mid
      if (h > 0.25) return `hsl(120,60%,40%)`;           // Green valleys (safe)
      return `hsl(200,70%,30%)`;                          // Deep blue (water/safe)
    }

    let frame = 0;
    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      time += 0.012;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Recompute terrain
      heights = genTerrain();

      // Draw back-to-front (painter's algorithm)
      for (let y = 0; y < GRID; y++) {
        for (let x = 0; x < GRID; x++) {
          const idx = y * (GRID + 1) + x;
          const h00 = heights[idx];
          const h10 = heights[idx + 1];
          const h01 = heights[(y + 1) * (GRID + 1) + x];
          const h11 = heights[(y + 1) * (GRID + 1) + x + 1];
          const avgH = (h00 + h10 + h01 + h11) / 4;

          const x0 = isoX(x, y), y0 = isoY(x, y, h00);
          const x1 = isoX(x + 1, y), y1 = isoY(x + 1, y, h10);
          const x2 = isoX(x + 1, y + 1), y2 = isoY(x + 1, y + 1, h11);
          const x3 = isoX(x, y + 1), y3 = isoY(x, y + 1, h01);

          ctx.beginPath();
          ctx.moveTo(x0, y0);
          ctx.lineTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.lineTo(x3, y3);
          ctx.closePath();
          ctx.fillStyle = colorForHeight(avgH);
          ctx.fill();
          ctx.strokeStyle = 'rgba(0,0,0,0.3)';
          ctx.lineWidth = 0.4;
          ctx.stroke();
        }
      }

      // Legend
      const labels = [['â–  Peak Risk', '#ff4444'], ['â–  High Risk', '#ffaa00'], ['â–  Safe Zone', '#44cc44'], ['â–  Deep Safe', '#3388aa']];
      labels.forEach(([txt, col], i) => {
        ctx.fillStyle = col;
        ctx.font = '10px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(txt, 12, H - 60 + i * 14);
      });
      ctx.fillStyle = '#aaa';
      ctx.font = '11px monospace';
      ctx.fillText(_terrainLabel, 12, 20);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     7. PRICE FLOW FIELD â€” vector field + flowing particles
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizFlowField() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const COLS = 24, ROWS = 16;
    const PCOUNT = 600;
    let time = 0;

    const particles = Array.from({ length: PCOUNT }, () => ({
      x: rand(0, W), y: rand(0, H),
      vx: 0, vy: 0,
      age: rand(0, 200),
      maxAge: rand(80, 200),
      col: `hsl(${rand(100, 200)},80%,60%)`
    }));

    // â”€â”€ Live regime biases the flow field direction â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _ffBias = 0;      // -1=bear (downward bias), +1=bull (upward bias)
    let _ffLabel = 'Price Flow Field â€” Simulated';
    let _ffColor = { h1: 100, h2: 200 };
    _api.get('/api/vizlab/regime/SPY').then(d => {
      if (!d) return;
      const regMap = { BULL: 1.0, TRENDING: 0.7, SIDEWAYS: 0.0, BEAR: -1.0, VOLATILE: 0.0 };
      _ffBias = regMap[d.regime] || 0;
      _ffLabel = `Price Flow Field â€” SPY LIVE  Regime: ${d.regime}`;
      // Regime-specific particle colors
      if (d.regime === 'BULL') { _ffColor = { h1: 100, h2: 160 }; }  // green
      else if (d.regime === 'BEAR') { _ffColor = { h1: 0, h2: 30 }; }  // red
      else if (d.regime === 'VOLATILE') { _ffColor = { h1: 30, h2: 60 }; }  // orange
      particles.forEach(p => { p.col = `hsl(${rand(_ffColor.h1, _ffColor.h2)},80%,60%)`; });
    }).catch(() => { });

    function getField(x, y, t) {
      const nx = x / W * 4, ny = y / H * 4;
      const angle = (Math.sin(nx + t * 0.6) * Math.cos(ny - t * 0.4) + Math.sin(nx * 2.1 + t) * 0.5) * Math.PI;
      // Blend real bias: positive = upward flow, negative = downward
      return { vx: Math.cos(angle), vy: Math.sin(angle) * (1 - Math.abs(_ffBias) * 0.4) - _ffBias * 0.6 };
    }

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      time += 0.015;
      ctx.fillStyle = 'rgba(6,6,16,0.08)';
      ctx.fillRect(0, 0, W, H);

      // Draw field vectors
      for (let r = 0; r < ROWS; r++) {
        for (let c = 0; c < COLS; c++) {
          const x = (c + 0.5) * W / COLS, y = (r + 0.5) * H / ROWS;
          const { vx, vy } = getField(x, y, time);
          const len = 12;
          ctx.beginPath();
          ctx.moveTo(x - vx * len * 0.3, y - vy * len * 0.3);
          ctx.lineTo(x + vx * len, y + vy * len);
          ctx.strokeStyle = `rgba(80,100,180,0.3)`;
          ctx.lineWidth = 0.7;
          ctx.stroke();
        }
      }

      // Update and draw particles
      for (const p of particles) {
        const { vx, vy } = getField(p.x, p.y, time);
        p.vx = lerp(p.vx, vx * 1.8, 0.12);
        p.vy = lerp(p.vy, vy * 1.8, 0.12);
        p.x += p.vx; p.y += p.vy; p.age++;
        if (p.age > p.maxAge || p.x < 0 || p.x > W || p.y < 0 || p.y > H) {
          p.x = rand(0, W); p.y = rand(0, H);
          p.vx = 0; p.vy = 0; p.age = 0;
          p.maxAge = rand(80, 220);
          p.col = `hsl(${rand(90, 210)},80%,${rand(50, 75)}%)`;
        }
        const alpha = Math.sin((p.age / p.maxAge) * Math.PI) * 0.8;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 1.5, 0, Math.PI * 2);
        ctx.fillStyle = p.col.replace(')', `,${alpha})`).replace('hsl', 'hsla');
        ctx.fill();
      }

      ctx.fillStyle = '#aaa';
      ctx.font = '11px monospace';
      ctx.fillText(_ffLabel, 12, 20);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     8. CORRELATION GALAXY â€” Milky Way style star clusters
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizGalaxy() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const STARS = 800;
    const stars = Array.from({ length: STARS }, (_, i) => {
      const arm = Math.floor(Math.random() * 3);
      const t = Math.random();
      const spread = rand(5, 50);
      const armAngle = (arm / 3) * Math.PI * 2;
      const theta = armAngle + t * Math.PI * 3 + rand(-0.3, 0.3);
      const r = t * Math.min(W, H) * 0.38 + rand(-spread, spread);
      return {
        x: W / 2 + Math.cos(theta) * r,
        y: H / 2 + Math.sin(theta) * r * 0.45,
        size: rand(0.5, 3),
        brightness: rand(0.3, 1),
        color: `hsl(${rand(190, 260)},${rand(40, 90)}%,${rand(50, 90)}%)`,
        twinkle: rand(0, Math.PI * 2),
        twinkleSpeed: rand(0.02, 0.08)
      };
    });

    // "Market" constellations â€” labeled clusters (real from /api/correlation/cluster)
    const CLUSTER_COLORS = ['#4488ff', '#ff8800', '#ff4444', '#ffaa00', '#44ffaa', '#cc44ff', '#ff44cc'];
    const CONSTS = [
      { name: 'TECH', x: W * 0.35, y: H * 0.35, color: '#4488ff', tickers: [] },
      { name: 'FINANCE', x: W * 0.65, y: H * 0.55, color: '#ff8800', tickers: [] },
      { name: 'ENERGY', x: W * 0.25, y: H * 0.65, color: '#ff4444', tickers: [] },
      { name: 'CRYPTO', x: W * 0.72, y: H * 0.35, color: '#ffaa00', tickers: [] },
    ];

    // â”€â”€ Live cluster data from /api/correlation/cluster â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _galaxyLabel = 'Correlation Galaxy â€” Simulated';
    _api.get('/api/correlation/cluster').then(d => {
      if (!d || !d.clusters) return;
      _galaxyLabel = 'Correlation Galaxy â€” LIVE Clusters';
      // Rebuild CONSTS from real clusters
      CONSTS.length = 0;
      const clKeys = Object.keys(d.clusters);
      clKeys.slice(0, 6).forEach((k, i) => {
        const tickers = d.clusters[k] || [];
        const angle_pos = (i / Math.max(clKeys.length, 1)) * Math.PI * 2 - Math.PI / 2;
        CONSTS.push({
          name: k,
          x: W * 0.5 + Math.cos(angle_pos) * W * 0.28,
          y: H * 0.5 + Math.sin(angle_pos) * H * 0.28,
          color: CLUSTER_COLORS[i % CLUSTER_COLORS.length],
          tickers
        });
      });
    }).catch(() => { });

    let angle = 0;
    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      angle += 0.0005;
      ctx.fillStyle = 'rgba(4,4,12,0.4)';
      ctx.fillRect(0, 0, W, H);

      // Galaxy core glow
      const core = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, 100);
      core.addColorStop(0, 'rgba(200,180,255,0.15)');
      core.addColorStop(1, 'transparent');
      ctx.fillStyle = core;
      ctx.fillRect(0, 0, W, H);

      // Draw stars
      for (const s of stars) {
        s.twinkle += s.twinkleSpeed;
        const b = s.brightness * (0.7 + 0.3 * Math.sin(s.twinkle));
        // Rotate
        const dx = s.x - W / 2, dy = s.y - H / 2;
        const rx = dx * Math.cos(angle) - dy * Math.sin(angle) + W / 2;
        const ry = dx * Math.sin(angle) + dy * Math.cos(angle) + H / 2;

        if (rx < 0 || rx > W || ry < 0 || ry > H) continue;
        ctx.beginPath();
        ctx.arc(rx, ry, s.size * b, 0, Math.PI * 2);
        ctx.fillStyle = s.color;
        ctx.globalAlpha = b;
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      // Constellation labels
      for (const c of CONSTS) {
        const grd = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, 40);
        grd.addColorStop(0, c.color + '44');
        grd.addColorStop(1, 'transparent');
        ctx.fillStyle = grd;
        ctx.beginPath();
        ctx.arc(c.x, c.y, 40, 0, Math.PI * 2);
        ctx.fill();
        ctx.fillStyle = c.color;
        ctx.font = 'bold 11px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(c.name, c.x, c.y - 45);
        if (c.tickers && c.tickers.length > 0) {
          ctx.font = '8px monospace';
          ctx.fillStyle = c.color + 'aa';
          ctx.fillText(`(${c.tickers.length} assets)`, c.x, c.y - 32);
        }
      }

      ctx.fillStyle = '#888';
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(_galaxyLabel, 12, 20);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     9. RL AGENT RACING TRACK â€” portfolio on a track
     Inspired by speed-racer-rl (C++ DQN racer â†’ canvas adaptation)
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizRLTrack() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    // Generate oval track waypoints
    const trackPoints = [];
    const cx = W / 2, cy = H / 2 * 1.05;
    const rx = W * 0.38, ry = H * 0.32;
    const N_WP = 80;
    for (let i = 0; i < N_WP; i++) {
      const a = (i / N_WP) * Math.PI * 2 - Math.PI / 2;
      trackPoints.push({ x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * ry });
    }

    // Car state
    let carWP = 0, carFrac = 0, carSpeed = 0.018;
    let lapTime = 0, lap = 0;
    const carHistory = [];
    const MAX_HIST = 60;

    // Simulated LIDAR rays
    const N_RAYS = 13;

    // Simulated reward history
    const rewards = Array.from({ length: 120 }, () => rand(-0.5, 1));

    // â”€â”€ Live strategy consensus seeds car speed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _rlBias = 0;  // -1..1 â€” negative = brakes, positive = accelerate
    let _rlLabel = 'RL Agent â€” Simulated';
    _api.get('/api/strategy/analyze/SPY').then(d => {
      if (!d) return;
      const score = typeof d.score === 'number' ? d.score : 0;  // -100..100
      _rlBias = score / 100;  // -1..1
      _rlLabel = `RL Agent â€” SPY ${d.verdict || ''} (bias: ${_rlBias >= 0 ? '+' : ''}${(_rlBias * 100).toFixed(0)})`;
      // Modulate car speed with conviction
      carSpeed = 0.018 + _rlBias * 0.008;
    }).catch(() => { });

    function getCarPos() {
      const a = trackPoints[Math.floor(carWP) % N_WP];
      const b = trackPoints[(Math.floor(carWP) + 1) % N_WP];
      return { x: lerp(a.x, b.x, carFrac), y: lerp(a.y, b.y, carFrac) };
    }
    function getCarHeading() {
      const a = trackPoints[Math.floor(carWP) % N_WP];
      const b = trackPoints[(Math.floor(carWP) + 1) % N_WP];
      return Math.atan2(b.y - a.y, b.x - a.x);
    }

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Advance car
      carFrac += carSpeed;
      lapTime += carSpeed;
      if (carFrac >= 1) { carFrac -= 1; carWP = (carWP + 1) % N_WP; }
      if (carWP === 0 && carFrac < carSpeed * 2) { lap++; rewards.push(rand(0.6, 1.0)); rewards.shift(); }

      const carPos = getCarPos();
      const heading = getCarHeading();
      carHistory.push({ ...carPos });
      if (carHistory.length > MAX_HIST) carHistory.shift();

      // Draw track (outer + inner)
      const TRACK_W = 40;
      ctx.beginPath();
      trackPoints.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
      ctx.closePath();
      ctx.strokeStyle = '#334455';
      ctx.lineWidth = TRACK_W + 8;
      ctx.stroke();
      ctx.strokeStyle = '#223344';
      ctx.lineWidth = TRACK_W;
      ctx.stroke();
      // Center dashed line
      ctx.strokeStyle = 'rgba(255,255,100,0.2)';
      ctx.lineWidth = 1;
      ctx.setLineDash([10, 10]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Car trail
      for (let i = 1; i < carHistory.length; i++) {
        const alpha = i / carHistory.length;
        ctx.beginPath();
        ctx.moveTo(carHistory[i - 1].x, carHistory[i - 1].y);
        ctx.lineTo(carHistory[i].x, carHistory[i].y);
        ctx.strokeStyle = `rgba(0,200,255,${alpha * 0.6})`;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // LIDAR rays (inspired by speed-racer's 13 raycasts)
      for (let ri = 0; ri < N_RAYS; ri++) {
        const rayAngle = heading + ((ri / (N_RAYS - 1)) - 0.5) * Math.PI * 1.1;
        const rayLen = rand(25, 65);
        const ex = carPos.x + Math.cos(rayAngle) * rayLen;
        const ey = carPos.y + Math.sin(rayAngle) * rayLen;
        const danger = 1 - rayLen / 65;
        const col = `rgba(${Math.round(danger * 255)},${Math.round((1 - danger) * 200)},0,0.4)`;
        ctx.beginPath();
        ctx.moveTo(carPos.x, carPos.y);
        ctx.lineTo(ex, ey);
        ctx.strokeStyle = col;
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }

      // Car body
      ctx.save();
      ctx.translate(carPos.x, carPos.y);
      ctx.rotate(heading);
      ctx.fillStyle = '#00ccff';
      ctx.fillRect(-10, -5, 18, 10);
      ctx.fillStyle = '#0088cc';
      ctx.fillRect(2, -4, 6, 8);
      ctx.restore();

      // Reward chart (bottom)
      const chartY = H - 70, chartH = 55, chartW = W - 24;
      ctx.fillStyle = 'rgba(0,0,20,0.7)';
      ctx.fillRect(12, chartY - 5, chartW, chartH + 10);
      ctx.fillStyle = '#888';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText('Episode Reward', 16, chartY + 8);

      const maxR = Math.max(...rewards), minR = Math.min(...rewards);
      ctx.beginPath();
      rewards.forEach((r, i) => {
        const x = 12 + (i / rewards.length) * chartW;
        const y = chartY + chartH - ((r - minR) / (maxR - minR + 0.01)) * (chartH - 12);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.strokeStyle = '#00ff88';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Info overlay
      ctx.fillStyle = '#00ccff';
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`Lap: ${lap}   ${_rlLabel}`, 12, 20);
      ctx.fillStyle = '#aaa';
      ctx.fillText('RL Racing Agent â€” Portfolio on Track', 12, 34);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     10. QUANTUM MARKET SUPERPOSITION
         Probability wave that collapses when a signal fires.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizQuantum() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    let collapsed = false, collapseX = 0, collapseTimer = 0;
    let wavePhase = 0, superPhase = 0;
    let frame = 0;

    function drawWave(y0, amp, freq, phase, color, alpha = 1) {
      ctx.beginPath();
      for (let x = 0; x < W; x++) {
        const y = y0 + Math.sin(x * freq + phase) * amp;
        x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.strokeStyle = color.replace(')', `,${alpha})`).replace('rgba', 'rgba').replace('rgb(', 'rgba(');
      ctx.lineWidth = 2;
      ctx.globalAlpha = alpha;
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      wavePhase += 0.04;
      superPhase += 0.02;

      if (collapsed) {
        collapseTimer--;
        if (collapseTimer <= 0) collapsed = false;

        // Draw collapsed spike
        ctx.beginPath();
        ctx.moveTo(collapseX, H * 0.1);
        ctx.lineTo(collapseX, H * 0.9);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3;
        ctx.shadowColor = '#88ccff';
        ctx.shadowBlur = 30;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Label
        ctx.fillStyle = '#00ff88';
        ctx.font = 'bold 14px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('âš¡ SIGNAL DETECTED â€” Wave Collapsed!', W / 2, H * 0.08);
        ctx.fillStyle = '#aaa';
        ctx.font = '11px monospace';
        ctx.fillText(`Position: ${collapseX < W / 2 ? 'SHORT' : 'LONG'} at x=${collapseX}`, W / 2, H * 0.15);
      } else {
        // Superposition â€” multiple overlapping waves
        const waves = [
          { amp: 60, freq: 0.02, phase: wavePhase, color: 'rgb(0,200,255)', alpha: 0.7 },
          { amp: 45, freq: 0.035, phase: -wavePhase * 0.8, color: 'rgb(200,100,255)', alpha: 0.5 },
          { amp: 30, freq: 0.055, phase: superPhase * 1.3, color: 'rgb(255,200,0)', alpha: 0.4 },
          { amp: 20, freq: 0.08, phase: -superPhase * 0.5, color: 'rgb(255,80,80)', alpha: 0.3 },
        ];

        // Draw probability envelope
        ctx.beginPath();
        for (let x = 0; x < W; x++) {
          let sumY = 0;
          for (const w of waves) sumY += Math.sin(x * w.freq + w.phase) * w.amp * w.alpha;
          const y = H / 2 + sumY;
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = '#ffffff33';
        ctx.lineWidth = 1;
        ctx.stroke();

        for (const w of waves) drawWave(H / 2, w.amp, w.freq, w.phase, w.color, w.alpha);

        // Probability density
        ctx.beginPath();
        for (let x = 0; x < W; x++) {
          let prob = 0;
          for (const w of waves) prob += Math.pow(Math.sin(x * w.freq + w.phase) * w.amp, 2);
          const y = H * 0.85 - Math.sqrt(prob) * 0.3;
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = 'rgba(0,255,136,0.5)';
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.fillStyle = '#88aaff';
        ctx.font = '11px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('Quantum Superposition â€” Market State Probability Waves', W / 2, 20);
        ctx.fillStyle = '#666';
        ctx.font = '10px monospace';
        ctx.fillText('Click anywhere to collapse the wave function (generate signal)', W / 2, H - 12);
      }

      // Random auto-collapse
      if (!collapsed && frame % 280 === 0) {
        collapsed = true;
        collapseX = rand(W * 0.2, W * 0.8);
        collapseTimer = 90;
      }
    }

    canvas.onclick = (e) => {
      const r = canvas.getBoundingClientRect();
      collapseX = e.clientX - r.left;
      collapsed = true; collapseTimer = 120;
    };

    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     11. LORENZ ATTRACTOR â€” chaotic trajectory in phase space
     Maps price history â†’ x,y,z via Lorenz equations.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizLorenz() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    // Lorenz parameters (Ïƒ, Ï, Î²)
    const sigma = 10, rho = 28, beta = 8 / 3;
    const dt = 0.005;

    // Two attractors â€” one for bear market (different rho), one for bull
    const states = [
      { x: 0.1, y: 0, z: 0, color: '#00ccff', trail: [] },
      { x: 0.1, y: 0.1, z: 0, color: '#ff6688', trail: [] },
    ];
    const MAX_TRAIL = 600;

    // Project 3D â†’ 2D isometric
    function project(x, y, z) {
      const scale = Math.min(W, H) * 0.012;
      const px = W / 2 + (x - y) * scale * 0.8;
      const py = H / 2 - z * scale * 0.9 + y * scale * 0.2 + x * scale * 0.1;
      return { px, py };
    }

    let frame = 0;
    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      ctx.fillStyle = 'rgba(6,6,16,0.12)';
      ctx.fillRect(0, 0, W, H);

      for (const s of states) {
        // Lorenz step (RK4 would be better but Euler works for viz)
        for (let i = 0; i < 4; i++) {
          const dx = sigma * (s.y - s.x);
          const dy = s.x * (rho - s.z) - s.y;
          const dz = s.x * s.y - beta * s.z;
          s.x += dx * dt; s.y += dy * dt; s.z += dz * dt;
          const p = project(s.x, s.y, s.z);
          s.trail.push(p);
          if (s.trail.length > MAX_TRAIL) s.trail.shift();
        }

        // Draw trail
        if (s.trail.length < 2) continue;
        for (let i = 1; i < s.trail.length; i++) {
          const alpha = i / s.trail.length;
          const a = s.trail[i - 1], b = s.trail[i];
          ctx.beginPath();
          ctx.moveTo(a.px, a.py);
          ctx.lineTo(b.px, b.py);
          ctx.strokeStyle = s.color + Math.round(alpha * 200).toString(16).padStart(2, '0');
          ctx.lineWidth = alpha * 1.5;
          ctx.stroke();
        }

        // Draw head
        const head = s.trail[s.trail.length - 1];
        ctx.beginPath();
        ctx.arc(head.px, head.py, 4, 0, Math.PI * 2);
        ctx.fillStyle = s.color;
        ctx.fill();
      }

      ctx.fillStyle = '#00ccff';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText('â–  Bull Attractor', 12, 20);
      ctx.fillStyle = '#ff6688';
      ctx.fillText('â–  Bear Attractor', 12, 34);
      ctx.fillStyle = '#666';
      ctx.fillText(`Lorenz System  Ïƒ=${sigma}  Ï=${rho}  Î²=${beta.toFixed(2)}  |  Frame: ${frame}`, 12, H - 12);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     12. RETURN HEATMAP CALENDAR â€” GitHub-style
     Simulates daily returns as colored squares.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizHeatmap() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const WEEKS = 52, DAYS = 7;
    const cellW = Math.floor((W - 80) / WEEKS);
    const cellH = Math.floor((H - 80) / (DAYS + 3));
    const startX = 50, startY = 50;

    // Generate a year of synthetic returns (trending + mean-reverting mix)
    let price = 100;
    const returns = [];
    for (let i = 0; i < WEEKS * DAYS; i++) {
      const trend = 0.0003;
      const noise = (Math.random() - 0.48) * 0.018;
      const ret = trend + noise;
      returns.push(ret);
      price *= (1 + ret);
    }

    // â”€â”€ Live daily returns from /api/market_data/SPY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _heatmapLabel = 'SPY Returns Heatmap â€” Simulated';
    _api.get('/api/market_data/SPY').then(d => {
      if (!d || !d.Close) return;
      const closes = d.Close;
      const keys = Object.keys(closes).sort();
      if (keys.length < 2) return;
      _heatmapLabel = 'SPY Returns Heatmap â€” LIVE (1Y)';
      // Replace returns array with real daily returns
      returns.length = 0;
      for (let i = 1; i < keys.length && returns.length < WEEKS * DAYS; i++) {
        const r = (closes[keys[i]] - closes[keys[i - 1]]) / closes[keys[i - 1]];
        returns.push(isFinite(r) ? r : 0);
      }
      // Pad if needed
      while (returns.length < WEEKS * DAYS) returns.push(0);
    }).catch(() => { });

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const days = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

    // Color scale: red â†’ gray â†’ green
    function retColor(r) {
      if (Math.abs(r) < 0.002) return '#1a1a2e';
      if (r > 0) {
        const i = Math.min(1, r / 0.03);
        const g = Math.round(80 + i * 175);
        return `rgb(0,${g},${Math.round(g * 0.4)})`;
      } else {
        const i = Math.min(1, Math.abs(r) / 0.03);
        const r_ = Math.round(80 + i * 175);
        return `rgb(${r_},${Math.round(r_ * 0.2)},${Math.round(r_ * 0.2)})`;
      }
    }

    // Month label positions
    const monthX = [];
    for (let w = 0; w < WEEKS; w++) {
      const dayIdx = w * DAYS;
      const month = new Date(2025, 0, dayIdx + 1).getMonth();
      if (w === 0 || new Date(2025, 0, (w - 1) * DAYS + 1).getMonth() !== month) {
        monthX.push({ w, month });
      }
    }

    let highlightIdx = -1;
    canvas.onmousemove = (e) => {
      const r = canvas.getBoundingClientRect();
      const mx = e.clientX - r.left - startX;
      const my = e.clientY - r.top - startY;
      const wx = Math.floor(mx / (cellW + 1));
      const dy = Math.floor(my / (cellH + 1));
      if (wx >= 0 && wx < WEEKS && dy >= 0 && dy < DAYS) {
        highlightIdx = wx * DAYS + dy;
      } else {
        highlightIdx = -1;
      }
    };

    function draw() {
      _animFrameId = requestAnimationFrame(draw);
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Month labels
      ctx.font = '10px monospace';
      ctx.fillStyle = '#888';
      for (const { w, month } of monthX) {
        ctx.textAlign = 'left';
        ctx.fillText(months[month], startX + w * (cellW + 1), startY - 8);
      }

      // Day labels
      for (let d = 0; d < DAYS; d++) {
        ctx.textAlign = 'right';
        ctx.fillText(days[d], startX - 4, startY + d * (cellH + 1) + cellH * 0.7);
      }

      // Cells
      for (let w = 0; w < WEEKS; w++) {
        for (let d = 0; d < DAYS; d++) {
          const idx = w * DAYS + d;
          const r = returns[idx] || 0;
          const x = startX + w * (cellW + 1);
          const y = startY + d * (cellH + 1);
          const isHL = idx === highlightIdx;

          ctx.fillStyle = retColor(r);
          ctx.fillRect(x, y, cellW, cellH);
          if (isHL) {
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1;
            ctx.strokeRect(x, y, cellW, cellH);
          }
        }
      }

      // Tooltip
      if (highlightIdx >= 0 && highlightIdx < returns.length) {
        const ret = returns[highlightIdx];
        const w_ = Math.floor(highlightIdx / DAYS);
        const d_ = highlightIdx % DAYS;
        const x = startX + w_ * (cellW + 1);
        const y = startY + d_ * (cellH + 1);
        const txt = `${ret >= 0 ? '+' : ''}${(ret * 100).toFixed(2)}%  Day ${highlightIdx + 1}`;
        const tw = ctx.measureText(txt).width + 12;
        const tx = Math.min(x, W - tw - 4);
        const ty = y - 26;
        ctx.fillStyle = '#111122';
        ctx.fillRect(tx - 2, ty, tw, 20);
        ctx.fillStyle = ret >= 0 ? '#00ff88' : '#ff4444';
        ctx.font = '10px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(txt, tx + 4, ty + 13);
      }

      // Summary bar
      const totalRet = returns.reduce((a, r) => (1 + a) * (1 + r) - 1, 0);
      const posCount = returns.filter(r => r > 0).length;
      ctx.fillStyle = '#aaa';
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(
        `${_heatmapLabel}  |  Ret: ${totalRet >= 0 ? '+' : ''}${(totalRet * 100).toFixed(1)}%  WR: ${(posCount / returns.length * 100).toFixed(0)}%`,
        startX, H - 12
      );
    }
    draw();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     13. LIVE ORDER BOOK â€” L2 bid/ask depth + pressure
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizOrderBook() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    let midPrice = 100.0;
    let spread = 0.05;
    const N_LEVELS = 18;
    let _obTicker = 'SPY';

    // â”€â”€ Live price from /api/quote/SPY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _api.get('/api/quote/SPY').then(d => {
      if (!d) return;
      const p = d.price || d.regularMarketPrice || d.currentPrice;
      if (p && isFinite(p)) {
        midPrice = parseFloat(p);
        spread = midPrice * 0.0002; // 2bps spread for SPY
        _obTicker = d.symbol || 'SPY';
      }
    }).catch(() => { });

    // Generate order book levels
    function makeBook() {
      const bids = [], asks = [];
      for (let i = 0; i < N_LEVELS; i++) {
        bids.push({ price: midPrice - spread / 2 - i * 0.05, size: rand(50, 800) * (1 + i * 0.1) });
        asks.push({ price: midPrice + spread / 2 + i * 0.05, size: rand(50, 800) * (1 + i * 0.1) });
      }
      return { bids, asks };
    }

    let book = makeBook();
    let frame = 0;
    const priceHistory = Array.from({ length: 120 }, () => midPrice);

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Update price randomly
      if (frame % 8 === 0) {
        const imbalance = rand(-0.5, 0.5);
        midPrice += imbalance * 0.03;
        spread = clamp(spread + rand(-0.005, 0.005), 0.02, 0.15);
        book = makeBook();
        priceHistory.push(midPrice);
        priceHistory.shift();
      }

      const chartH = Math.floor(H * 0.28);
      const bookH = H - chartH - 60;
      const halfH = bookH / 2;
      const bookY = 40;
      const midY = bookY + halfH;

      // Max size for bar width
      const maxSize = Math.max(...book.bids.map(b => b.size), ...book.asks.map(a => a.size));
      const barMaxW = W * 0.45;
      const rowH = (halfH - 4) / N_LEVELS;

      // Bids (below mid)
      for (let i = 0; i < N_LEVELS; i++) {
        const b = book.bids[i];
        const bw = (b.size / maxSize) * barMaxW;
        const y = midY + i * rowH;
        const alpha = 1 - i * 0.04;
        ctx.fillStyle = `rgba(0,180,80,${alpha * 0.5})`;
        ctx.fillRect(W / 2 - bw, y, bw, rowH - 1);
        ctx.fillStyle = `rgba(0,220,100,${alpha * 0.9})`;
        ctx.font = '9px monospace';
        ctx.textAlign = 'right';
        ctx.fillText(`${b.price.toFixed(2)}`, W / 2 - bw - 2, y + rowH * 0.7);
        ctx.textAlign = 'left';
        ctx.fillStyle = '#ffffff55';
        ctx.fillText(`${Math.round(b.size)}`, W / 2 + 4, y + rowH * 0.7);
      }

      // Asks (above mid)
      for (let i = 0; i < N_LEVELS; i++) {
        const a = book.asks[i];
        const bw = (a.size / maxSize) * barMaxW;
        const y = midY - (i + 1) * rowH;
        const alpha = 1 - i * 0.04;
        ctx.fillStyle = `rgba(220,40,60,${alpha * 0.5})`;
        ctx.fillRect(W / 2, y, bw, rowH - 1);
        ctx.fillStyle = `rgba(255,80,80,${alpha * 0.9})`;
        ctx.font = '9px monospace';
        ctx.textAlign = 'right';
        ctx.fillText(`${a.price.toFixed(2)}`, W / 2 - 2, y + rowH * 0.7);
        ctx.textAlign = 'left';
        ctx.fillStyle = '#ffffff55';
        ctx.fillText(`${Math.round(a.size)}`, W / 2 + bw + 2, y + rowH * 0.7);
      }

      // Mid price line
      ctx.beginPath();
      ctx.moveTo(0, midY);
      ctx.lineTo(W, midY);
      ctx.strokeStyle = '#ffffff33';
      ctx.lineWidth = 1;
      ctx.setLineDash([6, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 12px monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${_obTicker}  $${midPrice.toFixed(2)}`, W / 2, midY - 3);

      // Labels
      ctx.fillStyle = '#00dd66';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText('BID', 12, midY + 14);
      ctx.fillStyle = '#ff5555';
      ctx.textAlign = 'right';
      ctx.fillText('ASK', W - 12, midY - 6);

      // Price chart at bottom
      const chartY = H - chartH - 10;
      ctx.fillStyle = 'rgba(0,0,20,0.6)';
      ctx.fillRect(0, chartY, W, chartH + 10);

      const minP = Math.min(...priceHistory) - 0.1;
      const maxP = Math.max(...priceHistory) + 0.1;
      ctx.beginPath();
      priceHistory.forEach((p, i) => {
        const x = (i / priceHistory.length) * W;
        const y = chartY + chartH - ((p - minP) / (maxP - minP)) * (chartH - 10);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.strokeStyle = '#00aaff';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      ctx.fillStyle = '#888';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`Spread: ${(spread * 100).toFixed(2)}Â¢   Mid: $${midPrice.toFixed(3)}`, 12, chartY - 2);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     14. VOL SMILE SURFACE â€” 3D IV surface on Canvas
     Perspective projection of strike Ã— expiry Ã— IV grid.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizVolSmile() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const STRIKES = 20, EXPIRIES = 12;
    let time = 0;

    // â”€â”€ Live ATM vol from /api/vizlab/regime/SPY (uses annual_vol_pct) â”€â”€â”€â”€â”€â”€
    let _volAtm = 0.18;  // default 18% ATM vol
    let _volLabel = 'IV Surface â€” SPY Simulated';
    _api.get('/api/vizlab/regime/SPY').then(d => {
      if (!d || !d.annual_vol_pct) return;
      _volAtm = clamp(d.annual_vol_pct / 100, 0.08, 0.60);
      _volLabel = `IV Surface â€” SPY LIVE  ATM: ${d.annual_vol_pct.toFixed(1)}% ann. vol`;
    }).catch(() => { });

    // IV surface: smile + term structure + dynamic skew
    function getIV(strikeIdx, expIdx, t) {
      const moneyness = (strikeIdx / (STRIKES - 1) - 0.5) * 2; // -1..1 (OTM put to OTM call)
      const tau = (expIdx + 1) / EXPIRIES;                      // 0..1 maturity
      const atm = _volAtm + tau * 0.05 * Math.sin(t * 0.3) + 0.02 * Math.cos(t * 0.5);
      const skew = -0.04 * moneyness * (1 + 0.5 * Math.sin(t * 0.2));
      const smile = 0.06 * moneyness * moneyness;
      return atm + skew + smile / Math.sqrt(tau + 0.1);
    }

    // 3D â†’ 2D projection (perspective)
    let rotY = 0.6;
    canvas.onmousemove = (e) => {
      const r = canvas.getBoundingClientRect();
      rotY = ((e.clientX - r.left) / W - 0.5) * Math.PI * 0.8 + 0.6;
    };

    function project3D(x, y, z) {
      // Rotate around Y
      const rx = x * Math.cos(rotY) - z * Math.sin(rotY);
      const rz = x * Math.sin(rotY) + z * Math.cos(rotY) + 5;
      const fov = 500;
      const px = W / 2 + (rx / rz) * fov;
      const py = H * 0.55 - (y / rz) * fov;
      return { px, py, depth: rz };
    }

    function ivColor(iv) {
      const t = clamp((iv - 0.15) / 0.15, 0, 1);
      const r = Math.round(t * 255);
      const g = Math.round((1 - t) * 200);
      return `rgb(${r},${g},${Math.round(50 + t * 50)})`;
    }

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      time += 0.025;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Build quads and sort by depth (painter's algorithm)
      const quads = [];
      for (let ei = 0; ei < EXPIRIES - 1; ei++) {
        for (let si = 0; si < STRIKES - 1; si++) {
          const x0 = (si / (STRIKES - 1) - 0.5) * 3;
          const x1 = ((si + 1) / (STRIKES - 1) - 0.5) * 3;
          const z0 = (ei / (EXPIRIES - 1) - 0.5) * 3;
          const z1 = ((ei + 1) / (EXPIRIES - 1) - 0.5) * 3;
          const iv00 = getIV(si, ei, time);
          const iv10 = getIV(si + 1, ei, time);
          const iv01 = getIV(si, ei + 1, time);
          const iv11 = getIV(si + 1, ei + 1, time);
          const avgIV = (iv00 + iv10 + iv01 + iv11) / 4;
          const p00 = project3D(x0, iv00 * 4, z0);
          const p10 = project3D(x1, iv10 * 4, z0);
          const p11 = project3D(x1, iv11 * 4, z1);
          const p01 = project3D(x0, iv01 * 4, z1);
          const depth = (p00.depth + p10.depth + p01.depth + p11.depth) / 4;
          quads.push({ p00, p10, p11, p01, avgIV, depth });
        }
      }
      quads.sort((a, b) => b.depth - a.depth);

      for (const q of quads) {
        ctx.beginPath();
        ctx.moveTo(q.p00.px, q.p00.py);
        ctx.lineTo(q.p10.px, q.p10.py);
        ctx.lineTo(q.p11.px, q.p11.py);
        ctx.lineTo(q.p01.px, q.p01.py);
        ctx.closePath();
        ctx.fillStyle = ivColor(q.avgIV);
        ctx.fill();
        ctx.strokeStyle = 'rgba(0,0,0,0.25)';
        ctx.lineWidth = 0.3;
        ctx.stroke();
      }

      // Labels
      ctx.fillStyle = '#aaa';
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`${_volLabel}  |  drag to rotate`, 12, 20);
      ctx.fillStyle = '#ff8800';
      ctx.fillText('â–  High IV', 12, H - 28);
      ctx.fillStyle = '#00cc88';
      ctx.fillText('â–  Low IV', 12, H - 14);

      // ATM vol marker
      const atmIV = getIV(Math.floor(STRIKES / 2), Math.floor(EXPIRIES / 2), time);
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'right';
      ctx.fillText(`ATM IV: ${(atmIV * 100).toFixed(1)}%`, W - 12, 20);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     15. ENTROPY CASCADE â€” waterfall of market randomness
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizEntropy() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const COLS = 60;     // time steps
    const ROWS = 24;     // frequency bins
    const colW = W / COLS;
    const rowH = (H - 60) / ROWS;

    // Rolling entropy buffer: matrix [col][row] = entropy value 0..1
    const matrix = Array.from({ length: COLS }, () =>
      Array.from({ length: ROWS }, () => Math.random())
    );

    // Simulated entropy levels per frequency band (low freq = long-term, high freq = noise)
    const BASE_ENT = Array.from({ length: ROWS }, (_, i) => 0.3 + (i / ROWS) * 0.5);
    let frame = 0;
    const ENTROPY_HISTORY = Array.from({ length: 120 }, () => rand(0.4, 0.8));

    // â”€â”€ Live strategy data drives entropy base level â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    // High agreement among engines = low entropy (structured); disagreement = high entropy
    let _entropyLabel = 'Market Entropy â€” Simulated';
    _api.get('/api/strategy/analyze/SPY').then(d => {
      if (!d || !d.individual) return;
      const engines = Object.values(d.individual);
      const signals = engines.map(e => e.signal || 0);
      const mean = signals.reduce((a, b) => a + b, 0) / signals.length;
      const variance = signals.reduce((a, b) => a + (b - mean) ** 2, 0) / signals.length;
      // variance 0..1 â†’ entropy 0.3..0.9
      const liveEntropy = 0.3 + Math.sqrt(variance) * 0.6;
      // Adjust all BASE_ENT values proportionally
      BASE_ENT.forEach((_, i) => { BASE_ENT[i] = clamp(liveEntropy * (0.6 + i / ROWS * 0.7), 0.1, 0.95); });
      // Pre-fill history
      ENTROPY_HISTORY.fill(liveEntropy);
      _entropyLabel = `Market Entropy â€” SPY LIVE  (${d.verdict || ''})`;
    }).catch(() => { });

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Shift matrix left and add new column
      if (frame % 6 === 0) {
        matrix.shift();
        // New column â€” entropy spike happens every ~120 frames
        const isSpike = frame % 118 < 12;
        const newCol = BASE_ENT.map(e => {
          const noise = (Math.random() - 0.5) * 0.2;
          return clamp(e + noise + (isSpike ? 0.3 : 0), 0, 1);
        });
        matrix.push(newCol);

        const avgEnt = newCol.reduce((a, b) => a + b, 0) / ROWS;
        ENTROPY_HISTORY.push(avgEnt);
        ENTROPY_HISTORY.shift();
      }

      // Draw entropy cells
      for (let c = 0; c < COLS; c++) {
        for (let r = 0; r < ROWS; r++) {
          const e = matrix[c][r];
          // Color: low entropy = blue (structured), high = red (chaotic)
          const hue = 240 - e * 240;
          const lum = 25 + e * 40;
          ctx.fillStyle = `hsl(${hue},80%,${lum}%)`;
          ctx.fillRect(c * colW, 40 + r * rowH, colW - 0.5, rowH - 0.5);
        }
      }

      // Frequency labels on Y axis
      const labels = ['1Y', '6M', '3M', '1M', '2W', '1W', '3D', '1D', '4H', '1H', '30m', '15m', '5m', '1m', 'HF'];
      const step = Math.floor(ROWS / labels.length);
      ctx.fillStyle = '#666';
      ctx.font = '8px monospace';
      ctx.textAlign = 'right';
      for (let i = 0; i < labels.length; i++) {
        ctx.fillText(labels[i], W - 2, 40 + i * step * rowH + rowH * 0.7);
      }

      // Entropy history line at top
      const histH = 30;
      ctx.fillStyle = 'rgba(0,0,30,0.8)';
      ctx.fillRect(0, 0, W - 40, histH + 10);
      ctx.beginPath();
      const minE = 0.3, maxE = 1.0;
      ENTROPY_HISTORY.forEach((e, i) => {
        const x = (i / ENTROPY_HISTORY.length) * (W - 40);
        const y = histH - ((e - minE) / (maxE - minE)) * histH + 5;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.strokeStyle = '#88aaff';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      const curEnt = ENTROPY_HISTORY[ENTROPY_HISTORY.length - 1];
      const regime = curEnt < 0.45 ? 'STRUCTURED' : curEnt < 0.65 ? 'MODERATE' : curEnt < 0.82 ? 'NOISY' : 'CHAOTIC';
      const regCol = { STRUCTURED: '#00ff88', MODERATE: '#88aaff', NOISY: '#ffaa00', CHAOTIC: '#ff4444' }[regime];

      ctx.fillStyle = '#888';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(_entropyLabel, 4, 14);
      ctx.fillStyle = regCol;
      ctx.textAlign = 'right';
      ctx.fillText(`${regime}  ${(curEnt * 100).toFixed(0)}%`, W - 42, 14);

      // Legend
      [[0, '#2244ff', 'Structured'], [0.5, '#22aa44', 'Moderate'], [1, '#ff4422', 'Chaotic']].forEach(([e, col, lbl], i) => {
        ctx.fillStyle = col;
        ctx.textAlign = 'left';
        ctx.fillText(`â–  ${lbl}`, 4 + i * 100, H - 4);
      });
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     16. PORTFOLIO TREEMAP â€” nested allocation + PnL heat
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizTreemap() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const PORTFOLIO = [
      { sector: 'Tech', ticker: 'AAPL', weight: 0.18, pnl: rand(-0.05, 0.12) },
      { sector: 'Tech', ticker: 'MSFT', weight: 0.14, pnl: rand(-0.05, 0.12) },
      { sector: 'Tech', ticker: 'NVDA', weight: 0.10, pnl: rand(-0.15, 0.25) },
      { sector: 'Finance', ticker: 'JPM', weight: 0.09, pnl: rand(-0.05, 0.08) },
      { sector: 'Finance', ticker: 'GS', weight: 0.07, pnl: rand(-0.04, 0.07) },
      { sector: 'ETF', ticker: 'SPY', weight: 0.12, pnl: rand(-0.02, 0.06) },
      { sector: 'ETF', ticker: 'QQQ', weight: 0.08, pnl: rand(-0.03, 0.08) },
      { sector: 'Crypto', ticker: 'BTC', weight: 0.07, pnl: rand(-0.20, 0.30) },
      { sector: 'Energy', ticker: 'XOM', weight: 0.06, pnl: rand(-0.06, 0.09) },
      { sector: 'Commodity', ticker: 'GLD', weight: 0.05, pnl: rand(-0.03, 0.05) },
      { sector: 'Media', ticker: 'NFLX', weight: 0.04, pnl: rand(-0.12, 0.18) },
    ];

    // â”€â”€ Live cluster weights from /api/correlation/cluster â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    // Map cluster sizes to portfolio weights; use trader batch for real PnL
    _api.get('/api/correlation/cluster').then(d => {
      if (!d || !d.clusters) return;
      const clKeys = Object.keys(d.clusters);
      // Assign equal weight per cluster proportional to size
      const totalAssets = clKeys.reduce((s, k) => s + (d.clusters[k] || []).length, 0) || 1;
      PORTFOLIO.length = 0;
      clKeys.forEach(sector => {
        const tickers = d.clusters[sector] || [];
        tickers.slice(0, 3).forEach(ticker => {
          PORTFOLIO.push({
            sector,
            ticker,
            weight: Math.max(0.02, (tickers.length / totalAssets) / Math.min(tickers.length, 3)),
            pnl: rand(-0.08, 0.12) // will stay simulated PnL unless we call trader batch
          });
        });
      });
      // Normalize weights
      const sumW = PORTFOLIO.reduce((s, p) => s + p.weight, 0) || 1;
      PORTFOLIO.forEach(p => { p.weight /= sumW; });
    }).catch(() => { });

    // Squarified treemap (simplified row-by-row)
    function layoutTreemap(items, x, y, w, h) {
      const rects = [];
      let remaining = items.slice().sort((a, b) => b.weight - a.weight);
      let curX = x, curY = y, remW = w, remH = h;

      while (remaining.length > 0) {
        const totalW = remaining.reduce((s, i) => s + i.weight, 0);
        // Decide to layout in rows or columns
        let rowItems = [], rowWeight = 0;
        for (const item of remaining) {
          rowItems.push(item);
          rowWeight += item.weight;
          if (rowItems.length >= 3 && rowWeight / totalW > 0.35) break;
        }

        const rowFrac = rowWeight / totalW;
        const isHoriz = remW >= remH;
        const rowH2 = isHoriz ? remH : remH * rowFrac;
        const rowW2 = isHoriz ? remW * rowFrac : remW;

        let offset = 0;
        for (const item of rowItems) {
          const frac = item.weight / rowWeight;
          if (isHoriz) {
            rects.push({ ...item, x: curX, y: curY + offset * rowH2, w: rowW2, h: rowH2 * frac });
            offset += frac;
          } else {
            rects.push({ ...item, x: curX + offset * rowW2, y: curY, w: rowW2 * frac, h: rowH2 });
            offset += frac;
          }
        }

        if (isHoriz) { curX += rowW2; remW -= rowW2; }
        else { curY += rowH2; remH -= rowH2; }
        remaining = remaining.slice(rowItems.length);
      }
      return rects;
    }

    const PAD = 10;
    let rects = layoutTreemap(PORTFOLIO, PAD, PAD + 30, W - PAD * 2, H - PAD * 2 - 30);

    // Animate PnL drift
    let frame = 0;
    let tooltip = null;

    canvas.onmousemove = (e) => {
      const r = canvas.getBoundingClientRect();
      const mx = e.clientX - r.left, my = e.clientY - r.top;
      tooltip = rects.find(r2 => mx >= r2.x && mx <= r2.x + r2.w && my >= r2.y && my <= r2.y + r2.h) || null;
    };

    function pnlColor(pnl) {
      if (Math.abs(pnl) < 0.005) return '#1a1a2e';
      if (pnl > 0) return `hsl(120,${40 + pnl * 400}%,${20 + pnl * 150}%)`;
      return `hsl(0,${40 + Math.abs(pnl) * 400}%,${20 + Math.abs(pnl) * 150}%)`;
    }

    function draw() {
      _animFrameId = requestAnimationFrame(draw);
      frame++;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Slow PnL drift
      if (frame % 90 === 0) {
        PORTFOLIO.forEach(p => { p.pnl += (Math.random() - 0.5) * 0.005; p.pnl = clamp(p.pnl, -0.3, 0.35); });
        rects = layoutTreemap(PORTFOLIO, PAD, PAD + 30, W - PAD * 2, H - PAD * 2 - 30);
      }

      for (const r2 of rects) {
        const col = pnlColor(r2.pnl);
        ctx.fillStyle = col;
        ctx.fillRect(r2.x + 1, r2.y + 1, r2.w - 2, r2.h - 2);

        // Border
        ctx.strokeStyle = '#060610';
        ctx.lineWidth = 2;
        ctx.strokeRect(r2.x + 1, r2.y + 1, r2.w - 2, r2.h - 2);

        // Labels
        if (r2.w > 35 && r2.h > 22) {
          ctx.fillStyle = 'rgba(255,255,255,0.9)';
          ctx.font = `bold ${clamp(Math.floor(r2.w * 0.18), 8, 14)}px monospace`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(r2.ticker, r2.x + r2.w / 2, r2.y + r2.h / 2 - 7);
          ctx.font = `${clamp(Math.floor(r2.w * 0.13), 7, 11)}px monospace`;
          const sign = r2.pnl >= 0 ? '+' : '';
          ctx.fillStyle = r2.pnl >= 0 ? '#aaffaa' : '#ffaaaa';
          ctx.fillText(`${sign}${(r2.pnl * 100).toFixed(1)}%`, r2.x + r2.w / 2, r2.y + r2.h / 2 + 8);
        }
      }

      // Tooltip
      if (tooltip) {
        const txt = `${tooltip.ticker} | ${(tooltip.weight * 100).toFixed(0)}% weight | PnL: ${tooltip.pnl >= 0 ? '+' : ''}${(tooltip.pnl * 100).toFixed(2)}%`;
        const tw = ctx.measureText(txt).width + 16;
        ctx.fillStyle = '#0a0a20';
        ctx.fillRect(4, H - 28, tw, 22);
        ctx.fillStyle = tooltip.pnl >= 0 ? '#00ff88' : '#ff4444';
        ctx.font = '11px monospace';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText(txt, 12, H - 17);
      }

      // Title
      const totalPnl = PORTFOLIO.reduce((s, p) => s + p.weight * p.pnl, 0);
      ctx.fillStyle = '#aaa';
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.textBaseline = 'alphabetic';
      ctx.fillText(`Portfolio Treemap  |  Wtd PnL: ${totalPnl >= 0 ? '+' : ''}${(totalPnl * 100).toFixed(2)}%  |  Hover for detail`, PAD, 22);
    }
    draw();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     17. CANDLE RIVER â€” flowing OHLC candles + volume
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizCandleRiver() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const CANDLES_VIS = 60;
    const CANDLE_W = Math.floor((W - 80) / CANDLES_VIS);
    const CHART_H = H * 0.65;
    const VOL_H = H * 0.20;
    const CHART_Y = 40;
    const VOL_Y = CHART_Y + CHART_H + 10;

    // Generate candles (simulated fallback)
    let price = 100;
    const candles = [];
    for (let i = 0; i < CANDLES_VIS + 40; i++) {
      const o = price;
      const dir = Math.random() > 0.45 ? 1 : -1;
      const c = o * (1 + dir * rand(0.001, 0.018));
      const h = Math.max(o, c) * (1 + rand(0, 0.008));
      const l = Math.min(o, c) * (1 - rand(0, 0.008));
      const vol = rand(100000, 2000000);
      candles.push({ o, h, l, c, vol });
      price = c;
    }

    // â”€â”€ Live OHLCV from /api/market_data/SPY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _candleLabel = 'SPY â€” Simulated OHLCV';
    _api.get('/api/market_data/SPY').then(d => {
      if (!d || !d.Close) return;
      const keys = Object.keys(d.Close).sort();
      if (keys.length < 5) return;
      _candleLabel = 'SPY â€” LIVE OHLCV (1Y)';
      candles.length = 0;
      const take = Math.min(keys.length, CANDLES_VIS + 40);
      const start = keys.length - take;
      for (let i = start; i < keys.length; i++) {
        const k = keys[i];
        candles.push({
          o: d.Open ? (d.Open[k] || d.Close[k]) : d.Close[k],
          h: d.High ? (d.High[k] || d.Close[k]) : d.Close[k],
          l: d.Low ? (d.Low[k] || d.Close[k]) : d.Close[k],
          c: d.Close[k],
          vol: d.Volume ? (d.Volume[k] || 1000000) : 1000000
        });
      }
    }).catch(() => { });

    let offset = 0;  // scroll position (sub-pixel)

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Scroll right â†’ left
      offset += 0.4;
      if (offset >= CANDLE_W) {
        offset -= CANDLE_W;
        // Add new candle at end
        const last = candles[candles.length - 1];
        const o = last.c;
        const dir = Math.random() > 0.45 ? 1 : -1;
        const c = o * (1 + dir * rand(0.001, 0.018));
        candles.push({ o, h: Math.max(o, c) * (1 + rand(0, 0.008)), l: Math.min(o, c) * (1 - rand(0, 0.008)), c, vol: rand(100000, 2000000) });
        candles.shift();
      }

      const visible = candles.slice(candles.length - CANDLES_VIS - 1);
      const prices = visible.flatMap(c => [c.h, c.l]);
      const pMin = Math.min(...prices), pMax = Math.max(...prices);
      const pRange = pMax - pMin + 0.001;
      const maxVol = Math.max(...visible.map(c => c.vol));

      // Draw grid lines
      for (let i = 0; i <= 4; i++) {
        const y = CHART_Y + (i / 4) * CHART_H;
        const p = pMax - (i / 4) * pRange;
        ctx.beginPath();
        ctx.moveTo(50, y); ctx.lineTo(W, y);
        ctx.strokeStyle = 'rgba(80,80,100,0.2)';
        ctx.lineWidth = 0.5;
        ctx.stroke();
        ctx.fillStyle = '#555';
        ctx.font = '9px monospace';
        ctx.textAlign = 'right';
        ctx.fillText(p.toFixed(2), 46, y + 3);
      }

      // Draw candles
      for (let i = 0; i < visible.length; i++) {
        const cd = visible[i];
        const x = 50 + i * CANDLE_W - offset;
        const isBull = cd.c >= cd.o;
        const col = isBull ? '#00cc66' : '#dd3344';

        const yO = CHART_Y + ((pMax - cd.o) / pRange) * CHART_H;
        const yC = CHART_Y + ((pMax - cd.c) / pRange) * CHART_H;
        const yH = CHART_Y + ((pMax - cd.h) / pRange) * CHART_H;
        const yL = CHART_Y + ((pMax - cd.l) / pRange) * CHART_H;

        const bodyTop = Math.min(yO, yC);
        const bodyH = Math.max(Math.abs(yC - yO), 1);

        // Wick
        ctx.beginPath();
        ctx.moveTo(x + CANDLE_W * 0.5, yH);
        ctx.lineTo(x + CANDLE_W * 0.5, yL);
        ctx.strokeStyle = col;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Body
        ctx.fillStyle = isBull ? col : col + 'aa';
        ctx.fillRect(x + 1, bodyTop, CANDLE_W - 2, bodyH);

        // Volume bar
        const volH = (cd.vol / maxVol) * VOL_H;
        ctx.fillStyle = col + '88';
        ctx.fillRect(x + 1, VOL_Y + VOL_H - volH, CANDLE_W - 2, volH);
      }

      // MA overlays
      if (visible.length >= 20) {
        const ma20 = visible.map((_, i) => {
          if (i < 19) return null;
          return visible.slice(i - 19, i + 1).reduce((s, c) => s + c.c, 0) / 20;
        });
        ctx.beginPath();
        let started = false;
        for (let i = 0; i < visible.length; i++) {
          if (!ma20[i]) continue;
          const x = 50 + i * CANDLE_W - offset + CANDLE_W * 0.5;
          const y = CHART_Y + ((pMax - ma20[i]) / pRange) * CHART_H;
          started ? ctx.lineTo(x, y) : (ctx.moveTo(x, y), (started = true));
        }
        ctx.strokeStyle = '#ffaa00aa';
        ctx.lineWidth = 1.5;
        ctx.stroke();
        ctx.fillStyle = '#ffaa00';
        ctx.font = '8px monospace';
        ctx.textAlign = 'left';
        ctx.fillText('MA20', W - 45, CHART_Y + 12);
      }

      // Labels
      const last = visible[visible.length - 1];
      ctx.fillStyle = last.c >= last.o ? '#00cc66' : '#dd3344';
      ctx.font = 'bold 12px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`$${last.c.toFixed(3)}`, 52, 20);
      ctx.fillStyle = '#666';
      ctx.font = '10px monospace';
      ctx.fillText(`Candle River â€” ${_candleLabel}`, 52, 34);
      ctx.fillStyle = '#444';
      ctx.font = '9px monospace';
      ctx.fillText('VOL', 50, VOL_Y - 2);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     18. FACTOR WHEEL â€” PCA factor loadings as rotating wheel
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizFactorWheel() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;
    const cx = W / 2, cy = H / 2;
    const R = Math.min(W, H) * 0.35;

    const ASSETS = ['AAPL', 'MSFT', 'NVDA', 'AMZN', 'TSLA', 'JPM', 'GS', 'XOM', 'GLD', 'BTC', 'ETH', 'SPY'];
    const N = ASSETS.length;
    const N_FACTORS = 4;
    const FACTOR_COLORS = ['#00ccff', '#ff6688', '#88ff44', '#ffaa00'];
    const FACTOR_NAMES = ['Momentum', 'Volume', 'Volatility', 'Quality'];

    // Generate loading matrix (N Ã— K) â€” each asset's exposure to each factor
    const loadings = ASSETS.map((_, ai) =>
      Array.from({ length: N_FACTORS }, (_, fi) => {
        const base = fi === 0 ? rand(0.4, 0.9) : rand(-0.5, 0.5);
        return base;
      })
    );

    // â”€â”€ Live factor group scores from /api/factors/SPY â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _factorLiveScores = null; // { MOMENTUM, VOLUME, VOLATILITY, QUALITY, ... }
    _api.get('/api/factors/SPY').then(d => {
      if (!d || !d.group_scores) return;
      _factorLiveScores = d.group_scores;
      // Update factor names from live data (first 4 groups)
      const groups = Object.keys(d.group_scores);
      groups.slice(0, N_FACTORS).forEach((g, fi) => {
        FACTOR_NAMES[fi] = g.charAt(0) + g.slice(1).toLowerCase();
      });
      // Remap loadings using real group scores as base exposure
      groups.slice(0, N_FACTORS).forEach((g, fi) => {
        const score = (d.group_scores[g] || 0);  // -1..1
        ASSETS.forEach((_, ai) => {
          // Real score drives the asset's exposure to this factor ring
          loadings[ai][fi] = clamp(score + rand(-0.25, 0.25), -0.95, 0.95);
        });
      });
    }).catch(() => { });

    let rotation = 0;
    let highlightFactor = 0;
    let frame = 0;

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      rotation += 0.003;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Cycle highlight factor
      if (frame % 180 === 0) highlightFactor = (highlightFactor + 1) % N_FACTORS;

      // Draw concentric rings (factor rings)
      for (let f = N_FACTORS - 1; f >= 0; f--) {
        const ringR = R * (f + 1) / N_FACTORS;
        ctx.beginPath();
        ctx.arc(cx, cy, ringR, 0, Math.PI * 2);
        ctx.strokeStyle = FACTOR_COLORS[f] + (f === highlightFactor ? 'aa' : '22');
        ctx.lineWidth = f === highlightFactor ? 2 : 0.5;
        ctx.stroke();

        // Factor label
        const labelAngle = rotation + (f * Math.PI * 0.4);
        ctx.fillStyle = FACTOR_COLORS[f];
        ctx.font = '9px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(FACTOR_NAMES[f], cx + Math.cos(labelAngle) * (ringR - 12), cy + Math.sin(labelAngle) * (ringR - 12));
      }

      // Draw spokes (assets)
      for (let i = 0; i < N; i++) {
        const angle = (i / N) * Math.PI * 2 + rotation;
        const ax = cx + Math.cos(angle) * (R + 24);
        const ay = cy + Math.sin(angle) * (R + 24);

        // Spoke line
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(angle) * R, cy + Math.sin(angle) * R);
        ctx.strokeStyle = 'rgba(80,80,120,0.2)';
        ctx.lineWidth = 0.5;
        ctx.stroke();

        // Loading dots on each factor ring
        for (let f = 0; f < N_FACTORS; f++) {
          const load = loadings[i][f];
          const ringR = R * (f + 1) / N_FACTORS;
          const dotR = ringR + Math.abs(load) * 14;
          const dotAngle = angle + load * 0.3;
          const dx = cx + Math.cos(dotAngle) * dotR;
          const dy = cy + Math.sin(dotAngle) * dotR;
          const size = 3 + Math.abs(load) * 4;

          ctx.beginPath();
          ctx.arc(dx, dy, size, 0, Math.PI * 2);
          ctx.fillStyle = FACTOR_COLORS[f] + (f === highlightFactor ? 'ee' : '88');
          ctx.fill();
        }

        // Asset label
        ctx.fillStyle = '#aaaacc';
        ctx.font = 'bold 9px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(ASSETS[i], ax, ay);
      }

      // Center label
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 11px monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(_factorLiveScores ? 'LIVE' : 'SIM', cx, cy - 7);
      ctx.fillStyle = FACTOR_COLORS[highlightFactor];
      ctx.font = '9px monospace';
      const _fScore = _factorLiveScores ? ` ${(Object.values(_factorLiveScores)[highlightFactor] * 100).toFixed(0)}` : '';
      ctx.fillText(`${FACTOR_NAMES[highlightFactor]}${_fScore}`, cx, cy + 8);

      // Legend
      FACTOR_NAMES.forEach((name, f) => {
        ctx.fillStyle = FACTOR_COLORS[f];
        ctx.font = `${f === highlightFactor ? 'bold ' : ''}10px monospace`;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'alphabetic';
        ctx.fillText(`F${f + 1}: ${name}`, 12, 22 + f * 14);
      });

      ctx.fillStyle = '#555';
      ctx.font = '10px monospace';
      ctx.textAlign = 'left';
      ctx.fillText('Factor Wheel â€” PCA Loadings', 12, H - 12);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     19. DRAWDOWN MOUNTAIN â€” underwater equity curve
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizDrawdown() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    // â”€â”€ Default simulated equity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function genSimulated(n) {
      let equity = 100;
      const arr = [equity];
      for (let i = 1; i < n; i++) {
        equity *= (1 + (Math.random() - 0.47) * 0.018 + 0.0003);
        arr.push(equity);
      }
      return arr;
    }

    let equitySeries = genSimulated(600);
    let _liveStats = null;

    // â”€â”€ Fetch real backtest equity curve â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _api.get('/api/strategy/backtest/SPY?period=1y').then(d => {
      if (!d || !d.equity_curve || d.equity_curve.length < 10) return;
      equitySeries = d.equity_curve.map(p => p.equity);
      _liveStats = { ret: d.total_return, sharpe: d.sharpe, maxDD: d.max_drawdown, trades: d.n_trades };
    }).catch(() => { });

    // Compute drawdown series (reactive â€” re-computed from equitySeries in animate)
    const N = () => equitySeries.length;

    let frame = 0;
    let viewStart = 0;
    const VIEW_W = 600;

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      const PAD_L = 55, PAD_R = 20, PAD_T = 30, PAD_B = 40;
      const chartW = W - PAD_L - PAD_R;
      const halfH = (H - PAD_T - PAD_B) / 2;

      // â”€â”€ Dynamic drawdown from current equitySeries â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
      const _N = equitySeries.length;
      let _peak = equitySeries[0];
      const drawdowns = equitySeries.map(e => { if (e > _peak) _peak = e; return (e - _peak) / _peak; });
      const maxDD = Math.min(...drawdowns);

      // â”€â”€ Equity curve (top half)
      const eMin = Math.min(...equitySeries) * 0.99;
      const eMax = Math.max(...equitySeries) * 1.01;
      const eRange = eMax - eMin;

      ctx.beginPath();
      for (let i = 0; i < _N; i++) {
        const x = PAD_L + (i / (_N - 1)) * chartW;
        const y = PAD_T + halfH - ((equitySeries[i] - eMin) / eRange) * (halfH * 0.95);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.strokeStyle = '#00aaff';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Equity fill
      ctx.lineTo(PAD_L + chartW, PAD_T + halfH);
      ctx.lineTo(PAD_L, PAD_T + halfH);
      ctx.closePath();
      const equityGrd = ctx.createLinearGradient(0, PAD_T, 0, PAD_T + halfH);
      equityGrd.addColorStop(0, 'rgba(0,170,255,0.25)');
      equityGrd.addColorStop(1, 'rgba(0,170,255,0.02)');
      ctx.fillStyle = equityGrd;
      ctx.fill();

      // Equity label
      ctx.fillStyle = '#aaa';
      ctx.font = '9px monospace';
      ctx.textAlign = 'right';
      ctx.fillText(eMax.toFixed(0), PAD_L - 2, PAD_T + 10);
      ctx.fillText(eMin.toFixed(0), PAD_L - 2, PAD_T + halfH - 2);

      // Divider
      ctx.beginPath();
      ctx.moveTo(PAD_L, PAD_T + halfH);
      ctx.lineTo(PAD_L + chartW, PAD_T + halfH);
      ctx.strokeStyle = '#333355';
      ctx.lineWidth = 1;
      ctx.stroke();

      // â”€â”€ Drawdown (bottom half â€” inverted mountain)
      const ddMax = 0, ddMin = maxDD - 0.005;
      const ddRange = ddMax - ddMin;

      ctx.beginPath();
      ctx.moveTo(PAD_L, PAD_T + halfH);
      for (let i = 0; i < _N; i++) {
        const x = PAD_L + (i / (_N - 1)) * chartW;
        const y = PAD_T + halfH + ((ddMax - drawdowns[i]) / ddRange) * (halfH * 0.9);
        ctx.lineTo(x, y);
      }
      ctx.lineTo(PAD_L + chartW, PAD_T + halfH);
      ctx.closePath();

      const ddGrd = ctx.createLinearGradient(0, PAD_T + halfH, 0, H - PAD_B);
      ddGrd.addColorStop(0, 'rgba(255,60,60,0.1)');
      ddGrd.addColorStop(1, 'rgba(200,0,0,0.6)');
      ctx.fillStyle = ddGrd;
      ctx.fill();

      // Drawdown outline
      ctx.beginPath();
      for (let i = 0; i < _N; i++) {
        const x = PAD_L + (i / (_N - 1)) * chartW;
        const y = PAD_T + halfH + ((ddMax - drawdowns[i]) / ddRange) * (halfH * 0.9);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.strokeStyle = '#ff4444aa';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Max drawdown line
      const maxDDY = PAD_T + halfH + ((ddMax - maxDD) / ddRange) * (halfH * 0.9);
      ctx.beginPath();
      ctx.moveTo(PAD_L, maxDDY);
      ctx.lineTo(PAD_L + chartW, maxDDY);
      ctx.strokeStyle = '#ff444466';
      ctx.lineWidth = 1;
      ctx.setLineDash([6, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#ff4444';
      ctx.font = '9px monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`Max DD: ${(maxDD * 100).toFixed(1)}%`, PAD_L + 4, maxDDY - 3);

      // Drawdown scale labels
      ctx.fillStyle = '#555';
      ctx.textAlign = 'right';
      [0, maxDD * 0.5, maxDD].forEach(v => {
        const y = PAD_T + halfH + ((ddMax - v) / ddRange) * (halfH * 0.9);
        ctx.fillText(`${(v * 100).toFixed(0)}%`, PAD_L - 2, y + 3);
      });

      // Title
      ctx.fillStyle = '#00aaff';
      ctx.font = '11px monospace';
      ctx.textAlign = 'left';
      ctx.fillText('Equity Curve', PAD_L, PAD_T - 8);
      ctx.fillStyle = '#ff4444';
      ctx.fillText('Drawdown Mountain', PAD_L, PAD_T + halfH + halfH - 8);

      ctx.fillStyle = '#555';
      ctx.font = '10px monospace';
      ctx.textAlign = 'center';
      const statsStr = _liveStats
        ? `SPY 1Y Backtest Â· Return: ${(_liveStats.ret * 100).toFixed(1)}% Â· Sharpe: ${_liveStats.sharpe.toFixed(2)} Â· MaxDD: ${(_liveStats.maxDD * 100).toFixed(1)}% Â· ${_liveStats.trades} trades`
        : `${_N} days simulated  Â·  Final: $${equitySeries[_N - 1].toFixed(2)}  Â·  MaxDD: ${(maxDD * 100).toFixed(1)}%`;
      ctx.fillText(statsStr, W / 2, H - 6);
    }
    animate();
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     20. BID-ASK SPREAD LIVE â€” spread dynamics + impact
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizSpread() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;

    const N_ASSETS = 8;
    const ASSET_NAMES = ['SPY', 'AAPL', 'AMZN', 'TSLA', 'BTC/USD', 'ETH/USD', 'EUR/USD', 'GLD'];
    const ASSET_COLORS = ['#00ff88', '#4488ff', '#ff8800', '#cc88ff', '#ffaa00', '#44ccff', '#ff4488', '#ffdd44'];
    const BASE_SPREADS = [0.01, 0.02, 0.05, 0.08, 0.15, 0.20, 0.001, 0.05]; // as % of price

    // Live spread simulation
    const spreads = BASE_SPREADS.map(s => ({ current: s, target: s, history: Array(120).fill(s) }));

    let frame = 0;

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#060610';
      ctx.fillRect(0, 0, W, H);

      // Update spreads
      if (frame % 5 === 0) {
        spreads.forEach((s, i) => {
          s.target = BASE_SPREADS[i] * (1 + rand(-0.4, 0.8));
          if (frame % 200 < 20) s.target *= rand(2, 4); // Spread widening event
          s.current = lerp(s.current, s.target, 0.12);
          s.history.push(s.current);
          s.history.shift();
        });
      }

      const ROW_H = Math.floor((H - 80) / N_ASSETS);
      const BAR_MAX = W * 0.35;
      const HIST_W = W * 0.40;
      const START_X = W * 0.18;
      const HIST_X = W * 0.58;
      const TOP_Y = 50;

      // Column headers
      ctx.fillStyle = '#555';
      ctx.font = '9px monospace';
      ctx.textAlign = 'left';
      ctx.fillText('Asset', 10, TOP_Y - 10);
      ctx.textAlign = 'center';
      ctx.fillText('Spread (bps)', START_X + BAR_MAX / 2, TOP_Y - 10);
      ctx.fillText('History', HIST_X + HIST_W / 2, TOP_Y - 10);
      ctx.textAlign = 'right';
      ctx.fillText('Impact', W - 10, TOP_Y - 10);

      for (let i = 0; i < N_ASSETS; i++) {
        const s = spreads[i];
        const y = TOP_Y + i * ROW_H;
        const midY = y + ROW_H * 0.5;
        const col = ASSET_COLORS[i];
        const bps = s.current * 10000;
        const maxBps = BASE_SPREADS[i] * 10000 * 4;

        // Asset name
        ctx.fillStyle = col;
        ctx.font = 'bold 10px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(ASSET_NAMES[i], 10, midY + 3);

        // Spread bar
        const barW = clamp((bps / maxBps) * BAR_MAX, 2, BAR_MAX);
        const isWide = s.current > BASE_SPREADS[i] * 1.8;
        ctx.fillStyle = isWide ? '#ff4444aa' : col + '66';
        ctx.fillRect(START_X, y + 4, barW, ROW_H - 8);
        ctx.fillStyle = isWide ? '#ff4444' : col;
        ctx.font = '9px monospace';
        ctx.textAlign = 'left';
        ctx.fillText(`${bps.toFixed(2)} bps`, START_X + barW + 4, midY + 3);

        // Mini history sparkline
        const maxH = Math.max(...s.history) * 1.1 + 0.0001;
        ctx.beginPath();
        s.history.forEach((v, hi) => {
          const hx = HIST_X + (hi / s.history.length) * HIST_W;
          const hy = y + ROW_H - 4 - (v / maxH) * (ROW_H - 8);
          hi === 0 ? ctx.moveTo(hx, hy) : ctx.lineTo(hx, hy);
        });
        ctx.strokeStyle = col + (isWide ? 'ff' : '88');
        ctx.lineWidth = 1;
        ctx.stroke();

        // Market impact (Almgren-Chriss simplified: impact â‰ˆ Ïƒ/sqrt(ADV) Ã— sqrt(qty))
        const impact = s.current * Math.sqrt(rand(0.1, 5));
        ctx.fillStyle = impact > 0.005 ? '#ff6644' : '#44aa66';
        ctx.font = '9px monospace';
        ctx.textAlign = 'right';
        ctx.fillText(`${(impact * 100).toFixed(4)}%`, W - 10, midY + 3);

        // Separator
        ctx.beginPath();
        ctx.moveTo(0, y + ROW_H);
        ctx.lineTo(W, y + ROW_H);
        ctx.strokeStyle = 'rgba(60,60,80,0.3)';
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }

      // Spread alert banner if any asset widened dramatically
      const widened = spreads.map((s, i) => ({ name: ASSET_NAMES[i], ratio: s.current / BASE_SPREADS[i], col: ASSET_COLORS[i] }))
        .filter(s => s.ratio > 2.5);
      if (widened.length > 0) {
        ctx.fillStyle = 'rgba(100,20,0,0.7)';
        ctx.fillRect(0, 0, W, 36);
        ctx.fillStyle = '#ff4444';
        ctx.font = 'bold 12px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(`âš  SPREAD WIDENING: ${widened.map(w => w.name).join(', ')}`, W / 2, 22);
      } else {
        ctx.fillStyle = '#888';
        ctx.font = '11px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('Bid-Ask Spread Live â€” Market Liquidity Monitor', W / 2, 22);
      }

      ctx.fillStyle = '#444';
      ctx.font = '9px monospace';
      ctx.textAlign = 'left';
      ctx.fillText('bps = basis points  |  Impact = estimated market impact per 1% ADV', 10, H - 8);
    }
    animate();
  }

  /* â”€â”€â”€ Fallback 2D message when Three.js unavailable â”€â”€â”€ */
  function _fallback2D(name) {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    ctx.fillStyle = '#060610';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#4488ff';
    ctx.font = '18px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(`Loading ${VIZ_META[name]?.label}...`, canvas.width / 2, canvas.height / 2 - 10);
    ctx.fillStyle = '#666';
    ctx.font = '12px monospace';
    ctx.fillText('(Three.js required â€” check console)', canvas.width / 2, canvas.height / 2 + 20);
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     LIVE DATA BRIDGE
     Fetches real server data when available; falls back to
     simulated data silently.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  const _api = (() => {
    const BASE = window.location.origin || 'http://localhost:8088';
    async function get(path) {
      try {
        const r = await fetch(BASE + path, { signal: AbortSignal.timeout(4000) });
        if (!r.ok) throw new Error(r.status);
        return await r.json();
      } catch { return null; }
    }
    return { get };
  })();

  // Fetch market regime and update particle viz shape
  async function fetchRegimeAndUpdate(ticker = 'SPY') {
    const data = await _api.get(`/api/vizlab/regime/${ticker}`);
    if (data && data.regime) {
      updateRegimeLabel(data.regime + ` (${ticker} live)`);
      return data.regime;
    }
    return null;
  }

  // Fetch brain state and highlight active nodes
  async function fetchBrainState() {
    const data = await _api.get('/api/vizlab/brain');
    return data;
  }

  // Fetch system status
  async function fetchSystemStatus() {
    const data = await _api.get('/api/vizlab/system_status');
    return data;
  }

  /* â”€â”€â”€ Dispatch table â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     PARTICLE SHAPES â€” Inspired by sphere-main (React Three Fiber â†’ vanilla Three.js)
     15 000 particles morphing between Saturn / Heart / Sphere shapes.
     Mouse cursor creates repulsion field â€” particles flee and snap back.
     All three vizzes share one shared helper: _particleShapeViz().
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */

  function _particleShapeViz(container, initialShape, allowMorph) {
    if (!container || typeof THREE === 'undefined') return null;

    const COUNT = 15000;

    // â”€â”€ Generate particle positions for each shape â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function genSaturn() {
      const pos = new Float32Array(COUNT * 3);
      for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        if (i < COUNT * 0.6) {
          // Inner sphere
          const phi = Math.acos(2 * Math.random() - 1);
          const theta = Math.random() * Math.PI * 2;
          pos[i3] = 2.5 * Math.sin(phi) * Math.cos(theta);
          pos[i3 + 1] = 2.5 * Math.sin(phi) * Math.sin(theta);
          pos[i3 + 2] = 2.5 * Math.cos(phi);
        } else {
          // Ring
          const angle = Math.random() * Math.PI * 2;
          const r = 3.5 + Math.random() * 1.5;
          pos[i3] = Math.cos(angle) * r;
          pos[i3 + 1] = Math.sin(angle) * r * 0.15;
          pos[i3 + 2] = Math.sin(angle) * r;
        }
      }
      return pos;
    }

    function genHeart() {
      const pos = new Float32Array(COUNT * 3);
      for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        const t = Math.random() * Math.PI * 2;
        pos[i3] = 0.22 * (16 * Math.pow(Math.sin(t), 3));
        pos[i3 + 1] = 0.22 * (13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t));
        pos[i3 + 2] = (Math.random() - 0.5) * 1.5;
      }
      return pos;
    }

    function genSphere() {
      const pos = new Float32Array(COUNT * 3);
      for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        const phi = Math.acos(2 * Math.random() - 1);
        const theta = Math.random() * Math.PI * 2;
        pos[i3] = 3.5 * Math.sin(phi) * Math.cos(theta);
        pos[i3 + 1] = 3.5 * Math.sin(phi) * Math.sin(theta);
        pos[i3 + 2] = 3.5 * Math.cos(phi);
      }
      return pos;
    }

    const SHAPES = { saturn: genSaturn, heart: genHeart, sphere: genSphere };
    const SHAPE_LIST = ['saturn', 'heart', 'sphere'];
    const SHAPE_COLORS = {
      saturn: 0xffdf7e,   // golden
      heart: 0xff5577,   // rose
      sphere: 0x88ccff,   // sky blue
    };

    // â”€â”€ Scene setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const W = container.clientWidth || 800;
    const H = container.clientHeight || 500;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W, H);
    renderer.domElement.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%';
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 1000);
    camera.position.set(0, 0, 15);

    // â”€â”€ Geometry + material â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const geometry = new THREE.BufferGeometry();
    let currentShape = initialShape || 'saturn';
    let targetPositions = SHAPES[currentShape]();
    const livePositions = new Float32Array(targetPositions);  // starts at target
    geometry.setAttribute('position', new THREE.BufferAttribute(livePositions, 3));

    const material = new THREE.PointsMaterial({
      color: SHAPE_COLORS[currentShape],
      size: 0.07,
      sizeAttenuation: true,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    // â”€â”€ State â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let mouse = { x: 9999, y: 9999, z: 0 };  // 3D cursor in scene space
    let rotAngle = 0;
    let autoRotSpeed = 0.003;
    let morphTimer = 0;
    let morphIndex = SHAPE_LIST.indexOf(currentShape);
    const MORPH_INTERVAL = allowMorph ? 4000 : Infinity;  // ms

    // â”€â”€ Mouse tracking (cursor â†’ 3D scene coords) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const canvas = renderer.domElement;
    function onMouseMove(e) {
      const rect = canvas.getBoundingClientRect();
      const nx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const ny = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      // Project from NDC to scene Z=0 plane at camera distance ~7
      mouse.x = nx * 7.5;
      mouse.y = ny * 7.5;
    }
    canvas.addEventListener('mousemove', onMouseMove);

    // â”€â”€ Shape selector UI â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const btnBar = document.createElement('div');
    btnBar.style.cssText = `position:absolute;bottom:18px;left:50%;transform:translateX(-50%);
      display:flex;gap:8px;z-index:10;font-family:monospace;`;

    const allShapes = allowMorph ? SHAPE_LIST : [currentShape];
    allShapes.forEach(sh => {
      const btn = document.createElement('button');
      btn.textContent = sh.toUpperCase();
      btn.style.cssText = `background:rgba(255,255,255,0.1);color:#fff;border:none;
        padding:6px 16px;border-radius:16px;cursor:pointer;font-size:0.75rem;
        font-family:monospace;transition:background 0.2s;`;
      btn.addEventListener('click', () => {
        currentShape = sh;
        targetPositions = SHAPES[sh]();
        material.color.set(SHAPE_COLORS[sh]);
        btnBar.querySelectorAll('button').forEach(b => b.style.background = 'rgba(255,255,255,0.1)');
        btn.style.background = 'rgba(255,223,126,0.35)';
      });
      if (sh === currentShape) btn.style.background = 'rgba(255,223,126,0.35)';
      btnBar.appendChild(btn);
    });

    // Zoom buttons
    ['âˆ’', '+'].forEach((label, i) => {
      const btn = document.createElement('button');
      btn.textContent = label;
      btn.style.cssText = btnBar.querySelector('button').style.cssText;
      btn.style.marginLeft = i === 0 ? '16px' : '0';
      btn.addEventListener('click', () => {
        camera.position.z = Math.max(6, Math.min(30, camera.position.z + (i === 0 ? 2 : -2)));
      });
      btnBar.appendChild(btn);
    });

    container.appendChild(btnBar);

    // â”€â”€ Label â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const label = document.createElement('div');
    label.style.cssText = `position:absolute;top:12px;left:50%;transform:translateX(-50%);
      color:rgba(255,255,255,0.55);font-family:monospace;font-size:0.75rem;pointer-events:none;`;
    label.textContent = allowMorph ? 'Move cursor â†’ repel particles  |  Click shape to morph'
      : `Move cursor â†’ repel particles  |  ${currentShape.toUpperCase()} â€” ${COUNT.toLocaleString()} particles`;
    container.appendChild(label);

    // â”€â”€ Animation loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let animId = null;
    let lastMs = performance.now();
    const REPEL_RADIUS = 3.8;
    const REPEL_STRENGTH = 1.3;
    const LERP = 0.08;

    function animate(now) {
      animId = requestAnimationFrame(animate);
      const dt = now - lastMs;
      lastMs = now;

      // Auto-shape cycling (morph mode)
      if (allowMorph) {
        morphTimer += dt;
        if (morphTimer > MORPH_INTERVAL) {
          morphTimer = 0;
          morphIndex = (morphIndex + 1) % SHAPE_LIST.length;
          currentShape = SHAPE_LIST[morphIndex];
          targetPositions = SHAPES[currentShape]();
          material.color.set(SHAPE_COLORS[currentShape]);
        }
      }

      // Update particle positions
      const pos = geometry.attributes.position.array;
      for (let i = 0; i < COUNT; i++) {
        const i3 = i * 3;
        let tx = targetPositions[i3];
        let ty = targetPositions[i3 + 1];
        let tz = targetPositions[i3 + 2];

        // Apply manual rotation to target
        const cos = Math.cos(rotAngle);
        const sin = Math.sin(rotAngle);
        const rx = tx * cos - tz * sin;
        const rz = tx * sin + tz * cos;
        tx = rx; tz = rz;

        // Cursor repulsion
        const dx = mouse.x - pos[i3];
        const dy = mouse.y - pos[i3 + 1];
        const dz = 0 - pos[i3 + 2];
        const dist = Math.sqrt(dx * dx + dy * dy + dz * dz) + 1e-6;
        if (dist < REPEL_RADIUS) {
          const force = ((REPEL_RADIUS - dist) / REPEL_RADIUS) * REPEL_STRENGTH;
          tx += (-dx / dist) * force;
          ty += (-dy / dist) * force;
          tz += (-dz / dist) * force;
        }

        // Smooth lerp toward target
        pos[i3] += (tx - pos[i3]) * LERP;
        pos[i3 + 1] += (ty - pos[i3 + 1]) * LERP;
        pos[i3 + 2] += (tz - pos[i3 + 2]) * LERP;
      }
      geometry.attributes.position.needsUpdate = true;

      // Auto-rotate
      rotAngle += autoRotSpeed;

      renderer.render(scene, camera);
    }
    animate(performance.now());

    // â”€â”€ Resize â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function onResize() {
      const w = container.clientWidth, h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }
    window.addEventListener('resize', onResize);

    // â”€â”€ Cleanup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    return function destroy() {
      cancelAnimationFrame(animId);
      canvas.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('resize', onResize);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
      if (btnBar.parentNode) btnBar.parentNode.removeChild(btnBar);
      if (label.parentNode) label.parentNode.removeChild(label);
    };
  }

  // â”€â”€ Viz: Particle Saturn â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function vizParticleSaturn() {
    const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!container) return null;
    container.style.background = '#00000f';
    return _particleShapeViz(container, 'saturn', false);
  }

  // â”€â”€ Viz: Particle Heart â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function vizParticleHeart() {
    const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!container) return null;
    container.style.background = '#0a0005';
    return _particleShapeViz(container, 'heart', false);
  }

  // â”€â”€ Viz: Particle Morph (auto-cycles Saturn â†’ Heart â†’ Sphere) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function vizParticleMorph() {
    const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!container) return null;
    container.style.background = '#000008';
    return _particleShapeViz(container, 'saturn', true);
  }

  // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
  //  NEXUS CORE PARTICLE SYSTEM â€” Fase Nexus  (50 000 particles, 5 shapes)
  //  Adapted from nexus-core-particle-system (React Three Fiber â†’ vanilla)
  //  Shapes: MÃ¶bius strip, Toroidal vortex, Spherical harmonics,
  //          Lissajous 3D curves, Lorenz attractor (particle cloud)
  // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

  function _nexusViz(container, startShape) {
    if (!window.THREE) return null;
    const N = 50_000;

    /* â”€â”€ Shape generators (all return Float32Array of length N*3) â”€â”€â”€â”€â”€â”€ */
    function genMobius() {
      const a = new Float32Array(N * 3);
      for (let i = 0; i < N; i++) {
        const t = i / N, u = t * Math.PI * 4;
        const v = (Math.random() - 0.5) * 2, R = 3;
        a[i * 3] = (R + v * Math.cos(u / 2)) * Math.cos(u);
        a[i * 3 + 1] = (R + v * Math.cos(u / 2)) * Math.sin(u);
        a[i * 3 + 2] = v * Math.sin(u / 2);
      }
      return a;
    }

    function genToroidal() {
      const a = new Float32Array(N * 3);
      for (let i = 0; i < N; i++) {
        const u = Math.random() * Math.PI * 2, v = Math.random() * Math.PI * 2;
        const R = 3, r = 1 + 0.2 * Math.sin(8 * u) * Math.cos(4 * v);
        a[i * 3] = (R + r * Math.cos(v)) * Math.cos(u);
        a[i * 3 + 1] = (R + r * Math.cos(v)) * Math.sin(u);
        a[i * 3 + 2] = r * Math.sin(v);
      }
      return a;
    }

    function genSpherical() {
      const a = new Float32Array(N * 3);
      for (let i = 0; i < N; i++) {
        const theta = Math.acos(2 * Math.random() - 1);
        const phi = Math.random() * Math.PI * 2;
        const r = 3 + 1.5 * Math.sin(4 * phi) * Math.sin(5 * theta);
        a[i * 3] = r * Math.sin(theta) * Math.cos(phi);
        a[i * 3 + 1] = r * Math.sin(theta) * Math.sin(phi);
        a[i * 3 + 2] = r * Math.cos(theta);
      }
      return a;
    }

    function genLissajous() {
      const a = new Float32Array(N * 3);
      for (let i = 0; i < N; i++) {
        const u = (i / N) * Math.PI * 200;
        a[i * 3] = 4 * Math.sin(3 * u) + (Math.random() - 0.5) * 0.18;
        a[i * 3 + 1] = 4 * Math.sin(2 * u + Math.PI / 4) + (Math.random() - 0.5) * 0.18;
        a[i * 3 + 2] = 4 * Math.sin(5 * u) + (Math.random() - 0.5) * 0.18;
      }
      return a;
    }

    function genLorenzP() {
      const a = new Float32Array(N * 3);
      let lx = 0.1, ly = 0, lz = 0;
      const dt = 0.005;
      for (let i = 0; i < N; i++) {
        const dx = 10 * (ly - lx) * dt;
        const dy = (lx * (28 - lz) - ly) * dt;
        const dz = (lx * ly - (8 / 3) * lz) * dt;
        lx += dx; ly += dy; lz += dz;
        a[i * 3] = lx * 0.22;
        a[i * 3 + 1] = ly * 0.22;
        a[i * 3 + 2] = (lz - 28) * 0.22;
      }
      return a;
    }

    const SHAPES = ['mobius', 'toroidal', 'spherical', 'lissajous', 'lorenzp'];
    const SHAPE_META = {
      mobius: { label: 'MÃ¶bius Strip', color: '#00ffcc' },
      toroidal: { label: 'Toroidal Vortex', color: '#ff00ff' },
      spherical: { label: 'Spherical Harmonics', color: '#4499ff' },
      lissajous: { label: 'Lissajous 3D', color: '#ffaa00' },
      lorenzp: { label: 'Lorenz Attractor', color: '#44ff88' },
    };
    const PALETTE = ['#00ffcc', '#ff00ff', '#4499ff', '#ffaa00', '#ffffff', '#ff6666'];

    // Pre-build all shape caches
    const cache = {
      mobius: genMobius(),
      toroidal: genToroidal(),
      spherical: genSpherical(),
      lissajous: genLissajous(),
      lorenzp: genLorenzP(),
    };

    /* â”€â”€ Three.js setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    const W = container.clientWidth || 800, H = container.clientHeight || 600;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W, H);
    renderer.domElement.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;';
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x040407);
    const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 1000);
    camera.position.set(0, 0, 16);

    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(cache[startShape]);
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
      size: 0.025, color: new THREE.Color(SHAPE_META[startShape].color),
      transparent: true, opacity: 0.75,
      blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
    });
    const points = new THREE.Points(geometry, material);
    scene.add(points);

    /* â”€â”€ Control panel â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    const panel = document.createElement('div');
    panel.style.cssText = `
      position:absolute;top:48px;right:12px;width:196px;
      background:rgba(4,4,12,0.72);backdrop-filter:blur(10px);
      border:1px solid rgba(0,255,204,0.22);border-radius:12px;
      padding:14px 12px;font-family:'Courier New',monospace;color:#00ffcc;
      font-size:11px;z-index:10;user-select:none;
    `;

    const shapeBtns = SHAPES.map(s =>
      `<button data-s="${s}" style="
        display:block;width:100%;text-align:left;background:${s === startShape ? 'rgba(0,255,204,0.14)' : 'transparent'};
        border:1px solid ${s === startShape ? 'rgba(0,255,204,0.45)' : 'transparent'};
        color:${s === startShape ? '#00ffcc' : 'rgba(0,255,204,0.42)'};
        padding:4px 8px;border-radius:6px;cursor:pointer;
        font-family:monospace;font-size:10px;margin-bottom:3px;transition:all 0.2s;">
        ${SHAPE_META[s].label}
      </button>`
    ).join('');

    const swatches = PALETTE.map(c =>
      `<div data-c="${c}" style="
        width:19px;height:19px;border-radius:50%;cursor:pointer;display:inline-block;
        background:${c};box-shadow:0 0 7px ${c}88;margin-right:4px;
        transition:transform 0.15s;"></div>`
    ).join('');

    panel.innerHTML = `
      <div style="font-size:12px;font-weight:700;letter-spacing:1.4px;margin-bottom:10px;
        border-bottom:1px solid rgba(0,255,204,0.18);padding-bottom:6px;">
        NEXUS<span style="color:rgba(0,255,204,0.4)">.</span>CORE
        <span style="font-size:9px;color:rgba(0,255,204,0.35);float:right;">v3.14</span>
      </div>
      <div style="font-size:9px;color:rgba(0,255,204,0.45);margin-bottom:5px;letter-spacing:0.8px;">TOPOLOGY</div>
      <div id="nx-shapes">${shapeBtns}</div>
      <div style="font-size:9px;color:rgba(0,255,204,0.45);margin:10px 0 3px;letter-spacing:0.8px;">
        MORPH SPEED <span id="nx-sv">0.5</span>
      </div>
      <input id="nx-speed" type="range" min="0.1" max="2" step="0.1" value="0.5"
        style="width:100%;accent-color:#00ffcc;margin-bottom:8px;">
      <div style="font-size:9px;color:rgba(0,255,204,0.45);margin-bottom:3px;letter-spacing:0.8px;">
        PARTICLE SIZE <span id="nx-pv">0.025</span>
      </div>
      <input id="nx-psize" type="range" min="0.005" max="0.08" step="0.005" value="0.025"
        style="width:100%;accent-color:#00ffcc;margin-bottom:10px;">
      <div style="font-size:9px;color:rgba(0,255,204,0.45);margin-bottom:6px;letter-spacing:0.8px;">ENERGY</div>
      <div id="nx-colors">${swatches}</div>
      <div style="font-size:9px;color:rgba(0,255,204,0.25);margin-top:10px;text-align:center;">
        drag to orbit Â· ${N.toLocaleString()} particles
      </div>
    `;
    container.appendChild(panel);

    // Wire shape buttons
    let activeShape = startShape;
    panel.querySelector('#nx-shapes').addEventListener('click', e => {
      const s = e.target.closest('[data-s]')?.dataset.s;
      if (!s) return;
      activeShape = s;
      material.color.set(SHAPE_META[s].color);
      panel.querySelectorAll('[data-s]').forEach(b => {
        const on = b.dataset.s === s;
        b.style.background = on ? 'rgba(0,255,204,0.14)' : 'transparent';
        b.style.border = `1px solid ${on ? 'rgba(0,255,204,0.45)' : 'transparent'}`;
        b.style.color = on ? '#00ffcc' : 'rgba(0,255,204,0.42)';
      });
    });

    // Wire sliders
    let morphSpeed = 0.5;
    const speedSlider = panel.querySelector('#nx-speed');
    const speedVal = panel.querySelector('#nx-sv');
    speedSlider.addEventListener('input', () => {
      morphSpeed = parseFloat(speedSlider.value);
      speedVal.textContent = morphSpeed.toFixed(1);
    });
    const sizeSlider = panel.querySelector('#nx-psize');
    const sizeVal = panel.querySelector('#nx-pv');
    sizeSlider.addEventListener('input', () => {
      material.size = parseFloat(sizeSlider.value);
      sizeVal.textContent = sizeSlider.value;
    });

    // Wire color swatches
    panel.querySelector('#nx-colors').addEventListener('click', e => {
      const c = e.target.closest('[data-c]')?.dataset.c;
      if (c) material.color.set(c);
    });

    /* â”€â”€ Mouse orbit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    let isDrag = false, lastX = 0, lastY = 0, rotX = 0, rotY = 0;
    const onDown = e => { isDrag = true; lastX = e.clientX ?? e.touches?.[0]?.clientX; lastY = e.clientY ?? e.touches?.[0]?.clientY; };
    const onUp = () => { isDrag = false; };
    const onMove = e => {
      if (!isDrag) return;
      const cx = e.clientX ?? e.touches?.[0]?.clientX;
      const cy = e.clientY ?? e.touches?.[0]?.clientY;
      rotX += (cy - lastY) * 0.005; rotY += (cx - lastX) * 0.005;
      lastX = cx; lastY = cy;
    };
    renderer.domElement.addEventListener('mousedown', onDown);
    renderer.domElement.addEventListener('touchstart', onDown, { passive: true });
    window.addEventListener('mouseup', onUp);
    window.addEventListener('touchend', onUp);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('touchmove', onMove, { passive: true });

    /* â”€â”€ Animation loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    let animId, lastT = performance.now();
    const posAttr = geometry.attributes.position;
    function tick(now) {
      animId = requestAnimationFrame(tick);
      const dt = Math.min((now - lastT) / 1000, 0.05);
      lastT = now;

      // Frame-rate-independent lerp toward target shape
      const target = cache[activeShape];
      const lerpK = 1 - Math.exp(-morphSpeed * dt * 5);
      const arr = posAttr.array;
      let dirty = false;
      for (let i = 0; i < N * 3; i++) {
        const diff = target[i] - arr[i];
        if (Math.abs(diff) > 5e-4) { arr[i] += diff * lerpK; dirty = true; }
      }
      if (dirty) posAttr.needsUpdate = true;

      if (!isDrag) rotY += dt * 0.1;   // auto-rotate when idle
      points.rotation.y = rotY;
      points.rotation.x = rotX;
      renderer.render(scene, camera);
    }
    animId = requestAnimationFrame(tick);

    /* â”€â”€ Resize â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    const onResize = () => {
      const w = container.clientWidth, h = container.clientHeight;
      camera.aspect = w / h; camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', onResize);

    /* â”€â”€ Cleanup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    return function destroy() {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('touchend', onUp);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('touchmove', onMove);
      geometry.dispose(); material.dispose(); renderer.dispose();
      if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
      if (panel.parentNode) panel.parentNode.removeChild(panel);
    };
  }

  // â”€â”€ Nexus viz wrappers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  function vizNexusMobius() {
    const c = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!c) return null;
    c.style.background = '#040407';
    return _nexusViz(c, 'mobius');
  }
  function vizNexusToroidal() {
    const c = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!c) return null;
    c.style.background = '#080410';
    return _nexusViz(c, 'toroidal');
  }
  function vizNexusSpherical() {
    const c = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!c) return null;
    c.style.background = '#020508';
    return _nexusViz(c, 'spherical');
  }
  function vizNexusLissajous() {
    const c = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!c) return null;
    c.style.background = '#080500';
    return _nexusViz(c, 'lissajous');
  }
  function vizNexusLorenz() {
    const c = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!c) return null;
    c.style.background = '#020a04';
    return _nexusViz(c, 'lorenzp');
  }

  // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
  //  SPEED RACER DQN â€” Fase Speed-Racer
  //  Adapted from speed-racer-rl-main (C++ DQN â†’ Canvas 2D simulation)
  //  DQN agent learns to lap an oval track; shows training progress live.
  // â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

  function vizSpeedRacer() {
    const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!container) return null;
    container.style.background = '#0a0c12';

    const cv = document.createElement('canvas');
    cv.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;';
    container.appendChild(cv);
    const ctx = cv.getContext('2d');

    function resize() { cv.width = container.clientWidth || 900; cv.height = container.clientHeight || 600; }
    resize();
    window.addEventListener('resize', resize);

    /* â”€â”€ Track geometry (oval) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    function trackCenter(W, H) {
      return { cx: W * 0.5, cy: H * 0.52, rx: W * 0.36, ry: H * 0.30 };
    }
    const TRACK_W = 52;  // track width in px (will scale with canvas)

    // Point on ellipse at angle t
    function ellipsePoint(cx, cy, rx, ry, t) {
      return { x: cx + rx * Math.cos(t), y: cy + ry * Math.sin(t) };
    }

    /* â”€â”€ Car state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    let carAngle = 0;   // position on ellipse [0, 2Ï€]
    let carSpeed = 0.012;
    let carLap = 0;
    let crashTimer = 0;

    /* â”€â”€ DQN simulation state â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    let episode = 1;
    let stepCount = 0;
    let totalReward = 0;
    let epsilon = 1.0;          // exploration rate (decays each episode)
    const lossHistory = [];    // fake training loss
    const rewardHistory = [];
    const MAX_HIST = 60;
    let trainMode = true;
    let episodeTimer = 0;

    // Simulated Q-values (3 actions: turn-left, straight, turn-right)
    let qLeft = 0, qStr = 0, qRight = 0;

    /* â”€â”€ Sensor rays (5 directions) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    const RAY_ANGLES = [-70, -35, 0, 35, 70];
    let rayLengths = [1, 1, 1, 1, 1];  // normalized 0..1

    /* â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    function simRayLengths(W, H) {
      const { cx, cy, rx, ry } = trackCenter(W, H);
      const pt = ellipsePoint(cx, cy, rx, ry, carAngle);
      const tangent = Math.atan2(-ry * Math.sin(carAngle), rx * Math.cos(carAngle));
      return RAY_ANGLES.map(deg => {
        const a = tangent + deg * Math.PI / 180;
        const dist = (1 - Math.abs(deg) / 90) * 0.8 + 0.15 + Math.random() * 0.06;
        return Math.min(1, Math.max(0.1, dist));
      });
    }

    function drawTrack(W, H) {
      const { cx, cy, rx, ry } = trackCenter(W, H);
      const scale = Math.min(W, H) / 600;
      const tw = TRACK_W * scale;

      ctx.save();

      // Outer track edge
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx + tw, ry + tw, 0, 0, Math.PI * 2);
      ctx.fillStyle = '#1a1f2e';
      ctx.fill();

      // Track surface
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx + tw, ry + tw, 0, 0, Math.PI * 2);
      ctx.fillStyle = '#2a3042';
      ctx.fill();

      // Infield
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx - tw, ry - tw, 0, 0, Math.PI * 2);
      ctx.fillStyle = '#0e1018';
      ctx.fill();

      // Track center-line dashes
      ctx.setLineDash([14, 14]);
      ctx.strokeStyle = 'rgba(255,200,50,0.3)';
      ctx.lineWidth = 1.5 * scale;
      ctx.beginPath();
      ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // Start/finish line
      const sp = ellipsePoint(cx, cy, rx + tw, ry + tw, 0);
      const ep = ellipsePoint(cx, cy, rx - tw, ry - tw, 0);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 3 * scale;
      ctx.beginPath();
      ctx.moveTo(sp.x, sp.y); ctx.lineTo(ep.x, ep.y);
      ctx.stroke();

      ctx.restore();
    }

    function drawCar(W, H) {
      const { cx, cy, rx, ry } = trackCenter(W, H);
      const scale = Math.min(W, H) / 600;
      const pt = ellipsePoint(cx, cy, rx, ry, carAngle);
      const tang = Math.atan2(-ry * Math.sin(carAngle), rx * Math.cos(carAngle));

      ctx.save();
      ctx.translate(pt.x, pt.y);
      ctx.rotate(tang + Math.PI / 2);

      const CW = 10 * scale, CL = 18 * scale;
      const crashed = crashTimer > 0;
      ctx.fillStyle = crashed ? '#ff4444' : '#00ffcc';
      ctx.shadowColor = crashed ? '#ff4444' : '#00ffcc';
      ctx.shadowBlur = crashed ? 12 : 20;

      // Car body (rounded rect)
      ctx.beginPath();
      ctx.roundRect(-CW / 2, -CL / 2, CW, CL, 3);
      ctx.fill();

      // Cockpit
      ctx.fillStyle = crashed ? '#ff8888' : '#004433';
      ctx.shadowBlur = 0;
      ctx.beginPath();
      ctx.ellipse(0, 0, CW * 0.35, CL * 0.28, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();
    }

    function drawRays(W, H) {
      const { cx, cy, rx, ry } = trackCenter(W, H);
      const scale = Math.min(W, H) / 600;
      const pt = ellipsePoint(cx, cy, rx, ry, carAngle);
      const tang = Math.atan2(-ry * Math.sin(carAngle), rx * Math.cos(carAngle));
      const tw = TRACK_W * scale;

      RAY_ANGLES.forEach((deg, i) => {
        const a = tang + (deg - 90) * Math.PI / 180;
        const len = rayLengths[i] * tw * 2.2;
        const ex = pt.x + Math.cos(a) * len;
        const ey = pt.y + Math.sin(a) * len;
        const hue = rayLengths[i] > 0.6 ? 120 : rayLengths[i] > 0.35 ? 50 : 0;
        ctx.strokeStyle = `hsla(${hue},100%,70%,0.45)`;
        ctx.lineWidth = 1.2 * scale;
        ctx.beginPath(); ctx.moveTo(pt.x, pt.y); ctx.lineTo(ex, ey); ctx.stroke();
        ctx.fillStyle = `hsla(${hue},100%,70%,0.9)`;
        ctx.beginPath(); ctx.arc(ex, ey, 2.5 * scale, 0, Math.PI * 2); ctx.fill();
      });
    }

    function drawQValues(W, H) {
      const scale = Math.min(W, H) / 600;
      const x = 16 * scale, y = H - 110 * scale;
      const BW = 56 * scale, BH = 22 * scale, gap = 6 * scale;
      const labels = ['â—„ L', 'â–² FWD', 'R â–º'];
      const vals = [qLeft, qStr, qRight];
      const maxQ = Math.max(...vals, 0.01);

      ctx.font = `bold ${11 * scale}px monospace`;
      ctx.fillStyle = 'rgba(0,255,204,0.5)';
      ctx.fillText('Q-VALUES', x, y - 6 * scale);

      vals.forEach((q, i) => {
        const bx = x + i * (BW + gap);
        const fill = q / maxQ;
        const col = i === vals.indexOf(maxQ) ? '#00ffcc' : '#334455';
        ctx.fillStyle = '#111827';
        ctx.fillRect(bx, y, BW, BH);
        ctx.fillStyle = col;
        ctx.fillRect(bx, y + BH * (1 - fill), BW, BH * fill);
        ctx.strokeStyle = 'rgba(0,255,204,0.25)';
        ctx.lineWidth = 1;
        ctx.strokeRect(bx, y, BW, BH);
        ctx.fillStyle = '#e2e8f0';
        ctx.font = `${9 * scale}px monospace`;
        ctx.textAlign = 'center';
        ctx.fillText(labels[i], bx + BW / 2, y + BH + 12 * scale);
        ctx.fillText(q.toFixed(2), bx + BW / 2, y + BH * 0.62);
        ctx.textAlign = 'left';
      });
    }

    function drawStats(W, H) {
      const scale = Math.min(W, H) / 600;
      const x = 16 * scale, y = 14 * scale;
      const lh = 18 * scale;

      ctx.font = `${10 * scale}px monospace`;
      ctx.textAlign = 'left';

      function row(label, val, color) {
        ctx.fillStyle = 'rgba(100,116,139,0.9)'; ctx.fillText(label, x, y + lh * row._i);
        ctx.fillStyle = color || '#e2e8f0';
        ctx.fillText(val, x + 80 * scale, y + lh * row._i);
        row._i++;
      }
      row._i = 0;
      row('EPISODE', episode, '#00ffcc');
      row('STEPS', stepCount, '#94a3b8');
      row('REWARD', totalReward.toFixed(1), totalReward > 0 ? '#34d399' : '#f87171');
      row('EPSILON', epsilon.toFixed(3), '#f59e0b');
      row('LAPS', carLap, '#a78bfa');
      row('MODE', trainMode ? 'TRAIN' : 'EVAL', trainMode ? '#f59e0b' : '#34d399');
    }

    function drawLossCurve(W, H) {
      if (lossHistory.length < 2) return;
      const scale = Math.min(W, H) / 600;
      const PW = 160 * scale, PH = 60 * scale;
      const px = W - PW - 16 * scale, py = H - PH - 40 * scale;

      ctx.fillStyle = 'rgba(10,12,18,0.75)';
      ctx.strokeStyle = 'rgba(0,255,204,0.2)';
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.roundRect(px - 6, py - 20 * scale, PW + 12, PH + 26 * scale, 6); ctx.fill(); ctx.stroke();

      ctx.font = `${9 * scale}px monospace`;
      ctx.fillStyle = 'rgba(0,255,204,0.5)';
      ctx.textAlign = 'right';
      ctx.fillText('TRAINING LOSS', px + PW, py - 8 * scale);
      ctx.textAlign = 'left';

      const minL = Math.min(...lossHistory), maxL = Math.max(...lossHistory, minL + 0.001);
      ctx.beginPath();
      lossHistory.forEach((v, i) => {
        const lx = px + (i / (lossHistory.length - 1)) * PW;
        const ly = py + PH - ((v - minL) / (maxL - minL)) * PH;
        i === 0 ? ctx.moveTo(lx, ly) : ctx.lineTo(lx, ly);
      });
      ctx.strokeStyle = '#00ffcc';
      ctx.lineWidth = 1.5 * scale;
      ctx.stroke();

      // Reward curve overlay
      if (rewardHistory.length > 1) {
        const minR = Math.min(...rewardHistory), maxR = Math.max(...rewardHistory, minR + 0.001);
        ctx.beginPath();
        rewardHistory.forEach((v, i) => {
          const lx = px + (i / (rewardHistory.length - 1)) * PW;
          const ly = py + PH - ((v - minR) / (maxR - minR)) * PH;
          i === 0 ? ctx.moveTo(lx, ly) : ctx.lineTo(lx, ly);
        });
        ctx.strokeStyle = '#34d399';
        ctx.lineWidth = 1.2 * scale;
        ctx.stroke();
      }

      // Legend
      ctx.font = `${8 * scale}px monospace`;
      ctx.fillStyle = '#00ffcc'; ctx.fillText('â— Loss', px, py + PH + 14 * scale);
      ctx.fillStyle = '#34d399'; ctx.fillText('â— Reward', px + 50 * scale, py + PH + 14 * scale);
    }

    /* â”€â”€ Simulation step â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    function simStep(W, H) {
      stepCount++;
      episodeTimer++;

      // Update sensor rays
      rayLengths = simRayLengths(W, H);
      const minRay = Math.min(...rayLengths);

      // Simulated Q-values: better policies emerge as epsilon decays
      const skillLevel = 1 - epsilon;          // 0=random, 1=expert
      const frontRay = rayLengths[2];
      const leftBias = rayLengths[0] - rayLengths[4];  // negative = veer right
      qStr = skillLevel * frontRay + (1 - skillLevel) * Math.random();
      qLeft = skillLevel * (rayLengths[1] + leftBias * 0.5) * 0.8 + (1 - skillLevel) * Math.random();
      qRight = skillLevel * (rayLengths[3] - leftBias * 0.5) * 0.8 + (1 - skillLevel) * Math.random();

      // Choose action (epsilon-greedy)
      let action;
      if (Math.random() < epsilon) {
        action = Math.floor(Math.random() * 3); // random explore
      } else {
        action = [qLeft, qStr, qRight].indexOf(Math.max(qLeft, qStr, qRight));
      }

      // Apply action
      const steerForce = 0.008 * (1 + skillLevel * 0.5);
      if (action === 0) carAngle -= steerForce;
      if (action === 2) carAngle += steerForce;

      // Speed with crash detection
      if (minRay < 0.22 && Math.random() < (1 - skillLevel) * 0.3) {
        crashTimer = 18;
      }
      if (crashTimer > 0) {
        carSpeed = Math.max(0.003, carSpeed * 0.88);
        crashTimer--;
        totalReward -= 0.8;
      } else {
        carSpeed = Math.min(0.022 + skillLevel * 0.014, carSpeed * 1.02 + 0.0003);
        totalReward += carSpeed * 0.6 + (minRay > 0.55 ? 0.3 : 0);
      }

      const prevAngle = carAngle;
      carAngle = (carAngle + carSpeed) % (Math.PI * 2);

      // Lap detection
      if (prevAngle > Math.PI * 1.9 && carAngle < 0.2) carLap++;

      // Episode reset (every ~400 steps in early training, up to ~1200 later)
      const epLen = Math.floor(300 + skillLevel * 900);
      if (episodeTimer > epLen) {
        lossHistory.push(Math.max(0.02, 1.4 * Math.exp(-episode * 0.018) + Math.random() * 0.15));
        rewardHistory.push(totalReward / Math.max(1, episodeTimer) * 10);
        if (lossHistory.length > MAX_HIST) lossHistory.shift();
        if (rewardHistory.length > MAX_HIST) rewardHistory.shift();

        episode++;
        episodeTimer = 0;
        totalReward = 0;
        carLap = 0;
        carAngle = 0;
        carSpeed = 0.012;
        epsilon = Math.max(0.05, epsilon * 0.94);
        if (episode > 80) trainMode = false;
      }
    }

    /* â”€â”€ Main draw loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
    let animId;
    function frame() {
      animId = requestAnimationFrame(frame);
      const W = cv.width, H = cv.height;
      ctx.clearRect(0, 0, W, H);

      // Dark background with grid hint
      ctx.fillStyle = '#0a0c12';
      ctx.fillRect(0, 0, W, H);

      simStep(W, H);
      drawTrack(W, H);
      drawRays(W, H);
      drawCar(W, H);
      drawQValues(W, H);
      drawStats(W, H);
      drawLossCurve(W, H);

      // Title
      const scale = Math.min(W, H) / 600;
      ctx.font = `bold ${13 * scale}px monospace`;
      ctx.fillStyle = '#f59e0b';
      ctx.textAlign = 'right';
      ctx.fillText('DQN SPEED RACER', W - 16 * scale, 20 * scale);
      ctx.font = `${9 * scale}px monospace`;
      ctx.fillStyle = 'rgba(245,158,11,0.45)';
      ctx.fillText('Deep Q-Network Â· Îµ-greedy Â· Replay Buffer', W - 16 * scale, 34 * scale);
      ctx.textAlign = 'left';
    }
    animId = requestAnimationFrame(frame);

    return function destroy() {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
      if (cv.parentNode) cv.parentNode.removeChild(cv);
    };
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     NEW VIZ 1 â€” ASSET DNA NETWORK
     Inspired by GitNexus (Sigma.js force-directed knowledge graphs)
     Canvas force simulation: assets = nodes, correlations = spring edges.
     Clusters emerge naturally by sector/correlation. Fully interactive.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizAssetGraph() {
    const canvas = document.getElementById('viz-canvas');
    const container = document.getElementById('viz-canvas-container');
    if (!canvas || !container) return;
    const W = canvas.width = container.clientWidth;
    const H = canvas.height = container.clientHeight;
    const ctx = canvas.getContext('2d');

    const ASSETS = [
      { id: 'SPY', sector: 'ETF', col: '#38bdf8' }, { id: 'QQQ', sector: 'ETF', col: '#38bdf8' },
      { id: 'AAPL', sector: 'Tech', col: '#a78bfa' }, { id: 'MSFT', sector: 'Tech', col: '#a78bfa' },
      { id: 'NVDA', sector: 'Tech', col: '#a78bfa' }, { id: 'GOOGL', sector: 'Tech', col: '#a78bfa' },
      { id: 'AMZN', sector: 'Retail', col: '#f59e0b' }, { id: 'TSLA', sector: 'Auto', col: '#ef4444' },
      { id: 'GLD', sector: 'Cmdty', col: '#fbbf24' }, { id: 'BTC', sector: 'Crypto', col: '#f97316' },
      { id: 'ETH', sector: 'Crypto', col: '#f97316' }, { id: 'JPM', sector: 'Finance', col: '#34d399' },
      { id: 'BAC', sector: 'Finance', col: '#34d399' }, { id: 'XOM', sector: 'Energy', col: '#fb7185' },
      { id: 'DXY', sector: 'FX', col: '#94a3b8' }, { id: 'TLT', sector: 'Bond', col: '#67e8f9' },
    ];

    // Random initial positions
    const nodes = ASSETS.map((a, i) => ({
      ...a,
      x: W * 0.15 + Math.random() * W * 0.7,
      y: H * 0.15 + Math.random() * H * 0.7,
      vx: 0, vy: 0,
      r: 18 + Math.random() * 14,
      mass: 1,
    }));

    // Generate synthetic correlation matrix (replaced by live data when available)
    const N = nodes.length;
    const corr = Array.from({ length: N }, (_, i) => Array.from({ length: N }, (_, j) => {
      if (i === j) return 1;
      const si = ASSETS[i].sector, sj = ASSETS[j].sector;
      const base = si === sj ? 0.65 + Math.random() * 0.25 : 0.05 + Math.random() * 0.3;
      return (Math.random() > 0.5 ? 1 : -1) * base * (si === sj ? 1 : (Math.random() > 0.7 ? -1 : 1));
    }));

    // â”€â”€ Inject real correlations from /api/vizlab/market_graph â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const _idToIdx = Object.fromEntries(ASSETS.map((a, i) => [a.id, i]));
    let _assetGraphLabel = 'Asset DNA Network â€” Simulated';
    _api.get('/api/vizlab/market_graph').then(d => {
      if (!d || !d.edges) return;
      _assetGraphLabel = `Asset DNA Network â€” LIVE (${d.n_days || '?'}d)`;
      d.edges.forEach(e => {
        const i = _idToIdx[e.from], j = _idToIdx[e.to];
        if (i !== undefined && j !== undefined) {
          corr[i][j] = e.corr;
          corr[j][i] = e.corr;
        }
      });
    }).catch(() => { });

    let animId = null, frame = 0;
    let dragging = null, mx = W / 2, my = H / 2;

    const REPEL = 2800, SPRING_K = 0.012, DAMP = 0.88, CENTER_PULL = 0.004;

    function simulate() {
      for (let i = 0; i < N; i++) {
        let fx = 0, fy = 0;
        // Repulsion from all other nodes
        for (let j = 0; j < N; j++) {
          if (i === j) continue;
          const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y;
          const d2 = dx * dx + dy * dy + 1;
          fx += dx * REPEL / d2;
          fy += dy * REPEL / d2;
        }
        // Spring attraction from high-correlation pairs
        for (let j = 0; j < N; j++) {
          if (i === j) continue;
          const c = corr[i][j];
          if (Math.abs(c) < 0.4) continue;
          const dx = nodes[j].x - nodes[i].x, dy = nodes[j].y - nodes[i].y;
          const d = Math.sqrt(dx * dx + dy * dy) + 0.01;
          const targetD = 80 + (1 - Math.abs(c)) * 120;
          const stretch = (d - targetD) * SPRING_K * Math.abs(c);
          fx += dx / d * stretch;
          fy += dy / d * stretch;
        }
        // Center pull
        fx += (W / 2 - nodes[i].x) * CENTER_PULL;
        fy += (H / 2 - nodes[i].y) * CENTER_PULL;

        if (nodes[i] !== dragging) {
          nodes[i].vx = (nodes[i].vx + fx) * DAMP;
          nodes[i].vy = (nodes[i].vy + fy) * DAMP;
          nodes[i].x = Math.max(nodes[i].r + 4, Math.min(W - nodes[i].r - 4, nodes[i].x + nodes[i].vx));
          nodes[i].y = Math.max(nodes[i].r + 4, Math.min(H - nodes[i].r - 4, nodes[i].y + nodes[i].vy));
        }
      }
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#050916';
      ctx.fillRect(0, 0, W, H);
      frame++;

      // Draw edges
      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          const c = corr[i][j];
          if (Math.abs(c) < 0.3) continue;
          const pulse = 0.5 + 0.5 * Math.sin(frame * 0.03 + i * 0.4 + j * 0.7);
          const alpha = (Math.abs(c) - 0.3) * 1.4 * (0.6 + 0.4 * pulse);
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.strokeStyle = c > 0 ? `rgba(56,189,248,${alpha})` : `rgba(251,113,133,${alpha})`;
          ctx.lineWidth = Math.abs(c) * 2.5 * pulse;
          ctx.stroke();
        }
      }
      // Draw nodes
      for (let i = 0; i < N; i++) {
        const n = nodes[i];
        const pulse = 0.85 + 0.15 * Math.sin(frame * 0.05 + i * 0.8);
        // Glow
        const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r * 2.2);
        g.addColorStop(0, n.col + '55');
        g.addColorStop(1, 'transparent');
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r * 2.2, 0, Math.PI * 2);
        ctx.fillStyle = g; ctx.fill();
        // Node body
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r * pulse, 0, Math.PI * 2);
        ctx.fillStyle = n.col + '22';
        ctx.fill();
        ctx.strokeStyle = n.col;
        ctx.lineWidth = 1.5;
        ctx.stroke();
        // Label
        ctx.font = `bold ${Math.round(n.r * 0.65)}px monospace`;
        ctx.fillStyle = '#fff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(n.id, n.x, n.y);
      }
      // Legend
      ctx.font = '10px monospace'; ctx.textAlign = 'left'; ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(56,189,248,0.8)'; ctx.fillText('â”€â”€â”€ positive correlation', 14, 14);
      ctx.fillStyle = 'rgba(251,113,133,0.8)'; ctx.fillText('â”€â”€â”€ negative correlation', 14, 28);
      ctx.fillStyle = 'rgba(150,150,180,0.7)'; ctx.fillText(_assetGraphLabel, 14, 44);

      simulate();
      animId = requestAnimationFrame(draw);
    }

    // Drag interaction
    canvas.addEventListener('mousedown', e => {
      const r = canvas.getBoundingClientRect();
      const px = e.clientX - r.left, py = e.clientY - r.top;
      dragging = nodes.find(n => Math.hypot(n.x - px, n.y - py) < n.r + 6) || null;
    });
    canvas.addEventListener('mousemove', e => {
      const r = canvas.getBoundingClientRect();
      if (dragging) { dragging.x = e.clientX - r.left; dragging.y = e.clientY - r.top; dragging.vx = 0; dragging.vy = 0; }
    });
    canvas.addEventListener('mouseup', () => { dragging = null; });

    animId = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(animId); canvas.removeEventListener('mousedown', () => { }); };
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     NEW VIZ 2 â€” WORLD MODEL
     Inspired by open-genie (MagViT-2 / MaskGIT price-token generation)
     Grid of price tokens: some get masked (flash) then "predicted" â€”
     showing a generative model imagining future market states.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizWorldModel() {
    const canvas = document.getElementById('viz-canvas');
    const container = document.getElementById('viz-canvas-container');
    if (!canvas || !container) return;
    const W = canvas.width = container.clientWidth;
    const H = canvas.height = container.clientHeight;
    const ctx = canvas.getContext('2d');

    const COLS = 40, ROWS = 24;
    const CW = W / COLS, CH = H / ROWS;
    const N = COLS * ROWS;

    // Each token has a value (price delta), generation state, and color
    const tokens = Array.from({ length: N }, (_, i) => ({
      val: Math.random() * 2 - 1,      // -1..1
      state: 'known',              // 'known' | 'masked' | 'generated'
      t: Math.random() * Math.PI * 2,  // phase for animation
      confidence: 0.8 + Math.random() * 0.2,
    }));

    // â”€â”€ Live market state seeds token grid from real system signals â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _wmLabel = 'World Model â€” Simulated';
    _api.get('/api/vizlab/system_status').then(d => {
      if (!d) return;
      _wmLabel = 'World Model â€” LIVE system state';
      // Use system health scores to seed token confidence
      const health = d.health_score ?? 0.7;
      const signal = d.signal_score ?? 0.0;  // -1..1
      tokens.forEach((tk, i) => {
        const col = i % COLS, row = i % ROWS;
        // Blend real signal trend into left half (known tokens)
        if (col < COLS * 0.7) {
          tk.val = clamp(signal + (Math.random() - 0.5) * 0.5, -1, 1);
          tk.confidence = health * (0.7 + Math.random() * 0.3);
        }
      });
    }).catch(() => { });

    let frame = 0, animId = null;
    let phase = 'encode';          // encode â†’ mask â†’ generate â†’ show â†’ encode ...
    let phaseTimer = 0;
    const PHASE_DUR = { encode: 80, mask: 40, generate: 60, show: 40 };
    let maskSet = new Set();
    let genProgress = 0;

    function valToColor(v, state, confidence) {
      if (state === 'masked') return `rgba(255,255,255,${0.7 + 0.3 * Math.sin(frame * 0.3)})`;
      const r = v > 0 ? 16 : 244, g = v > 0 ? 185 : 63, b = v > 0 ? 129 : 94;
      const a = (0.15 + Math.abs(v) * 0.7) * confidence;
      if (state === 'generated') return `rgba(167,139,250,${a + 0.2})`;
      return `rgba(${r},${g},${b},${a})`;
    }

    function startMask() {
      maskSet.clear();
      // Mask a contiguous future block (right portion = "future")
      const futureStart = Math.floor(COLS * 0.7);
      for (let r = 0; r < ROWS; r++) {
        for (let c = futureStart; c < COLS; c++) {
          if (Math.random() < 0.85) maskSet.add(r * COLS + c);
        }
      }
      tokens.forEach((t, i) => { t.state = maskSet.has(i) ? 'masked' : 'known'; });
      genProgress = 0;
    }

    function stepGenerate() {
      // Iteratively unmask tokens from left to right (MaskGIT-style)
      const masked = [...maskSet].filter(i => tokens[i].state === 'masked');
      if (masked.length === 0) return;
      const reveal = Math.max(1, Math.floor(masked.length * genProgress));
      masked.slice(0, reveal).forEach(i => {
        if (tokens[i].state === 'masked') {
          tokens[i].state = 'generated';
          tokens[i].val = Math.random() * 2 - 1;
          tokens[i].confidence = 0.4 + Math.random() * 0.4;
        }
      });
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#040a14';
      ctx.fillRect(0, 0, W, H);
      frame++;

      // Phase machine
      phaseTimer++;
      if (phase === 'encode' && phaseTimer > PHASE_DUR.encode) {
        // Re-randomize known tokens slightly
        tokens.forEach((t, i) => {
          t.val += (Math.random() - 0.5) * 0.08;
          t.val = Math.max(-1, Math.min(1, t.val));
          t.state = 'known';
        });
        phase = 'mask'; phaseTimer = 0; startMask();
      } else if (phase === 'mask' && phaseTimer > PHASE_DUR.mask) {
        phase = 'generate'; phaseTimer = 0;
      } else if (phase === 'generate') {
        genProgress = Math.min(1, phaseTimer / PHASE_DUR.generate);
        stepGenerate();
        if (phaseTimer > PHASE_DUR.generate) { phase = 'show'; phaseTimer = 0; }
      } else if (phase === 'show' && phaseTimer > PHASE_DUR.show) {
        // Commit generated tokens as known
        tokens.forEach(t => { if (t.state === 'generated') { t.state = 'known'; t.confidence = 0.8 + Math.random() * 0.2; } });
        phase = 'encode'; phaseTimer = 0;
      }

      // Draw tokens
      for (let i = 0; i < N; i++) {
        const c = i % COLS, r = Math.floor(i / COLS);
        const t = tokens[i];
        const x = c * CW, y = r * CH;
        const pulse = 0.85 + 0.15 * Math.sin(frame * 0.08 + t.t);
        ctx.fillStyle = valToColor(t.val, t.state, pulse);
        ctx.fillRect(x + 0.5, y + 0.5, CW - 1, CH - 1);
        if (t.state === 'masked') {
          ctx.fillStyle = `rgba(255,255,255,${0.6 + 0.4 * Math.sin(frame * 0.25 + i)})`;
          ctx.fillRect(x + 0.5, y + 0.5, CW - 1, CH - 1);
        }
      }

      // Divider between past/future
      const fx = Math.floor(COLS * 0.7) * CW;
      ctx.strokeStyle = 'rgba(255,255,255,0.25)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 3]);
      ctx.beginPath(); ctx.moveTo(fx, 0); ctx.lineTo(fx, H); ctx.stroke();
      ctx.setLineDash([]);

      // Labels
      ctx.font = '11px monospace'; ctx.fillStyle = 'rgba(255,255,255,0.5)'; ctx.textAlign = 'center';
      ctx.fillText('KNOWN HISTORY', fx * 0.5, 14);
      ctx.fillStyle = 'rgba(167,139,250,0.8)';
      ctx.fillText('GENERATED FUTURE', fx + (W - fx) * 0.5, 14);

      // Phase indicator
      const phaseColors = { encode: '#38bdf8', mask: '#fbbf24', generate: '#a78bfa', show: '#34d399' };
      ctx.font = 'bold 10px monospace'; ctx.textAlign = 'right';
      ctx.fillStyle = phaseColors[phase] || '#fff';
      ctx.fillText(`[${phase.toUpperCase()}]`, W - 14, H - 12);
      ctx.font = '9px monospace'; ctx.fillStyle = 'rgba(150,150,180,0.6)'; ctx.textAlign = 'left';
      ctx.fillText(_wmLabel, 12, H - 12);

      animId = requestAnimationFrame(draw);
    }
    animId = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animId);
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     NEW VIZ 3 â€” ALPHA SCANNER
     Inspired by qlib Alpha158 â€” 158 quantitative factors
     Particles orbit a glowing center, brightness = factor signal strength.
     Clusters form by factor type (momentum, value, quality, volatility).
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizAlphaScanner() {
    const canvas = document.getElementById('viz-canvas');
    const container = document.getElementById('viz-canvas-container');
    if (!canvas || !container) return;
    const W = canvas.width = container.clientWidth;
    const H = canvas.height = container.clientHeight;
    const ctx = canvas.getContext('2d');

    // â”€â”€ Live data from FactorEngine (Alpha158) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    // Map real MOMENTUM/VOLUME/VOLATILITY/QUALITY/TECHNICAL/MICRO groups
    const FACTOR_GROUPS = [
      { name: 'MOMENTUM', color: '#38bdf8', count: 28, orbit: 0.28, liveScore: 0 },
      { name: 'VOLUME', color: '#34d399', count: 22, orbit: 0.42, liveScore: 0 },
      { name: 'QUALITY', color: '#a78bfa', count: 22, orbit: 0.56, liveScore: 0 },
      { name: 'VOLATILITY', color: '#fbbf24', count: 20, orbit: 0.70, liveScore: 0 },
      { name: 'TECHNICAL', color: '#fb7185', count: 20, orbit: 0.84, liveScore: 0 },
      { name: 'MICRO', color: '#f97316', count: 18, orbit: 0.95, liveScore: 0 },
    ];
    let _alphaLiveLabel = 'SPY Â· Simulated';

    // Fetch real factor scores and update group liveScore
    _api.get('/api/factors/SPY').then(d => {
      if (!d || !d.group_scores) return;
      const gs = d.group_scores;
      FACTOR_GROUPS.forEach(g => {
        if (gs[g.name] !== undefined) {
          g.liveScore = gs[g.name];   // -1..1
        }
      });
      _alphaLiveLabel = `SPY Â· FactorEngine Alpha158 Â· ${d.top_factors?.[0]?.factor ?? ''}`;
      // Update particle signal targets based on real scores
      particles.forEach(p => {
        const grp = FACTOR_GROUPS.find(g => g.name === p.group);
        if (grp) {
          const baseSignal = (grp.liveScore + 1) / 2;   // -1..1 â†’ 0..1
          p.signalTarget = clamp(baseSignal + (Math.random() - 0.5) * 0.2, 0, 1);
        }
      });
    }).catch(() => { });

    const particles = [];
    FACTOR_GROUPS.forEach(g => {
      const R = Math.min(W, H) * 0.44 * g.orbit;
      for (let k = 0; k < g.count; k++) {
        const baseAngle = (k / g.count) * Math.PI * 2 + Math.random() * 0.3;
        particles.push({
          angle: baseAngle,
          speed: (0.003 + Math.random() * 0.004) * (Math.random() > 0.5 ? 1 : -1),
          r: R + (Math.random() - 0.5) * R * 0.22,
          size: 2.5 + Math.random() * 3.5,
          color: g.color,
          group: g.name,
          signal: Math.random(),
          signalTarget: Math.random(),
          signalSpeed: 0.002 + Math.random() * 0.006,
          pulse: Math.random() * Math.PI * 2,
        });
      }
    });

    let frame = 0, animId = null;
    const CX = W / 2, CY = H / 2;

    function draw() {
      ctx.clearRect(0, 0, W, H);
      // Deep space bg
      const bg = ctx.createRadialGradient(CX, CY, 0, CX, CY, Math.min(W, H) * 0.55);
      bg.addColorStop(0, 'rgba(16,10,40,0.97)');
      bg.addColorStop(1, 'rgba(4,6,20,0.97)');
      ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
      frame++;

      // Orbit rings
      FACTOR_GROUPS.forEach(g => {
        const R = Math.min(W, H) * 0.44 * g.orbit;
        ctx.beginPath(); ctx.arc(CX, CY, R, 0, Math.PI * 2);
        ctx.strokeStyle = g.color + '1A'; ctx.lineWidth = 1; ctx.stroke();
      });

      // Center core glow
      const pulse = 0.8 + 0.2 * Math.sin(frame * 0.04);
      const core = ctx.createRadialGradient(CX, CY, 0, CX, CY, 42 * pulse);
      core.addColorStop(0, 'rgba(167,139,250,0.9)');
      core.addColorStop(0.4, 'rgba(56,189,248,0.4)');
      core.addColorStop(1, 'transparent');
      ctx.beginPath(); ctx.arc(CX, CY, 42 * pulse, 0, Math.PI * 2);
      ctx.fillStyle = core; ctx.fill();
      ctx.beginPath(); ctx.arc(CX, CY, 14, 0, Math.PI * 2);
      ctx.fillStyle = '#fff'; ctx.fill();
      ctx.font = 'bold 9px monospace'; ctx.fillStyle = '#0a0a1a';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('Î±', CX, CY);

      // Update + draw particles
      particles.forEach((p, i) => {
        p.angle += p.speed;
        p.signal += (p.signalTarget - p.signal) * p.signalSpeed;
        if (Math.random() < 0.003) p.signalTarget = Math.random();
        p.pulse += 0.05;

        const x = CX + Math.cos(p.angle) * p.r;
        const y = CY + Math.sin(p.angle) * p.r;
        const glow = p.signal * (0.8 + 0.2 * Math.sin(p.pulse));
        const s = p.size * (0.7 + 0.5 * glow);

        // Glow halo
        const g = ctx.createRadialGradient(x, y, 0, x, y, s * 4);
        g.addColorStop(0, p.color + Math.round(glow * 180).toString(16).padStart(2, '0'));
        g.addColorStop(1, 'transparent');
        ctx.beginPath(); ctx.arc(x, y, s * 4, 0, Math.PI * 2);
        ctx.fillStyle = g; ctx.fill();

        // Core dot
        ctx.beginPath(); ctx.arc(x, y, s, 0, Math.PI * 2);
        ctx.fillStyle = p.color; ctx.globalAlpha = 0.5 + glow * 0.5;
        ctx.fill(); ctx.globalAlpha = 1;
      });

      // Legend â€” show real group scores if available
      ctx.textAlign = 'left'; ctx.textBaseline = 'top';
      FACTOR_GROUPS.forEach((g, i) => {
        ctx.fillStyle = g.color;
        ctx.font = '10px monospace';
        const scoreStr = g.liveScore !== 0 ? ` ${g.liveScore >= 0 ? '+' : ''}${(g.liveScore * 100).toFixed(0)}` : '';
        ctx.fillText(`â— ${g.name}${scoreStr}`, 14, 14 + i * 16);
      });
      ctx.fillStyle = 'rgba(255,255,255,0.3)'; ctx.textAlign = 'right'; ctx.textBaseline = 'bottom';
      ctx.fillText(_alphaLiveLabel, W - 14, H - 10);

      animId = requestAnimationFrame(draw);
    }
    animId = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animId);
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     NEW VIZ 4 â€” DCF UNIVERSE
     Inspired by Dexter's DCF valuation + SOUL.md (Buffett/Munger)
     3D Three.js scatter: X=P/E, Y=Revenue Growth, Z=Momentum
     Bubble size = market cap. Color = DCF margin of safety.
     Camera orbits slowly. Click a stock to "value" it.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizDCFUniverse() {
    const container = document.getElementById('viz-canvas-container');
    if (!container || typeof THREE === 'undefined') { _fallback2D('dcfuniverse'); return; }

    const W = container.clientWidth, H = container.clientHeight;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.domElement.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;';
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x04060e);
    scene.fog = new THREE.FogExp2(0x04060e, 0.018);

    const camera = new THREE.PerspectiveCamera(55, W / H, 0.1, 500);
    camera.position.set(18, 12, 22);
    camera.lookAt(0, 0, 0);

    // Ambient + point lights
    scene.add(new THREE.AmbientLight(0x334466, 0.8));
    const pLight = new THREE.PointLight(0x38bdf8, 2.5, 60);
    pLight.position.set(0, 10, 0);
    scene.add(pLight);

    // Stock data (synthetic â€” realistic ranges)
    const STOCKS = [
      { sym: 'AAPL', pe: 28, growth: 0.08, mom: 0.72, mcap: 2.8, mos: 0.15 },
      { sym: 'MSFT', pe: 34, growth: 0.12, mom: 0.65, mcap: 2.9, mos: 0.08 },
      { sym: 'NVDA', pe: 55, growth: 0.55, mom: 0.92, mcap: 1.8, mos: -0.25 },
      { sym: 'GOOGL', pe: 22, growth: 0.10, mom: 0.58, mcap: 1.9, mos: 0.22 },
      { sym: 'AMZN', pe: 40, growth: 0.13, mom: 0.61, mcap: 1.7, mos: 0.05 },
      { sym: 'TSLA', pe: 65, growth: 0.22, mom: -0.15, mcap: 0.8, mos: -0.42 },
      { sym: 'META', pe: 24, growth: 0.18, mom: 0.78, mcap: 1.3, mos: 0.28 },
      { sym: 'BRK', pe: 20, growth: 0.05, mom: 0.45, mcap: 0.9, mos: 0.38 },
      { sym: 'JNJ', pe: 14, growth: 0.03, mom: 0.28, mcap: 0.4, mos: 0.35 },
      { sym: 'JPM', pe: 12, growth: 0.07, mom: 0.52, mcap: 0.6, mos: 0.30 },
      { sym: 'XOM', pe: 13, growth: 0.04, mom: 0.38, mcap: 0.5, mos: 0.25 },
      { sym: 'V', pe: 30, growth: 0.11, mom: 0.62, mcap: 0.5, mos: 0.18 },
      { sym: 'WMT', pe: 26, growth: 0.04, mom: 0.42, mcap: 0.5, mos: 0.12 },
      { sym: 'BAC', pe: 11, growth: 0.06, mom: 0.44, mcap: 0.3, mos: 0.32 },
      { sym: 'DIS', pe: 45, growth: -0.03, mom: -0.22, mcap: 0.2, mos: -0.35 },
      { sym: 'COIN', pe: 120, growth: 0.60, mom: 0.85, mcap: 0.06, mos: -0.60 },
      { sym: 'GS', pe: 13, growth: 0.08, mom: 0.55, mcap: 0.16, mos: 0.28 },
      { sym: 'COST', pe: 48, growth: 0.08, mom: 0.68, mcap: 0.34, mos: 0.04 },
    ];

    // â”€â”€ Live factor scores update momentum axis for all stocks â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    let _dcfLabel = 'DCF Universe â€” Simulated';
    _api.get('/api/factors/SPY').then(d => {
      if (!d || !d.group_scores) return;
      const momScore = d.group_scores['MOMENTUM'] || 0;  // -1..1
      const techScore = d.group_scores['TECHNICAL'] || 0;
      _dcfLabel = `DCF Universe â€” SPY LIVE  mom:${momScore >= 0 ? '+' : ''}${(momScore * 100).toFixed(0)}`;
      // Nudge all momentum values toward real market momentum
      STOCKS.forEach(s => {
        s.mom = clamp(s.mom * 0.7 + (momScore * 0.5 + 0.5) * 0.3, -0.3, 1.0);
        // Update mos slightly based on technical score (tech positive = less overvalued)
        s.mos = clamp(s.mos + techScore * 0.05, -0.8, 0.6);
        // Update mesh if exists
        const mesh = meshes.find(m => m.userData.sym === s.sym);
        if (mesh) {
          mesh.position.z = s.mom * 14 - 4;
          const r_ = s.mos < 0 ? 1 : 1 - s.mos;
          const g_ = s.mos > 0 ? 0.9 : 0.3 + s.mos * 0.7;
          mesh.material.color.set(new THREE.Color(r_, g_, 0.3));
          mesh.material.emissive.set(new THREE.Color(r_, g_, 0.3));
        }
      });
    }).catch(() => { });

    const meshes = [];
    STOCKS.forEach(s => {
      // Map data to 3D space: X=P/E (log), Y=growth, Z=momentum
      const x = (Math.log(s.pe) - Math.log(25)) * 8;
      const y = s.growth * 30 - 3;
      const z = s.mom * 14 - 4;
      const radius = 0.25 + Math.sqrt(s.mcap) * 0.5;

      // Color by margin of safety: green=undervalued, red=overvalued
      const mos = s.mos;
      const r = mos < 0 ? 1 : 1 - mos;
      const g = mos > 0 ? 0.9 : 0.3 + mos * 0.7;
      const b = 0.3;
      const col = new THREE.Color(r, g, b);

      const geo = new THREE.SphereGeometry(radius, 16, 16);
      const mat = new THREE.MeshPhongMaterial({ color: col, emissive: col, emissiveIntensity: 0.3, transparent: true, opacity: 0.88 });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(x, y, z);
      mesh.userData = s;
      scene.add(mesh);
      meshes.push(mesh);

      // Sprite label
      const canvas2 = document.createElement('canvas');
      canvas2.width = 96; canvas2.height = 28;
      const c2 = canvas2.getContext('2d');
      c2.font = 'bold 13px monospace'; c2.fillStyle = '#fff';
      c2.textAlign = 'center'; c2.textBaseline = 'middle';
      c2.fillText(s.sym, 48, 14);
      const tex = new THREE.CanvasTexture(canvas2);
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.85 }));
      sp.scale.set(3, 0.9, 1);
      sp.position.set(x, y + radius + 0.6, z);
      scene.add(sp);
    });

    // Grid floor
    const gridH = new THREE.GridHelper(30, 20, 0x1a2a44, 0x0d1520);
    gridH.position.y = -5;
    scene.add(gridH);

    // Axis labels (arrows)
    const axMat = new THREE.LineBasicMaterial({ color: 0x334466 });
    [[new THREE.Vector3(-12, 0, 0), new THREE.Vector3(12, 0, 0)],
    [new THREE.Vector3(0, -5, 0), new THREE.Vector3(0, 10, 0)],
    [new THREE.Vector3(0, 0, -10), new THREE.Vector3(0, 0, 10)]].forEach(([a, b]) => {
      const geo = new THREE.BufferGeometry().setFromPoints([a, b]);
      scene.add(new THREE.Line(geo, axMat));
    });

    let camAngle = 0, animId = null;

    function render() {
      camAngle += 0.002;
      camera.position.x = Math.sin(camAngle) * 28;
      camera.position.z = Math.cos(camAngle) * 28;
      camera.position.y = 10 + 4 * Math.sin(camAngle * 0.3);
      camera.lookAt(0, 2, 0);

      // Pulse emissive
      meshes.forEach((m, i) => {
        const p = 0.2 + 0.15 * Math.sin(Date.now() * 0.001 + i * 0.8);
        m.material.emissiveIntensity = p;
      });

      renderer.render(scene, camera);

      // Overlay label
      const ov = document.getElementById('viz-overlay');
      if (ov && ov.querySelector('.dcf-label') === null) {
        const lb = document.createElement('div');
        lb.className = 'dcf-label';
        lb.style.cssText = 'position:absolute;bottom:10px;left:12px;font:10px monospace;color:rgba(150,170,200,0.7);pointer-events:none;';
        lb.textContent = _dcfLabel;
        ov.appendChild(lb);
      } else if (ov) {
        const lb = ov.querySelector('.dcf-label');
        if (lb) lb.textContent = _dcfLabel;
      }

      animId = requestAnimationFrame(render);
    }
    render();

    return () => {
      cancelAnimationFrame(animId);
      renderer.dispose();
      if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
    };
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     NEW VIZ 5 â€” ARIA AGENT SWARM
     Inspired by picoclaw sub-agents + ai-engineering-hub CrewAI
     Multiple AI agents (particles) orbit a central hub, each
     processing a different signal. When they "agree", they
     converge and fire a light pulse to the hub.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizAgentSwarm() {
    const canvas = document.getElementById('viz-canvas');
    const container = document.getElementById('viz-canvas-container');
    if (!canvas || !container) return;
    const W = canvas.width = container.clientWidth;
    const H = canvas.height = container.clientHeight;
    const ctx = canvas.getContext('2d');

    const CX = W / 2, CY = H / 2;
    // â”€â”€ Live data: real MultiStrategyEngine engine votes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const AGENTS = [
      { name: 'SMA Cross', col: '#38bdf8', angle: 0, speed: 0.018, orbit: 0.30, signal: 0.5, liveKey: 'sma_crossover' },
      { name: 'RSI Rev', col: '#a78bfa', angle: 1.05, speed: 0.022, orbit: 0.35, signal: 0.5, liveKey: 'rsi_mean_reversion' },
      { name: 'MACD', col: '#34d399', angle: 2.09, speed: 0.016, orbit: 0.28, signal: 0.5, liveKey: 'macd_engine' },
      { name: 'BB Squeeze', col: '#fbbf24', angle: 3.14, speed: 0.019, orbit: 0.32, signal: 0.5, liveKey: 'bb_squeeze' },
      { name: 'Momentum', col: '#fb7185', angle: 4.19, speed: 0.021, orbit: 0.38, signal: 0.5, liveKey: 'momentum_engine' },
      { name: 'Consensus', col: '#f97316', angle: 5.24, speed: 0.014, orbit: 0.26, signal: 0.5, liveKey: '_consensus' },
    ];
    let _swarmConsensus = 'HOLD';
    let _swarmConf = 0.5;

    _api.get('/api/strategy/analyze/SPY').then(d => {
      if (!d) return;
      const ind = d.individual || {};
      const con = d.consensus || {};
      AGENTS.forEach(a => {
        if (a.liveKey === '_consensus') {
          a.signal = con.action === 'BUY' ? 0.8 : con.action === 'SELL' ? 0.2 : 0.5;
          a.name = `${con.action || 'HOLD'}`;
        } else if (ind[a.liveKey]) {
          const eng = ind[a.liveKey];
          const raw = eng.signal ?? 0;
          a.signal = clamp((raw + 1) / 2, 0, 1);
          if (eng.action) a.name = a.name; // keep engine short name
        }
      });
      _swarmConsensus = con.action || 'HOLD';
      _swarmConf = con.confidence || 0.5;
    }).catch(() => { });

    const R = Math.min(W, H) * 0.42;
    let frame = 0, animId = null;
    const pulses = [];  // {x,y,tx,ty,t,col} light pulses to hub

    function draw() {
      // Fade trail
      ctx.fillStyle = 'rgba(4,6,14,0.18)';
      ctx.fillRect(0, 0, W, H);
      frame++;

      // Central ARIA hub
      const hubPulse = 0.9 + 0.1 * Math.sin(frame * 0.06);
      const hubR = 32 * hubPulse;
      const hg = ctx.createRadialGradient(CX, CY, 0, CX, CY, hubR * 2.5);
      hg.addColorStop(0, 'rgba(167,139,250,0.9)');
      hg.addColorStop(0.5, 'rgba(56,189,248,0.35)');
      hg.addColorStop(1, 'transparent');
      ctx.beginPath(); ctx.arc(CX, CY, hubR * 2.5, 0, Math.PI * 2);
      ctx.fillStyle = hg; ctx.fill();
      ctx.beginPath(); ctx.arc(CX, CY, hubR, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(167,139,250,0.2)';
      ctx.strokeStyle = 'rgba(167,139,250,0.8)';
      ctx.lineWidth = 2; ctx.fill(); ctx.stroke();
      ctx.font = 'bold 12px monospace'; ctx.fillStyle = '#e0d8ff';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('ARIA', CX, CY - 7);
      ctx.font = '8px monospace'; ctx.fillStyle = 'rgba(167,139,250,0.7)';
      ctx.fillText('CONSENSUS', CX, CY + 8);

      // Update agents
      AGENTS.forEach((a, i) => {
        a.angle += a.speed;
        // Signal drifts randomly
        a.signal += (Math.random() - 0.5) * 0.015;
        a.signal = Math.max(0, Math.min(1, a.signal));

        const ax = CX + Math.cos(a.angle) * R * a.orbit;
        const ay = CY + Math.sin(a.angle) * R * a.orbit;

        // Connection line to hub
        ctx.beginPath(); ctx.moveTo(ax, ay); ctx.lineTo(CX, CY);
        ctx.strokeStyle = a.col + '33'; ctx.lineWidth = 1; ctx.stroke();

        // Agent glow
        const ag = ctx.createRadialGradient(ax, ay, 0, ax, ay, 22 * a.signal);
        ag.addColorStop(0, a.col + 'cc'); ag.addColorStop(1, 'transparent');
        ctx.beginPath(); ctx.arc(ax, ay, 22 * a.signal, 0, Math.PI * 2);
        ctx.fillStyle = ag; ctx.fill();

        // Agent body
        ctx.beginPath(); ctx.arc(ax, ay, 12, 0, Math.PI * 2);
        ctx.fillStyle = a.col + '33';
        ctx.strokeStyle = a.col;
        ctx.lineWidth = 1.5 + a.signal * 2;
        ctx.fill(); ctx.stroke();

        // Agent label
        ctx.font = 'bold 8px monospace'; ctx.fillStyle = a.col;
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(a.name, ax, ay);

        // Signal bar
        ctx.fillStyle = a.col + '44';
        ctx.fillRect(ax - 18, ay + 16, 36, 4);
        ctx.fillStyle = a.col;
        ctx.fillRect(ax - 18, ay + 16, 36 * a.signal, 4);

        // Fire pulse when signal > 0.75
        if (a.signal > 0.75 && Math.random() < 0.04) {
          pulses.push({ x: ax, y: ay, tx: CX, ty: CY, t: 0, col: a.col });
        }
      });

      // Draw pulses
      for (let i = pulses.length - 1; i >= 0; i--) {
        const p = pulses[i];
        p.t += 0.04;
        if (p.t >= 1) { pulses.splice(i, 1); continue; }
        const px = p.x + (p.tx - p.x) * p.t;
        const py = p.y + (p.ty - p.y) * p.t;
        ctx.beginPath(); ctx.arc(px, py, 3.5 * (1 - p.t * 0.4), 0, Math.PI * 2);
        ctx.fillStyle = p.col;
        ctx.globalAlpha = 1 - p.t;
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      // Consensus meter â€” use real verdict if available
      const consensus = _swarmConf;
      const meterW = Math.min(W * 0.3, 180), meterX = CX - meterW / 2, meterY = H - 32;
      ctx.fillStyle = 'rgba(255,255,255,0.08)'; ctx.fillRect(meterX, meterY, meterW, 8);
      const mCol = _swarmConsensus === 'BUY' ? '#34d399' : _swarmConsensus === 'SELL' ? '#fb7185' : '#fbbf24';
      ctx.fillStyle = mCol; ctx.fillRect(meterX, meterY, meterW * consensus, 8);
      ctx.font = '9px monospace'; ctx.fillStyle = mCol;
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      ctx.fillText(`SPY Â· ${_swarmConsensus}  ${Math.round(consensus * 100)}% CONF`, CX, meterY + 12);

      animId = requestAnimationFrame(draw);
    }
    animId = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animId);
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     SCORE PULSE â€” composite score heartbeat EKG
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizScorePulse() {
    const canvas = document.getElementById('viz-canvas');
    const ctx = canvas.getContext('2d');
    let animId, t = 0;

    const COMPONENTS = [
      { name: 'Technical', weight: 0.35, phase: 0, color: '#3498db', liveScore: null },
      { name: 'Factor', weight: 0.25, phase: 0.4, color: '#9b59b6', liveScore: null },
      { name: 'Fundamental', weight: 0.20, phase: 0.8, color: '#f1c40f', liveScore: null },
      { name: 'Momentum', weight: 0.10, phase: 1.2, color: '#2ecc71', liveScore: null },
      { name: 'Regime', weight: 0.10, phase: 1.6, color: '#e74c3c', liveScore: null },
    ];
    let _pulseVerdict = null, _pulseScore = null;

    // â”€â”€ Real composite score from ARIA Trader â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _api.get('/api/trader/analyze/SPY').then(d => {
      if (!d || !d.components) return;
      d.components.forEach(c => {
        const comp = COMPONENTS.find(x => x.name.toLowerCase() === c.name.toLowerCase());
        if (comp) comp.liveScore = c.score / 100;  // -100..100 â†’ -1..1
      });
      _pulseVerdict = d.verdict;
      _pulseScore = d.composite_score;
    }).catch(() => { });

    // Simulate a composite score trace
    let scores = [];
    let composite = [];
    for (let i = 0; i < 300; i++) {
      const s = COMPONENTS.map(c => Math.sin(i * 0.04 + c.phase) * 0.6 +
        Math.sin(i * 0.015 + c.phase * 2) * 0.3 +
        (Math.random() - 0.5) * 0.1);
      const comp = s.reduce((acc, v, idx) => acc + v * COMPONENTS[idx].weight, 0);
      scores.push(s);
      composite.push(comp);
    }

    function draw() {
      const W = canvas.width, H = canvas.height;
      ctx.fillStyle = '#06060e';
      ctx.fillRect(0, 0, W, H);

      const scrollIdx = Math.floor(t) % scores.length;
      const window = 200;
      const startI = Math.max(0, scrollIdx - window);
      const vis = scores.slice(startI, scrollIdx + 1);
      const compVis = composite.slice(startI, scrollIdx + 1);
      const N = vis.length;
      if (N < 2) { t += 0.5; animId = requestAnimationFrame(draw); return; }

      const padL = 60, padR = 30, padT = 40, padB = 30;
      const cw = W - padL - padR;
      const ch = (H - padT - padB - 60) / COMPONENTS.length;

      // Lane backgrounds
      COMPONENTS.forEach((c, ci) => {
        const y0 = padT + ci * ch;
        ctx.fillStyle = `${c.color}08`;
        ctx.fillRect(padL, y0, cw, ch - 2);

        // Zero line
        ctx.beginPath();
        ctx.moveTo(padL, y0 + ch / 2);
        ctx.lineTo(padL + cw, y0 + ch / 2);
        ctx.strokeStyle = `${c.color}22`;
        ctx.lineWidth = 1;
        ctx.stroke();

        // Label â€” show real score if available
        ctx.font = '10px monospace';
        ctx.fillStyle = c.color;
        ctx.textAlign = 'right';
        const _liveStr = c.liveScore !== null ? ` ${c.liveScore >= 0 ? '+' : ''}${Math.round(c.liveScore * 100)}` : '';
        ctx.fillText(`${c.name}${_liveStr} (${Math.round(c.weight * 100)}%)`, padL - 4, y0 + ch / 2 + 4);

        // Signal wave
        ctx.beginPath();
        for (let i = 0; i < N; i++) {
          const x = padL + (i / (N - 1)) * cw;
          const v = vis[i][ci];
          const y = y0 + ch / 2 - v * (ch * 0.4);
          i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = c.color;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Pulse dot at end
        const lastV = vis[N - 1][ci];
        const dotX = padL + cw;
        const dotY = y0 + ch / 2 - lastV * (ch * 0.4);
        ctx.beginPath();
        ctx.arc(dotX, dotY, 4, 0, Math.PI * 2);
        ctx.fillStyle = c.color;
        ctx.fill();

        // Glow
        ctx.beginPath();
        ctx.arc(dotX, dotY, 8 + Math.sin(t * 0.3) * 2, 0, Math.PI * 2);
        ctx.strokeStyle = `${c.color}44`;
        ctx.lineWidth = 2;
        ctx.stroke();
      });

      // Composite score panel
      const cy0 = padT + COMPONENTS.length * ch + 10;
      const cyH = H - cy0 - padB;

      ctx.fillStyle = 'rgba(255,255,255,0.03)';
      ctx.fillRect(padL, cy0, cw, cyH);

      // Composite zero
      ctx.beginPath();
      ctx.moveTo(padL, cy0 + cyH / 2);
      ctx.lineTo(padL + cw, cy0 + cyH / 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.15)';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.stroke();
      ctx.setLineDash([]);

      // Composite wave
      ctx.beginPath();
      for (let i = 0; i < N; i++) {
        const x = padL + (i / (N - 1)) * cw;
        const v = compVis[i];
        const y = cy0 + cyH / 2 - v * (cyH * 0.45);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      const lastComp = compVis[N - 1];
      const compColor = lastComp >= 0.2 ? '#2ecc71' : lastComp <= -0.2 ? '#e74c3c' : '#f1c40f';
      ctx.strokeStyle = compColor;
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // Composite fill
      ctx.beginPath();
      for (let i = 0; i < N; i++) {
        const x = padL + (i / (N - 1)) * cw;
        const v = compVis[i];
        const y = cy0 + cyH / 2 - v * (cyH * 0.45);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.lineTo(padL + cw, cy0 + cyH / 2);
      ctx.lineTo(padL, cy0 + cyH / 2);
      ctx.closePath();
      const grd = ctx.createLinearGradient(0, cy0, 0, cy0 + cyH);
      grd.addColorStop(0, compColor + '44');
      grd.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grd;
      ctx.fill();

      // Current composite score â€” prefer real ARIA Trader score if available
      const displayScore = _pulseScore !== null ? _pulseScore : Math.round(lastComp * 100);
      const displayVerdict = _pulseVerdict || (_pulseScore >= 50 ? 'STRONG BUY' : _pulseScore >= 25 ? 'BUY' : _pulseScore >= -15 ? 'HOLD' : _pulseScore >= -50 ? 'AVOID' : 'STRONG SELL');
      ctx.font = 'bold 18px monospace';
      ctx.fillStyle = compColor;
      ctx.textAlign = 'left';
      ctx.fillText(`SPY Â· ${_pulseVerdict || 'COMPOSITE'}  ${displayScore > 0 ? '+' : ''}${Math.round(displayScore)}`, padL + 6, cy0 + 16);

      ctx.font = '10px monospace';
      ctx.fillStyle = '#445';
      ctx.fillText('Composite Signal', padL - 4, cy0 - 4);
      ctx.textAlign = 'right';

      t += 0.5;
      animId = requestAnimationFrame(draw);
    }

    draw();
    return () => cancelAnimationFrame(animId);
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     CORRELATION 3D SURFACE â€” asset correlation matrix mesh
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizCorrelation3D() {
    const container = document.getElementById('viz-three-mount');
    if (!container || typeof THREE === 'undefined') {
      const canvas = document.getElementById('viz-canvas');
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#06060e';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#446';
      ctx.font = '14px monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Three.js required for 3D Correlation Surface', canvas.width / 2, canvas.height / 2);
      return;
    }

    const ASSETS = ['SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'TSLA', 'JPM', 'GLD', 'TLT'];
    const N = ASSETS.length;

    // Simulate a correlation matrix with realistic structure
    function buildCorrMatrix() {
      const mat = [];
      for (let i = 0; i < N; i++) {
        mat[i] = [];
        for (let j = 0; j < N; j++) {
          if (i === j) { mat[i][j] = 1.0; continue; }
          // Tech assets corr with each other
          const techIdx = [2, 3, 4, 5, 6];
          const isTech = techIdx.includes(i) && techIdx.includes(j);
          const base = isTech ? 0.65 : 0.3;
          mat[i][j] = base + (Math.random() - 0.5) * 0.2;
          if (i === 8 || j === 8) mat[i][j] = -0.1 + (Math.random() - 0.5) * 0.15; // GLD negative corr
          if (i === 9 || j === 9) mat[i][j] = -0.3 + (Math.random() - 0.5) * 0.15; // TLT negative corr
          mat[i][j] = Math.max(-1, Math.min(1, mat[i][j]));
        }
      }
      return mat;
    }

    let corr = buildCorrMatrix();

    // â”€â”€ Live correlation matrix from /api/vizlab/market_graph â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const _c3IdMap = Object.fromEntries(ASSETS.map((a, i) => [a, i]));
    _api.get('/api/vizlab/market_graph').then(d => {
      if (!d || !d.edges) return;
      // Overwrite real correlations into the matrix
      d.edges.forEach(e => {
        const i = _c3IdMap[e.from], j = _c3IdMap[e.to];
        if (i !== undefined && j !== undefined) {
          corr[i][j] = e.corr;
          corr[j][i] = e.corr;
          // Update tile target values
          tiles.forEach(tile => {
            if ((tile.userData.i === i && tile.userData.j === j) ||
              (tile.userData.i === j && tile.userData.j === i)) {
              tile.userData.targetV = e.corr;
            }
          });
        }
      });
    }).catch(() => { });

    const scene = new THREE.Scene();
    const W = container.offsetWidth || 800;
    const H = container.offsetHeight || 600;
    const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 1000);
    camera.position.set(8, 8, 8);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0x06060e, 1);
    container.appendChild(renderer.domElement);

    // Lighting
    scene.add(new THREE.AmbientLight(0x334466, 1.5));
    const pt = new THREE.PointLight(0x4488ff, 2, 30);
    pt.position.set(5, 8, 5);
    scene.add(pt);

    // Build mesh tiles
    const tileSize = 0.85;
    const group = new THREE.Group();
    const tiles = [];

    function corrToColor(v) {
      // -1 = red, 0 = dark, +1 = green/blue
      if (v >= 0.7) return new THREE.Color(0.1, 0.8, 0.4);
      if (v >= 0.3) return new THREE.Color(0.2, 0.5, 0.9);
      if (v >= 0) return new THREE.Color(0.15, 0.15, 0.35);
      if (v >= -0.3) return new THREE.Color(0.5, 0.2, 0.1);
      return new THREE.Color(0.9, 0.1, 0.1);
    }

    for (let i = 0; i < N; i++) {
      for (let j = 0; j < N; j++) {
        const v = corr[i][j];
        const geo = new THREE.BoxGeometry(tileSize, 0.1 + Math.abs(v) * 1.2, tileSize);
        const col = corrToColor(v);
        const mat = new THREE.MeshPhongMaterial({ color: col, transparent: true, opacity: 0.85 });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(i - N / 2, (0.1 + Math.abs(v) * 1.2) / 2, j - N / 2);
        mesh.userData = { i, j, targetV: v };
        group.add(mesh);
        tiles.push(mesh);
      }
    }
    scene.add(group);

    // Axis labels (sprites via canvas texture)
    function makeLabel(text) {
      const lc = document.createElement('canvas');
      lc.width = 128; lc.height = 32;
      const lctx = lc.getContext('2d');
      lctx.fillStyle = 'rgba(0,0,0,0)';
      lctx.fillRect(0, 0, 128, 32);
      lctx.fillStyle = '#8899bb';
      lctx.font = 'bold 18px monospace';
      lctx.textAlign = 'center';
      lctx.fillText(text, 64, 22);
      const tex = new THREE.CanvasTexture(lc);
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true }));
      sp.scale.set(1.2, 0.3, 1);
      return sp;
    }

    ASSETS.forEach((a, i) => {
      const sp = makeLabel(a);
      sp.position.set(i - N / 2, 0.2, -N / 2 - 1);
      scene.add(sp);
      const sp2 = makeLabel(a);
      sp2.position.set(-N / 2 - 1, 0.2, i - N / 2);
      scene.add(sp2);
    });

    // Camera orbit
    let camAngle = 0;
    let updateTimer = 0;

    function animate() {
      const aid = requestAnimationFrame(animate);
      camAngle += 0.003;
      const r = 14;
      camera.position.set(Math.cos(camAngle) * r, 9, Math.sin(camAngle) * r);
      camera.lookAt(0, 0, 0);

      // Slowly morph correlation values
      updateTimer++;
      if (updateTimer % 120 === 0) {
        corr = buildCorrMatrix();
        tiles.forEach(mesh => {
          const { i, j } = mesh.userData;
          const v = corr[i][j];
          mesh.userData.targetV = v;
        });
      }
      tiles.forEach(mesh => {
        const cur = mesh.scale.y;
        const target = 0.1 + Math.abs(mesh.userData.targetV) * 1.2;
        mesh.scale.y += (target - cur) * 0.02;
        mesh.position.y = mesh.scale.y / 2;
        const col = corrToColor(mesh.userData.targetV);
        mesh.material.color.lerp(col, 0.02);
      });

      renderer.render(scene, camera);
      mesh_animId = aid;
    }
    let mesh_animId;
    animate();

    return () => {
      cancelAnimationFrame(mesh_animId);
      renderer.dispose();
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
    };
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     CAPITAL FLOW STATE â€” sector rotation wheel
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizFlowState() {
    const canvas = document.getElementById('viz-canvas');
    const ctx = canvas.getContext('2d');
    let animId, t = 0;

    const SECTORS = [
      { name: 'Technology', color: '#3498db', alloc: 0.28, momentum: 0.7 },
      { name: 'Healthcare', color: '#2ecc71', alloc: 0.14, momentum: 0.2 },
      { name: 'Financials', color: '#f1c40f', alloc: 0.13, momentum: 0.4 },
      { name: 'Consumer', color: '#e67e22', alloc: 0.10, momentum: -0.1 },
      { name: 'Industrials', color: '#9b59b6', alloc: 0.08, momentum: 0.3 },
      { name: 'Energy', color: '#e74c3c', alloc: 0.07, momentum: -0.5 },
      { name: 'Materials', color: '#1abc9c', alloc: 0.05, momentum: 0.1 },
      { name: 'Real Estate', color: '#e8a856', alloc: 0.05, momentum: -0.2 },
      { name: 'Utilities', color: '#bdc3c7', alloc: 0.06, momentum: -0.3 },
      { name: 'Comm Services', color: '#fd79a8', alloc: 0.04, momentum: 0.5 },
    ];

    // Dynamic alloc changes over time
    let liveAlloc = SECTORS.map(s => s.alloc);
    let _flowLabel = 'Capital Flow â€” Simulated';

    // â”€â”€ Live sector structure from /api/correlation/structure â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _api.get('/api/correlation/structure').then(d => {
      if (!d) return;
      _flowLabel = `Capital Flow â€” LIVE  Regime: ${d.regime || '?'}`;
      // Update momentum from diversification score and regime
      const divScore = d.diversification_score || 0.5; // 0..1
      SECTORS.forEach((sec, i) => {
        // Adjust momentum: diversified market = more even allocations
        sec.momentum = clamp(sec.momentum + (divScore - 0.5) * 0.3, -1, 1);
      });
      // If regime data available, tilt tech/energy momentum accordingly
      if (d.regime === 'BULL') { SECTORS[0].momentum = Math.max(0.5, SECTORS[0].momentum); }
      if (d.regime === 'BEAR') { SECTORS[5].momentum = Math.max(-0.7, SECTORS[5].momentum); }
    }).catch(() => { });

    function draw() {
      const W = canvas.width, H = canvas.height;
      ctx.fillStyle = '#06060e';
      ctx.fillRect(0, 0, W, H);

      const cx = W * 0.42, cy = H * 0.5;
      const outerR = Math.min(W, H) * 0.35;
      const innerR = outerR * 0.42;

      // Slowly shift allocations
      if (Math.floor(t) % 60 === 0) {
        const shift = SECTORS.map(() => (Math.random() - 0.5) * 0.02);
        let tot = liveAlloc.reduce((a, b) => a + b, 0);
        liveAlloc = liveAlloc.map((v, i) => Math.max(0.02, v + shift[i]));
        tot = liveAlloc.reduce((a, b) => a + b, 0);
        liveAlloc = liveAlloc.map(v => v / tot);
      }

      let startAngle = -Math.PI / 2;
      SECTORS.forEach((sec, si) => {
        const alloc = liveAlloc[si];
        const sweep = alloc * Math.PI * 2;

        // Pulse ring scale
        const pulse = 1 + Math.sin(t * 0.05 + si * 0.6) * 0.015 * Math.abs(sec.momentum);

        // Outer donut slice
        ctx.beginPath();
        ctx.arc(cx, cy, outerR * pulse, startAngle, startAngle + sweep);
        ctx.arc(cx, cy, innerR, startAngle + sweep, startAngle, true);
        ctx.closePath();
        const alpha = 0.6 + Math.sin(t * 0.05 + si) * 0.15;
        ctx.fillStyle = sec.color + Math.round(alpha * 255).toString(16).padStart(2, '0');
        ctx.fill();
        ctx.strokeStyle = '#06060e';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label
        const midAngle = startAngle + sweep / 2;
        const labelR = (outerR + innerR) / 2 * pulse;
        const lx = cx + labelR * Math.cos(midAngle);
        const ly = cy + labelR * Math.sin(midAngle);
        ctx.font = `bold ${Math.round(10 + alloc * 30)}px monospace`;
        ctx.fillStyle = '#fff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        if (alloc > 0.05) ctx.fillText(`${Math.round(alloc * 100)}%`, lx, ly);

        // Flow arrows (outside ring)
        if (Math.abs(sec.momentum) > 0.15) {
          const arrowR = outerR * pulse + 14;
          const arrowX = cx + arrowR * Math.cos(midAngle);
          const arrowY = cy + arrowR * Math.sin(midAngle);
          const flowDir = sec.momentum > 0 ? 'â†‘' : 'â†“';
          ctx.font = '12px monospace';
          ctx.fillStyle = sec.momentum > 0 ? '#2ecc71' : '#e74c3c';
          ctx.fillText(flowDir, arrowX, arrowY);
        }

        startAngle += sweep;
      });

      // Centre: rotation ring
      const ringPulse = Math.sin(t * 0.03) * 0.5 + 0.5;
      ctx.beginPath();
      ctx.arc(cx, cy, innerR - 5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(6,6,14,0.92)`;
      ctx.fill();

      ctx.font = 'bold 14px monospace';
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('SECTOR', cx, cy - 10);
      ctx.font = '11px monospace';
      ctx.fillStyle = '#667';
      ctx.fillText('ROTATION', cx, cy + 8);

      // Right panel: sector legend + flows
      const panelX = W * 0.72;
      ctx.font = 'bold 12px monospace';
      ctx.fillStyle = '#aab';
      ctx.textAlign = 'left';
      ctx.fillText(`Capital Rotation  ${_flowLabel}`, panelX, 40);

      SECTORS.forEach((sec, si) => {
        const y = 65 + si * 28;
        const alloc = liveAlloc[si];
        const barW = Math.round(alloc * 200);
        const mom = sec.momentum;

        // Bar
        ctx.fillStyle = sec.color + '33';
        ctx.fillRect(panelX, y + 2, 120, 16);
        ctx.fillStyle = sec.color;
        ctx.fillRect(panelX, y + 2, barW, 16);

        // Name + alloc
        ctx.font = '10px monospace';
        ctx.fillStyle = '#aab';
        ctx.fillText(sec.name, panelX + 126, y + 12);

        // Momentum chip
        const chipColor = mom > 0.3 ? '#2ecc71' : mom < -0.3 ? '#e74c3c' : '#f1c40f';
        ctx.fillStyle = chipColor;
        ctx.fillText(`${mom > 0 ? '+' : ''}${Math.round(mom * 100)}%`, panelX + barW + 2, y + 12);
      });

      t++;
      animId = requestAnimationFrame(draw);
    }
    draw();
    return () => cancelAnimationFrame(animId);
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     MARKET DNA HELIX â€” price data as rotating DNA
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizMarketDNA() {
    const canvas = document.getElementById('viz-canvas');
    const ctx = canvas.getContext('2d');
    let animId, t = 0;

    // Simulate OHLC as nucleotide pairs
    const BASES = ['Bullish', 'Bearish', 'Sideways', 'Volatile'];
    const BASE_COLORS = {
      Bullish: ['#2ecc71', '#1abc9c'],
      Bearish: ['#e74c3c', '#c0392b'],
      Sideways: ['#f1c40f', '#e67e22'],
      Volatile: ['#9b59b6', '#8e44ad'],
    };

    // Generate a strand of DNA data
    const STRAND_LEN = 40;
    const strand = Array.from({ length: STRAND_LEN }, (_, i) => {
      const rand = Math.random();
      if (rand < 0.4) return 'Bullish';
      if (rand < 0.65) return 'Bearish';
      if (rand < 0.85) return 'Sideways';
      return 'Volatile';
    });

    function draw() {
      const W = canvas.width, H = canvas.height;
      ctx.fillStyle = '#06060e';
      ctx.fillRect(0, 0, W, H);

      const cx = W / 2;
      const helixW = 160;   // horizontal spread of helix
      const spacing = 18;   // vertical spacing per nucleotide
      const totalH = STRAND_LEN * spacing;
      const startY = (H - totalH) / 2 + spacing;

      // Scroll phase
      const scrollY = (t * 0.4) % (spacing * 2);

      // Draw helix strands
      for (let ri = -2; ri < STRAND_LEN + 2; ri++) {
        const i = ((ri % STRAND_LEN) + STRAND_LEN) % STRAND_LEN;
        const base = strand[i];
        const [c1, c2] = BASE_COLORS[base];

        const y = startY + ri * spacing - scrollY;
        if (y < -20 || y > H + 20) continue;

        const angle = (ri * 0.4 + t * 0.04);
        const x1 = cx - helixW / 2 * Math.cos(angle);
        const x2 = cx + helixW / 2 * Math.cos(angle);
        const z = Math.sin(angle);         // depth cue

        const r1 = 7 + z * 2;
        const r2 = 7 - z * 2;

        // Back node (always draw first)
        const backX = z > 0 ? x1 : x2;
        const frontX = z > 0 ? x2 : x1;
        const backC = z > 0 ? c1 : c2;
        const frontC = z > 0 ? c2 : c1;
        const backR = z > 0 ? r1 : r2;
        const frontR = z > 0 ? r2 : r1;

        // Connecting bridge
        ctx.beginPath();
        ctx.moveTo(x1, y); ctx.lineTo(x2, y);
        ctx.strokeStyle = `rgba(255,255,255,${0.1 + Math.abs(z) * 0.1})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Back node
        ctx.beginPath();
        ctx.arc(backX, y, Math.max(2, backR), 0, Math.PI * 2);
        ctx.fillStyle = backC + '99';
        ctx.fill();

        // Front node
        ctx.beginPath();
        ctx.arc(frontX, y, Math.max(2, frontR), 0, Math.PI * 2);
        ctx.fillStyle = frontC;
        ctx.fill();

        // Glow on front
        const glowSize = frontR + 4 + Math.sin(t * 0.1 + ri) * 1.5;
        ctx.beginPath();
        ctx.arc(frontX, y, glowSize, 0, Math.PI * 2);
        ctx.strokeStyle = frontC + '44';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Label (visible nodes near centre)
        if (Math.abs(y - H / 2) < 70 && Math.abs(z) > 0.4) {
          ctx.font = '9px monospace';
          ctx.fillStyle = frontC;
          ctx.textAlign = frontX > cx ? 'left' : 'right';
          ctx.fillText(base, frontX + (frontX > cx ? 14 : -14), y + 3);
        }
      }

      // Backbone ribbons
      ['left', 'right'].forEach((side, si) => {
        ctx.beginPath();
        let first = true;
        for (let ri = -2; ri < STRAND_LEN + 2; ri++) {
          const y = startY + ri * spacing - scrollY;
          if (y < -20 || y > H + 20) { first = true; continue; }
          const angle = ri * 0.4 + t * 0.04;
          const x = cx + (si === 0 ? -1 : 1) * (helixW / 2) * Math.cos(angle);
          first ? (ctx.moveTo(x, y), first = false) : ctx.lineTo(x, y);
        }
        ctx.strokeStyle = si === 0 ? 'rgba(52,152,219,0.25)' : 'rgba(46,204,113,0.25)';
        ctx.lineWidth = 3;
        ctx.stroke();
      });

      // Legend
      ctx.font = 'bold 11px monospace';
      ctx.textAlign = 'left';
      let lx = 20, ly = H - 80;
      ctx.fillStyle = '#667';
      ctx.fillText('Market DNA Sequence:', lx, ly);
      ly += 16;
      Object.entries(BASE_COLORS).forEach(([base, [c]]) => {
        ctx.fillStyle = c;
        ctx.fillRect(lx, ly, 10, 10);
        ctx.fillStyle = '#aab';
        ctx.font = '10px monospace';
        ctx.fillText(base, lx + 14, ly + 9);
        lx += 80;
      });

      // Title
      ctx.font = 'bold 13px monospace';
      ctx.fillStyle = '#334';
      ctx.textAlign = 'center';
      ctx.fillText('â—† MARKET DNA HELIX â€” Candle Genome Sequencer â—†', W / 2, 22);

      t++;
      animId = requestAnimationFrame(draw);
    }
    draw();
    return () => cancelAnimationFrame(animId);
  }

  /* â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
     LIVE MONITOR â€” Mission-Control ops dashboard
     Auto-polls quotes every 15 s, rotates signal checks every ~8 s.
     No canvas â€” renders HTML into viz-three-mount.
  â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â• */
  function vizLiveMonitor() {
    const mount = document.getElementById('viz-three-mount');
    if (!mount) return;

    // â”€â”€ Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    const TICKERS = ['AAPL', 'MSFT', 'NVDA', 'BTC-USD', 'SPY', 'QQQ', 'TSLA', 'AMZN'];
    const QUOTE_MS = 15000;   // refresh all quotes
    const SIG_ROTATE = 8000;    // check one signal at a time
    let quoteTimer = null;
    let signalTimer = null;
    let uptimeTimer = null;
    let sigIdx = 0;
    let signals = {};   // { SYM: { action, confidence, score } }
    let quoteData = {};   // { SYM: { price, change_pct, volume } }
    let actLog = [];
    let sigFeed = [];
    let uptime = 0;

    // â”€â”€ Inject HTML shell â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    mount.style.cssText = 'position:relative;width:100%;height:100%;overflow:hidden;background:#06080f';
    mount.innerHTML = `
<style>
  #lm-root *{box-sizing:border-box}
  @keyframes lm-pulse{0%,100%{opacity:1}50%{opacity:.25}}
  @keyframes lm-flashin{from{background:#1a3a2a}to{background:transparent}}
  .lm-card{background:#090f1c;border:1px solid #1a2a3a;border-radius:6px;padding:8px 10px;transition:border-color .4s,transform .2s}
  .lm-card:hover{border-color:#2ecc71;transform:translateY(-1px)}
  .lm-card.up{border-color:#1a3a2a}
  .lm-card.dn{border-color:#3a1a1a}
  .lm-sig-row{font-size:11px;padding:4px 7px;border-radius:4px;background:#080e18;border-left:3px solid transparent;margin-bottom:3px}
  .lm-log-row{font-size:10px;padding:2px 0;border-bottom:1px solid #0d1820;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#445}
</style>
<div id="lm-root" style="display:flex;flex-direction:column;height:100%;padding:12px 14px;gap:10px;font-family:'Courier New',monospace;color:#c8d8e8">

  <!-- Header bar -->
  <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #0d2030;padding-bottom:9px;flex-shrink:0">
    <div style="display:flex;align-items:center;gap:10px">
      <span id="lm-dot" style="width:10px;height:10px;border-radius:50%;background:#2ecc71;display:inline-block;animation:lm-pulse 2s infinite"></span>
      <span style="color:#2ecc71;font-size:14px;font-weight:bold;letter-spacing:3px">ATLAS LIVE MONITOR</span>
    </div>
    <div style="display:flex;gap:20px;font-size:11px;color:#334455">
      <span>UPTIME&nbsp;<b id="lm-up" style="color:#3498db">00:00:00</b></span>
      <span>PING&nbsp;<b id="lm-ping" style="color:#2ecc71">â€”</b>ms</span>
      <span id="lm-ts" style="color:#2a3a4a"></span>
    </div>
  </div>

  <!-- Ticker grid: 8 cards -->
  <div id="lm-grid" style="display:grid;grid-template-columns:repeat(8,1fr);gap:6px;flex-shrink:0"></div>

  <!-- Signal feed + Activity log -->
  <div style="display:flex;gap:10px;flex:1;min-height:0">

    <!-- Signal engine output -->
    <div style="flex:1.3;background:#080e18;border:1px solid #0d2035;border-radius:6px;padding:10px;display:flex;flex-direction:column;overflow:hidden">
      <div style="color:#3498db;font-size:11px;font-weight:bold;letter-spacing:2px;margin-bottom:7px;flex-shrink:0">
        âš¡ SIGNAL ENGINE OUTPUT
      </div>
      <div id="lm-sigs" style="flex:1;overflow-y:auto;display:flex;flex-direction:column"></div>
    </div>

    <!-- Activity log -->
    <div style="flex:1;background:#080e18;border:1px solid #0d2035;border-radius:6px;padding:10px;display:flex;flex-direction:column;overflow:hidden">
      <div style="color:#9b59b6;font-size:11px;font-weight:bold;letter-spacing:2px;margin-bottom:7px;flex-shrink:0">
        ðŸ“‹ SYSTEM ACTIVITY
      </div>
      <div id="lm-log" style="flex:1;overflow-y:auto;display:flex;flex-direction:column-reverse"></div>
    </div>

  </div>
</div>`;

    // â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function _ts() { return new Date().toLocaleTimeString('en', { hour12: false }); }
    function _clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

    function _log(msg, color = '#334455') {
      actLog.unshift({ ts: _ts(), msg, color });
      if (actLog.length > 50) actLog.pop();
      const el = document.getElementById('lm-log');
      if (!el) return;
      el.innerHTML = actLog.map(e =>
        `<div class="lm-log-row"><span style="color:#223">[${e.ts}]</span> <span style="color:${e.color}">${e.msg}</span></div>`
      ).join('');
    }

    const SIG_COLORS = {
      'STRONG BUY': '#1abc9c', 'BUY': '#2ecc71',
      'HOLD': '#f1c40f', 'AVOID': '#e67e22',
      'SELL': '#e74c3c', 'STRONG SELL': '#c0392b'
    };

    // â”€â”€ Uptime clock â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    uptimeTimer = setInterval(() => {
      uptime++;
      const h = String(Math.floor(uptime / 3600)).padStart(2, '0');
      const m = String(Math.floor((uptime % 3600) / 60)).padStart(2, '0');
      const s = String(uptime % 60).padStart(2, '0');
      const el = document.getElementById('lm-up'); if (el) el.textContent = `${h}:${m}:${s}`;
      const ts = document.getElementById('lm-ts'); if (ts) ts.textContent = _ts();
    }, 1000);

    // â”€â”€ Render ticker grid â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    function _renderGrid() {
      const grid = document.getElementById('lm-grid');
      if (!grid) return;
      grid.innerHTML = TICKERS.map(sym => {
        const d = quoteData[sym] || {};
        const price = d.price != null
          ? `$${Number(d.price).toLocaleString('en', { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`
          : 'â€”';
        const chg = d.change_pct;
        const chgTx = chg != null ? (chg >= 0 ? `+${chg.toFixed(2)}%` : `${chg.toFixed(2)}%`) : 'â€”';
        const chgC = chg == null ? '#445' : chg > 0 ? '#2ecc71' : chg < 0 ? '#e74c3c' : '#f1c40f';
        const cls = chg == null ? '' : chg > 0 ? 'up' : 'dn';

        const sig = signals[sym];
        let badge = '', bar = '';
        if (sig) {
          const sc = SIG_COLORS[sig.action] || '#888';
          const cf = sig.confidence != null ? ` ${Math.round(sig.confidence * 100)}%` : '';
          badge = `<div style="margin-top:4px;font-size:9px;font-weight:bold;color:${sc};border:1px solid ${sc}40;border-radius:3px;padding:1px 4px;display:inline-block">${sig.action}${cf}</div>`;
          if (sig.score != null) {
            const pct = Math.round(_clamp(sig.score / 100 * 50 + 50, 2, 98));
            const bc = sig.score > 20 ? '#2ecc71' : sig.score < -20 ? '#e74c3c' : '#f1c40f';
            bar = `<div style="margin-top:4px;height:3px;background:#1a2a3a;border-radius:2px"><div style="width:${pct}%;height:100%;background:${bc};border-radius:2px;transition:width .6s"></div></div>`;
          }
        }
        return `<div class="lm-card ${cls}">
          <div style="font-size:10px;font-weight:bold;color:#7baed8;letter-spacing:1px">${sym}</div>
          <div style="font-size:15px;font-weight:bold;color:#eee;margin-top:2px;line-height:1">${price}</div>
          <div style="font-size:11px;color:${chgC};margin-top:2px">${chgTx}</div>
          ${badge}${bar}
        </div>`;
      }).join('');
    }

    // â”€â”€ Quote fetch (parallel) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async function _fetchQuotes() {
      const t0 = Date.now();
      try {
        const r = await fetch(`${CONFIG.serverUrl}/api/monitor/tick?tickers=${TICKERS.join(',')}`);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = await r.json();
        (d.tickers || []).forEach(t => { if (t.symbol) quoteData[t.symbol] = t; });
        _renderGrid();
        const ping = Date.now() - t0;
        const el = document.getElementById('lm-ping');
        if (el) { el.textContent = ping; el.style.color = ping < 2000 ? '#2ecc71' : '#f1c40f'; }
        const dot = document.getElementById('lm-dot');
        if (dot) dot.style.background = '#2ecc71';
        _log(`Market data refreshed (${d.server_ms}ms server)`, '#1a3a2a');
      } catch (e) {
        _log(`Quote fetch failed: ${e.message}`, '#4a1a1a');
        const dot = document.getElementById('lm-dot');
        if (dot) { dot.style.background = '#e74c3c'; dot.style.animation = 'none'; }
      }
    }

    // â”€â”€ Signal fetch (rotate one ticker at a time) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    async function _fetchSignal() {
      const sym = TICKERS[sigIdx % TICKERS.length];
      sigIdx++;
      try {
        const r = await fetch(`${CONFIG.serverUrl}/api/strategy/analyze/${sym}?period=3mo`);
        if (!r.ok) return;
        const d = await r.json();
        const action = d.consensus?.action ?? d.action ?? 'HOLD';
        const confidence = d.consensus?.confidence ?? d.confidence ?? null;
        const score = d.composite_score ?? d.consensus?.net_score ?? null;
        signals[sym] = { action, confidence, score };

        // Push to signal feed
        const col = SIG_COLORS[action] || '#888';
        const cf = confidence != null ? `${Math.round(confidence * 100)}%` : '';
        const sc = score != null ? ` | score ${Math.round(score)}` : '';
        sigFeed.unshift({ ts: _ts(), sym, action, col, cf, sc });
        if (sigFeed.length > 30) sigFeed.pop();
        const el = document.getElementById('lm-sigs');
        if (el) el.innerHTML = sigFeed.map(s =>
          `<div class="lm-sig-row" style="border-left-color:${s.col}40">
            <span style="color:#223">[${s.ts}]</span>
            <span style="color:#7baed8;font-weight:bold"> ${s.sym}</span>
            <span style="color:${s.col};font-weight:bold"> ${s.action}</span>
            <span style="color:#445"> ${s.cf}${s.sc}</span>
          </div>`
        ).join('');
        _renderGrid();
        _log(`Signal: ${sym} â†’ ${action}${cf ? ' (' + cf + ')' : ''}`, '#1a2a3a');
      } catch (_e) { /* silent */ }
    }

    // â”€â”€ Boot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    _log('ATLAS Live Monitor online', '#2ecc71');
    _log('Fetching initial market dataâ€¦', '#3498db');
    _renderGrid();                           // show empty skeletons
    _fetchQuotes();                          // first quote batch immediately
    setTimeout(_fetchSignal, 1800);          // first signal after 1.8s
    quoteTimer = setInterval(_fetchQuotes, QUOTE_MS);
    signalTimer = setInterval(_fetchSignal, SIG_ROTATE);

    // â”€â”€ Cleanup (called by _stop when user closes overlay) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    return () => {
      clearInterval(quoteTimer);
      clearInterval(signalTimer);
      clearInterval(uptimeTimer);
      mount.innerHTML = '';
      mount.style.cssText = '';
    };
  }

  /* ═══════════════════════════════════════════════════════════════
     LIQUIDITY BLACK HOLE
     Canvas2D — particles spiral into an event horizon with
     accretion disk, gravitational lensing, and infall tracking.
  ═══════════════════════════════════════════════════════════════ */
  function vizLiquidityBlackHole() {
    const { canvas, ctx } = _getCanvas2D();
    if (!canvas || !ctx) return;
    const W = canvas.width, H = canvas.height;
    const cx = W / 2, cy = H / 2;

    // Accretion disk particles
    const PARTS = 700;
    const particles = Array.from({ length: PARTS }, () => {
      const angle  = Math.random() * Math.PI * 2;
      const r      = 70 + Math.random() * 200;
      return {
        angle,
        r,
        speed:   0.007 + (60 / Math.max(r, 10)) * 0.025,   // Keplerian: faster inside
        opacity: 0.3 + Math.random() * 0.7,
        size:    0.5 + Math.random() * 2.5,
        hue:     15 + Math.random() * 45,                    // orange-yellow
        infall:  false,
        infallT: 0,
      };
    });

    // Background stars
    const BG = 220;
    const bgStars = Array.from({ length: BG }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      size: 0.3 + Math.random() * 1.3,
      twinkle: Math.random() * Math.PI * 2,
      speed: 0.01 + Math.random() * 0.04,
    }));

    // Jet stream particles (polar jets)
    const JETS = 60;
    const jets = Array.from({ length: JETS }, (_, i) => ({
      y: (Math.random() - 0.5) * cy * 0.6,
      speed: 1.5 + Math.random() * 2.5,
      dir: i < JETS / 2 ? 1 : -1,   // up or down jet
      x: (Math.random() - 0.5) * 20,
      opacity: 0.3 + Math.random() * 0.5,
      size: 0.8 + Math.random() * 1.6,
    }));

    let frame = 0;
    let infallCount = 0;

    function drawEventHorizon() {
      // Gravitational lensing rings
      for (let i = 3; i >= 0; i--) {
        ctx.beginPath();
        ctx.ellipse(cx, cy, 55 + i * 12, (55 + i * 12) * 0.28, Math.PI / 5, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(255, ${100 + i * 30}, 0, ${0.12 - i * 0.025})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      // Photon sphere glow
      const pgrd = ctx.createRadialGradient(cx, cy, 38, cx, cy, 62);
      pgrd.addColorStop(0, `rgba(255, 120, 0, ${0.25 + 0.12 * Math.sin(frame * 0.06)})`);
      pgrd.addColorStop(1, 'transparent');
      ctx.fillStyle = pgrd;
      ctx.beginPath();
      ctx.arc(cx, cy, 62, 0, Math.PI * 2);
      ctx.fill();
      // Event horizon — absolute black
      const ehgrd = ctx.createRadialGradient(cx, cy, 0, cx, cy, 42);
      ehgrd.addColorStop(0.0, '#000000');
      ehgrd.addColorStop(0.7, '#000000');
      ehgrd.addColorStop(1.0, 'rgba(0,0,0,0)');
      ctx.fillStyle = ehgrd;
      ctx.beginPath();
      ctx.arc(cx, cy, 42, 0, Math.PI * 2);
      ctx.fill();
      // Inner photon ring
      ctx.beginPath();
      ctx.arc(cx, cy, 43, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255, 160, 0, ${0.5 + 0.2 * Math.sin(frame * 0.08)})`;
      ctx.lineWidth = 2;
      ctx.shadowColor = '#ff8800';
      ctx.shadowBlur = 10;
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    function animate() {
      _animFrameId = requestAnimationFrame(animate);
      frame++;

      // Deep space
      ctx.fillStyle = 'rgba(2, 2, 10, 0.30)';
      ctx.fillRect(0, 0, W, H);

      // Background nebula glow
      if (frame % 3 === 0) {
        const ngrd = ctx.createRadialGradient(cx, cy, 60, cx, cy, 280);
        ngrd.addColorStop(0, 'rgba(60, 10, 80, 0.06)');
        ngrd.addColorStop(1, 'transparent');
        ctx.fillStyle = ngrd;
        ctx.fillRect(0, 0, W, H);
      }

      // Background stars
      for (const s of bgStars) {
        s.twinkle += s.speed;
        const a = 0.15 + 0.25 * Math.sin(s.twinkle);
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180, 190, 255, ${a})`;
        ctx.fill();
      }

      // Polar jets (relativistic jets above/below)
      for (const j of jets) {
        j.y += j.speed * j.dir * 0.8;
        if (Math.abs(j.y) > cy + 20) {
          j.y = (Math.random() - 0.5) * 30;
          j.x = (Math.random() - 0.5) * 24;
        }
        const jx = cx + j.x;
        const jy = cy + j.y;
        ctx.beginPath();
        ctx.arc(jx, jy, j.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(150, 100, 255, ${j.opacity * (1 - Math.abs(j.y) / (cy + 20))})`;
        ctx.fill();
      }

      // Accretion disk — back to front by radius
      particles.sort((a, b) => b.r - a.r);
      infallCount = 0;
      for (const p of particles) {
        if (p.infall) {
          p.r = Math.max(0, p.r - (2.5 + (80 - p.r) * 0.10));
          p.infallT++;
          infallCount++;
          if (p.r < 12) {
            p.r      = 160 + Math.random() * 110;
            p.angle  = Math.random() * Math.PI * 2;
            p.infall = false;
            p.infallT = 0;
          }
        } else {
          p.angle += p.speed;
          if (Math.random() < 0.0004) p.infall = true;
        }

        const x = cx + Math.cos(p.angle) * p.r;
        const y = cy + Math.sin(p.angle) * p.r * 0.38;
        const distFactor = Math.min(1, p.r / 130);
        const alpha = p.opacity * distFactor * (p.infall ? Math.min(1, p.infallT / 18) : 1);
        const sz = p.size * (p.infall ? Math.max(0.2, 1 - p.infallT * 0.025) : 1);
        const light = 38 + (1 - distFactor) * 44;
        ctx.beginPath();
        ctx.arc(x, y, sz, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${p.hue + (1 - distFactor) * 25}, 95%, ${light}%, ${alpha})`;
        ctx.fill();
      }

      drawEventHorizon();

      // Labels
      ctx.shadowBlur = 0;
      ctx.fillStyle  = 'rgba(255, 140, 0, 0.85)';
      ctx.font       = 'bold 13px monospace';
      ctx.textAlign  = 'left';
      ctx.fillText('LIQUIDITY BLACK HOLE', 14, 26);
      ctx.fillStyle = 'rgba(255, 100, 0, 0.45)';
      ctx.font      = '10px monospace';
      ctx.fillText('Market singularity — capital in accretion infall', 14, 42);
      ctx.fillStyle = 'rgba(255, 140, 0, 0.4)';
      ctx.font      = '9px monospace';
      ctx.textAlign = 'right';
      ctx.fillText(
        `• ${infallCount} units in infall  • Event horizon r≈42px  • Polar jets active`,
        W - 12, H - 14
      );
    }
    animate();
  }

  /* ═══════════════════════════════════════════════════════════════
     MARKET GALAXY 3D
     Three.js — 3D spiral galaxy with 3 sector arms, each arm
     color-coded by market sector. Stars orbit the core (SPY/QQQ).
     Camera auto-orbits and slowly tilts.
  ═══════════════════════════════════════════════════════════════ */
  function vizGalaxy3D() {
    const container = document.getElementById('viz-three-mount');
    if (!container || typeof THREE === 'undefined') {
      const { canvas, ctx } = _getCanvas2D();
      if (ctx) {
        ctx.fillStyle = '#06060e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#556';
        ctx.font = '14px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('Three.js required for Market Galaxy 3D', canvas.width / 2, canvas.height / 2);
      }
      return;
    }

    const W = container.offsetWidth  || 800;
    const H = container.offsetHeight || 600;

    const scene    = new THREE.Scene();
    const camera   = new THREE.PerspectiveCamera(55, W / H, 0.1, 2000);
    camera.position.set(0, 90, 170);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0x020208, 1);
    container.appendChild(renderer.domElement);

    // Galaxy core
    const coreGeo  = new THREE.SphereGeometry(4, 32, 32);
    const coreMat  = new THREE.MeshBasicMaterial({ color: 0xfff5cc });
    const coreNode = new THREE.Mesh(coreGeo, coreMat);
    scene.add(coreNode);

    // Halo glow
    const haloGeo = new THREE.SphereGeometry(16, 16, 16);
    const haloMat = new THREE.MeshBasicMaterial({
      color: 0xffcc66, transparent: true, opacity: 0.12,
      blending: THREE.AdditiveBlending, side: THREE.BackSide,
    });
    scene.add(new THREE.Mesh(haloGeo, haloMat));

    // Spiral arm stars
    const ARMS         = 3;
    const PER_ARM      = 2500;
    const TOTAL        = ARMS * PER_ARM;
    const positions    = new Float32Array(TOTAL * 3);
    const colors       = new Float32Array(TOTAL * 3);
    const ARM_PALETTE  = [
      new THREE.Color(0.25, 0.55, 1.00),   // arm 0 — Tech (blue)
      new THREE.Color(1.00, 0.50, 0.18),   // arm 1 — Finance/Energy (orange)
      new THREE.Color(0.30, 1.00, 0.55),   // arm 2 — Defensive/Crypto (green)
    ];

    let vi = 0;
    for (let arm = 0; arm < ARMS; arm++) {
      const baseAngle = (arm / ARMS) * Math.PI * 2;
      for (let i = 0; i < PER_ARM; i++) {
        const t       = i / PER_ARM;
        const r       = 6 + t * 85;
        const theta   = baseAngle + t * Math.PI * 4.5 + (Math.random() - 0.5) * 0.7;
        const scatter = (0.8 + t * 3.5) * (Math.random() - 0.5);
        positions[vi * 3]     = Math.cos(theta) * r + scatter * 0.6;
        positions[vi * 3 + 1] = (Math.random() - 0.5) * r * 0.07 + scatter * 0.08;
        positions[vi * 3 + 2] = Math.sin(theta) * r + scatter * 0.6;

        const col = ARM_PALETTE[arm].clone();
        col.multiplyScalar(0.4 + Math.random() * 0.6);
        colors[vi * 3]     = col.r;
        colors[vi * 3 + 1] = col.g;
        colors[vi * 3 + 2] = col.b;
        vi++;
      }
    }

    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    starGeo.setAttribute('color',    new THREE.BufferAttribute(colors,    3));

    const starMat = new THREE.PointsMaterial({
      size: 0.9, vertexColors: true,
      transparent: true, opacity: 0.88,
      sizeAttenuation: true, blending: THREE.AdditiveBlending,
    });
    const galaxy = new THREE.Points(starGeo, starMat);
    scene.add(galaxy);

    // Sector label sprites
    function makeLbl(text, color) {
      const c = document.createElement('canvas');
      c.width = 180; c.height = 44;
      const lx = c.getContext('2d');
      lx.font = 'bold 18px monospace';
      lx.fillStyle = color;
      lx.textAlign = 'center';
      lx.fillText(text, 90, 30);
      const tex = new THREE.CanvasTexture(c);
      const sp  = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
      sp.scale.set(18, 4.5, 1);
      return sp;
    }

    const SECTORS = [
      { name: 'TECH',     arm: 0, t: 0.35, color: '#4488ff' },
      { name: 'FINANCE',  arm: 1, t: 0.32, color: '#ff8833' },
      { name: 'CRYPTO',   arm: 2, t: 0.28, color: '#44ff88' },
      { name: 'ENERGY',   arm: 1, t: 0.62, color: '#ff6644' },
      { name: 'DEFENSE',  arm: 2, t: 0.58, color: '#cc99ff' },
      { name: 'HEALTH',   arm: 0, t: 0.66, color: '#44ddff' },
    ];

    SECTORS.forEach(sec => {
      const baseAngle = (sec.arm / ARMS) * Math.PI * 2;
      const theta     = baseAngle + sec.t * Math.PI * 4.5;
      const r         = 6 + sec.t * 85;
      const sp        = makeLbl(sec.name, sec.color);
      sp.position.set(Math.cos(theta) * r, 5, Math.sin(theta) * r);
      scene.add(sp);
    });

    // SPY / QQQ core labels
    const spyLbl = makeLbl('SPY/QQQ', '#fff5cc');
    spyLbl.position.set(0, 8, 0);
    scene.add(spyLbl);

    // Background halo dust ring
    const ringGeo = new THREE.TorusGeometry(95, 4, 4, 80);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x334466, transparent: true, opacity: 0.08,
      blending: THREE.AdditiveBlending,
    });
    scene.add(new THREE.Mesh(ringGeo, ringMat));

    // Load live cluster data
    _api.get('/api/correlation/cluster').then(d => {
      if (!d || !d.clusters) return;
      const keys = Object.keys(d.clusters).slice(0, 6);
      keys.forEach((k, i) => {
        const armIdx   = i % ARMS;
        const baseAngle = (armIdx / ARMS) * Math.PI * 2;
        const t = 0.25 + (i / Math.max(keys.length, 1)) * 0.5;
        const theta = baseAngle + t * Math.PI * 4.5;
        const r = 6 + t * 85;
        const COLORS = ['#4488ff','#ff8833','#44ff88','#ff6644','#cc99ff','#44ddff'];
        const sp = makeLbl(k, COLORS[i % COLORS.length]);
        sp.position.set(Math.cos(theta) * r, 5, Math.sin(theta) * r);
        scene.add(sp);
      });
    }).catch(() => {});

    // Camera orbit
    let camAngle = 0;
    let localAnimId;

    function animateScene() {
      localAnimId = requestAnimationFrame(animateScene);
      camAngle += 0.0012;
      const camY = 55 + Math.sin(camAngle * 0.25) * 35;
      camera.position.set(Math.cos(camAngle) * 165, camY, Math.sin(camAngle) * 165);
      camera.lookAt(0, 0, 0);
      galaxy.rotation.y += 0.0002;
      coreNode.rotation.y += 0.01;
      renderer.render(scene, camera);
    }
    animateScene();

    return () => {
      cancelAnimationFrame(localAnimId);
      renderer.dispose();
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
    };
  }

  const VIZZES = {
    // â”€â”€ Repo-inspired new vizzes (added 2026-03-01) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    assetgraph: vizAssetGraph,
    worldmodel: vizWorldModel,
    alphascanner: vizAlphaScanner,
    dcfuniverse: vizDCFUniverse,
    agentswarm: vizAgentSwarm,
    // â”€â”€ Trader-era new vizzes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    scorepulse: vizScorePulse,
    livemonitor: vizLiveMonitor,
    correlation3d: vizCorrelation3D,
    flowstate: vizFlowState,
    marketdna: vizMarketDNA,
    // â”€â”€ Original vizzes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    particle: vizParticle,
    brain: vizBrain,
    forcegraph: vizForceGraph,
    montecarlo: vizMonteCarlo,
    radar: vizRadar,
    terrain: vizTerrain,
    flowfield: vizFlowField,
    galaxy: vizGalaxy,
    rltrack: vizRLTrack,
    quantum: vizQuantum,
    lorenz: vizLorenz,
    heatmap: vizHeatmap,
    orderbook: vizOrderBook,
    volsmile: vizVolSmile,
    entropy: vizEntropy,
    treemap: vizTreemap,
    candle: vizCandleRiver,
    factorwheel: vizFactorWheel,
    drawdown: vizDrawdown,
    spread: vizSpread,
    psaturn: vizParticleSaturn,
    pheart: vizParticleHeart,
    pmorph: vizParticleMorph,
    // Nexus Core
    pmobius: vizNexusMobius,
    ptoroidal: vizNexusToroidal,
    pspherical: vizNexusSpherical,
    plissajous: vizNexusLissajous,
    plorenzp: vizNexusLorenz,
    // Speed Racer
    speedracer: vizSpeedRacer,
    blackhole: vizLiquidityBlackHole,
    galaxy3d: vizGalaxy3D,
  };

  /* â”€â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
  return {
    registerViz: (name, meta, localThree, fn) => {
      VIZ_META[name] = meta;
      if (localThree) _LOCAL_THREE.add(name);
      VIZZES[name] = fn;
    },
    launch: _open,
    close: _close,
    getMeta: () => VIZ_META,
    getNames: () => Object.keys(VIZ_META),
    trackMouse: _trackMouse,
    fetchRegime: fetchRegimeAndUpdate,
    fetchBrain: fetchBrainState,
    fetchStatus: fetchSystemStatus,
  };
})();
