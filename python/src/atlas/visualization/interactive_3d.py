"""
ATLAS Interactive 3D Visualizations
======================================
Generates standalone HTML files with Three.js for interactive 3D exploration.
No server needed — just open the HTML file in a browser.

Copyright (c) 2026 M&C. All rights reserved.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.viz.3d_interactive")


class Interactive3DRenderer:
    """
    Generate self-contained HTML files with Three.js 3D visualizations.
    """

    def __init__(self, output_dir: str = "data/renders/3d_interactive"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _base_html(self, title: str, scene_js: str, width: int = 1200, height: int = 800) -> str:
        """Generate complete HTML with Three.js scene."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} — Atlas 3D</title>
<style>
    body {{ margin: 0; background: #0a0a0a; overflow: hidden; font-family: monospace; }}
    canvas {{ display: block; }}
    #info {{
        position: absolute; top: 10px; left: 10px; color: #0ff;
        font-size: 14px; z-index: 10; background: rgba(0,0,0,0.7);
        padding: 10px; border-radius: 5px;
    }}
    #info h2 {{ margin: 0 0 5px 0; color: #0f0; font-size: 16px; }}
</style>
</head>
<body>
<div id="info"><h2>{title}</h2><span id="details">Drag to rotate, scroll to zoom</span></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
// Atlas 3D Visualization
const WIDTH = window.innerWidth;
const HEIGHT = window.innerHeight;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0a0a);

const camera = new THREE.PerspectiveCamera(60, WIDTH / HEIGHT, 0.1, 10000);
const renderer = new THREE.WebGLRenderer({{ antialias: true }});
renderer.setSize(WIDTH, HEIGHT);
renderer.setPixelRatio(window.devicePixelRatio);
document.body.appendChild(renderer.domElement);

// Lights
const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
scene.add(ambientLight);
const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
directionalLight.position.set(50, 100, 50);
scene.add(directionalLight);
const pointLight = new THREE.PointLight(0x00ffff, 0.5, 500);
pointLight.position.set(0, 80, 0);
scene.add(pointLight);

// Grid helper
const grid = new THREE.GridHelper(200, 40, 0x333333, 0x222222);
scene.add(grid);

// Orbit-like controls (manual implementation since OrbitControls isn't on CDN r128)
let isDragging = false;
let previousMouse = {{ x: 0, y: 0 }};
let spherical = {{ radius: 150, theta: Math.PI / 4, phi: Math.PI / 3 }};

function updateCamera() {{
    camera.position.x = spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
    camera.position.y = spherical.radius * Math.cos(spherical.phi);
    camera.position.z = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
    camera.lookAt(0, 20, 0);
}}

renderer.domElement.addEventListener('mousedown', (e) => {{
    isDragging = true;
    previousMouse = {{ x: e.clientX, y: e.clientY }};
}});
renderer.domElement.addEventListener('mousemove', (e) => {{
    if (!isDragging) return;
    const dx = e.clientX - previousMouse.x;
    const dy = e.clientY - previousMouse.y;
    spherical.theta += dx * 0.01;
    spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + dy * 0.01));
    previousMouse = {{ x: e.clientX, y: e.clientY }};
    updateCamera();
}});
renderer.domElement.addEventListener('mouseup', () => {{ isDragging = false; }});
renderer.domElement.addEventListener('wheel', (e) => {{
    spherical.radius = Math.max(20, Math.min(500, spherical.radius + e.deltaY * 0.1));
    updateCamera();
}});

updateCamera();

// === SCENE DATA ===
{scene_js}

// Animation loop
function animate() {{
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}}
animate();

window.addEventListener('resize', () => {{
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}});
</script>
</body>
</html>"""

    def volatility_surface(
        self,
        strikes: np.ndarray,
        expiries: np.ndarray,
        iv_matrix: np.ndarray,
        title: str = "Implied Volatility Surface",
        filename: str = "vol_surface_interactive.html",
    ) -> str:
        """Interactive 3D volatility surface."""
        n_strikes, n_expiries = iv_matrix.shape

        # Normalize to scene coordinates
        x_scale = 100 / max(n_expiries, 1)
        z_scale = 100 / max(n_strikes, 1)
        y_scale = 200  # Height scale for IV values

        scene_js = f"""
const geometry = new THREE.BufferGeometry();
const vertices = [];
const colors = [];
const colorMap = new THREE.Color();

const ivData = {json.dumps(iv_matrix.tolist())};
const nStrikes = {n_strikes};
const nExpiries = {n_expiries};
const xScale = {x_scale};
const zScale = {z_scale};
const yScale = {y_scale};

// Create vertices
for (let i = 0; i < nStrikes; i++) {{
    for (let j = 0; j < nExpiries; j++) {{
        const x = (j - nExpiries/2) * xScale;
        const y = ivData[i][j] * yScale;
        const z = (i - nStrikes/2) * zScale;
        vertices.push(x, y, z);

        // Color by IV level (low=blue, high=red)
        const t = ivData[i][j] / 0.8;
        colorMap.setHSL(0.7 - t * 0.7, 1.0, 0.5);
        colors.push(colorMap.r, colorMap.g, colorMap.b);
    }}
}}

// Create faces (indices)
const indices = [];
for (let i = 0; i < nStrikes - 1; i++) {{
    for (let j = 0; j < nExpiries - 1; j++) {{
        const a = i * nExpiries + j;
        const b = a + 1;
        const c = a + nExpiries;
        const d = c + 1;
        indices.push(a, b, c);
        indices.push(b, d, c);
    }}
}}

geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
geometry.setIndex(indices);
geometry.computeVertexNormals();

const material = new THREE.MeshPhongMaterial({{
    vertexColors: true,
    side: THREE.DoubleSide,
    shininess: 50,
    transparent: true,
    opacity: 0.85,
}});

const mesh = new THREE.Mesh(geometry, material);
scene.add(mesh);

// Wireframe overlay
const wire = new THREE.WireframeGeometry(geometry);
const lineMat = new THREE.LineBasicMaterial({{ color: 0x444444, opacity: 0.3, transparent: true }});
scene.add(new THREE.LineSegments(wire, lineMat));
"""
        html = self._base_html(title, scene_js)
        path = self.output_dir / filename
        path.write_text(html)
        logger.info("Interactive Vol Surface: %s", path)
        return str(path)

    def correlation_mountain(
        self,
        corr_matrix: pd.DataFrame,
        title: str = "Correlation Mountain",
        filename: str = "correlation_mountain_interactive.html",
    ) -> str:
        """Interactive 3D correlation landscape with bar columns."""
        n = len(corr_matrix)
        data = corr_matrix.values.tolist()
        labels = corr_matrix.columns.tolist()

        scene_js = f"""
const corrData = {json.dumps(data)};
const labels = {json.dumps(labels)};
const n = {n};
const spacing = 8;

for (let i = 0; i < n; i++) {{
    for (let j = 0; j < n; j++) {{
        const val = corrData[i][j];
        const height = Math.abs(val) * 40;
        const geo = new THREE.BoxGeometry(spacing * 0.7, height, spacing * 0.7);
        const color = val > 0 ?
            new THREE.Color().setHSL(0.35, 0.8, 0.3 + val * 0.5) :
            new THREE.Color().setHSL(0.0, 0.8, 0.3 + Math.abs(val) * 0.5);
        const mat = new THREE.MeshPhongMaterial({{ color, transparent: true, opacity: 0.8 }});
        const bar = new THREE.Mesh(geo, mat);
        bar.position.set(
            (j - n/2) * spacing,
            height / 2,
            (i - n/2) * spacing
        );
        scene.add(bar);
    }}
}}

// Axis labels (simplified — canvas text)
document.getElementById('details').innerHTML =
    'Assets: ' + labels.join(', ') + '<br>Drag to rotate, scroll to zoom';
"""
        html = self._base_html(title, scene_js)
        path = self.output_dir / filename
        path.write_text(html)
        logger.info("Interactive Correlation Mountain: %s", path)
        return str(path)

    def monte_carlo_mountain(
        self,
        paths: np.ndarray,
        title: str = "Monte Carlo Path Density",
        filename: str = "mc_mountain_interactive.html",
        n_time_slices: int = 15,
        n_bins: int = 30,
    ) -> str:
        """Interactive 3D Monte Carlo density mountain."""
        n_paths, n_steps = paths.shape
        step_indices = np.linspace(0, n_steps - 1, n_time_slices, dtype=int)

        price_min = float(paths.min())
        price_max = float(paths.max())
        bins = np.linspace(price_min, price_max, n_bins + 1)

        # Build histogram data
        hist_data = []
        for step in step_indices:
            counts, _ = np.histogram(paths[:, step], bins=bins)
            hist_data.append(counts.tolist())

        scene_js = f"""
const histData = {json.dumps(hist_data)};
const nSlices = {n_time_slices};
const nBins = {n_bins};
const xSpacing = 100 / nBins;
const zSpacing = 100 / nSlices;
const maxCount = Math.max(...histData.flat());

for (let t = 0; t < nSlices; t++) {{
    for (let b = 0; b < nBins; b++) {{
        const val = histData[t][b];
        if (val < 1) continue;
        const height = (val / maxCount) * 60;
        const geo = new THREE.BoxGeometry(xSpacing * 0.8, height, zSpacing * 0.8);
        const hue = 0.55 + (val / maxCount) * 0.15;
        const color = new THREE.Color().setHSL(hue, 0.9, 0.5);
        const mat = new THREE.MeshPhongMaterial({{ color, transparent: true, opacity: 0.7 }});
        const bar = new THREE.Mesh(geo, mat);
        bar.position.set(
            (b - nBins/2) * xSpacing,
            height / 2,
            (t - nSlices/2) * zSpacing
        );
        scene.add(bar);
    }}
}}

document.getElementById('details').innerHTML =
    '{n_paths} paths, {n_time_slices} time slices, {n_bins} price bins<br>Drag to rotate';
"""
        html = self._base_html(title, scene_js)
        path = self.output_dir / filename
        path.write_text(html)
        logger.info("Interactive MC Mountain: %s", path)
        return str(path)
