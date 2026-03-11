/**
 * Atlas Viz Lab — Market Physics Simulations  UHQ v2.0
 * =====================================================
 *
 *  vizBlackhole  — Liquidity Singularity
 *    · 35 000-particle accretion disk with temperature-correct colours
 *      (inner blue-white 10⁷ K  →  outer orange-red 10⁴ K)
 *    · Dual bloom layers (soft base + wide glow halo)
 *    · Relativistic jets along Z-axis (blue plasma)
 *    · Photon-sphere torus + layered corona
 *    · Cinematic spiral camera approach on load
 *    · ETF → multi-vortex (4 orbiting sub-holes)
 *    · Stock → single unified singularity
 *
 *  vizGalaxy3D   — Market Galaxy
 *    · 40 000-particle spiral galaxy + 3 000-particle dense nucleus
 *    · 8 sector arms (ETF) or 2 arms (Stock), each with a distinct sector colour
 *    · Fixed bug: galaxy tilt now accumulates rather than being reset each frame
 *    · Galactic core: luminous yellow-white nucleus with independent material
 *    · Soft bloom layers on both disk and core
 *    · Slow camera orbit + gentle tilt oscillation
 */

(function () {
  'use strict';

  if (!window.VizLab || !window.VizLab.registerViz) {
    console.error('[viz_mmo] VizLab not found.');
    return;
  }

  // ── Fall back to inline helpers if UHQ didn't load ────────────────────
  const _lerp  = (a, b, t) => a + (b - a) * t;
  const _clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const _rand  = (a, b) => a + Math.random() * (b - a);

  function _setupRenderer(renderer) {
    if (window.UHQ) { window.UHQ.setupRenderer(renderer); return; }
    renderer.toneMapping         = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    renderer.outputColorSpace    = THREE.SRGBColorSpace;
  }

  function _softMat(opts) {
    if (window.UHQ) return window.UHQ.softMat(opts);
    const { size = 0.18, opacity = 0.88 } = opts || {};
    return new THREE.PointsMaterial({
      size, vertexColors: true, transparent: true, opacity,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
  }

  function _glowMat(opts) {
    if (window.UHQ) return window.UHQ.glowMat(opts);
    const { size = 1.1, opacity = 0.15 } = opts || {};
    return new THREE.PointsMaterial({
      size, vertexColors: true, transparent: true, opacity,
      blending: THREE.AdditiveBlending, depthWrite: false,
    });
  }

  /* ══════════════════════════════════════════════════════════════════════
     BLACK HOLE v2  —  Liquidity Singularity
  ══════════════════════════════════════════════════════════════════════ */
  function vizBlackhole() {
    const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!container || typeof THREE === 'undefined') return null;

    const W = container.clientWidth  || 800;
    const H = (container.clientHeight || 500) - 50;
    const DISK_COUNT = 35000;
    const JET_COUNT  = 2000;

    // Ticker context
    const ticker = window.__MMO_CURRENT_TICKER__ || 'SPY';
    window.__MMO_CURRENT_TICKER__ = null;
    const isETF = ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VIX'].includes(ticker);

    // ── Scene ────────────────────────────────────────────────────────────
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000004);

    const camera = new THREE.PerspectiveCamera(52, W / H, 0.1, 500);
    // Start position for cinematic approach
    camera.position.set(0, 80, 130);
    camera.lookAt(0, 0, 0);

    // ── Renderer ─────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    _setupRenderer(renderer);

    const mount = document.getElementById('viz-three-mount');
    if (!mount) return null;
    mount.innerHTML = '';
    mount.appendChild(renderer.domElement);

    // ── Context label ────────────────────────────────────────────────────
    const label = document.createElement('div');
    Object.assign(label.style, {
      position: 'absolute', bottom: '14px', left: '16px', zIndex: '10',
      fontFamily: 'monospace', fontSize: '11px', letterSpacing: '0.6px',
      textShadow: '0 0 10px currentColor', pointerEvents: 'none',
    });
    label.innerHTML = isETF
      ? `<span style="color:#ff9500">ETF</span> <span style="color:#888">${ticker}</span> — multi-vortex accretion system`
      : `<span style="color:#00d4ff">STOCK</span> <span style="color:#888">${ticker}</span> — unified singularity core`;
    label.style.color = isETF ? '#ff9500' : '#00d4ff';
    mount.appendChild(label);

    // ── Temperature-correct disk colour ──────────────────────────────────
    // Inner (r≈3)  → blue-white  (T~10^7 K)
    // Mid   (r~15) → white-yellow transition
    // Outer (r≈45) → orange-red  (T~10^4 K)
    function diskColor(radius, col, i3) {
      const t = _clamp((radius - 3) / 42, 0, 1);
      if (t < 0.22) {
        // Blue-white corona
        const u = t / 0.22;
        col[i3]     = _lerp(0.80, 1.0, u);
        col[i3 + 1] = _lerp(0.90, 1.0, u);
        col[i3 + 2] = 1.0;
      } else if (t < 0.52) {
        // White → yellow
        const u = (t - 0.22) / 0.30;
        col[i3]     = 1.0;
        col[i3 + 1] = _lerp(1.0, 0.75, u);
        col[i3 + 2] = _lerp(1.0, 0.05, u);
      } else {
        // Yellow → orange → deep red
        const u = (t - 0.52) / 0.48;
        col[i3]     = _lerp(1.0, 0.55, u);
        col[i3 + 1] = _lerp(0.75, 0.08, u);
        col[i3 + 2] = 0.0;
      }
    }

    // ── Accretion disk particles ──────────────────────────────────────────
    const dGeo  = new THREE.BufferGeometry();
    const dPos  = new Float32Array(DISK_COUNT * 3);
    const dCol  = new Float32Array(DISK_COUNT * 3);
    const dVels = new Float32Array(DISK_COUNT * 3);

    for (let i = 0; i < DISK_COUNT; i++) {
      const i3  = i * 3;
      const ang = Math.random() * Math.PI * 2;
      const r   = _rand(4, 46);
      // Thin disk: height exponentially suppressed at large radii
      const h   = _rand(-1, 1) * Math.exp(-r * 0.055) * 1.5;
      dPos[i3]     = Math.cos(ang) * r;
      dPos[i3 + 1] = h;
      dPos[i3 + 2] = Math.sin(ang) * r;
      diskColor(r, dCol, i3);
      const v        = Math.sqrt(125 / (r + 0.5));
      dVels[i3]     = -Math.sin(ang) * v;
      dVels[i3 + 1] = _rand(-0.005, 0.005);
      dVels[i3 + 2] =  Math.cos(ang) * v;
    }

    dGeo.setAttribute('position', new THREE.BufferAttribute(dPos, 3));
    dGeo.setAttribute('color',    new THREE.BufferAttribute(dCol, 3));

    // Two layers: crisp detail + wide glow halo
    const diskDetail = new THREE.Points(dGeo, _softMat({ size: 0.20, opacity: 0.85 }));
    const diskGlow   = new THREE.Points(dGeo, _glowMat({ size: 1.10, opacity: 0.16 }));
    scene.add(diskDetail);
    scene.add(diskGlow);

    // ── Relativistic jets ─────────────────────────────────────────────────
    const jGeo  = new THREE.BufferGeometry();
    const jPos  = new Float32Array(JET_COUNT * 3);
    const jCol  = new Float32Array(JET_COUNT * 3);
    const jVels = new Float32Array(JET_COUNT * 3);

    for (let i = 0; i < JET_COUNT; i++) {
      const i3  = i * 3;
      const dir = i < JET_COUNT / 2 ? 1 : -1;
      const spr = _rand(0, 0.4);
      const ang = Math.random() * Math.PI * 2;
      jPos[i3]     = Math.cos(ang) * spr;
      jPos[i3 + 1] = dir * _rand(1, 5);
      jPos[i3 + 2] = Math.sin(ang) * spr;
      jVels[i3 + 1] = dir * _rand(0.08, 0.22);
      // Blue-violet plasma colour
      jCol[i3]     = _rand(0.30, 0.55);
      jCol[i3 + 1] = _rand(0.15, 0.35);
      jCol[i3 + 2] = 1.0;
    }
    jGeo.setAttribute('position', new THREE.BufferAttribute(jPos, 3));
    jGeo.setAttribute('color',    new THREE.BufferAttribute(jCol, 3));

    const jetDetail = new THREE.Points(jGeo, _softMat({ size: 0.16, opacity: 0.75 }));
    const jetGlow   = new THREE.Points(jGeo, _glowMat({ size: 0.85, opacity: 0.14 }));
    scene.add(jetDetail);
    scene.add(jetGlow);

    // ── Event horizon (black sphere) ──────────────────────────────────────
    const R_EH = isETF ? 3.0 : 4.5;
    const ehMesh = new THREE.Mesh(
      new THREE.SphereGeometry(R_EH, 64, 64),
      new THREE.MeshBasicMaterial({ color: 0x000000 })
    );
    scene.add(ehMesh);

    // ── Photon-sphere ring ─────────────────────────────────────────────────
    const photonRing = new THREE.Mesh(
      new THREE.TorusGeometry(R_EH * 1.28, 0.07, 16, 200),
      new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.75 })
    );
    photonRing.rotation.x = Math.PI / 2;
    scene.add(photonRing);

    // ── Corona glow layers (additive spheres, inside-out normals) ──────────
    const coronaLayers = [
      { r: R_EH * 1.55, color: 0xff5500, opacity: 0.055 },
      { r: R_EH * 2.10, color: 0x4400ff, opacity: 0.030 },
      { r: R_EH * 3.00, color: 0xff2200, opacity: 0.012 },
    ];
    for (const lyr of coronaLayers) {
      scene.add(new THREE.Mesh(
        new THREE.SphereGeometry(lyr.r, 32, 32),
        new THREE.MeshBasicMaterial({
          color: lyr.color, transparent: true, opacity: lyr.opacity,
          blending: THREE.AdditiveBlending, side: THREE.BackSide,
        })
      ));
    }

    // ── Gravity sources ───────────────────────────────────────────────────
    const blackholes = [{ pos: new THREE.Vector3(0, 0, 0), mass: isETF ? 65 : 120 }];
    if (isETF) {
      for (let v = 0; v < 4; v++) {
        const a = (Math.PI * 2 / 4) * v;
        const d = 13 + Math.random() * 3;
        blackholes.push({
          pos: new THREE.Vector3(Math.cos(a) * d, 0, Math.sin(a) * d),
          mass: 12, angle: a, dist: d, speed: _rand(0.008, 0.018),
        });
      }
    }

    // ── Cinematic camera state ─────────────────────────────────────────────
    const camTarget  = new THREE.Vector3(0, 22, 42);
    const camStart   = camera.position.clone();
    let   camT       = 0;     // 0 → 1 approach progress
    let   orbitAngle = 0;

    // ── Animation loop ────────────────────────────────────────────────────
    let animId = null;
    let time   = 0;

    function animate() {
      animId = requestAnimationFrame(animate);
      time  += 0.016;

      // — Camera approach / orbit —
      if (camT < 1) {
        camT = Math.min(1, camT + 0.004);
        const ease = 1 - Math.pow(1 - camT, 3);
        camera.position.lerpVectors(camStart, camTarget, ease);
        camera.lookAt(0, 0, 0);
      } else {
        orbitAngle += 0.0006;
        const orR = Math.sqrt(camera.position.x ** 2 + camera.position.z ** 2);
        camera.position.x = Math.cos(orbitAngle) * orR;
        camera.position.z = Math.sin(orbitAngle) * orR;
        camera.lookAt(0, 0, 0);
      }

      // — Orbiting ETF sub-holes —
      if (isETF) {
        for (let v = 1; v < blackholes.length; v++) {
          const bh = blackholes[v];
          bh.angle += bh.speed;
          bh.pos.x = Math.cos(bh.angle) * bh.dist;
          bh.pos.z = Math.sin(bh.angle) * bh.dist;
        }
      }

      // — Disk particle physics —
      const dp = dGeo.attributes.position.array;
      const dc = dGeo.attributes.color.array;

      for (let i = 0; i < DISK_COUNT; i++) {
        const i3 = i * 3;
        let px = dp[i3], py = dp[i3 + 1], pz = dp[i3 + 2];
        let fx = 0, fy = 0, fz = 0;
        let minDist = 9999;

        for (const bh of blackholes) {
          const dx = bh.pos.x - px, dy = bh.pos.y - py, dz = bh.pos.z - pz;
          const distSq = Math.max(0.1, dx * dx + dy * dy + dz * dz);
          const dist   = Math.sqrt(distSq);
          if (dist < minDist) minDist = dist;
          const force  = bh.mass / distSq;
          fx += (dx / dist) * force;
          fy += (dy / dist) * force;
          fz += (dz / dist) * force;
        }

        dVels[i3]     = (dVels[i3]     + fx) * 0.994;
        dVels[i3 + 1] = (dVels[i3 + 1] + fy) * 0.988;
        dVels[i3 + 2] = (dVels[i3 + 2] + fz) * 0.994;

        dp[i3]     += dVels[i3];
        dp[i3 + 1] += dVels[i3 + 1];
        dp[i3 + 2] += dVels[i3 + 2];

        // — Blueshift: colour shift to white-blue when very close —
        if (minDist < 7) {
          const bf = _clamp(1 - (minDist - 2) / 5, 0, 1) * 0.12;
          dc[i3]     = _lerp(dc[i3],     0.25, bf);
          dc[i3 + 1] = _lerp(dc[i3 + 1], 0.75, bf);
          dc[i3 + 2] = _lerp(dc[i3 + 2], 1.0,  bf);
        }

        // — Swallowed → respawn at outer disk edge —
        let swallowed = false;
        for (const bh of blackholes) {
          if ((bh.pos.x - px) ** 2 + (bh.pos.z - pz) ** 2 < (R_EH * 1.15) ** 2) {
            swallowed = true; break;
          }
        }
        if (swallowed) {
          const ang = Math.random() * Math.PI * 2;
          const r   = _rand(40, 47);
          dp[i3]     = Math.cos(ang) * r;
          dp[i3 + 1] = _rand(-1, 1) * Math.exp(-r * 0.055) * 1.5;
          dp[i3 + 2] = Math.sin(ang) * r;
          diskColor(r, dc, i3);
          const v      = Math.sqrt(125 / (r + 0.5));
          dVels[i3]    = -Math.sin(ang) * v;
          dVels[i3+1]  = _rand(-0.003, 0.003);
          dVels[i3+2]  =  Math.cos(ang) * v;
        }
      }
      dGeo.attributes.position.needsUpdate = true;
      dGeo.attributes.color.needsUpdate    = true;

      // — Jet physics —
      const jp = jGeo.attributes.position.array;
      for (let i = 0; i < JET_COUNT; i++) {
        const i3 = i * 3;
        jp[i3]     += jVels[i3];
        jp[i3 + 1] += jVels[i3 + 1];
        jp[i3 + 2] += jVels[i3 + 2];
        // Slight radial spread as jet rises
        jp[i3]     *= 1.0012;
        jp[i3 + 2] *= 1.0012;
        if (Math.abs(jp[i3 + 1]) > 25) {
          const dir = jp[i3 + 1] > 0 ? 1 : -1;
          const ang = Math.random() * Math.PI * 2;
          const spr = _rand(0, 0.3);
          jp[i3]     = Math.cos(ang) * spr;
          jp[i3 + 1] = dir * _rand(1, 4);
          jp[i3 + 2] = Math.sin(ang) * spr;
        }
      }
      jGeo.attributes.position.needsUpdate = true;

      // — Photon ring opacity pulse —
      photonRing.material.opacity = 0.55 + Math.sin(time * 2.5) * 0.20;

      renderer.render(scene, camera);
    }

    animate();
    return () => { cancelAnimationFrame(animId); renderer.dispose(); };
  }

  /* ══════════════════════════════════════════════════════════════════════
     GALAXY 3D v2  —  Market Galaxy
  ══════════════════════════════════════════════════════════════════════ */
  function vizGalaxy3D() {
    const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
    if (!container || typeof THREE === 'undefined') return null;

    const W = container.clientWidth  || 800;
    const H = (container.clientHeight || 500) - 50;
    const DISK_COUNT = 40000;
    const CORE_COUNT =  3500;

    const ticker = window.__MMO_CURRENT_TICKER__ || 'SPY';
    window.__MMO_CURRENT_TICKER__ = null;
    const isETF = ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VIX'].includes(ticker);

    // ── Scene ─────────────────────────────────────────────────────────────
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x010208);
    scene.fog = new THREE.FogExp2(0x010208, 0.0022);

    const camera = new THREE.PerspectiveCamera(52, W / H, 0.1, 1000);
    camera.position.set(0, 50, 70);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    _setupRenderer(renderer);

    const mount = document.getElementById('viz-three-mount');
    if (!mount) return null;
    mount.innerHTML = '';
    mount.appendChild(renderer.domElement);

    // ── Context label ──────────────────────────────────────────────────────
    const label = document.createElement('div');
    Object.assign(label.style, {
      position: 'absolute', bottom: '14px', left: '16px', zIndex: '10',
      fontFamily: 'monospace', fontSize: '11px', color: '#50fa7b',
      textShadow: '0 0 10px #50fa7b', pointerEvents: 'none',
    });
    const ARMS = isETF ? 8 : 2;
    label.innerHTML = isETF
      ? `<span style="color:#ff9500">ETF</span> <span style="color:#888">${ticker}</span> — ${ARMS} sector arms`
      : `<span style="color:#00d4ff">STOCK</span> <span style="color:#888">${ticker}</span> — focused orbital structure`;
    mount.appendChild(label);

    // ── Sector arm colours (one per market sector) ─────────────────────────
    const ARM_COLORS = [
      [0.20, 0.80, 1.00],  // Tech        — cyan
      [1.00, 0.72, 0.10],  // Finance      — gold
      [0.28, 1.00, 0.48],  // Health       — green
      [1.00, 0.28, 0.28],  // Energy       — red
      [0.78, 0.28, 1.00],  // Utilities    — purple
      [1.00, 0.52, 0.05],  // Industrials  — orange
      [0.28, 0.60, 1.00],  // Consumer     — blue
      [0.80, 1.00, 0.28],  // Materials    — lime
    ];

    // ── Disk particles ─────────────────────────────────────────────────────
    const dGeo    = new THREE.BufferGeometry();
    const dPos    = new Float32Array(DISK_COUNT * 3);
    const dCol    = new Float32Array(DISK_COUNT * 3);
    const dParams = new Float32Array(DISK_COUNT * 3); // angle, radius, speed

    const tight   = isETF ? 0.28 : 1.05;
    const maxR    = isETF ? 52    : 42;
    const minR    = isETF ?  2    :  1;
    const hSpread = isETF ? 16    :  7;

    for (let i = 0; i < DISK_COUNT; i++) {
      const i3     = i * 3;
      const armIdx = i % ARMS;
      const armOff = (armIdx / ARMS) * Math.PI * 2;
      const radius = minR + Math.random() * (maxR - minR);
      const angle  = armOff + radius * tight + _rand(-0.38, 0.38);
      const speed  = _rand(0.0004, 0.0028) * ((isETF ? 22 : 42) / (radius + 4));

      dParams[i3]     = angle;
      dParams[i3 + 1] = radius;
      dParams[i3 + 2] = speed;

      dPos[i3]     = Math.cos(angle) * radius;
      dPos[i3 + 1] = (_rand(-1, 1) * hSpread) / (radius + 1.5);
      dPos[i3 + 2] = Math.sin(angle) * radius;

      // Arm colour with radial brightness falloff
      const ac   = ARM_COLORS[armIdx % ARM_COLORS.length];
      const fade = _clamp(1.25 - radius / maxR, 0.25, 1.0);
      const sc   = _rand(0.82, 1.00);
      dCol[i3]     = _clamp(ac[0] * fade * sc, 0, 1);
      dCol[i3 + 1] = _clamp(ac[1] * fade * sc, 0, 1);
      dCol[i3 + 2] = _clamp(ac[2] * fade * sc, 0, 1);
    }

    dGeo.setAttribute('position', new THREE.BufferAttribute(dPos, 3));
    dGeo.setAttribute('color',    new THREE.BufferAttribute(dCol, 3));

    const diskDetail = new THREE.Points(dGeo, _softMat({ size: isETF ? 0.16 : 0.20, opacity: 0.86 }));
    const diskGlow   = new THREE.Points(dGeo, _glowMat({ size: isETF ? 0.80 : 1.00, opacity: 0.14 }));

    // Wrap both in a group so a single rotation affects them identically
    const galaxyGroup = new THREE.Group();
    galaxyGroup.add(diskDetail);
    galaxyGroup.add(diskGlow);
    scene.add(galaxyGroup);

    // ── Galactic nucleus (dense, bright yellow-white core) ─────────────────
    const cGeo = new THREE.BufferGeometry();
    const cPos = new Float32Array(CORE_COUNT * 3);
    const cCol = new Float32Array(CORE_COUNT * 3);

    for (let i = 0; i < CORE_COUNT; i++) {
      const i3    = i * 3;
      const phi   = Math.acos(2 * Math.random() - 1);
      const theta = Math.random() * Math.PI * 2;
      const r     = _rand(0, 3.2);
      cPos[i3]     = Math.sin(phi) * Math.cos(theta) * r;
      cPos[i3 + 1] = Math.cos(phi) * r * 0.22; // flatten to disk
      cPos[i3 + 2] = Math.sin(phi) * Math.sin(theta) * r;
      const br     = _rand(0.88, 1.00);
      cCol[i3]     = br;
      cCol[i3 + 1] = _rand(0.92, 1.00) * br;
      cCol[i3 + 2] = _rand(0.72, 0.88) * br; // warm white
    }

    cGeo.setAttribute('position', new THREE.BufferAttribute(cPos, 3));
    cGeo.setAttribute('color',    new THREE.BufferAttribute(cCol, 3));

    const coreDetail = new THREE.Points(cGeo, _softMat({ size: 0.50, opacity: 0.95 }));
    const coreGlow   = new THREE.Points(cGeo, _glowMat({ size: 2.80, opacity: 0.30 }));
    galaxyGroup.add(coreDetail);
    galaxyGroup.add(coreGlow);

    // ── Animation ──────────────────────────────────────────────────────────
    let animId     = null;
    let camOrbitA  = Math.atan2(camera.position.z, camera.position.x);
    let tiltBase   = -0.18;

    function animate() {
      animId = requestAnimationFrame(animate);

      // Orbital mechanics — update each particle's angle + rebuild X/Z
      const dp = dGeo.attributes.position.array;
      for (let i = 0; i < DISK_COUNT; i++) {
        const i3        = i * 3;
        dParams[i3]    += dParams[i3 + 2];
        const ang       = dParams[i3];
        const r         = dParams[i3 + 1];
        dp[i3]          = Math.cos(ang) * r;
        dp[i3 + 2]      = Math.sin(ang) * r;
        // Y is static (height doesn't change)
      }
      dGeo.attributes.position.needsUpdate = true;

      // Slow self-rotation of the whole group (accumulating, not constant)
      galaxyGroup.rotation.y += 0.00045;

      // Subtle tilt oscillation (± 2°)
      galaxyGroup.rotation.x = tiltBase + Math.sin(Date.now() * 0.000065) * 0.035;

      // Gentle camera orbit
      camOrbitA += 0.00038;
      const camR = Math.hypot(camera.position.x, camera.position.z);
      camera.position.x = Math.cos(camOrbitA) * camR;
      camera.position.z = Math.sin(camOrbitA) * camR;
      camera.lookAt(0, 0, 0);

      renderer.render(scene, camera);
    }

    animate();
    return () => { cancelAnimationFrame(animId); renderer.dispose(); };
  }

  // ── Registration ────────────────────────────────────────────────────────
  window.VizLab.registerViz(
    'blackhole',
    {
      cat: 'art', label: 'Liquidity Black Hole', icon: '🌌', api: null,
      desc: 'UHQ v2 — Temperature-correct accretion disk (blue-white core → red outer), ' +
            'relativistic plasma jets, photon-sphere ring, layered corona, cinematic approach. ' +
            'ETF = multi-vortex system  ·  Stock = unified singularity.',
    },
    true, vizBlackhole
  );

  window.VizLab.registerViz(
    'galaxy3d',
    {
      cat: 'art', label: 'Market Galaxy 3D', icon: '🌠', api: null,
      desc: 'UHQ v2 — 40 k particle spiral galaxy. ETF: 8 sector arms (Tech/Finance/Health/Energy…) ' +
            'each with a distinct colour. Dense yellow-white galactic nucleus. Soft bloom layers. ' +
            'Slow camera orbit. Fixed galaxy-tilt accumulation.',
    },
    true, vizGalaxy3D
  );
})();
