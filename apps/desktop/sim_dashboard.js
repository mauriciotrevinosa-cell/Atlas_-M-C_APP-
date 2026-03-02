/**
 * Desktop Simulation Dashboard
 * Runs inside Atlas desktop UI and consumes /api/sim/dashboard/* endpoints.
 */

(function () {
    const state = {
        modules: [],
        moduleVisibility: {},
        moduleArtifacts: {},
        lastSequence: 0,
        pollTimer: null,
        pollMs: 1500
    };

    const els = {
        mode: document.getElementById('desktop-sim-mode'),
        ticker: document.getElementById('desktop-sim-ticker'),
        usePortfolio: document.getElementById('desktop-sim-use-portfolio'),
        interval: document.getElementById('desktop-sim-interval'),
        startBtn: document.getElementById('desktop-sim-start-btn'),
        stopBtn: document.getElementById('desktop-sim-stop-btn'),
        applyBtn: document.getElementById('desktop-sim-apply-btn'),
        status: document.getElementById('desktop-sim-status'),
        moduleToggles: document.getElementById('desktop-sim-module-toggles'),
        modulePanels: document.getElementById('desktop-sim-module-panels'),
        timeline: document.getElementById('desktop-sim-timeline'),
        alerts: document.getElementById('desktop-sim-alerts'),
        runner: document.getElementById('desktop-sim-runner'),
        tick: document.getElementById('desktop-sim-tick'),
        artifacts: document.getElementById('desktop-sim-artifacts'),
        errors: document.getElementById('desktop-sim-errors')
    };

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function setStatus(text, color = '#888') {
        if (!els.status) return;
        els.status.textContent = text;
        els.status.style.color = color;
    }

    function getLocalPortfolioPositions() {
        try {
            const raw = localStorage.getItem('atlas_portfolio');
            if (!raw) return [];
            const parsed = JSON.parse(raw);
            if (!parsed || !Array.isArray(parsed.positions)) return [];
            return parsed.positions
                .map(item => ({
                    symbol: String(item.symbol || '').toUpperCase(),
                    qty: Number(item.qty) || 0,
                    avg_price: Number(item.avg_price) || 0,
                    current_price: Number(item.current_price) || Number(item.avg_price) || 0
                }))
                .filter(item => item.symbol && item.qty > 0 && item.current_price > 0);
        } catch {
            return [];
        }
    }

    async function simApi(path, options = {}) {
        const response = await fetch(path, options);
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            const detail = payload.detail || `${response.status} ${response.statusText}`;
            throw new Error(detail);
        }
        return payload;
    }

    function renderModuleToggles() {
        if (!els.moduleToggles) return;
        els.moduleToggles.innerHTML = '';
        state.modules.forEach(module => {
            const id = module.module_id;
            if (!(id in state.moduleVisibility)) state.moduleVisibility[id] = true;

            const row = document.createElement('label');
            row.style.display = 'flex';
            row.style.alignItems = 'center';
            row.style.gap = '8px';
            row.style.color = '#ddd';
            row.style.fontSize = '13px';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.checked = Boolean(state.moduleVisibility[id]);
            checkbox.addEventListener('change', () => {
                state.moduleVisibility[id] = checkbox.checked;
                renderModulePanels();
            });

            const text = document.createElement('span');
            text.textContent = module.title || id;

            row.appendChild(checkbox);
            row.appendChild(text);
            els.moduleToggles.appendChild(row);
        });
    }

    function updateMetrics(apiState) {
        if (!apiState) return;
        if (els.runner) {
            els.runner.textContent = apiState.running ? 'RUNNING' : 'STOPPED';
            els.runner.style.color = apiState.running ? '#4caf50' : '#ff8a65';
        }
        if (els.tick) els.tick.textContent = String(apiState.tick ?? 0);
        if (els.artifacts) els.artifacts.textContent = String(apiState.artifacts_cached ?? 0);
        if (els.errors) els.errors.textContent = String(apiState.warning_error_events ?? 0);
    }

    function applyApiState(apiState) {
        if (!apiState) return;
        state.lastSequence = Math.max(state.lastSequence, Number(apiState.last_sequence || 0));
        if (Array.isArray(apiState.modules)) {
            state.modules = apiState.modules;
            renderModuleToggles();
        }
        if (apiState.config) {
            if (els.mode && apiState.config.mode) els.mode.value = apiState.config.mode;
            if (els.ticker && apiState.config.ticker) els.ticker.value = apiState.config.ticker;
            if (els.interval && apiState.config.tick_interval_seconds) {
                els.interval.value = String(apiState.config.tick_interval_seconds);
            }
        }
        updateMetrics(apiState);
    }

    function mergeArtifacts(artifacts) {
        artifacts.forEach(artifact => {
            const moduleId = artifact.module_id;
            if (!state.moduleArtifacts[moduleId]) state.moduleArtifacts[moduleId] = [];
            state.moduleArtifacts[moduleId].push(artifact);
            state.moduleArtifacts[moduleId] = state.moduleArtifacts[moduleId].slice(-260);
            state.lastSequence = Math.max(state.lastSequence, Number(artifact.sequence || 0));
        });
    }

    function allArtifactsSorted() {
        const combined = [];
        Object.values(state.moduleArtifacts).forEach(items => combined.push(...items));
        combined.sort((a, b) => Number(a.sequence || 0) - Number(b.sequence || 0));
        return combined;
    }

    function renderTimeline() {
        if (!els.timeline) return;
        const svg = els.timeline;
        const width = svg.clientWidth || 760;
        const height = svg.clientHeight || 140;
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        const artifacts = allArtifactsSorted();
        if (!artifacts.length) {
            svg.innerHTML = `<text x="12" y="${height / 2}" fill="#667" font-size="11">No artifacts yet</text>`;
            return;
        }

        const moduleIds = state.modules.map(m => m.module_id);
        const counts = {};
        moduleIds.forEach(id => { counts[id] = 0; });

        const cumulativeByModule = {};
        moduleIds.forEach(id => { cumulativeByModule[id] = []; });

        artifacts.forEach((artifact, idx) => {
            if (!(artifact.module_id in counts)) counts[artifact.module_id] = 0;
            counts[artifact.module_id] += 1;
            Object.keys(counts).forEach(mid => {
                cumulativeByModule[mid] = cumulativeByModule[mid] || [];
                cumulativeByModule[mid].push({ x: idx, y: counts[mid] });
            });
        });

        const maxY = Math.max(1, ...Object.values(counts));
        const left = 8;
        const right = width - 8;
        const top = 8;
        const bottom = height - 18;
        const plotW = Math.max(1, right - left);
        const plotH = Math.max(1, bottom - top);
        const xScale = index => left + (index / Math.max(1, artifacts.length - 1)) * plotW;
        const yScale = value => bottom - (value / maxY) * plotH;

        const palette = ['#4fc3f7', '#81c784', '#ffb74d', '#ba68c8', '#f06292'];
        const keys = Object.keys(cumulativeByModule);
        const paths = keys.map((moduleId, idx) => {
            const points = cumulativeByModule[moduleId];
            if (!points || !points.length) return '';
            let d = '';
            points.forEach((point, pidx) => {
                d += `${pidx === 0 ? 'M' : 'L'}${xScale(point.x).toFixed(2)} ${yScale(point.y).toFixed(2)} `;
            });
            return `<path d="${d.trim()}" fill="none" stroke="${palette[idx % palette.length]}" stroke-width="2" />`;
        }).join('');

        svg.innerHTML = `
            <rect x="0" y="0" width="${width}" height="${height}" fill="#0b101d"></rect>
            ${paths}
            <text x="${left}" y="${height - 4}" fill="#778" font-size="10">seq ${artifacts[0].sequence} -> ${artifacts[artifacts.length - 1].sequence}</text>
            <text x="${right - 40}" y="12" fill="#778" font-size="10">max ${maxY}</text>
        `;
    }

    function renderAlerts() {
        if (!els.alerts) return;
        const events = allArtifactsSorted()
            .filter(item => item.artifact_type === 'EVENT')
            .filter(item => {
                const sev = String(item.payload?.severity || 'info').toLowerCase();
                return sev === 'warning' || sev === 'error';
            })
            .slice(-6)
            .reverse();

        if (!events.length) {
            els.alerts.innerHTML = '<div style="color:#4caf50;">No warning/error events.</div>';
            return;
        }

        els.alerts.innerHTML = events.map(event => {
            const severity = String(event.payload?.severity || 'info').toLowerCase();
            const color = severity === 'error' ? '#ef5350' : '#ffca28';
            return `
                <div style="padding:6px 8px; margin-bottom:6px; border:1px solid #2b3348; border-radius:6px; background:#111827;">
                    <div style="font-size:11px; color:${color}; text-transform:uppercase;">${severity}</div>
                    <div style="font-size:12px; color:#ddd;">${escapeHtml(event.payload?.message || '')}</div>
                </div>
            `;
        }).join('');
    }

    function renderTimeseriesSvg(points) {
        if (!Array.isArray(points) || points.length < 2) {
            return '<div style="color:#667; font-size:12px;">Not enough points.</div>';
        }
        const w = 460;
        const h = 150;
        const xs = points.map((_, idx) => idx);
        const ys = points.map(point => Number(point.y) || 0);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        const yRange = maxY - minY || 1;
        const xScale = idx => 8 + (idx / Math.max(1, xs.length - 1)) * (w - 16);
        const yScale = val => h - 10 - ((val - minY) / yRange) * (h - 20);

        const path = ys.map((value, idx) =>
            `${idx === 0 ? 'M' : 'L'}${xScale(idx).toFixed(2)} ${yScale(value).toFixed(2)}`
        ).join(' ');

        return `
            <svg viewBox="0 0 ${w} ${h}" width="100%" height="150" style="background:#0b101d; border-radius:8px;">
                <path d="${path}" fill="none" stroke="#4fc3f7" stroke-width="2"></path>
                <text x="10" y="14" fill="#88a" font-size="10">${minY.toFixed(2)} - ${maxY.toFixed(2)}</text>
            </svg>
        `;
    }

    function renderHistogramSvg(bins, counts) {
        if (!Array.isArray(bins) || !Array.isArray(counts) || !bins.length || bins.length !== counts.length) {
            return '<div style="color:#667; font-size:12px;">Invalid histogram payload.</div>';
        }
        const w = 460;
        const h = 150;
        const maxCount = Math.max(1, ...counts.map(v => Number(v) || 0));
        const barW = (w - 20) / bins.length;

        const bars = bins.map((bin, idx) => {
            const c = Number(counts[idx]) || 0;
            const barH = (c / maxCount) * (h - 30);
            const x = 10 + idx * barW;
            const y = h - 18 - barH;
            return `
                <rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${Math.max(4, barW - 8).toFixed(2)}" height="${barH.toFixed(2)}" fill="#81c784"></rect>
                <text x="${(x + (barW / 2)).toFixed(2)}" y="${h - 6}" fill="#88a" font-size="10" text-anchor="middle">${escapeHtml(String(bin))}</text>
            `;
        }).join('');

        return `
            <svg viewBox="0 0 ${w} ${h}" width="100%" height="150" style="background:#0b101d; border-radius:8px;">
                ${bars}
            </svg>
        `;
    }

    function renderArtifactCard(artifact) {
        const type = artifact.artifact_type;
        const payload = artifact.payload || {};
        const title = escapeHtml(artifact.title || type);

        if (type === 'SCALAR') {
            const value = payload.value;
            const unit = payload.unit || '';
            const threshold = Number(payload.threshold);
            const num = Number(value) || 0;
            const min = Number(payload.min);
            const max = Number(payload.max);
            const progress = (isFinite(min) && isFinite(max) && max > min)
                ? Math.max(0, Math.min(100, ((num - min) / (max - min)) * 100))
                : null;
            const delta = isFinite(threshold) ? (num - threshold).toFixed(2) : null;
            return `
                <div style="border:1px solid #2b3348; border-radius:8px; padding:10px; background:#111827;">
                    <div style="font-size:12px; color:#9ab;">${title}</div>
                    <div style="font-size:22px; color:#fff; font-weight:700;">${escapeHtml(String(value))} ${escapeHtml(String(unit))}</div>
                    ${delta !== null ? `<div style="font-size:11px; color:#89a;">vs threshold: ${delta}</div>` : ''}
                    ${progress !== null ? `<div style="margin-top:6px; height:8px; border-radius:4px; background:#223;">
                        <div style="height:8px; width:${progress.toFixed(1)}%; border-radius:4px; background:#4fc3f7;"></div>
                    </div>` : ''}
                </div>
            `;
        }

        if (type === 'TIMESERIES') {
            return `
                <div style="border:1px solid #2b3348; border-radius:8px; padding:10px; background:#111827;">
                    <div style="font-size:12px; color:#9ab; margin-bottom:6px;">${title}</div>
                    ${renderTimeseriesSvg(payload.points || [])}
                </div>
            `;
        }

        if (type === 'HISTOGRAM') {
            return `
                <div style="border:1px solid #2b3348; border-radius:8px; padding:10px; background:#111827;">
                    <div style="font-size:12px; color:#9ab; margin-bottom:6px;">${title}</div>
                    ${renderHistogramSvg(payload.bins || [], payload.counts || [])}
                </div>
            `;
        }

        if (type === 'TABLE') {
            const columns = Array.isArray(payload.columns) ? payload.columns : [];
            const rows = Array.isArray(payload.rows) ? payload.rows : [];
            const head = columns.map(col => `<th style="padding:6px; text-align:left; color:#9ab; font-size:11px;">${escapeHtml(String(col))}</th>`).join('');
            const body = rows.slice(0, 8).map(row => {
                const cells = Array.isArray(row) ? row : columns.map(col => row[col]);
                return `<tr>${cells.map(cell => `<td style="padding:6px; border-top:1px solid #1c2538; color:#ddd; font-size:12px;">${escapeHtml(String(cell))}</td>`).join('')}</tr>`;
            }).join('');
            return `
                <div style="border:1px solid #2b3348; border-radius:8px; padding:10px; background:#111827;">
                    <div style="font-size:12px; color:#9ab; margin-bottom:6px;">${title}</div>
                    <table style="width:100%; border-collapse:collapse;">
                        <thead><tr>${head}</tr></thead>
                        <tbody>${body}</tbody>
                    </table>
                </div>
            `;
        }

        return '';
    }

    function renderModulePanels() {
        if (!els.modulePanels) return;

        const html = state.modules
            .filter(module => state.moduleVisibility[module.module_id] !== false)
            .map(module => {
                const items = state.moduleArtifacts[module.module_id] || [];
                const latestByType = {};
                const events = [];
                const logs = [];

                items.forEach(item => {
                    if (item.artifact_type === 'EVENT') events.push(item);
                    else if (item.artifact_type === 'LOG') logs.push(item);
                    else latestByType[item.artifact_type] = item;
                });

                const cards = ['SCALAR', 'TIMESERIES', 'HISTOGRAM', 'TABLE']
                    .map(type => latestByType[type] ? renderArtifactCard(latestByType[type]) : '')
                    .join('');

                const recentText = [...events.slice(-3), ...logs.slice(-3)].reverse().map(item => {
                    const color = item.artifact_type === 'EVENT'
                        ? (String(item.payload?.severity || '').toLowerCase() === 'error' ? '#ef5350' : '#ffca28')
                        : '#9ab';
                    return `<div style="font-size:11px; color:${color}; margin-top:4px;">
                        [${escapeHtml(String(item.artifact_type))}] ${escapeHtml(String(item.payload?.message || ''))}
                    </div>`;
                }).join('');

                return `
                    <div style="border:1px solid #333; border-radius:10px; padding:20px; background:#0d1422;">
                        <div style="font-size:16px; color:#fff; margin-bottom:6px; font-weight:600;">${escapeHtml(module.title || module.module_id)}</div>
                        <div style="font-size:12px; color:#778; margin-bottom:16px;">${escapeHtml(module.description || '')}</div>
                        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:16px;">
                            ${cards || '<div style="font-size:12px; color:#667;">No artifacts yet.</div>'}
                        </div>
                        <div style="margin-top:12px; padding-top:12px; border-top:1px solid #1c2538;">${recentText}</div>
                    </div>
                `;
            })
            .join('');

        els.modulePanels.innerHTML = html || '<div style="color:#667; font-size:12px;">No visible modules.</div>';
    }

    async function hydrateFromSnapshot() {
        const snapshot = await simApi('/api/sim/dashboard/snapshot');
        applyApiState(snapshot.state);
        state.moduleArtifacts = {};

        (snapshot.modules || []).forEach(module => {
            const moduleId = module.module_id;
            const items = [];
            const latestArtifacts = module.latest_artifacts || {};
            Object.values(latestArtifacts).forEach(artifact => items.push(artifact));
            (module.recent_events || []).forEach(artifact => items.push(artifact));
            (module.recent_logs || []).forEach(artifact => items.push(artifact));
            items.sort((a, b) => Number(a.sequence || 0) - Number(b.sequence || 0));
            state.moduleArtifacts[moduleId] = items.slice(-260);
        });

        renderTimeline();
        renderAlerts();
        renderModulePanels();
    }

    async function pollTick() {
        try {
            const apiState = await simApi('/api/sim/dashboard/state');
            applyApiState(apiState);

            const data = await simApi(`/api/sim/dashboard/artifacts?since_sequence=${state.lastSequence}&limit=500`);
            if (Array.isArray(data.artifacts) && data.artifacts.length) {
                mergeArtifacts(data.artifacts);
                renderTimeline();
                renderAlerts();
                renderModulePanels();
            }
        } catch (err) {
            setStatus(`Simulation API error: ${err.message}`, '#e57373');
        }
    }

    function buildConfigPayload() {
        const mode = els.mode ? els.mode.value : 'stock';
        const ticker = els.ticker ? String(els.ticker.value || 'SPY').toUpperCase() : 'SPY';
        const interval = Number(els.interval ? els.interval.value : 1) || 1;
        const usePortfolio = Boolean(els.usePortfolio && els.usePortfolio.checked);

        const payload = {
            mode,
            ticker,
            tick_interval_seconds: interval,
            use_portfolio: usePortfolio
        };
        if (usePortfolio) payload.positions = getLocalPortfolioPositions();
        return payload;
    }

    async function startSimulation() {
        try {
            setStatus('Starting simulation...', '#9ab');
            const payload = buildConfigPayload();
            const response = await simApi('/api/sim/dashboard/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            applyApiState(response);
            setStatus('Simulation running', '#4caf50');
        } catch (err) {
            setStatus(`Start failed: ${err.message}`, '#e57373');
        }
    }

    async function stopSimulation() {
        try {
            setStatus('Stopping simulation...', '#9ab');
            const response = await simApi('/api/sim/dashboard/stop', { method: 'POST' });
            applyApiState(response);
            setStatus('Simulation stopped', '#ffb74d');
        } catch (err) {
            setStatus(`Stop failed: ${err.message}`, '#e57373');
        }
    }

    async function applyConfig() {
        try {
            setStatus('Applying config...', '#9ab');
            const payload = buildConfigPayload();
            const response = await simApi('/api/sim/dashboard/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            applyApiState(response);
            setStatus('Config updated', '#4caf50');
        } catch (err) {
            setStatus(`Config failed: ${err.message}`, '#e57373');
        }
    }

    function bindEvents() {
        if (els.startBtn) els.startBtn.addEventListener('click', startSimulation);
        if (els.stopBtn) els.stopBtn.addEventListener('click', stopSimulation);
        if (els.applyBtn) els.applyBtn.addEventListener('click', applyConfig);
    }

    async function init() {
        if (!els.mode || !els.modulePanels) return;
        bindEvents();
        try {
            await hydrateFromSnapshot();
            setStatus('Ready', '#9ab');
        } catch (err) {
            setStatus(`Init failed: ${err.message}`, '#e57373');
        }

        if (state.pollTimer) clearInterval(state.pollTimer);
        state.pollTimer = setInterval(pollTick, state.pollMs);
    }

    document.addEventListener('DOMContentLoaded', init);
})();

