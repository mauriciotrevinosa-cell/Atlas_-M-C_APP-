/**
 * Derivatives Dashboard — Fase 12.4
 * ====================================
 * Black-Scholes options analytics UI.
 * Fully offline — derives IV from realised vol.
 *
 * Panels
 * -------
 * 1. Greeks Calculator   — manual S/K/T/σ inputs, live recalc
 * 2. Options Chain       — ATM ± 5 strikes, call/put table with heatmap
 * 3. IV Surface          — Canvas 2D surface plot (expiry × strike)
 * 4. Synthetics Panel    — Straddle / Strangle / Spread P&L profiles
 * 5. Signal Composer     — Kelly + vol-scaling position sizing
 *
 * Copyright (c) 2026 M&C. All rights reserved.
 */

window.DerivativesModule = (() => {
  "use strict";

  // ── State ──────────────────────────────────────────────────────────────────
  let _ticker   = "SPY";
  let _chain    = null;
  let _surface  = null;
  let _greeks   = null;
  let _composer = null;

  // ── CSS injection ──────────────────────────────────────────────────────────
  function _injectStyles() {
    if (document.getElementById("deriv-styles")) return;
    const style = document.createElement("style");
    style.id = "deriv-styles";
    style.textContent = `
      #view-derivatives {
        padding: 16px 16px 80px;  /* 80px bottom clears the 58px nav bar */
        color: #e2e8f0;
        font-family: 'Courier New', monospace;
        background: #0a0e1a;
        min-height: 100vh;
      }
      .deriv-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
        flex-wrap: wrap;
      }
      .deriv-header h2 {
        margin: 0;
        font-size: 1.4rem;
        color: #a78bfa;
        letter-spacing: 0.05em;
      }
      .deriv-ticker-input {
        background: #1e293b;
        border: 1px solid #334155;
        color: #e2e8f0;
        padding: 6px 12px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 1rem;
        width: 100px;
        text-transform: uppercase;
      }
      .deriv-btn {
        background: linear-gradient(135deg, #7c3aed, #4f46e5);
        color: white;
        border: none;
        padding: 7px 16px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.85rem;
        font-family: monospace;
        transition: opacity 0.2s;
      }
      .deriv-btn:hover { opacity: 0.85; }
      .deriv-btn.secondary {
        background: #1e293b;
        border: 1px solid #4f46e5;
        color: #a78bfa;
      }
      .deriv-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
        gap: 16px;
      }
      .deriv-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px;
      }
      .deriv-card h3 {
        margin: 0 0 12px;
        font-size: 0.9rem;
        color: #818cf8;
        text-transform: uppercase;
        letter-spacing: 0.1em;
      }
      /* Greeks grid */
      .greeks-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }
      .greek-box {
        background: #0f172a;
        border-radius: 6px;
        padding: 10px;
        text-align: center;
      }
      .greek-label {
        font-size: 0.7rem;
        color: #64748b;
        margin-bottom: 4px;
      }
      .greek-value {
        font-size: 1.3rem;
        font-weight: bold;
        color: #e2e8f0;
      }
      .greek-value.positive { color: #34d399; }
      .greek-value.negative { color: #f87171; }
      /* Inputs row */
      .input-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 12px;
      }
      .input-group {
        display: flex;
        flex-direction: column;
        gap: 3px;
        min-width: 80px;
      }
      .input-group label {
        font-size: 0.65rem;
        color: #64748b;
        text-transform: uppercase;
      }
      .input-group input, .input-group select {
        background: #0f172a;
        border: 1px solid #1e293b;
        color: #e2e8f0;
        padding: 4px 8px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.85rem;
        width: 100%;
      }
      /* Chain table */
      .chain-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.75rem;
      }
      .chain-table th {
        background: #1e293b;
        color: #818cf8;
        padding: 5px 8px;
        text-align: right;
        font-weight: normal;
        letter-spacing: 0.05em;
      }
      .chain-table td {
        padding: 4px 8px;
        text-align: right;
        border-bottom: 1px solid #0f172a;
        transition: background 0.15s;
      }
      .chain-table tr:hover td { background: #1e293b55; }
      .chain-table .atm { background: #1e1b4b44; }
      .chain-table .strike-col { color: #a78bfa; font-weight: bold; }
      .chain-table .call-col { color: #34d399; }
      .chain-table .put-col  { color: #f87171; }
      /* Surface canvas */
      #surface-canvas {
        width: 100%;
        height: 260px;
        border-radius: 6px;
        background: #0a0e1a;
      }
      /* Synthetics */
      .synth-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }
      .synth-box {
        background: #0f172a;
        border-radius: 6px;
        padding: 10px;
      }
      .synth-box h4 {
        margin: 0 0 6px;
        font-size: 0.75rem;
        color: #818cf8;
        text-transform: uppercase;
      }
      .synth-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.75rem;
        margin-bottom: 3px;
        color: #94a3b8;
      }
      .synth-row span:last-child { color: #e2e8f0; }
      /* Composer */
      .composer-row {
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px solid #1e293b;
        font-size: 0.8rem;
        color: #94a3b8;
      }
      .composer-row span:last-child { color: #e2e8f0; }
      .composer-action-BUY  { color: #34d399 !important; font-weight: bold; }
      .composer-action-SELL { color: #f87171 !important; font-weight: bold; }
      .composer-action-HOLD { color: #94a3b8 !important; }
      /* Scenario table */
      .scenario-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.75rem;
        margin-top: 10px;
      }
      .scenario-table th {
        color: #818cf8;
        text-align: right;
        padding: 4px 6px;
        font-weight: normal;
        border-bottom: 1px solid #1e293b;
      }
      .scenario-table td {
        text-align: right;
        padding: 3px 6px;
        color: #94a3b8;
      }
      .scenario-table td:first-child { color: #e2e8f0; }
      .loading-text { color: #475569; font-style: italic; font-size: 0.8rem; }
      .badge-synth {
        background: #f59e0b22;
        color: #f59e0b;
        border: 1px solid #f59e0b44;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.65rem;
        margin-left: 8px;
      }
    `;
    document.head.appendChild(style);
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  function _fmt(val, decimals = 4) {
    if (val == null) return "—";
    const n = parseFloat(val);
    return isNaN(n) ? "—" : n.toFixed(decimals);
  }
  function _colorClass(val) {
    const n = parseFloat(val);
    if (isNaN(n) || n === 0) return "";
    return n > 0 ? "positive" : "negative";
  }

  async function _fetchJSON(url) {
    // Resolve relative paths to the Python backend
    const resolvedUrl = url.startsWith('/') ? `${CONFIG.serverUrl}${url}` : url;
    const res = await fetch(resolvedUrl);
    const raw = await res.text();
    let data = null;
    if (raw) {
      try {
        data = JSON.parse(raw);
      } catch (_) {
        data = null;
      }
    }

    if (!res.ok) {
      const msg =
        (data && (data.detail || data.error || data.message)) ||
        raw ||
        `${res.status} ${res.statusText}`;
      throw new Error(msg);
    }

    if (data == null) {
      throw new Error(raw || `Invalid JSON response (${res.status})`);
    }
    return data;
  }

  // ── Greeks Calculator ──────────────────────────────────────────────────────
  async function _loadGreeks() {
    const card = document.getElementById("deriv-greeks-card");
    if (!card) return;

    const S     = parseFloat(document.getElementById("g-spot")?.value || 100);
    const K     = parseFloat(document.getElementById("g-strike")?.value || 100);
    const T_d   = parseFloat(document.getElementById("g-expiry")?.value || 30);
    const sigma = parseFloat(document.getElementById("g-sigma")?.value || 0.20);
    const r     = parseFloat(document.getElementById("g-rate")?.value || 0.05);
    const otype = document.getElementById("g-type")?.value || "call";

    const T = T_d / 365;
    try {
      const data = await _fetchJSON(
        `/api/options/greeks?S=${S}&K=${K}&T=${T}&sigma=${sigma}&r=${r}&option_type=${otype}`
      );
      _greeks    = data;
      _renderGreeks(data);
    } catch (e) {
      console.error("Greeks fetch error:", e);
    }
  }

  function _renderGreeks(data) {
    const g = data.greeks || {};
    const synthBox = document.getElementById("deriv-synth-box");

    document.getElementById("g-price-val").textContent = _fmt(g.price, 2);
    document.getElementById("g-delta-val").textContent = _fmt(g.delta);
    document.getElementById("g-gamma-val").textContent = _fmt(g.gamma);
    document.getElementById("g-theta-val").textContent = _fmt(g.theta, 4);
    document.getElementById("g-vega-val").textContent  = _fmt(g.vega, 4);
    document.getElementById("g-rho-val").textContent   = _fmt(g.rho, 4);

    // Colour
    ["delta", "theta", "rho"].forEach(k => {
      const el = document.getElementById(`g-${k}-val`);
      if (el) el.className = "greek-value " + _colorClass(g[k]);
    });

    // Synthetics
    if (synthBox && data.synthetics) {
      _renderSynthetics(data.synthetics, synthBox);
    }
  }

  // ── Options Chain ──────────────────────────────────────────────────────────
  async function _loadChain() {
    const expiry = parseInt(document.getElementById("chain-expiry")?.value || 30);
    const n      = parseInt(document.getElementById("chain-strikes")?.value || 11);
    const chainBody = document.getElementById("chain-body");
    if (chainBody) chainBody.innerHTML = '<tr><td colspan="7" class="loading-text">Loading chain…</td></tr>';

    try {
      _chain = await _fetchJSON(`/api/options/chain/${_ticker}?expiry_days=${expiry}&n_strikes=${n}`);
      _renderChain(_chain);
      // Update Greeks spot with live spot
      const spotEl = document.getElementById("g-spot");
      if (spotEl && _chain.spot) spotEl.value = _chain.spot.toFixed(2);
      const strikeEl = document.getElementById("g-strike");
      if (strikeEl && _chain.spot) strikeEl.value = _chain.spot.toFixed(2);
    } catch (e) {
      const msg = e && e.message ? e.message : String(e);
      if (chainBody) chainBody.innerHTML = `<tr><td colspan="7" style="color:#f87171">${msg}</td></tr>`;
    }
  }

  function _renderChain(data) {
    const body = document.getElementById("chain-body");
    if (!body) return;
    const spot   = data.spot || 0;
    const strikes = data.strikes || [];

    body.innerHTML = strikes.map(row => {
      const isATM = Math.abs(row.strike - spot) / (spot + 1e-6) < 0.02;
      const cls   = isATM ? "atm" : "";
      const c     = row.call || {};
      const p     = row.put  || {};
      return `
        <tr class="${cls}">
          <td class="call-col">${_fmt(c.price, 2)}</td>
          <td class="call-col">${_fmt(c.delta, 3)}</td>
          <td class="call-col">${_fmt(c.gamma, 4)}</td>
          <td class="strike-col">${_fmt(row.strike, 2)}</td>
          <td class="put-col">${_fmt(p.delta, 3)}</td>
          <td class="put-col">${_fmt(p.gamma, 4)}</td>
          <td class="put-col">${_fmt(p.price, 2)}</td>
        </tr>`;
    }).join("");

    // Update atm_iv display
    const ivEl = document.getElementById("chain-atm-iv");
    if (ivEl) ivEl.textContent = `ATM IV: ${((data.atm_iv || 0) * 100).toFixed(1)}%`;
  }

  // ── IV Surface ────────────────────────────────────────────────────────────
  async function _loadSurface() {
    const canvas = document.getElementById("surface-canvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#475569";
    ctx.font = "13px monospace";
    ctx.fillText("Loading surface…", 20, 30);

    try {
      _surface = await _fetchJSON(`/api/options/surface/${_ticker}`);
      _renderSurface(_surface, canvas);
    } catch (e) {
      const msg = e && e.message ? e.message : String(e);
      ctx.fillStyle = "#f87171";
      ctx.fillText(`Error: ${msg}`, 20, 30);
    }
  }

  function _renderSurface(data, canvas) {
    const ctx = canvas.getContext("2d");
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const grid     = data.iv_grid || [];
    const strikes  = data.strikes || [];
    const expiries = data.expiries || [];
    if (!grid.length || !strikes.length) return;

    const nT = grid.length;
    const nK = grid[0].length;

    // Find IV range
    let minIV = Infinity, maxIV = -Infinity;
    grid.forEach(row => row.forEach(v => {
      if (v < minIV) minIV = v;
      if (v > maxIV) maxIV = v;
    }));

    const pad = { l: 48, r: 16, t: 24, b: 36 };
    const pW  = W - pad.l - pad.r;
    const pH  = H - pad.t - pad.b;
    const cellW = pW / nK;
    const cellH = pH / nT;

    // Colour: low IV = deep blue, high IV = bright red/orange
    function ivColor(iv) {
      const t = (iv - minIV) / (maxIV - minIV + 1e-9);
      const r = Math.round(20  + t * 235);
      const g = Math.round(100 - t * 80);
      const b = Math.round(200 - t * 160);
      return `rgb(${r},${g},${b})`;
    }

    // Draw cells
    for (let ti = 0; ti < nT; ti++) {
      for (let ki = 0; ki < nK; ki++) {
        const x = pad.l + ki * cellW;
        const y = pad.t + ti * cellH;
        const iv = grid[ti][ki];
        ctx.fillStyle = ivColor(iv);
        ctx.fillRect(x, y, cellW - 1, cellH - 1);
        // Label only in larger cells
        if (cellW > 40 && cellH > 20) {
          ctx.fillStyle = "rgba(255,255,255,0.7)";
          ctx.font = "9px monospace";
          ctx.fillText((iv * 100).toFixed(0) + "%", x + 4, y + cellH - 6);
        }
      }
    }

    // Axes
    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px monospace";

    // Y axis — expiries
    for (let ti = 0; ti < nT; ti++) {
      const y = pad.t + ti * cellH + cellH / 2;
      const days = Math.round((expiries[ti] || 0) * 365);
      ctx.fillText(`${days}d`, 2, y + 4);
    }

    // X axis — strikes
    for (let ki = 0; ki < nK; ki += Math.ceil(nK / 4)) {
      const x = pad.l + ki * cellW;
      ctx.fillText(_fmt(strikes[ki], 0), x, H - 4);
    }

    // Title
    ctx.fillStyle = "#818cf8";
    ctx.font = "11px monospace";
    ctx.fillText(`${_ticker} IV Surface (${data.synthetic ? "synthetic" : "live"})`, pad.l, 16);
  }

  // ── Synthetics ────────────────────────────────────────────────────────────
  function _renderSynthetics(synths, container) {
    if (!container) return;
    const boxes = [
      { key: "straddle",   label: "Straddle" },
      { key: "strangle",   label: "Strangle" },
      { key: "bull_spread",label: "Bull Spread" },
      { key: "bear_spread",label: "Bear Spread" },
    ];
    container.innerHTML = `<div class="synth-grid">${boxes.map(({ key, label }) => {
      const s = synths[key] || {};
      const rows = Object.entries(s).map(([k, v]) =>
        `<div class="synth-row">
          <span>${k.replace(/_/g, " ")}</span>
          <span>${typeof v === "number" ? v.toFixed(4) : v}</span>
        </div>`
      ).join("");
      return `<div class="synth-box"><h4>${label}</h4>${rows}</div>`;
    }).join("")}</div>`;
  }

  // ── Signal Composer ────────────────────────────────────────────────────────
  async function _loadComposer() {
    const box = document.getElementById("composer-result");
    if (box) box.innerHTML = '<p class="loading-text">Composing signals…</p>';
    const capital = parseFloat(document.getElementById("composer-capital")?.value || 100000);

    try {
      _composer = await _fetchJSON(`/api/signal/compose/${_ticker}?capital=${capital}`);
      _renderComposer(_composer);
    } catch (e) {
      const msg = e && e.message ? e.message : String(e);
      if (box) box.innerHTML = `<p style="color:#f87171">Error: ${msg}</p>`;
    }
  }

  function _renderComposer(data) {
    const box = document.getElementById("composer-result");
    if (!box) return;

    const actionCls = `composer-action-${data.action}`;

    const votesHTML = Object.entries(data.engine_votes || {}).map(([eng, vote]) =>
      `<div class="composer-row">
        <span>${eng}</span>
        <span class="composer-action-${vote}">${vote}</span>
      </div>`
    ).join("");

    const scenRows = (data.scenarios || []).map(s =>
      `<tr>
        <td>${(s.confidence * 100).toFixed(0)}%</td>
        <td>${(s.kelly * 100).toFixed(1)}%</td>
        <td>${s.size_pct.toFixed(2)}%</td>
        <td>$${Number(s.dollar).toLocaleString()}</td>
      </tr>`
    ).join("");

    box.innerHTML = `
      <div class="composer-row">
        <span>Action</span>
        <span class="${actionCls}">${data.action}</span>
      </div>
      <div class="composer-row">
        <span>Confidence</span>
        <span>${((data.confidence || 0) * 100).toFixed(1)}%</span>
      </div>
      <div class="composer-row">
        <span>Kelly Fraction</span>
        <span>${((data.kelly_fraction || 0) * 100).toFixed(2)}%</span>
      </div>
      <div class="composer-row">
        <span>Vol Scalar</span>
        <span>${(data.vol_scalar || 1).toFixed(3)}×</span>
      </div>
      <div class="composer-row">
        <span>Size</span>
        <span>${(data.size_pct || 0).toFixed(2)}%</span>
      </div>
      <div class="composer-row">
        <span>$ Amount</span>
        <span>$${Number(data.dollar_amount || 0).toLocaleString()}</span>
      </div>
      ${data.blocked ? `<div style="color:#f87171;margin-top:6px">⛔ ${data.block_reason}</div>` : ""}
      <div style="margin-top:10px;margin-bottom:6px;color:#64748b;font-size:0.7rem">ENGINE VOTES</div>
      ${votesHTML}
      <div style="margin-top:10px;color:#64748b;font-size:0.7rem;margin-bottom:4px">SIZING SCENARIOS</div>
      <table class="scenario-table">
        <tr><th>Conf</th><th>Kelly</th><th>Size%</th><th>$</th></tr>
        ${scenRows}
      </table>
      <div style="margin-top:8px;font-size:0.7rem;color:#64748b">${data.reasoning || ""}</div>
    `;
  }

  // ── HTML builder ──────────────────────────────────────────────────────────
  function _buildHTML() {
    const container = document.getElementById("view-derivatives");
    if (!container || container.dataset.built) return;
    container.dataset.built = "1";

    container.innerHTML = `
      <div class="deriv-header">
        <h2>⚡ Derivatives & Signal Analytics</h2>
        <input id="deriv-ticker" class="deriv-ticker-input" value="${_ticker}" placeholder="Ticker" />
        <button class="deriv-btn" onclick="DerivativesModule.setTicker()">Load</button>
        <span class="badge-synth" id="deriv-synth-badge"></span>
      </div>

      <div class="deriv-grid">

        <!-- Greeks Calculator -->
        <div class="deriv-card">
          <h3>📐 Greeks Calculator</h3>
          <div class="input-row">
            <div class="input-group">
              <label>Spot (S)</label>
              <input id="g-spot" type="number" value="100" step="0.01" onchange="DerivativesModule.calcGreeks()" />
            </div>
            <div class="input-group">
              <label>Strike (K)</label>
              <input id="g-strike" type="number" value="100" step="0.01" onchange="DerivativesModule.calcGreeks()" />
            </div>
            <div class="input-group">
              <label>Expiry (days)</label>
              <input id="g-expiry" type="number" value="30" min="1" max="730" onchange="DerivativesModule.calcGreeks()" />
            </div>
            <div class="input-group">
              <label>IV (σ)</label>
              <input id="g-sigma" type="number" value="0.20" step="0.01" min="0.01" max="5" onchange="DerivativesModule.calcGreeks()" />
            </div>
            <div class="input-group">
              <label>Rate (r)</label>
              <input id="g-rate" type="number" value="0.05" step="0.005" onchange="DerivativesModule.calcGreeks()" />
            </div>
            <div class="input-group">
              <label>Type</label>
              <select id="g-type" onchange="DerivativesModule.calcGreeks()">
                <option value="call">Call</option>
                <option value="put">Put</option>
              </select>
            </div>
          </div>
          <div class="greeks-grid">
            <div class="greek-box">
              <div class="greek-label">Price</div>
              <div class="greek-value" id="g-price-val">—</div>
            </div>
            <div class="greek-box">
              <div class="greek-label">Delta (Δ)</div>
              <div class="greek-value" id="g-delta-val">—</div>
            </div>
            <div class="greek-box">
              <div class="greek-label">Gamma (Γ)</div>
              <div class="greek-value" id="g-gamma-val">—</div>
            </div>
            <div class="greek-box">
              <div class="greek-label">Theta (Θ/day)</div>
              <div class="greek-value" id="g-theta-val">—</div>
            </div>
            <div class="greek-box">
              <div class="greek-label">Vega (ν/1%)</div>
              <div class="greek-value" id="g-vega-val">—</div>
            </div>
            <div class="greek-box">
              <div class="greek-label">Rho (ρ/1%)</div>
              <div class="greek-value" id="g-rho-val">—</div>
            </div>
          </div>
        </div>

        <!-- Synthetic Positions -->
        <div class="deriv-card">
          <h3>🔀 Synthetic Positions</h3>
          <div id="deriv-synth-box"><p class="loading-text">Calculate Greeks first</p></div>
        </div>

        <!-- Options Chain -->
        <div class="deriv-card" style="grid-column: span 2;">
          <h3>📊 Options Chain <span id="chain-atm-iv" style="font-size:0.75rem;color:#94a3b8;margin-left:8px"></span></h3>
          <div class="input-row">
            <div class="input-group">
              <label>Expiry (days)</label>
              <input id="chain-expiry" type="number" value="30" min="1" max="365" />
            </div>
            <div class="input-group">
              <label>Strikes</label>
              <input id="chain-strikes" type="number" value="11" min="3" max="21" />
            </div>
            <button class="deriv-btn secondary" onclick="DerivativesModule.loadChain()" style="align-self:flex-end">Refresh</button>
          </div>
          <div style="overflow-x:auto">
            <table class="chain-table">
              <thead>
                <tr>
                  <th class="call-col">Call Price</th>
                  <th class="call-col">Call Δ</th>
                  <th class="call-col">Call Γ</th>
                  <th class="strike-col">Strike</th>
                  <th class="put-col">Put Δ</th>
                  <th class="put-col">Put Γ</th>
                  <th class="put-col">Put Price</th>
                </tr>
              </thead>
              <tbody id="chain-body">
                <tr><td colspan="7" class="loading-text">Loading…</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- IV Surface -->
        <div class="deriv-card">
          <h3>🌋 IV Surface</h3>
          <button class="deriv-btn secondary" onclick="DerivativesModule.loadSurface()" style="margin-bottom:8px">Refresh</button>
          <canvas id="surface-canvas" width="640" height="260"></canvas>
        </div>

        <!-- Signal Composer -->
        <div class="deriv-card">
          <h3>⚖️ Signal Composer (Kelly + Vol)</h3>
          <div class="input-row">
            <div class="input-group">
              <label>Capital ($)</label>
              <input id="composer-capital" type="number" value="100000" step="10000" />
            </div>
            <button class="deriv-btn" onclick="DerivativesModule.loadComposer()" style="align-self:flex-end">Compose</button>
          </div>
          <div id="composer-result"><p class="loading-text">Click Compose to run</p></div>
        </div>

      </div>
    `;
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  async function init() {
    _injectStyles();
    _buildHTML();
    const tickerEl = document.getElementById("deriv-ticker");
    if (tickerEl) _ticker = tickerEl.value.toUpperCase() || "SPY";
    await Promise.all([_loadChain(), _loadSurface(), _loadGreeks()]);
  }

  async function setTicker() {
    const el = document.getElementById("deriv-ticker");
    if (el) _ticker = el.value.toUpperCase().trim() || "SPY";
    await Promise.all([_loadChain(), _loadSurface(), _loadComposer()]);
  }

  async function calcGreeks() {
    await _loadGreeks();
  }

  async function loadChain() {
    await _loadChain();
  }

  async function loadSurface() {
    await _loadSurface();
  }

  async function loadComposer() {
    await _loadComposer();
  }

  return { init, setTicker, calcGreeks, loadChain, loadSurface, loadComposer };
})();
