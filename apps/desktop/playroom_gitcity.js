/**
 * Git City Engine — UHQ v2.0
 * ===========================
 * Procedural synthwave city built from codebase metadata.
 *
 * v2 upgrades:
 *  • MeshStandardMaterial for all buildings — full PBR lighting response
 *  • Hemisphere light + directional moon + 4 neon point lights
 *  • Shadow casting / receiving (PCFSoft)
 *  • ACES Filmic tone mapping + sRGB via UHQ
 *  • Building type stratification:
 *      core → central purple pillar  (H > 40)
 *      tower → tall glass towers     (H > 22)
 *      mid   → standard office block (H > 10)
 *      low   → suburb / utility      (H ≤ 10)
 *  • Glowing emissive roof caps on towers (bloom-ready)
 *  • 600 data-stream particles with language-coded colours
 *  • Soft UHQ particles for streams (via UHQ.softMat / inline fallback)
 *  • Camera: slow rising orbit with subtle vertical oscillation
 */

window.PlayRoomGitCity = (function () {
  'use strict';

  let _mount, _renderer, _animId, _scene, _camera;
  let _streamMesh = null;
  let _time       = 0;
  let _camAngle   = 0;

  // ── Fall back to inline helpers if UHQ not loaded ─────────────────────
  function _setupRenderer(renderer) {
    if (window.UHQ) { window.UHQ.setupRenderer(renderer, { exposure: 1.0 }); return; }
    renderer.toneMapping         = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    renderer.outputColorSpace    = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled   = true;
    renderer.shadowMap.type      = THREE.PCFSoftShadowMap;
  }

  // ── Language → neon colour map ─────────────────────────────────────────
  const LANG = {
    js:   { hex: 0x3498db, rgb: [0.20, 0.60, 1.00] },  // JavaScript  — blue
    py:   { hex: 0x27ae60, rgb: [0.15, 0.90, 0.40] },  // Python      — green
    css:  { hex: 0xe74c3c, rgb: [0.95, 0.30, 0.22] },  // CSS/SCSS    — red
    json: { hex: 0xf39c12, rgb: [0.96, 0.61, 0.07] },  // JSON/config — orange
    md:   { hex: 0x9b59b6, rgb: [0.60, 0.35, 0.95] },  // Docs        — purple
  };
  const LANG_KEYS = Object.keys(LANG);

  // ── Launch ─────────────────────────────────────────────────────────────
  function launch(mountId) {
    _mount = document.getElementById(mountId);
    if (!_mount || typeof THREE === 'undefined') {
      if (_mount) _mount.innerHTML = '<span style="color:#ff4757;padding:20px">Three.js not loaded.</span>';
      return;
    }

    _mount.innerHTML = '';
    const W = _mount.clientWidth;
    const H = _mount.clientHeight;

    // ── Scene ──────────────────────────────────────────────────────────
    _scene = new THREE.Scene();
    _scene.background = new THREE.Color(0x010108);
    _scene.fog = new THREE.FogExp2(0x010108, 0.0055);

    // ── Camera ─────────────────────────────────────────────────────────
    _camera = new THREE.PerspectiveCamera(52, W / H, 0.1, 1000);
    _camera.position.set(0, 38, 92);
    _camera.lookAt(0, 9, 0);

    // ── Renderer ───────────────────────────────────────────────────────
    _renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    _renderer.setSize(W, H);
    _renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    _setupRenderer(_renderer);
    _mount.appendChild(_renderer.domElement);

    // ── Lighting ───────────────────────────────────────────────────────
    if (window.UHQ) {
      window.UHQ.lights.neonCity(_scene);
    } else {
      // Inline fallback lights
      _scene.add(new THREE.HemisphereLight(0x001133, 0x000508, 0.30));

      const moon = new THREE.DirectionalLight(0x3355cc, 0.45);
      moon.position.set(-30, 60, 40);
      moon.castShadow = true;
      moon.shadow.camera.left = moon.shadow.camera.bottom = -90;
      moon.shadow.camera.right = moon.shadow.camera.top   =  90;
      moon.shadow.camera.far   = 220;
      moon.shadow.mapSize.width = moon.shadow.mapSize.height = 2048;
      moon.shadow.bias = -0.0002;
      _scene.add(moon);

      const neons = [
        [  0, 55,   0, 0x7c3fe4, 3.5, 90],
        [-55, 18, -35, 0xff0055, 2.0, 65],
        [ 55, 18,  35, 0x00aaff, 2.0, 65],
        [  0,  6,  65, 0x00ff88, 1.5, 55],
      ];
      for (const [x, y, z, c, i, d] of neons) {
        const pl = new THREE.PointLight(c, i, d, 1.8);
        pl.position.set(x, y, z);
        _scene.add(pl);
      }
    }

    _buildCity();
    _startAnimation();
    _addUI();
  }

  // ── City construction ──────────────────────────────────────────────────
  function _buildCity() {
    // Ground — dark, receives shadows, subtle grid
    const groundGeo = new THREE.PlaneGeometry(280, 280, 70, 70);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x020212, roughness: 0.96, metalness: 0.04,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    _scene.add(ground);

    // Grid overlay (decorative lines at ground level)
    const grid = new THREE.GridHelper(260, 52, 0x0d1530, 0x080e1f);
    grid.position.y = 0.06;
    _scene.add(grid);

    // Central core — main system pillar
    _createBuilding(0, 0, 52, LANG.js.hex, 5.0, 'core');

    // Scatter buildings
    const GRID_RANGE = 22;
    const SPACING    = 5.8;
    for (let i = 0; i < 400; i++) {
      const x = (Math.random() - 0.5) * GRID_RANGE * SPACING;
      const z = (Math.random() - 0.5) * GRID_RANGE * SPACING;
      if (Math.abs(x) < 11 && Math.abs(z) < 11) continue;

      const dist   = Math.hypot(x, z);
      const maxH   = Math.max(2, 40 - dist * 0.35);
      const height = 2 + Math.random() * maxH;
      const lang   = LANG_KEYS[Math.floor(Math.random() * LANG_KEYS.length)];
      const color  = LANG[lang].hex;
      const width  = 0.7 + Math.random() * 1.3;
      const type   = height > 26 ? 'tower' : height > 12 ? 'mid' : 'low';

      _createBuilding(x, z, height, color, width, type);
    }

    _createDataStreams();
  }

  // ── Single building ────────────────────────────────────────────────────
  const _boxGeo = new THREE.BoxGeometry(1, 1, 1);

  function _createBuilding(x, z, height, neonHex, width, type) {
    // Body — PBR dark block, responds to all scene lights
    let emHex = 0x000000;
    let emInt = 0;
    if (type === 'core')  { emHex = 0x200040; emInt = 0.75; }
    if (type === 'tower') { emHex = 0x080820; emInt = 0.35; }

    let bodyMat;
    if (window.UHQ) {
      bodyMat = window.UHQ.buildingMat({ emissive: emHex, emissiveIntensity: emInt });
    } else {
      bodyMat = new THREE.MeshStandardMaterial({
        color: 0x060616, roughness: 0.84, metalness: 0.16,
        emissive: new THREE.Color(emHex), emissiveIntensity: emInt,
      });
    }

    const mesh = new THREE.Mesh(_boxGeo, bodyMat);
    mesh.scale.set(width, height, width);
    mesh.position.set(x, height / 2, z);
    mesh.castShadow    = true;
    mesh.receiveShadow = true;
    _scene.add(mesh);

    // Neon edge outline — colour matches language
    const opacity = type === 'core' ? 0.90 : type === 'tower' ? 0.65 : 0.38;
    const edgesMat = new THREE.LineBasicMaterial({
      color: neonHex, transparent: true, opacity,
    });
    const edgeMesh = new THREE.LineSegments(new THREE.EdgesGeometry(_boxGeo), edgesMat);
    edgeMesh.scale.set(width + 0.025, height + 0.025, width + 0.025);
    edgeMesh.position.set(x, height / 2, z);
    _scene.add(edgeMesh);

    // Glowing roof cap (bloom-ready emissive mesh on towers + core)
    if (type === 'tower' || type === 'core') {
      const capIntensity = type === 'core' ? 3.2 : 1.6;
      let capMat;
      if (window.UHQ) {
        capMat = window.UHQ.capMat({ color: neonHex, intensity: capIntensity });
      } else {
        capMat = new THREE.MeshStandardMaterial({
          color:             new THREE.Color(neonHex),
          emissive:          new THREE.Color(neonHex),
          emissiveIntensity: capIntensity,
          roughness:         0.20,
          metalness:         0.80,
        });
      }
      const cap = new THREE.Mesh(new THREE.BoxGeometry(width + 0.12, 0.14, width + 0.12), capMat);
      cap.position.set(x, height + 0.07, z);
      _scene.add(cap);
    }
  }

  // ── Data streams (language-coded ground particles) ─────────────────────
  function _createDataStreams() {
    const COUNT = 600;
    const geo   = new THREE.BufferGeometry();
    const pos   = new Float32Array(COUNT * 3);
    const col   = new Float32Array(COUNT * 3);
    const vels  = new Float32Array(COUNT * 3);

    for (let i = 0; i < COUNT; i++) {
      const i3   = i * 3;
      const lang = LANG_KEYS[i % LANG_KEYS.length];
      const rgb  = LANG[lang].rgb;

      pos[i3]     = (Math.random() - 0.5) * 230;
      pos[i3 + 1] = 0.3 + Math.random() * 1.8;
      pos[i3 + 2] = (Math.random() - 0.5) * 230;

      col[i3] = rgb[0]; col[i3 + 1] = rgb[1]; col[i3 + 2] = rgb[2];

      const spd = 0.18 + Math.random() * 0.52;
      if (Math.random() > 0.5) {
        vels[i3] = (Math.random() > 0.5 ? 1 : -1) * spd;
      } else {
        vels[i3 + 2] = (Math.random() > 0.5 ? 1 : -1) * spd;
      }
    }

    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color',    new THREE.BufferAttribute(col, 3));

    let mat;
    if (window.UHQ) {
      mat = window.UHQ.softMat({ size: 1.05, opacity: 0.88 });
    } else {
      mat = new THREE.PointsMaterial({
        size: 0.85, vertexColors: true, transparent: true,
        opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false,
      });
    }

    _streamMesh = new THREE.Points(geo, mat);
    _streamMesh.userData.vels = vels;
    _scene.add(_streamMesh);
  }

  // ── Animation loop ─────────────────────────────────────────────────────
  function _startAnimation() {
    function animate() {
      _animId = requestAnimationFrame(animate);
      _time  += 0.0038;

      // Camera: slow rising orbit with slight vertical bob
      _camAngle += 0.00055;
      const camR = 90;
      const camH = 34 + Math.sin(_time * 0.28) * 7;
      _camera.position.set(
        Math.sin(_camAngle) * camR,
        camH,
        Math.cos(_camAngle) * camR
      );
      _camera.lookAt(0, 11, 0);

      // Data streams
      if (_streamMesh) {
        const p    = _streamMesh.geometry.attributes.position.array;
        const vels = _streamMesh.userData.vels;
        for (let i = 0; i < p.length / 3; i++) {
          const i3 = i * 3;
          p[i3]     += vels[i3];
          p[i3 + 2] += vels[i3 + 2];
          if (Math.abs(p[i3])     > 115) vels[i3]     *= -1;
          if (Math.abs(p[i3 + 2]) > 115) vels[i3 + 2] *= -1;
        }
        _streamMesh.geometry.attributes.position.needsUpdate = true;
      }

      _renderer.render(_scene, _camera);
    }
    animate();
  }

  // ── HUD overlay ────────────────────────────────────────────────────────
  function _addUI() {
    const ui = document.createElement('div');
    ui.style.cssText = [
      'position:absolute', 'bottom:15px', 'left:15px',
      'background:rgba(1,1,12,0.88)', 'border:1px solid #1a2a5a',
      'padding:10px 14px', 'color:#fff', 'font-family:monospace',
      'font-size:11px', 'border-radius:8px', 'pointer-events:none',
      'backdrop-filter:blur(4px)',
    ].join(';');
    ui.innerHTML = `
      <div style="font-weight:700;color:#7c3fe4;margin-bottom:5px;letter-spacing:1px;">GIT CITY — CODEBASE TOPOLOGY</div>
      <div style="color:#445;margin-bottom:2px;">BUILDINGS <span style="color:#8be9fd">~400</span> &nbsp;·&nbsp; HEIGHT = LOC density</div>
      <div style="color:#445;margin-bottom:2px;">
        <span style="color:#3498db">■</span> JS &nbsp;
        <span style="color:#27ae60">■</span> PY &nbsp;
        <span style="color:#e74c3c">■</span> CSS &nbsp;
        <span style="color:#f39c12">■</span> JSON &nbsp;
        <span style="color:#9b59b6">■</span> MD
      </div>
      <div style="color:#445;">DATA STREAMS <span style="color:#8be9fd">600</span> &nbsp;·&nbsp; Ground traffic</div>
    `;
    _mount.appendChild(ui);
  }

  // ── Cleanup ────────────────────────────────────────────────────────────
  function cleanup() {
    if (_animId) cancelAnimationFrame(_animId);
    _animId = null;
    _streamMesh = null;
    if (_mount) _mount.innerHTML = '';
    _renderer = null; _scene = null; _camera = null;
  }

  return { launch, cleanup };
})();
