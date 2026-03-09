/**
 * Git City Engine - Play Room
 * Turns abstract codebase metadata into a procedural 3D synthwave city.
 */

window.PlayRoomGitCity = (function () {
    let _mount, _renderer, _animId;
    let _scene, _camera;

    function launch(mountId) {
        _mount = document.getElementById(mountId);
        if (!_mount || typeof THREE === 'undefined') {
            if (_mount) _mount.innerHTML = '<span style="color:red;padding:20px;">Three.js not loaded.</span>';
            return;
        }

        _mount.innerHTML = '';
        const W = _mount.clientWidth;
        const H = _mount.clientHeight;

        _scene = new THREE.Scene();
        _scene.background = new THREE.Color(0x02030a);
        _scene.fog = new THREE.FogExp2(0x02030a, 0.005);

        _camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000);
        _camera.position.set(0, 30, 80);
        _camera.lookAt(0, 5, 0);

        _renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        _renderer.setSize(W, H);
        _renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        _mount.appendChild(_renderer.domElement);

        _buildCity();
        _startAnimation();

        // Overlay status text
        const uiLayer = document.createElement('div');
        uiLayer.style.cssText = 'position:absolute; bottom:15px; left:15px; background:rgba(2,3,10,0.8); border:1px solid #1f2a44; padding:10px; color:#fff; font-family:monospace; font-size:11px; border-radius:6px; pointer-events:none;';
        uiLayer.innerHTML = `
            <div style="font-weight:bold; color:#3498db; margin-bottom:5px;">GIT CITY [METRICS.PROCEDURAL]</div>
            <div>BUILDINGS: 400 (Files)</div>
            <div>HEIGHT: LOC Density</div>
            <div>COLOR: Language Metadata</div>
        `;
        _mount.appendChild(uiLayer);
    }

    function _buildCity() {
        const gridX = 20;
        const gridZ = 20;
        const spacing = 6;

        // Ground
        const groundGeo = new THREE.PlaneGeometry(500, 500);
        const groundMat = new THREE.MeshBasicMaterial({ color: 0x050510, transparent: true, opacity: 0.8 });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.y = -0.1;
        _scene.add(ground);

        // Buildings (Code Files)
        const blockGeo = new THREE.BoxGeometry(1, 1, 1);

        // Colors mapping to "languages"
        const colors = [0x3498db, 0xe74c3c, 0xf1c40f, 0x9b59b6, 0x2ecc71];

        // Central core (Main system)
        _createBuilding(blockGeo, 0, 0, 40, 0x7c3fe4, 4);

        for (let i = 0; i < 400; i++) {
            let x = (Math.random() - 0.5) * gridX * spacing;
            let z = (Math.random() - 0.5) * gridZ * spacing;

            // leave center empty for core
            if (Math.abs(x) < 8 && Math.abs(z) < 8) continue;

            // The further away from center, the lower the codebase LOC
            let dist = Math.sqrt(x * x + z * z);
            let maxHeight = Math.max(2, 30 - dist * 0.4);
            let height = 2 + Math.random() * maxHeight;

            let color = colors[Math.floor(Math.random() * colors.length)];

            _createBuilding(blockGeo, x, z, height, color, 1 + Math.random());
        }

        // Data Streams (Flying particles)
        _createDataStreams();
    }

    function _createBuilding(geo, x, z, height, hexColor, width) {
        // Base dark block
        const mat = new THREE.MeshBasicMaterial({ color: 0x111122 });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.scale.set(width, height, width);
        mesh.position.set(x, height / 2, z);
        _scene.add(mesh);

        // Neon outline
        const edges = new THREE.EdgesGeometry(geo);
        const lineMat = new THREE.LineBasicMaterial({ color: hexColor, transparent: true, opacity: 0.5 });
        const line = new THREE.LineSegments(edges, lineMat);
        line.scale.set(width + 0.05, height + 0.05, width + 0.05);
        line.position.set(x, height / 2, z);
        _scene.add(line);
    }

    let _streamPoints;
    function _createDataStreams() {
        const count = 500;
        const geo = new THREE.BufferGeometry();
        const pos = new Float32Array(count * 3);
        const vels = new Float32Array(count * 3);

        for (let i = 0; i < count; i++) {
            let i3 = i * 3;
            pos[i3] = (Math.random() - 0.5) * 120;
            pos[i3 + 1] = 0.5; // low to ground (roads)
            pos[i3 + 2] = (Math.random() - 0.5) * 120;

            // X-axis traffic or Z-axis traffic
            if (Math.random() > 0.5) {
                vels[i3] = (Math.random() > 0.5 ? 1 : -1) * (0.2 + Math.random() * 0.5);
                vels[i3 + 1] = 0;
                vels[i3 + 2] = 0;
            } else {
                vels[i3] = 0;
                vels[i3 + 1] = 0;
                vels[i3 + 2] = (Math.random() > 0.5 ? 1 : -1) * (0.2 + Math.random() * 0.5);
            }
        }
        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        const mat = new THREE.PointsMaterial({ color: 0xffffff, size: 0.8, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending });
        _streamPoints = new THREE.Points(geo, mat);
        _streamPoints.userData.vels = vels;
        _scene.add(_streamPoints);
    }

    let time = 0;
    function _startAnimation() {
        function animate() {
            _animId = requestAnimationFrame(animate);
            time += 0.005;

            // Rotate camera slowly around the city
            _camera.position.x = Math.sin(time) * 90;
            _camera.position.z = Math.cos(time) * 90;
            _camera.lookAt(0, 10, 0);

            // Animate traffic
            if (_streamPoints) {
                let pos = _streamPoints.geometry.attributes.position.array;
                let vels = _streamPoints.userData.vels;
                for (let i = 0; i < pos.length / 3; i++) {
                    let i3 = i * 3;
                    pos[i3] += vels[i3];
                    pos[i3 + 2] += vels[i3 + 2];

                    if (Math.abs(pos[i3]) > 60) pos[i3] *= -0.99; // wrap bounds
                    if (Math.abs(pos[i3 + 2]) > 60) pos[i3 + 2] *= -0.99;
                }
                _streamPoints.geometry.attributes.position.needsUpdate = true;
            }

            _renderer.render(_scene, _camera);
        }
        animate();
    }

    function cleanup() {
        if (_animId) cancelAnimationFrame(_animId);
        _animId = null;
        if (_mount) _mount.innerHTML = '';
        _renderer = null;
        _scene = null;
        _camera = null;
    }

    return { launch, cleanup };
})();
