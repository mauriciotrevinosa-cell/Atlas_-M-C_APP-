/**
 * ARIA Jarvis Core — Pulsing Energy Nucleus
 * ============================================
 * ThreeJS-powered 3D energy orb that represents ARIA's consciousness.
 * Reacts physically to ARIA's state: idle, thinking, speaking, alert.
 *
 * States:
 *   IDLE     — slow breathe, soft blue-white glow
 *   THINKING — faster pulse, electric arc particles, golden glow
 *   SPEAKING — wave ripples, teal-cyan, voice-reactive
 *   ALERT    — red-orange pulsation for risk warnings
 *   ACTIVE   — bright white + particle burst for new signals
 *
 * Integrates with existing ARIA chat by hooking into:
 *   - Chat message send events (→ THINKING)
 *   - Chat message receive events (→ SPEAKING → IDLE)
 *   - Risk agent alerts (→ ALERT)
 *
 * @module AriaCore
 */

'use strict';

window.AriaCore = (() => {

  // ── State Machine ─────────────────────────────────────────────────────────
  const STATE = {
    IDLE:     'IDLE',
    THINKING: 'THINKING',
    SPEAKING: 'SPEAKING',
    ALERT:    'ALERT',
    ACTIVE:   'ACTIVE',
  };

  const STATE_CONFIG = {
    IDLE:     { pulseSpeed: 0.8,  intensity: 0.6,  colour: [0.2, 0.5, 1.0],   particles: 60,  particleSpeed: 0.003 },
    THINKING: { pulseSpeed: 2.5,  intensity: 1.2,  colour: [1.0, 0.8, 0.2],   particles: 120, particleSpeed: 0.008 },
    SPEAKING: { pulseSpeed: 1.8,  intensity: 0.9,  colour: [0.1, 0.9, 0.8],   particles: 90,  particleSpeed: 0.005 },
    ALERT:    { pulseSpeed: 3.5,  intensity: 1.5,  colour: [1.0, 0.3, 0.1],   particles: 150, particleSpeed: 0.012 },
    ACTIVE:   { pulseSpeed: 2.0,  intensity: 1.1,  colour: [0.5, 1.0, 0.5],   particles: 100, particleSpeed: 0.006 },
  };

  // ── Private vars ──────────────────────────────────────────────────────────
  let _scene, _camera, _renderer, _animId;
  let _coreMesh, _glowMesh, _ringMesh;
  let _particles, _particlePositions, _particleVelocities;
  let _currentState = STATE.IDLE;
  let _targetState  = STATE.IDLE;
  let _time         = 0;
  let _container    = null;
  let _initialized  = false;
  let _stateTimer   = null;

  // ── Easing ────────────────────────────────────────────────────────────────
  function lerp(a, b, t) { return a + (b - a) * Math.min(1, t); }
  function lerpVec3(a, b, t) { return a.map((v, i) => lerp(v, b[i], t)); }

  /* ═══════════════════════════════════════════════════════════
     INIT
  ═══════════════════════════════════════════════════════════ */
  function init(containerId = 'aria-core-mount') {
    if (_initialized) return;

    _container = document.getElementById(containerId);
    if (!_container || typeof THREE === 'undefined') {
      console.warn('[AriaCore] THREE.js not loaded or container not found');
      return;
    }

    const W = _container.offsetWidth  || 180;
    const H = _container.offsetHeight || 180;

    // Renderer
    _renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    _renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    _renderer.setSize(W, H);
    _renderer.setClearColor(0x000000, 0);
    _container.appendChild(_renderer.domElement);

    // Scene
    _scene  = new THREE.Scene();
    _camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 100);
    _camera.position.set(0, 0, 3.5);

    // Lighting
    const ambient = new THREE.AmbientLight(0x111133, 1.0);
    _scene.add(ambient);
    const pLight = new THREE.PointLight(0x4488ff, 3.0, 10);
    _scene.add(pLight);

    // Core sphere
    const coreGeo = new THREE.SphereGeometry(0.7, 64, 64);
    const coreMat = new THREE.MeshPhongMaterial({
      color: 0x2266ff,
      emissive: 0x001133,
      specular: 0x88ccff,
      shininess: 120,
      transparent: true,
      opacity: 0.9,
    });
    _coreMesh = new THREE.Mesh(coreGeo, coreMat);
    _scene.add(_coreMesh);

    // Outer glow sphere
    const glowGeo = new THREE.SphereGeometry(0.85, 32, 32);
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0x4488ff,
      transparent: true,
      opacity: 0.10,
      side: THREE.BackSide,
    });
    _glowMesh = new THREE.Mesh(glowGeo, glowMat);
    _scene.add(_glowMesh);

    // Equatorial ring
    const ringGeo = new THREE.TorusGeometry(0.95, 0.025, 16, 128);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x44aaff,
      transparent: true,
      opacity: 0.4,
    });
    _ringMesh = new THREE.Mesh(ringGeo, ringMat);
    _ringMesh.rotation.x = Math.PI / 2;
    _scene.add(_ringMesh);

    // Second ring (tilted)
    const ring2Geo = new THREE.TorusGeometry(0.92, 0.015, 16, 128);
    const ring2Mat = new THREE.MeshBasicMaterial({
      color: 0x88ddff,
      transparent: true,
      opacity: 0.25,
    });
    const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
    ring2.rotation.x = Math.PI / 3;
    ring2.rotation.z = Math.PI / 6;
    _scene.add(ring2);

    // Particle cloud
    _buildParticles(60);

    // Resize observer
    new ResizeObserver(() => {
      const w = _container.offsetWidth;
      const h = _container.offsetHeight;
      _camera.aspect = w / h;
      _camera.updateProjectionMatrix();
      _renderer.setSize(w, h);
    }).observe(_container);

    _animate();
    _initialized = true;

    // Hook into ARIA chat events
    _hookChatEvents();

    console.log('[AriaCore] Jarvis Core initialised');
  }

  /* ═══════════════════════════════════════════════════════════
     PARTICLE SYSTEM
  ═══════════════════════════════════════════════════════════ */
  function _buildParticles(count) {
    if (_particles) {
      _scene.remove(_particles);
      _particles.geometry.dispose();
      _particles.material.dispose();
    }

    _particlePositions  = new Float32Array(count * 3);
    _particleVelocities = [];

    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi   = Math.acos(2 * Math.random() - 1);
      const r     = 1.0 + Math.random() * 0.8;
      _particlePositions[i * 3]     = r * Math.sin(phi) * Math.cos(theta);
      _particlePositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      _particlePositions[i * 3 + 2] = r * Math.cos(phi);
      _particleVelocities.push({
        theta: (Math.random() - 0.5) * 0.02,
        phi:   (Math.random() - 0.5) * 0.01,
      });
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(_particlePositions, 3));

    const mat = new THREE.PointsMaterial({
      color: 0x88aaff,
      size: 0.04,
      transparent: true,
      opacity: 0.7,
      sizeAttenuation: true,
    });

    _particles = new THREE.Points(geo, mat);
    _scene.add(_particles);
  }

  /* ═══════════════════════════════════════════════════════════
     ANIMATION LOOP
  ═══════════════════════════════════════════════════════════ */
  function _animate() {
    _animId = requestAnimationFrame(_animate);
    _time += 0.016;

    const cfg    = STATE_CONFIG[_currentState];
    const pulse  = 0.5 + 0.5 * Math.sin(_time * cfg.pulseSpeed);
    const scale  = 1.0 + pulse * 0.08 * cfg.intensity;

    // Core pulse
    if (_coreMesh) {
      _coreMesh.scale.setScalar(scale);
      _coreMesh.rotation.y += 0.005;
      _coreMesh.rotation.x += 0.003;

      // Colour transition
      const tc = cfg.colour;
      const cc = _coreMesh.material.color;
      cc.r = lerp(cc.r, tc[0], 0.05);
      cc.g = lerp(cc.g, tc[1], 0.05);
      cc.b = lerp(cc.b, tc[2], 0.05);

      const em = _coreMesh.material.emissive;
      em.r = lerp(em.r, tc[0] * 0.2, 0.05);
      em.g = lerp(em.g, tc[1] * 0.2, 0.05);
      em.b = lerp(em.b, tc[2] * 0.2, 0.05);
    }

    // Glow pulse
    if (_glowMesh) {
      _glowMesh.scale.setScalar(scale * 1.05);
      _glowMesh.material.opacity = lerp(_glowMesh.material.opacity, 0.05 + pulse * 0.15 * cfg.intensity, 0.1);
      _glowMesh.material.color.set(new THREE.Color(...cfg.colour));
    }

    // Ring rotation
    if (_ringMesh) {
      _ringMesh.rotation.z += 0.004 * cfg.pulseSpeed;
      _ringMesh.material.opacity = lerp(_ringMesh.material.opacity, 0.3 + pulse * 0.3, 0.08);
    }

    // Particles
    if (_particles && _particlePositions) {
      const count = _particlePositions.length / 3;
      for (let i = 0; i < count; i++) {
        const vel = _particleVelocities[i];
        let x = _particlePositions[i * 3];
        let y = _particlePositions[i * 3 + 1];
        let z = _particlePositions[i * 3 + 2];

        // Orbit around core
        const len = Math.sqrt(x * x + y * y + z * z);
        const nx  = x / len;
        const nz  = z / len;
        x += -nz * vel.theta * cfg.particleSpeed * 10;
        z += nx  * vel.theta * cfg.particleSpeed * 10;
        y += vel.phi * cfg.particleSpeed * 5;

        // Re-normalise to sphere shell with drift
        const newLen = Math.sqrt(x * x + y * y + z * z);
        const targetR = 1.0 + 0.6 * pulse;
        x = (x / newLen) * targetR;
        y = (y / newLen) * targetR;
        z = (z / newLen) * targetR;

        _particlePositions[i * 3]     = x;
        _particlePositions[i * 3 + 1] = y;
        _particlePositions[i * 3 + 2] = z;
      }
      _particles.geometry.attributes.position.needsUpdate = true;
      _particles.material.color.set(new THREE.Color(...cfg.colour));
      _particles.material.size = 0.03 + pulse * 0.02;
      _particles.material.opacity = 0.4 + pulse * 0.4 * cfg.intensity;
    }

    // State transition
    if (_currentState !== _targetState) {
      _currentState = _targetState;
    }

    _renderer && _renderer.render(_scene, _camera);
  }

  /* ═══════════════════════════════════════════════════════════
     CHAT EVENT HOOKS
  ═══════════════════════════════════════════════════════════ */
  function _hookChatEvents() {
    // Hook input submit
    const sendBtn = document.getElementById('voice-btn');
    const input   = document.getElementById('input');

    if (input) {
      input.addEventListener('keydown', e => {
        if (e.key === 'Enter' && input.value.trim()) {
          setState(STATE.THINKING);
        }
      });
    }

    // Monitor chat mutations (new assistant messages → SPEAKING)
    const chat = document.getElementById('chat');
    if (chat) {
      new MutationObserver(mutations => {
        for (const m of mutations) {
          for (const node of m.addedNodes) {
            if (node.classList && node.classList.contains('assistant')) {
              setState(STATE.SPEAKING);
              // Auto-return to idle after speaking
              if (_stateTimer) clearTimeout(_stateTimer);
              _stateTimer = setTimeout(() => setState(STATE.IDLE), 4000);
            }
          }
        }
      }).observe(chat, { childList: true });
    }

    // Listen for custom risk alert events
    document.addEventListener('atlas:risk-alert', () => setState(STATE.ALERT));
    document.addEventListener('atlas:signal-active', () => {
      setState(STATE.ACTIVE);
      if (_stateTimer) clearTimeout(_stateTimer);
      _stateTimer = setTimeout(() => setState(STATE.IDLE), 3000);
    });
  }

  /* ═══════════════════════════════════════════════════════════
     PUBLIC API
  ═══════════════════════════════════════════════════════════ */
  function setState(newState) {
    if (!STATE_CONFIG[newState]) return;
    _targetState = newState;
    _currentState = newState;
  }

  function getState() { return _currentState; }

  function destroy() {
    if (_animId) cancelAnimationFrame(_animId);
    if (_renderer) { _renderer.dispose(); }
    _initialized = false;
  }

  // Boot when chat view opens (called from switchView)
  function boot(containerId) {
    if (_initialized) return;
    setTimeout(() => init(containerId), 100);
  }

  return { init, boot, setState, getState, destroy, STATE };

})();
