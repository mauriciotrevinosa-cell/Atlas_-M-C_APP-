/**
 * Atlas Viz Lab — Mau's Market Ontology Addon
 * Integrates "Black Hole" and "Galaxy" 3D simulations.
 */

(function () {
    if (!window.VizLab || !window.VizLab.registerViz) {
        console.error("VizLab not found or registerViz not exposed.");
        return;
    }

    // Helper inside the module
    function rand(min, max) { return min + Math.random() * (max - min); }

    /* ═══════════════════════════════════════════════════════
       BLACK HOLE (Mau's Market Ontology - Gravity/Liquidity)
    ═══════════════════════════════════════════════════════ */
    function vizBlackhole() {
        const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
        if (!container || typeof THREE === 'undefined') { return null; }

        const W = container.clientWidth || 800; // fallback if measurement fails
        const H = (container.clientHeight || 500) - 50;
        const COUNT = 25000;

        // Detect Ticker & ETF Status
        const ticker = window.__MMO_CURRENT_TICKER__ || 'SPY';
        window.__MMO_CURRENT_TICKER__ = null; // consume
        const isETF = ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VIX'].includes(ticker);

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x020205);
        const camera = new THREE.PerspectiveCamera(65, W / H, 0.1, 500);
        camera.position.set(0, 15, 30);
        camera.lookAt(0, 0, 0);

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(W, H);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        const mount = document.getElementById('viz-three-mount');
        if (mount) {
            mount.innerHTML = '';
            mount.appendChild(renderer.domElement);
        }

        // Add visual text overlay in the corner for context
        const contextText = document.createElement('div');
        contextText.style.position = 'absolute';
        contextText.style.bottom = '10px';
        contextText.style.left = '15px';
        contextText.style.color = '#7c3fe4';
        contextText.style.fontFamily = 'monospace';
        contextText.style.fontSize = '10px';
        contextText.style.zIndex = '100';
        contextText.textContent = isETF
            ? `ETF DETECTED (${ticker}): Rendering underlying micro-vortices`
            : `STOCK DETECTED (${ticker}): Unified entity core`;
        if (mount) mount.appendChild(contextText);

        const geo = new THREE.BufferGeometry();
        const pos = new Float32Array(COUNT * 3);
        const col = new Float32Array(COUNT * 3);
        const vels = new Float32Array(COUNT * 3);

        for (let i = 0; i < COUNT; i++) {
            const i3 = i * 3;
            // Spawn in a wide accretion disk
            const angle = Math.random() * Math.PI * 2;
            const radius = rand(15, 45);
            pos[i3] = Math.cos(angle) * radius;
            pos[i3 + 1] = rand(-0.5, 0.5);
            pos[i3 + 2] = Math.sin(angle) * radius;

            col[i3] = rand(0.8, 1.0); // R
            col[i3 + 1] = rand(0.3, 0.6); // G
            col[i3 + 2] = rand(0.0, 0.2); // B

            // Orbital velocity
            const v = Math.sqrt(100 / radius);
            vels[i3] = -Math.sin(angle) * v;
            vels[i3 + 1] = rand(-0.01, 0.01);
            vels[i3 + 2] = Math.cos(angle) * v;
        }

        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        geo.setAttribute('color', new THREE.BufferAttribute(col, 3));

        const mat = new THREE.PointsMaterial({
            size: 0.15,
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        const points = new THREE.Points(geo, mat);
        scene.add(points);

        // Define Black Holes (1 for Stock, multiple for ETF representing underlying companies)
        const blackholes = [];
        const bhGeo = new THREE.SphereGeometry(1, 32, 32); // base size
        const bhMat = new THREE.MeshBasicMaterial({ color: 0x000000 });
        const glowGeo = new THREE.SphereGeometry(1.2, 32, 32);
        const glowMat = new THREE.MeshBasicMaterial({
            color: 0xff3300, transparent: true, opacity: 0.15, blending: THREE.AdditiveBlending
        });

        if (isETF) {
            // Main central core + 4 smaller orbiting vortices
            blackholes.push({ mesh: new THREE.Mesh(bhGeo, bhMat), glow: new THREE.Mesh(glowGeo, glowMat), pos: new THREE.Vector3(0, 0, 0), mass: 60, scale: 4 });
            for (let v = 0; v < 4; v++) {
                const b = new THREE.Mesh(bhGeo, bhMat);
                const g = new THREE.Mesh(glowGeo, glowMat);
                const angle = (Math.PI * 2 / 4) * v;
                const dist = 12 + Math.random() * 4;
                blackholes.push({ mesh: b, glow: g, pos: new THREE.Vector3(Math.cos(angle) * dist, rand(-1, 1), Math.sin(angle) * dist), mass: 15, scale: 1.5, angle: angle, dist: dist, speed: rand(0.01, 0.02) });
            }
        } else {
            // Single massive core for a stock
            blackholes.push({ mesh: new THREE.Mesh(bhGeo, bhMat), glow: new THREE.Mesh(glowGeo, glowMat), pos: new THREE.Vector3(0, 0, 0), mass: 100, scale: 5 });
        }

        blackholes.forEach(bh => {
            bh.mesh.scale.set(bh.scale, bh.scale, bh.scale);
            bh.glow.scale.set(bh.scale, bh.scale, bh.scale);
            scene.add(bh.mesh);
            scene.add(bh.glow);
        });

        let animId = null;
        function animate() {
            animId = requestAnimationFrame(animate);

            // Update orbiting blackholes
            if (isETF) {
                for (let v = 1; v < blackholes.length; v++) {
                    const bh = blackholes[v];
                    bh.angle += bh.speed;
                    bh.pos.x = Math.cos(bh.angle) * bh.dist;
                    bh.pos.z = Math.sin(bh.angle) * bh.dist;
                    bh.mesh.position.copy(bh.pos);
                    bh.glow.position.copy(bh.pos);
                }
            }

            const positions = geo.attributes.position.array;
            const colors = geo.attributes.color.array;

            for (let i = 0; i < COUNT; i++) {
                const i3 = i * 3;
                let px = positions[i3];
                let py = positions[i3 + 1];
                let pz = positions[i3 + 2];

                let totalFx = 0, totalFy = 0, totalFz = 0;
                let minDist = 9999;

                // Gravity pull towards all black holes
                blackholes.forEach(bh => {
                    const dx = bh.pos.x - px;
                    const dy = bh.pos.y - py;
                    const dz = bh.pos.z - pz;
                    const distSq = dx * dx + dy * dy + dz * dz;
                    const dist = Math.sqrt(distSq);

                    if (dist < minDist) minDist = dist;

                    const force = bh.mass / distSq;
                    totalFx += (dx / dist) * force;
                    totalFy += (dy / dist) * force;
                    totalFz += (dz / dist) * force;
                });

                vels[i3] += totalFx;
                vels[i3 + 1] += totalFy;
                vels[i3 + 2] += totalFz;

                // General relativity precession / drag
                vels[i3] *= 0.995;
                vels[i3 + 1] *= 0.99;
                vels[i3 + 2] *= 0.995;

                positions[i3] += vels[i3];
                positions[i3 + 1] += vels[i3 + 1];
                positions[i3 + 2] += vels[i3 + 2];

                // Color shifts to intense blue/white near EVENT HORIZONS
                if (minDist < 8) {
                    colors[i3] = lerp(colors[i3], 0.1, 0.05);
                    colors[i3 + 1] = lerp(colors[i3 + 1], 0.5, 0.05);
                    colors[i3 + 2] = lerp(colors[i3 + 2], 1.0, 0.05);
                }

                // If swallowed by any black hole (dynamic horizon check)
                let swallowed = false;
                for (let v = 0; v < blackholes.length; v++) {
                    const bh = blackholes[v];
                    const dSq = (bh.pos.x - px) ** 2 + (bh.pos.y - py) ** 2 + (bh.pos.z - pz) ** 2;
                    if (dSq < (bh.scale * 1.1) ** 2) { swallowed = true; break; }
                }

                if (swallowed) {
                    const angle = Math.random() * Math.PI * 2;
                    const radius = rand(40, 50);
                    positions[i3] = Math.cos(angle) * radius;
                    positions[i3 + 1] = rand(-1, 1);
                    positions[i3 + 2] = Math.sin(angle) * radius;

                    colors[i3] = rand(0.8, 1.0);
                    colors[i3 + 1] = rand(0.2, 0.4);
                    colors[i3 + 2] = 0.0;

                    const v = Math.sqrt(100 / radius);
                    vels[i3] = -Math.sin(angle) * v;
                    vels[i3 + 1] = rand(-0.01, 0.01);
                    vels[i3 + 2] = Math.cos(angle) * v;
                }
            }

            geo.attributes.position.needsUpdate = true;
            geo.attributes.color.needsUpdate = true;

            points.rotation.y += 0.002;
            renderer.render(scene, camera);
        }
        animate();

        return () => {
            cancelAnimationFrame(animId);
            renderer.dispose();
        };
    }

    function lerp(a, b, t) { return a + (b - a) * t; }

    /* ═══════════════════════════════════════════════════════
       GALAXY 3D (Asset Clusters & Correlation Orbits)
    ═══════════════════════════════════════════════════════ */
    function vizGalaxy3D() {
        const container = document.getElementById('viz-canvas-container') || document.getElementById('viz-overlay');
        if (!container || typeof THREE === 'undefined') { return null; }

        const W = container.clientWidth || 800; // fallback if measurement fails
        const H = (container.clientHeight || 500) - 50;
        const COUNT = 30000;

        // Detect Ticker & ETF Status 
        // (Use global flag set by MMO or fallback to SPY)
        const ticker = window.__MMO_CURRENT_TICKER__ || 'SPY';
        window.__MMO_CURRENT_TICKER__ = null; // consume
        const isETF = ['SPY', 'QQQ', 'DIA', 'IWM', 'VTI', 'VIX'].includes(ticker);

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x060814);
        const camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000);
        camera.position.set(0, 40, 60);
        camera.lookAt(0, 0, 0);

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.setSize(W, H);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        const mount = document.getElementById('viz-three-mount');
        if (mount) {
            mount.innerHTML = '';
            mount.appendChild(renderer.domElement);
        }

        // Add contextual indicator text
        const contextText = document.createElement('div');
        contextText.style.position = 'absolute';
        contextText.style.bottom = '10px';
        contextText.style.left = '15px';
        contextText.style.color = '#7c3fe4';
        contextText.style.fontFamily = 'monospace';
        contextText.style.fontSize = '10px';
        contextText.style.zIndex = '100';
        contextText.textContent = isETF
            ? `ETF (${ticker}): Multi-sector correlation clusters`
            : `STOCK (${ticker}): Single focused entity orbital`;
        if (mount) mount.appendChild(contextText);

        const geo = new THREE.BufferGeometry();
        const pos = new Float32Array(COUNT * 3);
        const col = new Float32Array(COUNT * 3);
        const params = new Float32Array(COUNT * 3); // angle, radius, speed

        // For ETFs we want many spiral arms (sectors), inside a stock it's tighter (just its divisions, maybe 2 arms)
        const ARMS = isETF ? 8 : 2;

        for (let i = 0; i < COUNT; i++) {
            const i3 = i * 3;
            // Spread of radius depends on if it's an ETF containing everything or a stock representing one specific mass
            const radius = isETF ? rand(4, 50) : rand(1, 40);

            const armOffset = (i % ARMS) * (Math.PI * 2 / ARMS);

            // Tightness of the spiral arm wrap
            const spiralTightness = isETF ? 0.3 : 1.2;
            const angle = armOffset + (radius * spiralTightness) + rand(-0.4, 0.4);

            params[i3] = angle;
            params[i3 + 1] = radius;

            // Speed relies heavily on radius. In an ETF, outer edges move very slowly. For a single stock, it's more cohesive
            const speedFact = isETF ? 30 : 50;
            params[i3 + 2] = rand(0.001, 0.005) * (speedFact / (radius + 5));

            pos[i3] = Math.cos(angle) * radius;
            // Thicker in center, thinner edges
            pos[i3 + 1] = (rand(-1, 1) * (isETF ? 20 : 8)) / (radius + 2);
            pos[i3 + 2] = Math.sin(angle) * radius;

            // Colors based on whether it is an ETF (Rainbow/diverse) or Stock (Focused corporate/technical colors)
            const t = Math.min(1, radius / 45);
            if (isETF) {
                // Different arms = different colors for different sectors
                const armColor = i % ARMS;
                if (armColor % 2 == 0) {
                    col[i3] = lerp(1.0, 0.2, t);
                    col[i3 + 1] = lerp(0.8, 0.3, t);
                    col[i3 + 2] = lerp(0.5, 1.0, t);
                } else {
                    col[i3] = lerp(0.2, 0.1, t);
                    col[i3 + 1] = lerp(1.0, 0.5, t);
                    col[i3 + 2] = lerp(0.4, 0.1, t);
                }
            } else {
                col[i3] = lerp(0.2, 0.1, t); // Stock color (Cyans/Blues)
                col[i3 + 1] = lerp(0.8, 0.3, t);
                col[i3 + 2] = lerp(1.0, 0.8, t);
            }
        }

        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        geo.setAttribute('color', new THREE.BufferAttribute(col, 3));

        const mat = new THREE.PointsMaterial({
            size: isETF ? 0.12 : 0.18, // slightly larger particles for individual stock to represent density
            vertexColors: true,
            transparent: true,
            opacity: 0.8,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });
        const points = new THREE.Points(geo, mat);
        scene.add(points);

        let animId = null;
        function animate() {
            animId = requestAnimationFrame(animate);

            const positions = geo.attributes.position.array;
            for (let i = 0; i < COUNT; i++) {
                const i3 = i * 3;
                params[i3] += params[i3 + 2]; // angle += speed
                const angle = params[i3];
                const radius = params[i3 + 1];

                positions[i3] = Math.cos(angle) * radius;
                positions[i3 + 2] = Math.sin(angle) * radius;
                // Keep Y the same
            }
            geo.attributes.position.needsUpdate = true;

            points.rotation.y += 0.001;
            points.rotation.x = -0.2;
            renderer.render(scene, camera);
        }
        animate();

        return () => {
            cancelAnimationFrame(animId);
            renderer.dispose();
        };
    }

    // Register with VizLab
    window.VizLab.registerViz(
        'blackhole',
        { cat: 'art', label: 'Liquidity Black Hole', icon: '🌌', api: null, desc: '3D Event horizon representing systemic liquidity traps and phase collapse.' },
        true, // creating its own renderer 
        vizBlackhole
    );

    window.VizLab.registerViz(
        'galaxy3d',
        { cat: 'art', label: 'Market Galaxy 3D', icon: '🌠', api: null, desc: 'Asset correlation clusters orbiting a central fundamental core.' },
        true,
        vizGalaxy3D
    );

})();
