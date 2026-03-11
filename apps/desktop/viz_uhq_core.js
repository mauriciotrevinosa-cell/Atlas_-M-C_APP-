/**
 * Atlas VizLab — UHQ (Ultra High Quality) Rendering Core  v1.0
 * =============================================================
 * Shared utilities injected once, used by every 3D visualization.
 *
 *  • ACES Filmic tone mapping  — eliminates the flat/washed-out look
 *  • sRGB colour space          — correct monitor output
 *  • Soft glow particle texture — turns hard pixels into light sources
 *  • Bloom simulation layer     — glow around bright particles (no extra lib)
 *  • Standard material factory  — PBR materials for geometry scenes
 *  • Scene lighting presets     — hemisphere + directional + neon points
 *
 * Usage (any viz file):
 *   const uhq = window.UHQ;
 *   uhq.setupRenderer(renderer);                   // tone map + sRGB
 *   const mat = uhq.softMat({ size: 0.18 });       // main particle layer
 *   const glow = uhq.glowMat({ size: 0.9 });       // bloom sim layer (same geo)
 *   uhq.lights.neonCity(scene);                    // git-city lighting preset
 */

window.UHQ = (() => {
  'use strict';

  if (typeof THREE === 'undefined') {
    console.warn('[UHQ] THREE not loaded — UHQ inactive.');
    return {};
  }

  /* ──────────────────────────────────────────────────────────────────────
     GLOW TEXTURE
     64×64 radial gradient: centre white → transparent edge.
     Replaces the default hard square/circle pixel of PointsMaterial.
  ────────────────────────────────────────────────────────────────────── */
  let _gTex = null;
  function _makeGlowTex() {
    if (_gTex) return _gTex;
    const size = 128;
    const c = document.createElement('canvas');
    c.width = c.height = size;
    const ctx = c.getContext('2d');
    const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    g.addColorStop(0.00, 'rgba(255,255,255,1.00)');
    g.addColorStop(0.08, 'rgba(255,255,255,0.98)');
    g.addColorStop(0.25, 'rgba(255,255,255,0.70)');
    g.addColorStop(0.50, 'rgba(255,255,255,0.25)');
    g.addColorStop(0.75, 'rgba(255,255,255,0.06)');
    g.addColorStop(1.00, 'rgba(255,255,255,0.00)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, size, size);
    _gTex = new THREE.CanvasTexture(c);
    return _gTex;
  }

  /* ──────────────────────────────────────────────────────────────────────
     RENDERER SETUP
     Call once per renderer immediately after construction.
  ────────────────────────────────────────────────────────────────────── */
  function setupRenderer(renderer, { exposure = 1.1 } = {}) {
    renderer.toneMapping        = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = exposure;
    renderer.outputColorSpace   = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled  = true;
    renderer.shadowMap.type     = THREE.PCFSoftShadowMap;
    return renderer;
  }

  /* ──────────────────────────────────────────────────────────────────────
     PARTICLE MATERIALS
     softMat  → main detail layer:   small, crisp, coloured
     glowMat  → bloom-sim layer:     large, faint halo — simulates post bloom
     Use both on the same BufferGeometry for the "glow" effect.
  ────────────────────────────────────────────────────────────────────── */
  function softMat({
    size     = 0.18,
    opacity  = 0.88,
    blending = THREE.AdditiveBlending,
  } = {}) {
    const tex = _makeGlowTex();
    return new THREE.PointsMaterial({
      size,
      vertexColors:    true,
      transparent:     true,
      opacity,
      blending,
      depthWrite:      false,
      map:             tex,
      alphaMap:        tex,
      sizeAttenuation: true,
    });
  }

  function glowMat({
    size     = 1.1,
    opacity  = 0.18,
    blending = THREE.AdditiveBlending,
  } = {}) {
    const tex = _makeGlowTex();
    return new THREE.PointsMaterial({
      size,
      vertexColors:    true,
      transparent:     true,
      opacity,
      blending,
      depthWrite:      false,
      map:             tex,
      alphaMap:        tex,
      sizeAttenuation: true,
    });
  }

  /* ──────────────────────────────────────────────────────────────────────
     STANDARD BUILDING / GEOMETRY MATERIAL
     PBR params tuned for dark synthwave aesthetics.
  ────────────────────────────────────────────────────────────────────── */
  function buildingMat({
    color            = 0x060616,
    roughness        = 0.82,
    metalness        = 0.18,
    emissive         = 0x000000,
    emissiveIntensity = 0,
  } = {}) {
    return new THREE.MeshStandardMaterial({
      color: new THREE.Color(color),
      roughness,
      metalness,
      emissive: new THREE.Color(emissive),
      emissiveIntensity,
    });
  }

  function capMat({ color = 0x7c3fe4, intensity = 1.8 } = {}) {
    return new THREE.MeshStandardMaterial({
      color:             new THREE.Color(color),
      emissive:          new THREE.Color(color),
      emissiveIntensity: intensity,
      roughness:         0.2,
      metalness:         0.8,
    });
  }

  /* ──────────────────────────────────────────────────────────────────────
     LIGHTING PRESETS
  ────────────────────────────────────────────────────────────────────── */
  const lights = {

    // Dark space / particle scenes — minimal ambient, no shadow casters
    space(scene, { ambientColor = 0x050515, ambientIntensity = 0.4 } = {}) {
      const amb = new THREE.AmbientLight(ambientColor, ambientIntensity);
      scene.add(amb);
      return { amb };
    },

    // Synthwave city — hemisphere + moon + neon point lights
    neonCity(scene) {
      const hemi = new THREE.HemisphereLight(0x001133, 0x000508, 0.3);
      scene.add(hemi);

      const moon = new THREE.DirectionalLight(0x3355cc, 0.45);
      moon.position.set(-30, 60, 40);
      moon.castShadow = true;
      moon.shadow.camera.near    = 1;
      moon.shadow.camera.far     = 220;
      moon.shadow.camera.left    = moon.shadow.camera.bottom = -90;
      moon.shadow.camera.right   = moon.shadow.camera.top   = 90;
      moon.shadow.mapSize.width  = moon.shadow.mapSize.height = 2048;
      moon.shadow.bias           = -0.0002;
      scene.add(moon);

      const neons = [
        { pos: [ 0,  55,   0], color: 0x7c3fe4, int: 3.5, dist: 90 },
        { pos: [-55,  18, -35], color: 0xff0055, int: 2.0, dist: 65 },
        { pos: [ 55,  18,  35], color: 0x00aaff, int: 2.0, dist: 65 },
        { pos: [  0,   6,  65], color: 0x00ff88, int: 1.5, dist: 55 },
      ];
      for (const n of neons) {
        const pl = new THREE.PointLight(n.color, n.int, n.dist, 1.8);
        pl.position.set(...n.pos);
        scene.add(pl);
      }

      return { hemi, moon };
    },
  };

  /* ──────────────────────────────────────────────────────────────────────
     MATH HELPERS (exposed so vizes don't re-define them)
  ────────────────────────────────────────────────────────────────────── */
  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function rand(a, b) { return a + Math.random() * (b - a); }

  // ── Public API ─────────────────────────────────────────────────────────
  const api = {
    setupRenderer,
    softMat,
    glowMat,
    buildingMat,
    capMat,
    lights,
    lerp, clamp, rand,
    get glowTexture() { return _makeGlowTex(); },
  };

  console.log('[UHQ] Core initialised ✓  (ACES · sRGB · soft particles · bloom sim)');
  return api;
})();
