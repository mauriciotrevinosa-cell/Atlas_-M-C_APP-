/**
 * Speed Racer (Neuroevolution Play Room Engine)
 * A fully self-contained Neural Network & Genetic Algorithm driving cars around a track!
 */

window.PlayRoomRacing = (function () {
    let _mount, _canvas, _ctx;
    let _animId = null;

    // Config
    const POPULATION_SIZE = 50;
    let generation = 1;
    let agents = [];
    let bestBrain = null;

    // Racing Track Bounds (Inner and Outer walls generated procedurally)
    let innerWall = [];
    let outerWall = [];
    let checkpoints = [];

    // --- Neural Net Core (from scratch!) ---
    class NeuralNet {
        constructor(inputs, hiddens, outputs) {
            this.in = inputs; this.hid = hiddens; this.out = outputs;
            this.w1 = new Array(inputs * hiddens).fill(0).map(() => Math.random() * 2 - 1);
            this.b1 = new Array(hiddens).fill(0).map(() => Math.random() * 2 - 1);
            this.w2 = new Array(hiddens * outputs).fill(0).map(() => Math.random() * 2 - 1);
            this.b2 = new Array(outputs).fill(0).map(() => Math.random() * 2 - 1);
        }
        relu(val) { return Math.max(0, val); }
        sigmoid(val) { return 1 / (1 + Math.exp(-val)); }
        predict(inputs) {
            let h = new Array(this.hid).fill(0);
            for (let i = 0; i < this.hid; i++) {
                for (let j = 0; j < this.in; j++) {
                    h[i] += inputs[j] * this.w1[i * this.in + j];
                }
                h[i] = this.relu(h[i] + this.b1[i]);
            }
            let o = new Array(this.out).fill(0);
            for (let i = 0; i < this.out; i++) {
                for (let j = 0; j < this.hid; j++) {
                    o[i] += h[j] * this.w2[i * this.hid + j];
                }
                o[i] = this.sigmoid(o[i] + this.b2[i]);
            }
            return o;
        }
        clone() {
            let c = new NeuralNet(this.in, this.hid, this.out);
            c.w1 = [...this.w1]; c.b1 = [...this.b1];
            c.w2 = [...this.w2]; c.b2 = [...this.b2];
            return c;
        }
        mutate(rate = 0.1) {
            const m = (val) => Math.random() < rate ? val + (Math.random() * 0.5 - 0.25) : val;
            this.w1 = this.w1.map(m); this.b1 = this.b1.map(m);
            this.w2 = this.w2.map(m); this.b2 = this.b2.map(m);
        }
    }

    // --- Vehicle Physics Agent ---
    class CarAgent {
        constructor(x, y) {
            this.x = x; this.y = y;
            this.angle = 0;
            this.speed = 0;
            this.maxSpeed = 5;
            this.acceleration = 0.2;
            this.friction = 0.05;
            this.alive = true;
            this.score = 0;
            this.brain = new NeuralNet(5, 8, 2); // 5 sensors, 2 outputs (throttle, steer)
            this.rayDist = 150;
            this.color = '#' + Math.floor(Math.random() * 16777215).toString(16).padStart(6, '0');
            this.laps = 0;
            this.checkIdx = 0;
        }
        update(walls) {
            if (!this.alive) return;

            // Sensors (5 rays spreading out in front)
            const angles = [-Math.PI / 4, -Math.PI / 8, 0, Math.PI / 8, Math.PI / 4];
            let readings = angles.map(a => this.castRay(this.angle + a, walls));

            // Neural decision
            let outputs = this.brain.predict(readings);
            // outputs[0] = throttle (0 to 1), outputs[1] = steering (0 to 1, mapped to -1 to 1)
            let throttle = outputs[0] > 0.5 ? 1 : 0;
            let steer = (outputs[1] * 2) - 1; // -1 to 1

            if (throttle) this.speed += this.acceleration;
            this.speed -= this.friction;
            if (this.speed < 0) this.speed = 0;
            if (this.speed > this.maxSpeed) this.speed = this.maxSpeed;

            if (this.speed > 0) this.angle += steer * 0.05;

            // Move
            this.x += Math.cos(this.angle) * this.speed;
            this.y += Math.sin(this.angle) * this.speed;

            // Collision detection loosely
            if (readings[2] < 10) { // frontline crashed
                this.alive = false;
                this.color = '#444';
            }

            // Score Logic: Progress through checkpoints
            let cp = checkpoints[this.checkIdx];
            let distToCp = Math.hypot(this.x - cp.x, this.y - cp.y);
            if (distToCp < 60) {
                this.checkIdx = (this.checkIdx + 1) % checkpoints.length;
                this.score += 100;
                if (this.checkIdx === 0) this.laps++;
            }
            this.score += this.speed * 0.1; // reward moving fast
        }

        castRay(rayAngle, walls) {
            let dx = Math.cos(rayAngle);
            let dy = Math.sin(rayAngle);
            let minDist = this.rayDist;

            // Cheap raycast vs line segments
            for (let loop of walls) {
                for (let i = 0; i < loop.length; i++) {
                    let p1 = loop[i];
                    let p2 = loop[(i + 1) % loop.length];
                    let d = hitRayLine(this.x, this.y, dx, dy, p1.x, p1.y, p2.x, p2.y);
                    if (d > 0 && d < minDist) minDist = d;
                }
            }
            return minDist;
        }

        draw(ctx) {
            ctx.save();
            ctx.translate(this.x, this.y);
            ctx.rotate(this.angle);
            ctx.fillStyle = this.color;
            ctx.fillRect(-10, -5, 20, 10);

            // Draw headlights for the best alive car
            if (this.alive && bestBrain && this.brain === bestBrain) {
                ctx.fillStyle = 'rgba(255, 255, 100, 0.4)';
                ctx.beginPath();
                ctx.moveTo(10, -3);
                ctx.lineTo(100, -30);
                ctx.lineTo(100, 30);
                ctx.lineTo(10, 3);
                ctx.fill();
            }
            ctx.restore();
        }
    }

    // Geometry intersection
    function hitRayLine(rx, ry, rdx, rdy, px, py, qx, qy) {
        let v1x = rx - px; let v1y = ry - py;
        let v2x = qx - px; let v2y = qy - py;
        let v3x = -rdy; let v3y = rdx;
        let dot = v2x * v3x + v2y * v3y;
        if (Math.abs(dot) < 0.0001) return -1;
        let t1 = (v2x * v1y - v2y * v1x) / dot;
        let t2 = (v1x * v3x + v1y * v3y) / dot;
        if (t1 >= 0 && t2 >= 0 && t2 <= 1) return t1;
        return -1;
    }

    // --- System Setup ---
    function launch(mountId) {
        _mount = document.getElementById(mountId);
        if (!_mount) return;
        _mount.innerHTML = '';

        _canvas = document.createElement('canvas');
        _canvas.width = _mount.clientWidth;
        _canvas.height = _mount.clientHeight;
        _ctx = _canvas.getContext('2d');
        _mount.appendChild(_canvas);

        generation = 1;
        bestBrain = null;
        generateTrack(_canvas.width, _canvas.height);
        initAgents(true);

        // Overlay status text
        const uiLayer = document.createElement('div');
        uiLayer.id = 'racing-ui';
        uiLayer.style.cssText = 'position:absolute; top:15px; left:15px; background:rgba(2,3,10,0.8); border:1px solid #e74c3c; padding:10px; color:#fff; font-family:monospace; font-size:12px; border-radius:6px; pointer-events:none;';
        _mount.appendChild(uiLayer);

        tick();
    }

    function generateTrack(w, h) {
        innerWall = []; outerWall = []; checkpoints = [];
        let cx = w / 2, cy = h / 2, pts = 16;
        let rBase = (Math.min(w, h) / 2) - 40;

        for (let i = 0; i < pts; i++) {
            let ang = (i / pts) * Math.PI * 2;
            let distort = 1 + (Math.random() * 0.4 - 0.2); // bumpy track
            let rxIn = rBase * 0.5 * distort;
            let rxOut = rBase * 0.9 * distort;

            innerWall.push({ x: cx + Math.cos(ang) * rxIn, y: cy + Math.sin(ang) * rxIn });
            outerWall.push({ x: cx + Math.cos(ang) * rxOut, y: cy + Math.sin(ang) * rxOut });
            // check at center of the track
            checkpoints.push({
                x: cx + Math.cos(ang) * (rxIn + rxOut) / 2,
                y: cy + Math.sin(ang) * (rxIn + rxOut) / 2
            });
        }
    }

    function initAgents(fullReset = false) {
        let cp0 = checkpoints[0];
        let pNext = checkpoints[1];
        let startAngle = Math.atan2(pNext.y - cp0.y, pNext.x - cp0.x);

        let newAgents = [];
        for (let i = 0; i < POPULATION_SIZE; i++) {
            let c = new CarAgent(cp0.x, cp0.y);
            c.angle = startAngle;
            if (!fullReset && bestBrain) {
                // Elite survival
                let nn = bestBrain.clone();
                if (i > 0) nn.mutate(0.15); // keep 1 exact copy, mutate the rest
                c.brain = nn;
            }
            newAgents.push(c);
        }
        agents = newAgents;
        bestBrain = agents[0].brain; // mark top player for highlighting
    }

    let frameCount = 0;
    function tick() {
        _animId = requestAnimationFrame(tick);

        // --- Logic ---
        let allDead = true;
        let maxScore = -1;
        let topAgent = null;

        agents.forEach(a => {
            a.update([innerWall, outerWall]);
            if (a.alive) allDead = false;
            if (a.score > maxScore) { maxScore = a.score; topAgent = a; }
        });

        if (topAgent) bestBrain = topAgent.brain;

        frameCount++;
        // Timeout generation after 600 frames to prevent infinite circling
        if (allDead || frameCount > 600) {
            generation++;
            frameCount = 0;
            initAgents(false);
        }

        // --- Render ---
        _ctx.fillStyle = '#111';
        _ctx.fillRect(0, 0, _canvas.width, _canvas.height);

        // draw track
        _ctx.strokeStyle = '#e74c3c';
        _ctx.lineWidth = 3;
        _ctx.beginPath();
        innerWall.forEach((p, i) => i === 0 ? _ctx.moveTo(p.x, p.y) : _ctx.lineTo(p.x, p.y));
        _ctx.closePath(); _ctx.stroke();

        _ctx.strokeStyle = '#ff7675';
        _ctx.beginPath();
        outerWall.forEach((p, i) => i === 0 ? _ctx.moveTo(p.x, p.y) : _ctx.lineTo(p.x, p.y));
        _ctx.closePath(); _ctx.stroke();

        // draw agents
        // sorting so the living ones are drawn on top
        agents.sort((a, b) => a.alive === b.alive ? 0 : a.alive ? 1 : -1).forEach(a => a.draw(_ctx));

        // Update UI
        let aliveCount = agents.filter(a => a.alive).length;
        document.getElementById('racing-ui').innerHTML = `
            <div style="font-weight:bold; color:#e74c3c; margin-bottom:5px;">RACING NEUROEVOLUTION</div>
            <div>GEN: ${generation}</div>
            <div>ALIVE: ${aliveCount} / ${POPULATION_SIZE}</div>
            <div>TOP SCORE: ${Math.floor(maxScore)}</div>
        `;
    }

    function cleanup() {
        if (_animId) cancelAnimationFrame(_animId);
        _animId = null;
        if (_mount) _mount.innerHTML = '';
        _ctx = null;
    }

    return { launch, cleanup };
})();
