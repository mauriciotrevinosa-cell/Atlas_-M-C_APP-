/**
 * Finance Module (Portfolio + 3D Lab)
 * Atlas v5.0 â€” Upgraded 3D with BufferGeometry, vertex coloring & orbit controls
 */

const portfolioStorageKey = 'atlas_portfolio';

// ==================== 3D STATE ====================
let threeRenderer = null;
let threeScene = null;
let threeCamera = null;
let threeAnimationId = null;
let simState = null;

const orbit = {
    isDragging: false,
    prev: { x: 0, y: 0 },
    spherical: { radius: 45, theta: Math.PI / 4, phi: Math.PI / 3 },
    autoRotate: true,
    autoSpeed: 0.003,
    resumeTimer: null
};

// ==================== PORTFOLIO STORAGE ====================

function getLocalPortfolio() {
    try {
        const stored = localStorage.getItem(portfolioStorageKey);
        if (!stored) return { total_equity: 0, positions: [] };
        const parsed = JSON.parse(stored);
        if (!parsed || !Array.isArray(parsed.positions)) {
            return { total_equity: 0, positions: [] };
        }
        return parsed;
    } catch {
        return { total_equity: 0, positions: [] };
    }
}

function saveLocalPortfolio(portfolio) {
    localStorage.setItem(portfolioStorageKey, JSON.stringify(portfolio));
}

function buildPortfolioSummary(positions) {
    const enriched = positions.map(pos => {
        const pnl = (pos.current_price - pos.avg_price) * pos.qty;
        const cost = pos.avg_price * pos.qty;
        const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0;
        return { ...pos, pnl, pnl_pct: pnlPct };
    });
    const totalEquity = enriched.reduce((sum, pos) => sum + pos.current_price * pos.qty, 0);
    return { total_equity: totalEquity, positions: enriched };
}

// ==================== PRICE FETCHING ====================

function resolveApiBaseUrl() {
    if (typeof CONFIG !== 'undefined' && CONFIG.serverUrl) return CONFIG.serverUrl;
    if (typeof window !== 'undefined' && window.location && window.location.origin && window.location.origin !== 'null') {
        return window.location.origin;
    }
    return 'http://localhost:8000';
}

async function fetchTickerPrice(ticker) {
    const baseUrl = resolveApiBaseUrl();

    // 1) Try local ARIA server
    try {
        let response = await fetch(`${baseUrl}/api/quote/${encodeURIComponent(ticker)}`);
        if (!response.ok) {
            response = await fetch(`${baseUrl}/api/market_data/${encodeURIComponent(ticker)}`);
        }
        if (response.ok) {
            const data = await response.json();
            if (data && typeof data.price === 'number' && Number.isFinite(data.price)) {
                localStorage.setItem(`atlas_last_price_${ticker}`, String(data.price));
                return data.price;
            }
        }
    } catch (err) {
        console.warn('Server price fetch failed, trying Yahoo...', err);
    }

    // 2) Yahoo Finance direct
    try {
        const yahooRes = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?interval=1d&range=1d`);
        if (yahooRes.ok) {
            const yahooData = await yahooRes.json();
            const livePrice = yahooData.chart.result[0].meta.regularMarketPrice;
            if (livePrice && Number.isFinite(livePrice) && livePrice > 0) {
                localStorage.setItem(`atlas_last_price_${ticker}`, String(livePrice));
                return livePrice;
            }
        }
    } catch (err2) {
        console.warn('Yahoo Finance also failed.', err2);
    }

    // 3) Cached price
    const cached = localStorage.getItem(`atlas_last_price_${ticker}`);
    if (cached && !Number.isNaN(Number(cached))) return Number(cached);
    return null;
}

// ==================== PORTFOLIO TABLE ====================

async function updatePortfolio() {
    try {
        let apiData = null;
        try {
            const response = await fetch('/api/portfolio');
            if (response.ok) apiData = await response.json();
        } catch (e) {
            console.warn("Portfolio API unavailable, using local.", e);
        }

        const local = getLocalPortfolio();
        const localPositions = Array.isArray(local.positions) ? local.positions : [];
        const apiPositions = apiData && Array.isArray(apiData.positions) ? apiData.positions : [];
        const apiHasActiveSession = Boolean(
            apiData &&
            (apiData.has_active_session === true ||
                (typeof apiData.has_active_session === 'undefined' && apiPositions.length > 0))
        );

        let uploadedPositions = [];
        try {
            const uploadedRes = await fetch('/api/portfolio/uploaded');
            if (uploadedRes.ok) {
                const uploadedData = await uploadedRes.json();
                if (uploadedData && Array.isArray(uploadedData.positions)) {
                    uploadedPositions = uploadedData.positions;
                }
            }
        } catch (e) {
            // ignore uploaded portfolio errors and fall back to local
        }

        // Backend portfolio is only authoritative when an active scenario session has positions.
        // Otherwise prefer uploaded package, then local seed.
        const sourcePositions =
            (apiHasActiveSession && apiPositions.length > 0) ? apiPositions
                : (uploadedPositions.length > 0 ? uploadedPositions : localPositions);

        const data = buildPortfolioSummary(sourcePositions);

        const totalEquityEl = document.getElementById('total-equity');
        if (totalEquityEl) totalEquityEl.textContent = formatCurrency(data.total_equity || 0);

        const tbody = document.getElementById('portfolio-table-body');
        if (!tbody) return;
        tbody.innerHTML = '';

        if (!data.positions || data.positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="padding:20px; text-align:center; color:#555;">No active positions</td></tr>';
            return;
        }

        data.positions.forEach(pos => {
            const safeQty = Number(pos.qty) || 0;
            const safeAvg = Number(pos.avg_price) || 0;
            const safeCurrent = Number(pos.current_price) || 0;
            const safePnl = Number(pos.pnl) || 0;
            const safePnlPct = Number(pos.pnl_pct) || 0;
            const mktValue = safeCurrent * safeQty;
            const pnlColor = safePnl >= 0 ? '#4caf50' : '#e74c3c';
            tbody.innerHTML += `
                <tr style="border-bottom:1px solid #222;">
                    <td style="padding:10px 12px; font-weight:bold;">${pos.symbol}</td>
                    <td style="padding:10px 8px; font-size:12px;">${safeQty.toFixed(4)}</td>
                    <td style="padding:10px 8px;">$${safeAvg.toFixed(2)}</td>
                    <td style="padding:10px 8px;">$${safeCurrent.toFixed(2)}</td>
                    <td style="padding:10px 8px;">$${mktValue.toFixed(2)}</td>
                    <td style="padding:10px 8px; color:${pnlColor}; font-weight:bold;">
                        ${safePnl >= 0 ? '+' : ''}$${safePnl.toFixed(2)} (${safePnlPct.toFixed(1)}%)
                    </td>
                </tr>`;
        });
    } catch (err) {
        console.error('Failed to update portfolio UI:', err);
    }
}

// ==================== 3D: COLOR SCHEMES ====================

function colorToHSL(t, scheme) {
    // t = normalized value 0..1
    switch (scheme) {
        case 'magma':
            // Blue(low) -> Purple -> Orange -> Yellow(high)
            return { h: 0.75 - t * 0.75, s: 0.85 + t * 0.15, l: 0.25 + t * 0.45 };
        case 'coolwarm':
            // Blue(negative) -> White(neutral) -> Red(positive)
            if (t < 0.5) return { h: 0.6, s: 0.8, l: 0.3 + (0.5 - t) * 0.8 };
            return { h: 0.0, s: 0.8, l: 0.3 + (t - 0.5) * 0.8 };
        case 'risk':
            // Yellow(low) -> Orange -> Deep red(high)
            return { h: 0.12 - t * 0.12, s: 1.0, l: 0.6 - t * 0.3 };
        case 'RdYlGn':
            // Red(loss) -> Yellow(neutral) -> Green(profit)
            return { h: t * 0.33, s: 0.8, l: 0.4 + Math.abs(t - 0.5) * 0.3 };
        default:
            return { h: 0.55, s: 0.7, l: 0.5 };
    }
}

// ==================== 3D: DATA DERIVATION ====================

function enrichPositions() {
    const local = getLocalPortfolio();
    const positions = Array.isArray(local.positions) ? local.positions : [];
    const enriched = positions.map(pos => {
        const cp = pos.current_price || pos.avg_price;
        const pnl = (cp - pos.avg_price) * pos.qty;
        const cost = pos.avg_price * pos.qty;
        const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0;
        const spread = pos.avg_price > 0 ? Math.abs(cp - pos.avg_price) / pos.avg_price : 0;
        return { ...pos, current_price: cp, pnl, pnl_pct: pnlPct, spread };
    });
    const totalEquity = enriched.reduce((sum, p) => sum + p.current_price * p.qty, 0);
    return { positions: enriched, totalEquity };
}

function getDemoPortfolioContext() {
    const demoPositions = [
        { symbol: 'SPY', qty: 6, avg_price: 620, current_price: 692.49 },
        { symbol: 'NVDA', qty: 10, avg_price: 160, current_price: 190.36 },
        { symbol: 'MSFT', qty: 4, avg_price: 430, current_price: 404.75 }
    ];
    const summary = buildPortfolioSummary(demoPositions);
    return { positions: summary.positions, totalEquity: summary.total_equity, isDemo: true };
}

function getRenderablePortfolioContext() {
    const context = enrichPositions();
    if (context.positions.length > 0) {
        return { ...context, isDemo: false };
    }
    return getDemoPortfolioContext();
}

function deriveVolSurface(positions, totalEquity) {
    const GRID = 24;
    const grid = [];
    const n = positions.length;

    // Each position contributes a "volatility column"
    // Spread = base IV, with term structure decay across Y-axis
    for (let i = 0; i < GRID; i++) {
        const row = [];
        const expiryFactor = i / (GRID - 1); // 0 = near-term, 1 = long-term
        for (let j = 0; j < GRID; j++) {
            const strikePos = j / (GRID - 1); // 0..1 across strike range

            // Find nearest position and interpolate
            const posIdx = Math.min(n - 1, Math.floor(strikePos * n));
            const nextIdx = Math.min(n - 1, posIdx + 1);
            const blend = (strikePos * n) - posIdx;

            const spreadA = positions[posIdx].spread;
            const spreadB = positions[nextIdx].spread;
            const baseIV = 0.15 + (spreadA * (1 - blend) + spreadB * blend) * 2.5;

            // Term structure: near-term vol is higher
            const termDecay = 1 + 0.4 * Math.exp(-expiryFactor * 3);

            // Smile: higher vol at extremes of strike range
            const moneyness = (strikePos - 0.5);
            const smile = 0.08 * moneyness * moneyness;

            // Small position-specific texture
            const texture = 0.02 * Math.sin(j * 0.8 + i * 0.5 + posIdx);

            row.push((baseIV * termDecay + smile + texture) * 15);
        }
        grid.push(row);
    }
    return grid;
}

function deriveCorrelation(positions) {
    const n = positions.length;
    const GRID = Math.max(8, n);
    const grid = [];

    // Build NxN pseudo-correlation from P&L co-directionality
    const pnlPcts = positions.map(p => p.pnl_pct);
    const maxSpread = Math.max(1, ...pnlPcts.map(Math.abs)) * 2;

    for (let i = 0; i < GRID; i++) {
        const row = [];
        const pi = Math.min(n - 1, Math.floor(i / GRID * n));
        for (let j = 0; j < GRID; j++) {
            const pj = Math.min(n - 1, Math.floor(j / GRID * n));

            if (pi === pj) {
                row.push(8); // Self-correlation = peak
            } else {
                const diff = Math.abs(pnlPcts[pi] - pnlPcts[pj]);
                const sameSign = (pnlPcts[pi] >= 0) === (pnlPcts[pj] >= 0);
                let corr = (1 - diff / maxSpread);
                if (!sameSign) corr = -corr * 0.8;

                // Add subtle texture
                corr += 0.05 * Math.sin(i * 1.2 + j * 0.7);
                row.push(corr * 8);
            }
        }
        grid.push(row);
    }
    return grid;
}

function deriveRisk(positions, totalEquity) {
    const GRID = 24;
    const grid = [];
    const te = totalEquity || 1;

    // Allocation weights per position
    const weights = positions.map(p => (p.current_price * p.qty) / te);

    for (let i = 0; i < GRID; i++) {
        const row = [];
        const marketReturn = -0.10 + (i / (GRID - 1)) * 0.20; // -10% to +10%
        for (let j = 0; j < GRID; j++) {
            const allocShift = j / (GRID - 1); // 0 = diversified, 1 = concentrated

            let var_val = 0;
            for (let k = 0; k < positions.length; k++) {
                // Concentration factor: shift weight toward position k as allocShift increases
                const nearestK = Math.floor(allocShift * positions.length);
                const concBoost = (k === nearestK) ? 1 + allocShift * 2 : 1 - allocShift * 0.3;
                const effectiveWeight = Math.max(0, weights[k] * concBoost);

                // Loss exposure = weight * |return| * equity
                var_val += effectiveWeight * Math.abs(marketReturn) * te * 0.01;
            }

            // Add volatility texture
            var_val += 0.5 * Math.sin(i * 0.4 + j * 0.3);
            row.push(Math.max(0, var_val));
        }
        grid.push(row);
    }
    return grid;
}

function deriveSimSurface(positions, totalEquity, sim) {
    const GRID = 24;
    const grid = [];
    const vol = sim.volatility;
    const trend = sim.trend;

    for (let i = 0; i < GRID; i++) {
        const row = [];
        for (let j = 0; j < GRID; j++) {
            const x = (j / (GRID - 1)) - 0.5;
            const y = (i / (GRID - 1)) - 0.5;

            // Base surface from portfolio P&L distribution
            let z = 0;
            for (let k = 0; k < positions.length; k++) {
                const posX = (k / Math.max(1, positions.length - 1)) - 0.5;
                const dist = Math.sqrt((x - posX) ** 2 + y * y);
                const peak = positions[k].pnl_pct / 20;
                z += peak * Math.exp(-dist * dist * 8);
            }

            // Apply simulation modifiers
            z *= vol;
            z += trend * 3;

            // Volatility adds surface roughness
            z += vol * 0.8 * Math.sin(j * 0.6 + sim.day * 0.3) * Math.cos(i * 0.5 + sim.day * 0.2);

            row.push(z * 5);
        }
        grid.push(row);
    }
    return grid;
}

// ==================== 3D: GEOMETRY BUILDER ====================

function buildDataSurface(grid, colorScheme) {
    const rows = grid.length;
    const cols = grid[0].length;

    // Find z range for normalization
    let zMin = Infinity, zMax = -Infinity;
    for (let i = 0; i < rows; i++) {
        for (let j = 0; j < cols; j++) {
            zMin = Math.min(zMin, grid[i][j]);
            zMax = Math.max(zMax, grid[i][j]);
        }
    }
    const zRange = (zMax - zMin) || 1;

    const spacing = 24 / Math.max(rows, cols);
    const heightScale = 12 / zRange;
    const vertices = new Float32Array(rows * cols * 3);
    const colors = new Float32Array(rows * cols * 3);
    const tmpColor = new THREE.Color();

    for (let i = 0; i < rows; i++) {
        for (let j = 0; j < cols; j++) {
            const idx = (i * cols + j) * 3;
            vertices[idx] = (j - cols / 2) * spacing;     // X
            vertices[idx + 1] = (grid[i][j] - zMin) * heightScale; // Y (height)
            vertices[idx + 2] = (i - rows / 2) * spacing;     // Z

            const t = (grid[i][j] - zMin) / zRange;
            const hsl = colorToHSL(t, colorScheme);
            tmpColor.setHSL(hsl.h, hsl.s, hsl.l);
            colors[idx] = tmpColor.r;
            colors[idx + 1] = tmpColor.g;
            colors[idx + 2] = tmpColor.b;
        }
    }

    // Quad-to-triangle tessellation
    const indices = [];
    for (let i = 0; i < rows - 1; i++) {
        for (let j = 0; j < cols - 1; j++) {
            const a = i * cols + j;
            const b = a + 1;
            const c = a + cols;
            const d = c + 1;
            indices.push(a, b, c);
            indices.push(b, d, c);
        }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();

    return geometry;
}

// ==================== 3D: SCENE & RENDERING ====================

function disposeThreeScene() {
    if (threeAnimationId) {
        cancelAnimationFrame(threeAnimationId);
        threeAnimationId = null;
    }
    if (threeScene) {
        threeScene.traverse(obj => {
            if (obj.geometry) obj.geometry.dispose();
            if (obj.material) {
                if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
                else obj.material.dispose();
            }
        });
    }
    if (threeRenderer) {
        threeRenderer.dispose();
        threeRenderer.forceContextLoss();
        threeRenderer.domElement.remove();
    }
    threeRenderer = null;
    threeScene = null;
    threeCamera = null;
}

function createThreeScene(container) {
    disposeThreeScene();

    const width = container.clientWidth;
    const height = container.clientHeight;

    threeScene = new THREE.Scene();
    threeScene.background = new THREE.Color('#0b0f1a');

    threeCamera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);

    // 3-light system (adapted from interactive_3d.py)
    threeScene.add(new THREE.AmbientLight(0x404040, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(10, 20, 15);
    threeScene.add(dirLight);
    const pointLight = new THREE.PointLight(0x00ffff, 0.4, 200);
    pointLight.position.set(0, 25, 0);
    threeScene.add(pointLight);

    // Dark grid
    threeScene.add(new THREE.GridHelper(40, 20, 0x1f2a44, 0x141928));

    threeRenderer = new THREE.WebGLRenderer({ antialias: true });
    threeRenderer.setSize(width, height);
    threeRenderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    container.appendChild(threeRenderer.domElement);

    // Reset orbit state
    orbit.spherical = { radius: 45, theta: Math.PI / 4, phi: Math.PI / 3 };
    orbit.autoRotate = true;
    orbit.isDragging = false;
    updateCameraFromSpherical();

    // Attach orbit controls
    setupOrbitControls(threeRenderer.domElement);
}

// ==================== 3D: ORBIT CONTROLS ====================

function updateCameraFromSpherical() {
    if (!threeCamera) return;
    const s = orbit.spherical;
    threeCamera.position.x = s.radius * Math.sin(s.phi) * Math.cos(s.theta);
    threeCamera.position.y = s.radius * Math.cos(s.phi);
    threeCamera.position.z = s.radius * Math.sin(s.phi) * Math.sin(s.theta);
    threeCamera.lookAt(0, 4, 0);
}

function setupOrbitControls(canvas) {
    canvas.style.cursor = 'grab';

    canvas.addEventListener('mousedown', e => {
        orbit.isDragging = true;
        orbit.autoRotate = false;
        orbit.prev = { x: e.clientX, y: e.clientY };
        canvas.style.cursor = 'grabbing';
        if (orbit.resumeTimer) clearTimeout(orbit.resumeTimer);
    });

    canvas.addEventListener('mousemove', e => {
        if (!orbit.isDragging) return;
        const dx = e.clientX - orbit.prev.x;
        const dy = e.clientY - orbit.prev.y;
        orbit.spherical.theta += dx * 0.01;
        orbit.spherical.phi = Math.max(0.15, Math.min(Math.PI - 0.15,
            orbit.spherical.phi + dy * 0.01));
        orbit.prev = { x: e.clientX, y: e.clientY };
        updateCameraFromSpherical();
    });

    const onMouseUp = () => {
        orbit.isDragging = false;
        canvas.style.cursor = 'grab';
        orbit.resumeTimer = setTimeout(() => {
            if (!orbit.isDragging) orbit.autoRotate = true;
        }, 3000);
    };
    canvas.addEventListener('mouseup', onMouseUp);
    canvas.addEventListener('mouseleave', onMouseUp);

    canvas.addEventListener('wheel', e => {
        e.preventDefault();
        orbit.spherical.radius = Math.max(15, Math.min(120,
            orbit.spherical.radius + e.deltaY * 0.05));
        updateCameraFromSpherical();
    }, { passive: false });

    // Touch support
    let touchPrev = null;
    canvas.addEventListener('touchstart', e => {
        if (e.touches.length === 1) {
            touchPrev = { x: e.touches[0].clientX, y: e.touches[0].clientY };
            orbit.autoRotate = false;
        }
    });
    canvas.addEventListener('touchmove', e => {
        if (!touchPrev || e.touches.length !== 1) return;
        e.preventDefault();
        const dx = e.touches[0].clientX - touchPrev.x;
        const dy = e.touches[0].clientY - touchPrev.y;
        orbit.spherical.theta += dx * 0.01;
        orbit.spherical.phi = Math.max(0.15, Math.min(Math.PI - 0.15,
            orbit.spherical.phi + dy * 0.01));
        touchPrev = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        updateCameraFromSpherical();
    }, { passive: false });
    canvas.addEventListener('touchend', () => {
        touchPrev = null;
        setTimeout(() => { orbit.autoRotate = true; }, 3000);
    });
}

// ==================== 3D: RENDER PIPELINE ====================

function renderScene(geometry) {
    if (!threeScene || !threeRenderer || !threeCamera) return;

    // Remove previous meshes (keep lights + grid)
    const toRemove = [];
    threeScene.traverse(obj => {
        if (obj.isMesh || obj.isLineSegments) toRemove.push(obj);
    });
    toRemove.forEach(obj => {
        obj.geometry?.dispose();
        obj.material?.dispose();
        threeScene.remove(obj);
    });

    // Surface mesh with Phong + vertex colors
    const material = new THREE.MeshPhongMaterial({
        vertexColors: true,
        side: THREE.DoubleSide,
        shininess: 50,
        transparent: true,
        opacity: 0.85
    });
    const mesh = new THREE.Mesh(geometry, material);
    threeScene.add(mesh);

    // Wireframe overlay
    const wireGeo = new THREE.WireframeGeometry(geometry);
    const wireMat = new THREE.LineBasicMaterial({
        color: 0x556677,
        opacity: 0.2,
        transparent: true
    });
    threeScene.add(new THREE.LineSegments(wireGeo, wireMat));

    // Animation loop: auto-rotate + render
    if (threeAnimationId) cancelAnimationFrame(threeAnimationId);
    const animate = () => {
        if (orbit.autoRotate) {
            orbit.spherical.theta += orbit.autoSpeed;
            updateCameraFromSpherical();
        }
        threeRenderer.render(threeScene, threeCamera);
        threeAnimationId = requestAnimationFrame(animate);
    };
    animate();
}

// ==================== 3D: LEGEND ====================

function updateLegend(type, legendId = '3d-legend') {
    const legend = document.getElementById(legendId);
    if (!legend) return;
    legend.style.display = 'block';
    const labels = {
        vol_surface: 'Blue = Low IV | Purple = Medium | Yellow = High IV  â€”  Shaped by position price spreads',
        correlation: 'Blue = Negative Corr | White = Neutral | Red = Positive  â€”  Based on P&L co-direction',
        risk: 'Yellow = Low Risk | Orange = Medium | Red = High Risk  â€”  Allocation vs market return',
        sim: 'Red = Loss Region | Yellow = Neutral | Green = Profit  â€”  Evolves with decisions'
    };
    legend.textContent = labels[type] || '';
}

function hideCorrelationPanel(panelId = 'correlation-panel') {
    const panel = document.getElementById(panelId);
    if (panel) panel.style.display = 'none';
}

function buildPortfolioCorrelationMatrix(positions) {
    const labels = positions.map(p => p.symbol || '?');
    const n = labels.length;
    const matrix = [];
    if (n === 0) return { labels, matrix };

    const values = positions.map(p => (Number(p.current_price) || 0) * (Number(p.qty) || 0));
    const totalValue = values.reduce((sum, v) => sum + v, 0) || 1;
    const pnlPcts = positions.map(p => Number(p.pnl_pct) || 0);
    const spreads = positions.map(p => Number(p.spread) || 0);
    const weights = values.map(v => v / totalValue);

    const maxPnlDiff = Math.max(1, Math.max(...pnlPcts) - Math.min(...pnlPcts));
    const maxSpreadDiff = Math.max(0.0001, Math.max(...spreads) - Math.min(...spreads));
    const maxWeightDiff = Math.max(0.0001, Math.max(...weights) - Math.min(...weights));

    for (let i = 0; i < n; i++) {
        const row = [];
        for (let j = 0; j < n; j++) {
            if (i === j) {
                row.push(1);
                continue;
            }
            const pnlSimilarity = 1 - Math.abs(pnlPcts[i] - pnlPcts[j]) / maxPnlDiff;
            const spreadSimilarity = 1 - Math.abs(spreads[i] - spreads[j]) / maxSpreadDiff;
            const weightSimilarity = 1 - Math.abs(weights[i] - weights[j]) / maxWeightDiff;
            const sameDirection = (pnlPcts[i] >= 0) === (pnlPcts[j] >= 0);

            let corr = (0.65 * pnlSimilarity + 0.25 * spreadSimilarity + 0.10 * weightSimilarity);
            if (!sameDirection) corr *= -0.85;

            row.push(Math.max(-1, Math.min(1, corr)));
        }
        matrix.push(row);
    }
    return { labels, matrix };
}

function correlationColor(value) {
    const v = Math.max(-1, Math.min(1, value));
    if (v >= 0) {
        const light = 62 - v * 26;
        return `hsl(7, 80%, ${light}%)`;
    }
    const light = 62 - Math.abs(v) * 22;
    return `hsl(212, 75%, ${light}%)`;
}

function renderCorrelationHeatmap(positions, panelId = 'correlation-panel', canvasId = 'correlation-canvas') {
    const panel = document.getElementById(panelId);
    const canvas = document.getElementById(canvasId);
    if (!panel || !canvas) return;

    if (!positions || positions.length < 2) {
        panel.style.display = 'none';
        return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    panel.style.display = 'block';
    const viewWidth = Math.max(480, Math.floor(canvas.getBoundingClientRect().width || 640));
    const viewHeight = 320;
    if (canvas.width !== viewWidth || canvas.height !== viewHeight) {
        canvas.width = viewWidth;
        canvas.height = viewHeight;
    }

    const { labels, matrix } = buildPortfolioCorrelationMatrix(positions);
    const n = labels.length;

    ctx.clearRect(0, 0, viewWidth, viewHeight);
    ctx.fillStyle = '#0f1523';
    ctx.fillRect(0, 0, viewWidth, viewHeight);

    const marginLeft = 86;
    const marginTop = 18;
    const marginRight = 16;
    const marginBottom = 74;
    const plotW = Math.max(1, viewWidth - marginLeft - marginRight);
    const plotH = Math.max(1, viewHeight - marginTop - marginBottom);
    const cellW = plotW / n;
    const cellH = plotH / n;

    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
            const x = marginLeft + j * cellW;
            const y = marginTop + i * cellH;
            ctx.fillStyle = correlationColor(matrix[i][j]);
            ctx.fillRect(x, y, cellW, cellH);
            ctx.strokeStyle = 'rgba(30, 50, 80, 0.5)';
            ctx.strokeRect(x, y, cellW, cellH);
        }
    }

    ctx.fillStyle = '#9ab';
    ctx.font = '10px Inter, Arial, sans-serif';
    for (let i = 0; i < n; i++) {
        const y = marginTop + (i + 0.5) * cellH;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(labels[i], marginLeft - 8, y);
    }

    for (let j = 0; j < n; j++) {
        const x = marginLeft + (j + 0.5) * cellW;
        ctx.save();
        ctx.translate(x, marginTop + plotH + 10);
        ctx.rotate(-Math.PI / 4);
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(labels[j], 0, 0);
        ctx.restore();
    }

    const legendY = viewHeight - 18;
    const legendX = marginLeft;
    const legendW = Math.min(220, plotW);
    const gradient = ctx.createLinearGradient(legendX, 0, legendX + legendW, 0);
    gradient.addColorStop(0, correlationColor(-1));
    gradient.addColorStop(0.5, '#f3f3f3');
    gradient.addColorStop(1, correlationColor(1));
    ctx.fillStyle = gradient;
    ctx.fillRect(legendX, legendY, legendW, 8);
    ctx.strokeStyle = '#33445f';
    ctx.strokeRect(legendX, legendY, legendW, 8);
    ctx.fillStyle = '#93a7c6';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'bottom';
    ctx.fillText('-1', legendX, legendY - 2);
    ctx.textAlign = 'center';
    ctx.fillText('0', legendX + legendW / 2, legendY - 2);
    ctx.textAlign = 'right';
    ctx.fillText('+1', legendX + legendW, legendY - 2);
}

function resolveRenderTargets(target = {}) {
    return {
        status: document.getElementById(target.statusId || '3d-render-status'),
        container: document.getElementById(target.containerId || '3d-output-container'),
        output: document.getElementById(target.outputId || 'three-output'),
        legendId: target.legendId || '3d-legend',
        correlationPanelId: target.correlationPanelId || 'correlation-panel',
        correlationCanvasId: target.correlationCanvasId || 'correlation-canvas'
    };
}

async function generate3D(type, target = {}) {
    const targets = resolveRenderTargets(target);
    const { status, container, output, legendId, correlationPanelId, correlationCanvasId } = targets;

    if (status) { status.textContent = `Generating ${type}...`; status.style.color = '#ccc'; }

    if (!output) {
        if (status) { status.textContent = 'Missing 3D container.'; status.style.color = '#e74c3c'; }
        return;
    }

    const { positions, totalEquity, isDemo } = getRenderablePortfolioContext();

    if (container) container.style.display = 'block';

    let grid;
    let colorScheme;

    if (type === 'vol_surface') {
        grid = deriveVolSurface(positions, totalEquity);
        colorScheme = 'magma';
    } else if (type === 'correlation') {
        grid = deriveCorrelation(positions);
        colorScheme = 'coolwarm';
    } else if (type === 'risk') {
        grid = deriveRisk(positions, totalEquity);
        colorScheme = 'risk';
    } else {
        return;
    }

    createThreeScene(output);
    const geometry = buildDataSurface(grid, colorScheme);
    renderScene(geometry);
    updateLegend(type, legendId);
    if (type === 'correlation') renderCorrelationHeatmap(positions, correlationPanelId, correlationCanvasId);
    else hideCorrelationPanel(correlationPanelId);

    if (status) {
        status.textContent = isDemo
            ? 'Render complete using demo portfolio. Add your own positions to customize output.'
            : 'Render complete - drag to rotate, scroll to zoom';
        status.style.color = '#4caf50';
    }
    return true;
}

function runFinanceSimulationFrame(target = {}) {
    const targets = resolveRenderTargets(target);
    const { status, container, output, legendId, correlationPanelId } = targets;
    if (!output) {
        if (status) {
            status.textContent = 'Missing 3D container.';
            status.style.color = '#e74c3c';
        }
        return false;
    }

    const { positions, totalEquity, isDemo } = getRenderablePortfolioContext();
    if (!simState) {
        simState = { day: 1, volatility: 1, trend: 0 };
    } else {
        simState.day += 1;
        simState.trend += (Math.random() - 0.5) * 0.1;
        simState.volatility = Math.max(0.3, Math.min(3, simState.volatility + (Math.random() - 0.5) * 0.2));
    }

    if (container) container.style.display = 'block';
    const grid = deriveSimSurface(positions, totalEquity, simState);
    createThreeScene(output);
    const geometry = buildDataSurface(grid, 'RdYlGn');
    renderScene(geometry);
    updateLegend('sim', legendId);
    hideCorrelationPanel(correlationPanelId);

    if (status) {
        const demoTag = isDemo ? ' | Demo portfolio' : '';
        status.textContent = `Simulation frame generated (day ${simState.day})${demoTag}`;
        status.style.color = '#4caf50';
    }
    return true;
}

// ==================== PORTFOLIO FORM ====================

function setupPortfolioForm() {
    const form = document.getElementById('portfolio-form');
    if (!form) return;

    form.addEventListener('submit', async event => {
        event.preventDefault();
        event.stopPropagation();
        const tickerInput = document.getElementById('portfolio-ticker');
        const ticker = tickerInput.value.trim().toUpperCase();
        if (!ticker) return;

        const qtyInput = document.getElementById('portfolio-qty');
        const avgInput = document.getElementById('portfolio-avg');
        const manualQty = qtyInput && qtyInput.value ? parseFloat(qtyInput.value) : null;
        const manualAvg = avgInput && avgInput.value ? parseFloat(avgInput.value) : null;

        const submitBtn = form.querySelector('button[type="submit"], button');
        const originalBtnText = submitBtn ? submitBtn.textContent : '';
        if (submitBtn) { submitBtn.textContent = 'Fetching...'; submitBtn.disabled = true; }

        let price = await fetchTickerPrice(ticker);

        if (submitBtn) { submitBtn.textContent = originalBtnText; submitBtn.disabled = false; }

        if (price === null && manualAvg === null) {
            const errMsg = document.getElementById('portfolio-error');
            if (errMsg) {
                errMsg.textContent = `Could not fetch price for ${ticker}. Enter an avg price manually or check the ticker.`;
                errMsg.style.display = 'block';
                setTimeout(() => { errMsg.style.display = 'none'; }, 5000);
            } else {
                alert(`Could not fetch price for ${ticker}. Check ticker symbol and internet connection.`);
            }
            return;
        }

        const qty = manualQty && manualQty > 0 ? manualQty : 1;
        const avgPrice = manualAvg && manualAvg > 0 ? manualAvg : price;
        const currentPrice = price || avgPrice;

        const local = getLocalPortfolio();
        const existing = local.positions.find(pos => pos.symbol === ticker);
        if (existing) {
            const totalCost = existing.qty * existing.avg_price + qty * avgPrice;
            existing.qty += qty;
            existing.avg_price = totalCost / existing.qty;
            existing.current_price = currentPrice;
        } else {
            local.positions.push({ symbol: ticker, qty, avg_price: avgPrice, current_price: currentPrice });
        }

        saveLocalPortfolio(local);
        form.reset();
        updatePortfolio();
    });
}

function setupPortfolioUpload() {
    const uploadInput = document.getElementById('portfolio-upload');
    const uploadBtn = document.getElementById('portfolio-upload-btn');
    const uploadStatus = document.getElementById('portfolio-upload-status');
    if (!uploadInput || !uploadBtn) return;

    uploadBtn.addEventListener('click', async () => {
        if (!uploadInput.files || uploadInput.files.length === 0) return;
        const file = uploadInput.files[0];
        try {
            const text = await file.text();
            const payload = JSON.parse(text);
            if (!payload || !Array.isArray(payload.positions)) {
                throw new Error('Invalid portfolio package.');
            }
            // Save locally for immediate use.
            const positions = payload.positions;
            const total_equity = positions.reduce((s, p) => s + (p.current_price * p.qty), 0);
            saveLocalPortfolio({ total_equity, positions });

            // Upload to server for persistence across sessions.
            const formData = new FormData();
            formData.append('file', file, file.name);
            await fetch('/api/portfolio/upload', { method: 'POST', body: formData });

            if (uploadStatus) {
                uploadStatus.textContent = 'Portfolio package uploaded.';
                uploadStatus.style.color = '#4caf50';
            }
            updatePortfolio();
        } catch (err) {
            if (uploadStatus) {
                uploadStatus.textContent = 'Upload failed. Invalid JSON or schema.';
                uploadStatus.style.color = '#e74c3c';
            }
        }
    });
}

// ==================== PORTFOLIO SEED (Real Data 2026-02-11) ====================

function seedPortfolio() {
    const SEED_VERSION = '2026.02.11-v3';
    const seeded = localStorage.getItem('atlas_portfolio_seed_version');
    const local = getLocalPortfolio();

    // Skip only if already seeded this version AND portfolio has data
    if (seeded === SEED_VERSION && local.positions && local.positions.length > 0) return;

    const realPositions = [
        { symbol: 'AAPL', qty: 0.4367, avg_price: 228.82, current_price: 275.83 },
        { symbol: 'AMZN', qty: 0.42792, avg_price: 233.33, current_price: 204.31 },
        { symbol: 'AVGO', qty: 0.33014, avg_price: 302.44, current_price: 343.09 },
        { symbol: 'AXP', qty: 0.29993, avg_price: 332.83, current_price: 354.54 },
        { symbol: 'BAC', qty: 1.96116, avg_price: 50.90, current_price: 53.88 },
        { symbol: 'CCEP', qty: 1.14126, avg_price: 87.47, current_price: 97.67 },
        { symbol: 'CRWD', qty: 0.21006, avg_price: 475.34, current_price: 415.79 },
        { symbol: 'GOOGL', qty: 0.3306, avg_price: 301.78, current_price: 310.90 },
        { symbol: 'HD', qty: 0.26518, avg_price: 376.45, current_price: 390.67 },
        { symbol: 'HP', qty: 3.46786, avg_price: 28.79, current_price: 34.41 },
        { symbol: 'IEUR', qty: 1.49825, avg_price: 66.69, current_price: 75.85 },
        { symbol: 'MA', qty: 0.17714, avg_price: 563.55, current_price: 538.00 },
        { symbol: 'MCD', qty: 0.32636, avg_price: 305.89, current_price: 322.67 },
        { symbol: 'MSCI', qty: 0.17103, avg_price: 583.32, current_price: 513.56 },
        { symbol: 'MSFT', qty: 0.22309, avg_price: 447.48, current_price: 404.75 },
        { symbol: 'NKE', qty: 1.45245, avg_price: 68.73, current_price: 62.48 },
        { symbol: 'NVDA', qty: 0.62514, avg_price: 159.69, current_price: 190.36 },
        { symbol: 'PANW', qty: 0.51768, avg_price: 192.88, current_price: 165.25 },
        { symbol: 'PEP', qty: 0.69104, avg_price: 144.46, current_price: 169.33 },
        { symbol: 'PG', qty: 0.65661, avg_price: 152.04, current_price: 159.84 },
        { symbol: 'SBUX', qty: 1.04586, avg_price: 95.45, current_price: 99.05 },
        { symbol: 'SPY', qty: 0.32882, avg_price: 612.72, current_price: 692.49 },
        { symbol: 'TEM', qty: 1.43675, avg_price: 69.50, current_price: 53.54 },
        { symbol: 'TSLA', qty: 0.25901, avg_price: 385.38, current_price: 428.52 },
        { symbol: 'VOO', qty: 0.16566, avg_price: 602.59, current_price: 636.87 },
        { symbol: 'VST', qty: 0.57098, avg_price: 174.87, current_price: 160.34 },
        { symbol: 'VTI', qty: 0.32419, avg_price: 308.05, current_price: 341.71 }
    ];

    const portfolio = { total_equity: 0, positions: realPositions };
    portfolio.total_equity = realPositions.reduce((s, p) => s + p.current_price * p.qty, 0);
    saveLocalPortfolio(portfolio);
    localStorage.setItem('atlas_portfolio_seed_version', SEED_VERSION);
    console.log(`Portfolio seeded: ${realPositions.length} positions, $${portfolio.total_equity.toFixed(2)} total equity`);
}

// ==================== SIMULATION LAB ====================

function setupSimulationLab() {
    const startBtn = document.getElementById('sim-start-btn');
    const nextBtn = document.getElementById('sim-next-btn');
    const autoBtn = document.getElementById('sim-auto-btn');
    const restartBtn = document.getElementById('sim-restart-btn');
    const decisionSelect = document.getElementById('sim-decision');
    const status = document.getElementById('sim-status');
    const AUTO_INTERVAL_MS = 900;
    let autoTimer = null;
    let isAutoRunning = false;

    if (!startBtn || !nextBtn || !decisionSelect || !status) return;

    const setAutoButtonState = running => {
        if (!autoBtn) return;
        autoBtn.textContent = running ? 'Pause Auto' : 'Auto Sim';
        autoBtn.classList.toggle('primary', running);
        autoBtn.classList.toggle('secondary', !running);
    };

    const stopAutoSim = () => {
        if (autoTimer) {
            clearInterval(autoTimer);
            autoTimer = null;
        }
        isAutoRunning = false;
        nextBtn.disabled = !simState;
        setAutoButtonState(false);
        updateStatus();
    };

    const hasPortfolioData = () => {
        const { positions } = getRenderablePortfolioContext();
        return positions.length > 0;
    };

    const updateStatus = () => {
        if (!simState) { status.textContent = 'Simulation idle.'; return; }
        const autoFlag = isAutoRunning ? '  |  Auto ON' : '';
        status.textContent = `Day ${simState.day}  |  Vol ${simState.volatility.toFixed(2)}  |  Trend ${simState.trend >= 0 ? '+' : ''}${simState.trend.toFixed(2)}${autoFlag}`;
    };

    const applyDecision = decision => {
        if (!simState) return;
        if (decision === 'risk_on') {
            simState.volatility = Math.min(2.5, simState.volatility + 0.2);
            simState.trend += 0.1;
        } else if (decision === 'risk_off') {
            simState.volatility = Math.max(0.3, simState.volatility - 0.2);
            simState.trend -= 0.1;
        } else if (decision === 'hedge') {
            simState.volatility = Math.max(0.4, simState.volatility - 0.1);
            simState.trend -= 0.05;
        }
    };

    const renderSimulation = () => {
        const output = document.getElementById('three-output');
        const outputContainer = document.getElementById('3d-output-container');
        if (!output) return;

        const { positions, totalEquity, isDemo } = getRenderablePortfolioContext();
        if (!simState) { status.textContent = 'Simulation idle.'; return; }
        if (outputContainer) outputContainer.style.display = 'block';

        const grid = deriveSimSurface(positions, totalEquity, simState);
        createThreeScene(output);
        const geometry = buildDataSurface(grid, 'RdYlGn');
        renderScene(geometry);
        updateLegend('sim');
        hideCorrelationPanel();

        if (isDemo) {
            status.textContent = `${status.textContent}  |  Demo portfolio`;
        }
    };

    const initializeSimulation = () => {
        if (!hasPortfolioData()) {
            status.textContent = 'Unable to initialize simulation.';
            status.style.color = '#f39c12';
            return false;
        }
        simState = { day: 1, volatility: 1, trend: 0 };
        nextBtn.disabled = false;
        if (autoBtn) autoBtn.disabled = false;
        status.style.color = '#aaa';
        updateStatus();
        renderSimulation();
        return true;
    };

    const advanceDay = () => {
        if (!simState) return;
        applyDecision(decisionSelect.value);
        simState.day += 1;
        simState.trend += (Math.random() - 0.5) * 0.1;
        simState.volatility = Math.max(0.3, Math.min(3,
            simState.volatility + (Math.random() - 0.5) * 0.2));
        updateStatus();
        renderSimulation();
    };

    startBtn.addEventListener('click', () => {
        stopAutoSim();
        initializeSimulation();
    });

    if (restartBtn) {
        restartBtn.addEventListener('click', () => {
            stopAutoSim();
            initializeSimulation();
        });
    }

    nextBtn.addEventListener('click', () => {
        if (!simState) {
            if (!initializeSimulation()) return;
        }
        advanceDay();
    });

    if (autoBtn) {
        autoBtn.addEventListener('click', () => {
            if (!simState) {
                if (!initializeSimulation()) return;
            }
            if (isAutoRunning) {
                stopAutoSim();
                return;
            }
            isAutoRunning = true;
            nextBtn.disabled = true;
            setAutoButtonState(true);
            updateStatus();
            autoTimer = setInterval(() => {
                if (!simState) {
                    stopAutoSim();
                    return;
                }
                advanceDay();
            }, AUTO_INTERVAL_MS);
        });
    }
}

// ==================== UTILITIES ====================

function formatCurrency(num) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
}

// ==================== INIT ====================

window.generate3D = generate3D;
window.updatePortfolio = updatePortfolio;
window.runFinanceSimulationFrame = runFinanceSimulationFrame;

document.addEventListener('DOMContentLoaded', () => {
    seedPortfolio();
    setupPortfolioForm();
    setupPortfolioUpload();
    setupSimulationLab();
    updatePortfolio();
});

