/**
 * Finance Module (Portfolio + 3D Lab)
 */

const portfolioStorageKey = 'atlas_portfolio';
let threeRenderer = null;
let threeScene = null;
let threeCamera = null;
let threeAnimationId = null;
let simState = null;

function getLocalPortfolio() {
    const stored = localStorage.getItem(portfolioStorageKey);
    if (stored) {
        return JSON.parse(stored);
    }
    return { total_equity: 0, positions: [] };
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

async function updatePortfolio() {
    let data = null;
    try {
        const response = await fetch('/api/portfolio');
        if (response.ok) {
            data = await response.json();
        }
    } catch (e) {
        console.warn("Portfolio API unavailable, using local portfolio.", e);
    }

    if (!data) {
        const local = getLocalPortfolio();
        data = buildPortfolioSummary(local.positions);
    } else {
        data = buildPortfolioSummary(data.positions || []);
    }

    // Update Equity
    document.getElementById('total-equity').textContent = formatCurrency(data.total_equity || 0);

    // Update Table
    const tbody = document.getElementById('portfolio-table-body');
    tbody.innerHTML = '';

    if (!data.positions || data.positions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding:20px; text-align:center; color:#555;">No active positions</td></tr>';
        return;
    }

    data.positions.forEach(pos => {
        const pnlColor = pos.pnl >= 0 ? '#4caf50' : '#e74c3c';
        const row = `
                <tr style="border-bottom:1px solid #222;">
                    <td style="padding:12px; font-weight:bold;">${pos.symbol}</td>
                    <td style="padding:12px;">${pos.qty}</td>
                    <td style="padding:12px;">$${pos.avg_price.toFixed(2)}</td>
                    <td style="padding:12px;">$${pos.current_price.toFixed(2)}</td>
                    <td style="padding:12px; color:${pnlColor}; font-weight:bold;">
                        ${pos.pnl >= 0 ? '+' : ''}$${pos.pnl.toFixed(2)} (${pos.pnl_pct.toFixed(1)}%)
                    </td>
                </tr>
            `;
        tbody.innerHTML += row;
    });
}

function disposeThreeScene() {
    if (threeAnimationId) {
        cancelAnimationFrame(threeAnimationId);
        threeAnimationId = null;
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

    threeCamera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    threeCamera.position.set(0, 18, 32);
    threeCamera.lookAt(0, 0, 0);

    const ambient = new THREE.AmbientLight(0xffffff, 0.7);
    threeScene.add(ambient);
    const directional = new THREE.DirectionalLight(0xffffff, 0.6);
    directional.position.set(10, 20, 15);
    threeScene.add(directional);

    threeRenderer = new THREE.WebGLRenderer({ antialias: true });
    threeRenderer.setSize(width, height);
    threeRenderer.setPixelRatio(window.devicePixelRatio || 1);
    container.appendChild(threeRenderer.domElement);
}

function buildSurfaceMesh(type, positions, simulationOverride) {
    const gridSize = 30;
    const spacing = 1;
    const amplitude = simulationOverride?.amplitude ?? Math.max(4, Math.min(10, positions.length * 2));
    const volatility = simulationOverride?.volatility ?? 0.6;

    const geometry = new THREE.PlaneGeometry(
        gridSize * spacing,
        gridSize * spacing,
        gridSize,
        gridSize
    );

    const positionsAttr = geometry.attributes.position;
    const totalEquity = positions.reduce((sum, pos) => sum + pos.current_price * pos.qty, 0);
    const equityFactor = totalEquity ? Math.min(10, totalEquity / 5000) : 1;

    for (let i = 0; i < positionsAttr.count; i += 1) {
        const x = positionsAttr.getX(i);
        const y = positionsAttr.getY(i);
        let z = 0;

        if (type === 'vol_surface') {
            z = Math.sin(x * 0.2) * Math.cos(y * 0.2) * amplitude * volatility;
        } else if (type === 'correlation') {
            z = Math.sin((x + y) * 0.15) * amplitude * 0.8 + Math.cos(x * 0.1) * amplitude * 0.2;
        } else if (type === 'risk') {
            z = Math.sqrt(x * x + y * y) * 0.15 * amplitude;
        } else if (type === 'sim') {
            z = Math.sin(x * 0.15 + y * 0.1) * amplitude * volatility;
        }

        positionsAttr.setZ(i, z * equityFactor);
    }

    positionsAttr.needsUpdate = true;
    geometry.computeVertexNormals();

    const material = new THREE.MeshStandardMaterial({
        color: type === 'risk' ? '#ff6f61' : '#4ea1ff',
        metalness: 0.2,
        roughness: 0.5,
        side: THREE.DoubleSide
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.rotation.x = -Math.PI / 2.5;
    return mesh;
}

function renderThreeScene(mesh) {
    if (!threeScene || !threeRenderer || !threeCamera) return;

    threeScene.clear();
    const gridHelper = new THREE.GridHelper(40, 20, '#1f2a44', '#1f2a44');
    threeScene.add(gridHelper);
    threeScene.add(mesh);

    const animate = () => {
        mesh.rotation.z += 0.002;
        threeRenderer.render(threeScene, threeCamera);
        threeAnimationId = requestAnimationFrame(animate);
    };
    animate();
}

async function generate3D(type) {
    const status = document.getElementById('3d-render-status');
    const container = document.getElementById('3d-output-container');
    const output = document.getElementById('three-output');
    const local = getLocalPortfolio();
    const portfolioData = buildPortfolioSummary(local.positions);

    status.textContent = `Generating ${type}...`;
    status.style.color = '#fff';

    if (!output) {
        status.textContent = "Missing 3D container.";
        status.style.color = 'red';
        return;
    }

    if (!portfolioData.positions.length) {
        status.textContent = "Add positions to generate a 3D model.";
        status.style.color = '#f39c12';
        return;
    }

    container.style.display = 'block';
    createThreeScene(output);
    const mesh = buildSurfaceMesh(type, portfolioData.positions);
    renderThreeScene(mesh);

    status.textContent = "Render complete!";
    status.style.color = '#4caf50';
}

function setupPortfolioForm() {
    const form = document.getElementById('portfolio-form');
    if (!form) return;

    form.addEventListener('submit', event => {
        event.preventDefault();
        const ticker = document.getElementById('portfolio-ticker').value.trim().toUpperCase();
        const qty = Number(document.getElementById('portfolio-qty').value);
        const avgPrice = Number(document.getElementById('portfolio-avg').value);
        const currentPrice = Number(document.getElementById('portfolio-current').value);

        if (!ticker || qty <= 0 || avgPrice <= 0 || currentPrice <= 0) return;

        const local = getLocalPortfolio();
        const existing = local.positions.find(pos => pos.symbol === ticker);
        if (existing) {
            existing.qty += qty;
            existing.avg_price = avgPrice;
            existing.current_price = currentPrice;
        } else {
            local.positions.push({
                symbol: ticker,
                qty,
                avg_price: avgPrice,
                current_price: currentPrice
            });
        }

        saveLocalPortfolio(local);
        form.reset();
        updatePortfolio();
    });
}

function setupSimulationLab() {
    const startBtn = document.getElementById('sim-start-btn');
    const nextBtn = document.getElementById('sim-next-btn');
    const decisionSelect = document.getElementById('sim-decision');
    const status = document.getElementById('sim-status');
    const output = document.getElementById('three-output');
    const outputContainer = document.getElementById('3d-output-container');

    if (!startBtn || !nextBtn || !decisionSelect || !status) return;

    const updateStatus = () => {
        if (!simState) {
            status.textContent = 'Simulation idle.';
            return;
        }
        status.textContent = `Day ${simState.day} • Vol ${simState.volatility.toFixed(2)} • Trend ${simState.trend.toFixed(2)}`;
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
        if (!output) return;
        const local = getLocalPortfolio();
        const portfolioData = buildPortfolioSummary(local.positions);
        if (!portfolioData.positions.length) {
            status.textContent = 'Add positions before running the simulation.';
            return;
        }
        if (outputContainer) {
            outputContainer.style.display = 'block';
        }
        createThreeScene(output);
        const mesh = buildSurfaceMesh('sim', portfolioData.positions, {
            amplitude: 6 + simState.trend * 2,
            volatility: simState.volatility
        });
        renderThreeScene(mesh);
    };

    startBtn.addEventListener('click', () => {
        simState = { day: 1, volatility: 1, trend: 0 };
        nextBtn.disabled = false;
        updateStatus();
        renderSimulation();
    });

    nextBtn.addEventListener('click', () => {
        if (!simState) return;
        applyDecision(decisionSelect.value);
        simState.day += 1;
        simState.trend += (Math.random() - 0.5) * 0.1;
        simState.volatility = Math.max(0.3, Math.min(3, simState.volatility + (Math.random() - 0.5) * 0.2));
        updateStatus();
        renderSimulation();
    });
}

function formatCurrency(num) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    updatePortfolio();
    setupPortfolioForm();
    setupSimulationLab();
});
