/**
 * User Decision Panel — Fase 14
 * ================================
 * Human-in-the-loop trade approval workflow.
 * Position sizing calculator with live Kelly + vol inputs.
 *
 * Panels
 * -------
 * 1. Live Signal Summary   — current engine consensus across tickers
 * 2. Position Sizing Calc  — interactive Kelly/risk calculator
 * 3. Trade Approval Queue  — pending orders requiring human confirmation
 * 4. Risk Dashboard        — portfolio-level guardrail status
 *
 * Copyright (c) 2026 M&C. All rights reserved.
 */

window.DecisionModule = (() => {
  "use strict";

  // ── State ──────────────────────────────────────────────────────────────────
  let _pendingOrders = [];  // orders waiting for approval
  let _approvedLog   = [];  // completed approvals
  let _capital       = 100_000;
  let _dailyPnl      = 0;
  let _drawdown      = 0;

  // ── Styles ─────────────────────────────────────────────────────────────────
  function _injectStyles() {
    if (document.getElementById("decision-styles")) return;
    const s = document.createElement("style");
    s.id = "decision-styles";
    s.textContent = `
      #view-decision {
        padding: 16px 16px 80px;  /* 80px bottom clears the 58px nav bar */
        color: #e2e8f0;
        font-family: 'Courier New', monospace;
        background: #0a0e1a;
        min-height: 100vh;
      }
      .dec-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
        flex-wrap: wrap;
      }
      .dec-header h2 {
        margin: 0;
        font-size: 1.4rem;
        color: #10b981;
        letter-spacing: 0.05em;
      }
      .dec-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
        gap: 16px;
      }
      .dec-card {
        background: #111827;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 16px;
      }
      .dec-card h3 {
        margin: 0 0 12px;
        font-size: 0.9rem;
        color: #10b981;
        text-transform: uppercase;
        letter-spacing: 0.1em;
      }
      /* Guardrail status */
      .guardrail-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        background: #0f172a;
        border-radius: 6px;
        margin-bottom: 6px;
        font-size: 0.8rem;
      }
      .guardrail-label { color: #64748b; }
      .guardrail-value { font-weight: bold; }
      .status-ok   { color: #34d399; }
      .status-warn { color: #f59e0b; }
      .status-danger { color: #f87171; }
      /* Position sizing calculator */
      .calc-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 10px;
      }
      .calc-group {
        display: flex;
        flex-direction: column;
        gap: 3px;
        min-width: 90px;
        flex: 1;
      }
      .calc-group label { font-size: 0.65rem; color: #64748b; text-transform: uppercase; }
      .calc-group input, .calc-group select {
        background: #0f172a;
        border: 1px solid #1e293b;
        color: #e2e8f0;
        padding: 5px 8px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.85rem;
      }
      .calc-result {
        background: #0f172a;
        border-radius: 8px;
        padding: 12px;
        margin-top: 10px;
      }
      .calc-result-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        border-bottom: 1px solid #1e293b;
        font-size: 0.82rem;
      }
      .calc-result-row:last-child { border-bottom: none; }
      .calc-result-row span:first-child { color: #64748b; }
      .calc-result-row span:last-child  { color: #e2e8f0; font-weight: bold; }
      .size-highlight { color: #10b981 !important; font-size: 1.1rem; }
      /* Approval queue */
      .order-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-left: 3px solid #f59e0b;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 10px;
      }
      .order-card.approved { border-left-color: #34d399; opacity: 0.7; }
      .order-card.rejected { border-left-color: #f87171; opacity: 0.6; }
      .order-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }
      .order-ticker {
        font-size: 1.1rem;
        font-weight: bold;
        color: #e2e8f0;
      }
      .order-action-BUY  { color: #34d399; font-weight: bold; }
      .order-action-SELL { color: #f87171; font-weight: bold; }
      .order-action-HOLD { color: #94a3b8; }
      .order-details {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 4px;
        font-size: 0.75rem;
        margin-bottom: 10px;
      }
      .order-detail-row { display: flex; gap: 4px; }
      .order-detail-row span:first-child { color: #475569; }
      .order-detail-row span:last-child  { color: #94a3b8; }
      .order-reasoning {
        font-size: 0.7rem;
        color: #475569;
        margin-bottom: 8px;
        line-height: 1.4;
      }
      .order-buttons { display: flex; gap: 8px; }
      .btn-approve {
        background: #065f46;
        color: #34d399;
        border: 1px solid #34d399;
        padding: 5px 14px;
        border-radius: 5px;
        cursor: pointer;
        font-family: monospace;
        font-size: 0.8rem;
        transition: background 0.2s;
      }
      .btn-approve:hover { background: #064e3b; }
      .btn-reject {
        background: #1f1f1f;
        color: #f87171;
        border: 1px solid #f87171;
        padding: 5px 14px;
        border-radius: 5px;
        cursor: pointer;
        font-family: monospace;
        font-size: 0.8rem;
        transition: background 0.2s;
      }
      .btn-reject:hover { background: #300; }
      .btn-modify {
        background: #1e293b;
        color: #f59e0b;
        border: 1px solid #f59e0b;
        padding: 5px 14px;
        border-radius: 5px;
        cursor: pointer;
        font-family: monospace;
        font-size: 0.8rem;
      }
      .empty-queue { color: #475569; font-size: 0.85rem; padding: 16px 0; text-align: center; }
      /* Signal summary */
      .signal-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 10px;
        background: #0f172a;
        border-radius: 5px;
        margin-bottom: 4px;
        font-size: 0.8rem;
      }
      .signal-ticker { color: #e2e8f0; font-weight: bold; min-width: 50px; }
      .signal-vote   { min-width: 50px; text-align: center; }
      .signal-conf   { color: #64748b; font-size: 0.7rem; }
      .vote-LONG  { color: #34d399; }
      .vote-SHORT { color: #f87171; }
      .vote-HOLD  { color: #94a3b8; }
      .conf-bar-wrap { width: 80px; height: 6px; background: #1e293b; border-radius: 3px; overflow:hidden; }
      .conf-bar      { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #10b981, #818cf8); }
      /* Tabs */
      .dec-tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 8px;
      }
      .dec-tab {
        padding: 5px 14px;
        border-radius: 5px 5px 0 0;
        cursor: pointer;
        font-size: 0.8rem;
        color: #64748b;
        border: 1px solid transparent;
        transition: all 0.2s;
      }
      .dec-tab.active {
        color: #10b981;
        border-color: #10b981;
        background: #065f4622;
      }
      .dec-tab:hover:not(.active) { color: #94a3b8; }
      .dec-btn {
        background: linear-gradient(135deg, #065f46, #10b981);
        color: white;
        border: none;
        padding: 6px 14px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.8rem;
        font-family: monospace;
      }
    `;
    document.head.appendChild(s);
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  function _fmt(v, d = 2) {
    const n = parseFloat(v);
    return isNaN(n) ? "—" : n.toFixed(d);
  }

  // ── Position Sizing Calculator ────────────────────────────────────────────
  function _calcPosition() {
    const cap      = parseFloat(document.getElementById("ps-capital")?.value  || 100000);
    const wr       = parseFloat(document.getElementById("ps-winrate")?.value  || 0.55);
    const avgWin   = parseFloat(document.getElementById("ps-avgwin")?.value   || 0.02);
    const avgLoss  = parseFloat(document.getElementById("ps-avgloss")?.value  || 0.01);
    const conf     = parseFloat(document.getElementById("ps-conf")?.value     || 0.65);
    const maxPos   = parseFloat(document.getElementById("ps-maxpos")?.value   || 0.10);
    const vol      = parseFloat(document.getElementById("ps-vol")?.value      || 0.20);
    const tgtVol   = parseFloat(document.getElementById("ps-tgtvol")?.value   || 0.15);

    // Kelly
    const b = avgWin / (avgLoss + 1e-9);
    const q = 1 - wr;
    const rawKelly = ((wr * b - q) / (b + 1e-9)) * 0.5;  // half-Kelly
    const kelly    = Math.max(0, Math.min(rawKelly, 0.25));

    // Vol scalar
    const volScalar = Math.max(0.25, Math.min(tgtVol / (vol + 1e-9), 4.0));

    // Final size
    const rawSize  = kelly * volScalar * conf;
    const sizePct  = Math.min(rawSize, maxPos);
    const sizeDollar = sizePct * cap;
    const riskDollar = sizeDollar * avgLoss;

    // Expectancy
    const expectancy = wr * avgWin - q * avgLoss;

    const box = document.getElementById("ps-result");
    if (!box) return;

    box.innerHTML = `
      <div class="calc-result-row">
        <span>Half-Kelly Fraction</span>
        <span>${(kelly * 100).toFixed(2)}%</span>
      </div>
      <div class="calc-result-row">
        <span>Vol Scalar</span>
        <span>${volScalar.toFixed(3)}×</span>
      </div>
      <div class="calc-result-row">
        <span>Raw Size (Kelly × Vol × Conf)</span>
        <span>${(rawSize * 100).toFixed(2)}%</span>
      </div>
      <div class="calc-result-row">
        <span>Capped Size (max ${(maxPos * 100).toFixed(0)}%)</span>
        <span class="size-highlight">${(sizePct * 100).toFixed(2)}%</span>
      </div>
      <div class="calc-result-row">
        <span>Dollar Amount</span>
        <span class="size-highlight">$${sizeDollar.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
      </div>
      <div class="calc-result-row">
        <span>Risk at Stop (avg loss)</span>
        <span style="color:#f87171">$${riskDollar.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
      </div>
      <div class="calc-result-row">
        <span>Expectancy (per trade %)</span>
        <span style="color:${expectancy >= 0 ? '#34d399' : '#f87171'}">${(expectancy * 100).toFixed(3)}%</span>
      </div>
    `;
  }

  // ── Order Queue ────────────────────────────────────────────────────────────
  async function _loadLiveSignals() {
    const tickers = ["SPY", "QQQ", "AAPL", "TSLA", "BTC-USD"];
    const rows = [];
    for (const tkr of tickers) {
      try {
        const res  = await fetch(`/api/signal/compose/${tkr}?capital=${_capital}`);
        const data = await res.json();
        rows.push({ ticker: tkr, ...data });
        // Add to pending if actionable
        if (data.action !== "HOLD" && !data.blocked) {
          const exists = _pendingOrders.find(o => o.ticker === tkr);
          if (!exists) {
            _pendingOrders.push({
              id:       `ORD-${Date.now()}-${tkr}`,
              ticker:   tkr,
              status:   "pending",
              ...data,
            });
          }
        }
      } catch (_) {
        rows.push({ ticker: tkr, action: "HOLD", confidence: 0, size_pct: 0 });
      }
    }
    _renderSignalSummary(rows);
    _renderQueue();
  }

  function _renderSignalSummary(rows) {
    const box = document.getElementById("signal-summary");
    if (!box) return;
    box.innerHTML = rows.map(r => `
      <div class="signal-row">
        <span class="signal-ticker">${r.ticker}</span>
        <span class="signal-vote vote-${r.action || "HOLD"}">${r.action || "HOLD"}</span>
        <span class="signal-conf">${((r.confidence || 0) * 100).toFixed(0)}%</span>
        <div class="conf-bar-wrap">
          <div class="conf-bar" style="width:${((r.confidence || 0) * 100).toFixed(0)}%"></div>
        </div>
        <span class="signal-conf" style="min-width:48px;text-align:right">${(r.size_pct || 0).toFixed(2)}%</span>
      </div>
    `).join("");
  }

  function _renderQueue() {
    const box = document.getElementById("approval-queue");
    if (!box) return;

    const pending = _pendingOrders.filter(o => o.status === "pending");
    if (!pending.length) {
      box.innerHTML = '<p class="empty-queue">✅ No pending orders</p>';
      return;
    }

    box.innerHTML = pending.map(order => `
      <div class="order-card" id="order-${order.id}">
        <div class="order-header">
          <span class="order-ticker">${order.ticker}</span>
          <span class="order-action-${order.action}">${order.action}</span>
        </div>
        <div class="order-details">
          <div class="order-detail-row">
            <span>Confidence:</span>
            <span>${((order.confidence || 0) * 100).toFixed(1)}%</span>
          </div>
          <div class="order-detail-row">
            <span>Kelly:</span>
            <span>${((order.kelly_fraction || 0) * 100).toFixed(2)}%</span>
          </div>
          <div class="order-detail-row">
            <span>Size:</span>
            <span>${(order.size_pct || 0).toFixed(2)}%</span>
          </div>
          <div class="order-detail-row">
            <span>$ Amount:</span>
            <span>$${Number(order.dollar_amount || 0).toLocaleString()}</span>
          </div>
          <div class="order-detail-row">
            <span>Vol Scalar:</span>
            <span>${(order.vol_scalar || 1).toFixed(3)}×</span>
          </div>
          <div class="order-detail-row">
            <span>Engines:</span>
            <span>${Object.keys(order.engine_votes || {}).length}</span>
          </div>
        </div>
        <div class="order-reasoning">${order.reasoning || ""}</div>
        <div class="order-buttons">
          <button class="btn-approve" onclick="DecisionModule.approve('${order.id}')">✅ Approve</button>
          <button class="btn-reject"  onclick="DecisionModule.reject('${order.id}')">❌ Reject</button>
          <button class="btn-modify"  onclick="DecisionModule.modify('${order.id}')">✏️ Modify</button>
        </div>
      </div>
    `).join("");
  }

  function _approve(id) {
    const order = _pendingOrders.find(o => o.id === id);
    if (!order) return;
    order.status = "approved";
    order.approvedAt = new Date().toISOString();
    _approvedLog.push(order);
    const card = document.getElementById(`order-${id}`);
    if (card) {
      card.classList.add("approved");
      card.querySelector(".order-buttons").innerHTML = `<span style="color:#34d399;font-size:0.8rem">✅ Approved ${new Date().toLocaleTimeString()}</span>`;
    }
    _updateApprovedCount();
  }

  function _reject(id) {
    const order = _pendingOrders.find(o => o.id === id);
    if (!order) return;
    order.status = "rejected";
    const card = document.getElementById(`order-${id}`);
    if (card) {
      card.classList.add("rejected");
      card.querySelector(".order-buttons").innerHTML = `<span style="color:#f87171;font-size:0.8rem">❌ Rejected</span>`;
    }
  }

  function _modify(id) {
    const order = _pendingOrders.find(o => o.id === id);
    if (!order) return;
    const newSize = prompt(`Modify position size % (current: ${(order.size_pct || 0).toFixed(2)}%):`, (order.size_pct || 0).toFixed(2));
    if (newSize === null) return;
    const parsed = parseFloat(newSize);
    if (isNaN(parsed) || parsed < 0) return;
    order.size_pct     = parsed;
    order.dollar_amount = (parsed / 100) * _capital;
    order.reasoning    += ` [Modified: size=${parsed.toFixed(2)}%]`;
    _renderQueue();
  }

  function _updateApprovedCount() {
    const el = document.getElementById("approved-count");
    if (el) el.textContent = `${_approvedLog.length} approved this session`;
  }

  // ── Risk Guardrails Display ───────────────────────────────────────────────
  function _renderGuardrails() {
    const box = document.getElementById("guardrail-box");
    if (!box) return;

    const dailyLimit = 0.02;
    const ddLimit    = 0.10;

    const dailyOk = _dailyPnl > -dailyLimit;
    const ddOk    = _drawdown < ddLimit;

    const dailyCls = _dailyPnl < -dailyLimit * 0.8 ? "status-danger"
                   : _dailyPnl < -dailyLimit * 0.5 ? "status-warn"
                   : "status-ok";
    const ddCls    = _drawdown > ddLimit * 0.8 ? "status-danger"
                   : _drawdown > ddLimit * 0.5 ? "status-warn"
                   : "status-ok";

    box.innerHTML = `
      <div class="guardrail-bar">
        <span class="guardrail-label">Daily P&L</span>
        <span class="guardrail-value ${dailyCls}">${(_dailyPnl * 100).toFixed(2)}%</span>
        <span style="color:#334155;font-size:0.7rem">limit: −${(dailyLimit * 100).toFixed(0)}%</span>
      </div>
      <div class="guardrail-bar">
        <span class="guardrail-label">Drawdown</span>
        <span class="guardrail-value ${ddCls}">${(_drawdown * 100).toFixed(2)}%</span>
        <span style="color:#334155;font-size:0.7rem">limit: ${(ddLimit * 100).toFixed(0)}%</span>
      </div>
      <div class="guardrail-bar">
        <span class="guardrail-label">Capital</span>
        <span class="guardrail-value status-ok">$${_capital.toLocaleString()}</span>
      </div>
      <div class="guardrail-bar">
        <span class="guardrail-label">Trading Status</span>
        <span class="guardrail-value ${dailyOk && ddOk ? 'status-ok' : 'status-danger'}">
          ${dailyOk && ddOk ? '🟢 ACTIVE' : '🔴 BLOCKED'}
        </span>
      </div>
      <div style="margin-top:12px">
        <div class="calc-group" style="margin-bottom:8px">
          <label>Simulate Daily P&L %</label>
          <input type="number" value="${(_dailyPnl * 100).toFixed(2)}" step="0.1"
            oninput="DecisionModule.setDailyPnl(this.value)" />
        </div>
        <div class="calc-group">
          <label>Simulate Drawdown %</label>
          <input type="number" value="${(_drawdown * 100).toFixed(2)}" step="0.1"
            oninput="DecisionModule.setDrawdown(this.value)" />
        </div>
      </div>
    `;
  }

  // ── HTML builder ──────────────────────────────────────────────────────────
  function _buildHTML() {
    const container = document.getElementById("view-decision");
    if (!container || container.dataset.built) return;
    container.dataset.built = "1";

    container.innerHTML = `
      <div class="dec-header">
        <h2>🎯 Decision Center</h2>
        <div class="calc-group" style="max-width:140px">
          <label>Capital ($)</label>
          <input type="number" id="dec-capital" value="100000" step="10000"
            onchange="DecisionModule.setCapital(this.value)" />
        </div>
        <button class="dec-btn" onclick="DecisionModule.refresh()">🔄 Refresh Signals</button>
        <span id="approved-count" style="font-size:0.75rem;color:#64748b"></span>
      </div>

      <div class="dec-grid">

        <!-- Live Signal Summary -->
        <div class="dec-card">
          <h3>📡 Live Signal Summary</h3>
          <div id="signal-summary"><p style="color:#475569;font-size:0.8rem">Loading…</p></div>
        </div>

        <!-- Risk Guardrails -->
        <div class="dec-card">
          <h3>🛡 Risk Guardrails</h3>
          <div id="guardrail-box"></div>
        </div>

        <!-- Position Sizing Calculator -->
        <div class="dec-card" style="grid-column: span 2;">
          <h3>📐 Position Sizing Calculator</h3>
          <div class="calc-row">
            <div class="calc-group">
              <label>Capital ($)</label>
              <input id="ps-capital" type="number" value="100000" step="10000" oninput="DecisionModule.calc()" />
            </div>
            <div class="calc-group">
              <label>Win Rate</label>
              <input id="ps-winrate" type="number" value="0.55" step="0.01" min="0" max="1" oninput="DecisionModule.calc()" />
            </div>
            <div class="calc-group">
              <label>Avg Win %</label>
              <input id="ps-avgwin" type="number" value="0.02" step="0.005" oninput="DecisionModule.calc()" />
            </div>
            <div class="calc-group">
              <label>Avg Loss %</label>
              <input id="ps-avgloss" type="number" value="0.01" step="0.005" oninput="DecisionModule.calc()" />
            </div>
            <div class="calc-group">
              <label>Confidence</label>
              <input id="ps-conf" type="number" value="0.65" step="0.05" min="0" max="1" oninput="DecisionModule.calc()" />
            </div>
            <div class="calc-group">
              <label>Max Position %</label>
              <input id="ps-maxpos" type="number" value="0.10" step="0.01" min="0.01" max="1" oninput="DecisionModule.calc()" />
            </div>
            <div class="calc-group">
              <label>Realised Vol</label>
              <input id="ps-vol" type="number" value="0.20" step="0.01" oninput="DecisionModule.calc()" />
            </div>
            <div class="calc-group">
              <label>Target Vol</label>
              <input id="ps-tgtvol" type="number" value="0.15" step="0.01" oninput="DecisionModule.calc()" />
            </div>
          </div>
          <div class="calc-result" id="ps-result">
            <p style="color:#475569;font-size:0.8rem">Adjust inputs to calculate position size.</p>
          </div>
        </div>

        <!-- Approval Queue -->
        <div class="dec-card" style="grid-column: span 2;">
          <h3>⏳ Trade Approval Queue</h3>
          <div id="approval-queue"><p class="empty-queue">Loading signals…</p></div>
        </div>

      </div>
    `;
  }

  // ── Public API ─────────────────────────────────────────────────────────────
  async function init() {
    _injectStyles();
    _buildHTML();
    _renderGuardrails();
    _calcPosition();
    await _loadLiveSignals();
  }

  async function refresh() {
    // Clear pending (keep approved/rejected)
    _pendingOrders = _pendingOrders.filter(o => o.status !== "pending");
    await _loadLiveSignals();
    _renderGuardrails();
  }

  function calc() { _calcPosition(); }

  function approve(id) { _approve(id); }
  function reject(id)  { _reject(id);  }
  function modify(id)  { _modify(id);  }

  function setCapital(val) {
    _capital = parseFloat(val) || 100000;
    const psEl = document.getElementById("ps-capital");
    if (psEl) psEl.value = _capital;
    _calcPosition();
  }

  function setDailyPnl(val) {
    _dailyPnl = parseFloat(val) / 100 || 0;
    _renderGuardrails();
  }

  function setDrawdown(val) {
    _drawdown = parseFloat(val) / 100 || 0;
    _renderGuardrails();
  }

  return { init, refresh, calc, approve, reject, modify, setCapital, setDailyPnl, setDrawdown };
})();
