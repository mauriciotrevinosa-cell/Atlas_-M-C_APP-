/**
 * Strategy Panel — Multi-Strategy Signal Analysis + Correlation Intelligence
 * ============================================================================
 * Powers the finance view's signal scanner, backtest runner, cluster viewer,
 * market structure analyzer, and pairs trading panel.
 *
 * API routes consumed:
 *   GET /api/strategy/analyze/{ticker}?period=6mo
 *   GET /api/strategy/backtest/{ticker}?period=1y
 *   GET /api/correlation/structure?tickers=...
 *   GET /api/correlation/cluster?tickers=...&n_clusters=4
 *   GET /api/correlation/pairs?tickers=...
 *
 * Copyright (c) 2026 M&C. All rights reserved.
 */

"use strict";

// ── colour helpers ────────────────────────────────────────────────────────────

const _SIGNAL_COLOR = {
  BUY:  { bg: "#0d2a1a", border: "#00c853", text: "#00e676" },
  SELL: { bg: "#2a0d0d", border: "#c62828", text: "#ef5350" },
  HOLD: { bg: "#15171f", border: "#3a3d55", text: "#667799" },
};

function _actionColor(action) {
  return _SIGNAL_COLOR[action?.toUpperCase()] || _SIGNAL_COLOR.HOLD;
}

function _confColor(conf) {
  if (conf >= 0.75) return "#00e676";
  if (conf >= 0.60) return "#ffea00";
  return "#ef5350";
}

// ── API fetch helper ──────────────────────────────────────────────────────────

async function _apiFetch(path, timeoutMs = 30000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(path, { signal: ctrl.signal });
    clearTimeout(timer);
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`HTTP ${res.status}: ${txt.slice(0, 200)}`);
    }
    return await res.json();
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

// ── Strategy Analysis ─────────────────────────────────────────────────────────

const ENGINE_LABELS = {
  sma:        "SMA Crossover",
  rsi_mr:     "RSI Mean-Rev",
  macd:       "MACD",
  bb_squeeze: "BB Squeeze",
  momentum:   "Momentum",
};

const ENGINE_WEIGHTS = {
  sma: 0.15, rsi_mr: 0.25, macd: 0.25, bb_squeeze: 0.20, momentum: 0.15,
};

let _lastStratTicker = null;

async function runStrategyAnalysis() {
  const ticker = (document.getElementById("strat-ticker")?.value || "AAPL").trim().toUpperCase();
  const period = document.getElementById("strat-period")?.value || "6mo";
  const statusEl = document.getElementById("strat-status");
  const btn = document.getElementById("strat-run-btn");

  if (!ticker) return;
  _lastStratTicker = ticker;

  statusEl.textContent = `Fetching ${ticker} data and running 5 engines...`;
  btn.disabled = true;

  // Hide old results
  document.getElementById("strat-consensus").style.display = "none";
  document.getElementById("strat-engines-card").style.display = "none";
  document.getElementById("strat-bt-result").textContent = "";
  document.getElementById("strat-equity-chart").style.display = "none";

  try {
    const data = await _apiFetch(`/api/strategy/analyze/${ticker}?period=${period}`, 40000);
    _renderStrategyResult(data);
    statusEl.textContent = `Analysis complete · ${data.bars_used} bars used`;
  } catch (err) {
    statusEl.textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
}

function _renderStrategyResult(data) {
  const consensus  = data.consensus;
  const individual = data.individual;

  // ── Consensus box ────────────────────────────────────────────────────────
  const consEl   = document.getElementById("strat-consensus");
  const actionEl = document.getElementById("strat-action");
  const barEl    = document.getElementById("strat-conf-bar");
  const confLbl  = document.getElementById("strat-conf-label");
  const reasonEl = document.getElementById("strat-reason");

  const action  = (consensus.action || "HOLD").toUpperCase();
  const conf    = consensus.confidence || 0.50;
  const colors  = _actionColor(action);

  consEl.style.display      = "block";
  consEl.style.borderColor  = colors.border;
  consEl.style.background   = colors.bg;
  actionEl.textContent      = action;
  actionEl.style.color      = colors.text;
  barEl.style.width         = `${Math.round(conf * 100)}%`;
  barEl.style.background    = _confColor(conf);
  confLbl.textContent       = `Confidence ${Math.round(conf * 100)}%`;
  reasonEl.textContent      = consensus.reason || "";

  // ── Per-engine rows ───────────────────────────────────────────────────────
  const engCard = document.getElementById("strat-engines-card");
  const metaEl  = document.getElementById("strat-ticker-meta");
  const rowsEl  = document.getElementById("strat-engine-rows");

  engCard.style.display = "block";
  const price5d = data.return_5d >= 0
    ? `+${data.return_5d}%` : `${data.return_5d}%`;
  const priceColor = data.return_5d >= 0 ? "#00c853" : "#ef5350";

  metaEl.innerHTML = `
    <span style="color:#aaa;">${data.ticker}</span>
    &nbsp;·&nbsp;
    <span style="color:#aaa;">$${data.last_close}</span>
    &nbsp;·&nbsp;5d:
    <span style="color:${priceColor};">${price5d}</span>
    &nbsp;·&nbsp;${data.bars_used} bars
  `;

  rowsEl.innerHTML = "";
  const engineOrder = ["sma", "rsi_mr", "macd", "bb_squeeze", "momentum"];
  engineOrder.forEach(key => {
    const sig    = individual[key] || { action: "HOLD", confidence: 0.50, reason: "" };
    const label  = ENGINE_LABELS[key] || key;
    const weight = ENGINE_WEIGHTS[key] || 0;
    const ec     = _actionColor(sig.action);
    const bar    = Math.round(sig.confidence * 100);

    const row = document.createElement("div");
    row.style.cssText = `
      display:flex; align-items:center; gap:10px;
      padding:8px 10px; border-radius:6px; border:1px solid #1e2030;
      background:#0b0e1a; font-size:12px;
    `;
    row.innerHTML = `
      <div style="width:110px; color:#aaa; flex-shrink:0;">${label}</div>
      <div style="
        min-width:48px; padding:2px 8px; border-radius:4px; text-align:center;
        font-weight:700; font-family:monospace; font-size:11px;
        color:${ec.text}; background:${ec.bg}; border:1px solid ${ec.border};
      ">${(sig.action || "HOLD").toUpperCase()}</div>
      <div style="flex:1; height:4px; border-radius:2px; background:#1a2030; overflow:hidden;">
        <div style="height:100%; width:${bar}%; background:${_confColor(sig.confidence)}; border-radius:2px;"></div>
      </div>
      <div style="color:#667; width:34px; text-align:right;">${bar}%</div>
      <div style="color:#445; width:38px; text-align:right; font-size:10px;">w=${weight}</div>
    `;
    rowsEl.appendChild(row);
  });
}

// ── Backtest ──────────────────────────────────────────────────────────────────

async function runStrategyBacktest() {
  const ticker = _lastStratTicker ||
    (document.getElementById("strat-ticker")?.value || "AAPL").trim().toUpperCase();

  const btEl    = document.getElementById("strat-bt-result");
  const chartEl = document.getElementById("strat-equity-chart");
  btEl.textContent = "Running walk-forward backtest...";
  chartEl.style.display = "none";

  try {
    const data = await _apiFetch(`/api/strategy/backtest/${ticker}?period=1y`, 60000);
    const retColor = data.total_return >= 0 ? "#00e676" : "#ef5350";
    btEl.innerHTML = `
      <span style="color:#aaa;">Return:</span>
      <span style="color:${retColor}; font-weight:700;">${data.total_return > 0 ? "+" : ""}${data.total_return}%</span>
      &nbsp;|&nbsp;
      <span style="color:#aaa;">Sharpe:</span>
      <span style="color:${_confColor(Math.min(1, (data.sharpe + 1) / 3))};">${data.sharpe}</span>
      &nbsp;|&nbsp;
      <span style="color:#aaa;">Max DD:</span>
      <span style="color:#ef5350;">-${data.max_drawdown}%</span>
      &nbsp;|&nbsp;
      <span style="color:#aaa;">Trades:</span> ${data.n_trades}
      &nbsp;·&nbsp;<span style="color:#667;">$${data.initial_cash.toFixed(0)} → $${data.final_equity.toFixed(0)}</span>
    `;
    _drawEquityCurve(chartEl, data.equity_curve, data.initial_cash);
  } catch (err) {
    btEl.textContent = `Backtest error: ${err.message}`;
  }
}

function _drawEquityCurve(canvas, curve, initialCash) {
  if (!curve || curve.length < 2) return;
  canvas.style.display = "block";
  const ctx = canvas.getContext("2d");
  const W = canvas.offsetWidth || 400;
  const H = canvas.offsetHeight || 100;
  canvas.width  = W;
  canvas.height = H;

  const values = curve.map(p => p.equity);
  const minV = Math.min(...values);
  const maxV = Math.max(...values);
  const range = maxV - minV || 1;

  ctx.clearRect(0, 0, W, H);

  // Grid line at initial cash
  const yCash = H - ((initialCash - minV) / range) * H;
  ctx.strokeStyle = "#1e2a3a";
  ctx.lineWidth   = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(0, yCash);
  ctx.lineTo(W, yCash);
  ctx.stroke();
  ctx.setLineDash([]);

  // Equity gradient fill
  const grad = ctx.createLinearGradient(0, 0, 0, H);
  grad.addColorStop(0, "rgba(0,200,120,0.3)");
  grad.addColorStop(1, "rgba(0,200,120,0.02)");

  ctx.beginPath();
  values.forEach((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - minV) / range) * H;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.lineTo(W, H);
  ctx.lineTo(0, H);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Equity line
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = (i / (values.length - 1)) * W;
    const y = H - ((v - minV) / range) * H;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.strokeStyle = values[values.length - 1] >= initialCash ? "#00c853" : "#ef5350";
  ctx.lineWidth   = 1.5;
  ctx.stroke();
}

// ── Market Structure ──────────────────────────────────────────────────────────

async function runStructureAnalysis() {
  const tickers = document.getElementById("struct-tickers")?.value || "SPY,QQQ,GLD,TLT";
  const resultEl = document.getElementById("struct-result");
  resultEl.textContent = "Analyzing market structure...";

  try {
    const data = await _apiFetch(
      `/api/correlation/structure?tickers=${encodeURIComponent(tickers)}&period=1y`, 45000
    );

    const regimeColor = {
      low: "#00e676", normal: "#ffea00", high: "#ff9100", crisis: "#ef5350",
    }[data.current_regime] || "#aaa";

    const topPairsHtml = (data.top_correlated_pairs || [])
      .slice(0, 5)
      .map(p => `<span style="color:#667;">${p.a}↔${p.b}</span> <span style="color:#aaa;">${p.corr}</span>`)
      .join("&nbsp; ");

    resultEl.innerHTML = `
      <div style="margin-bottom:6px;">
        Regime: <span style="color:${regimeColor}; font-weight:700; text-transform:uppercase;">${data.current_regime}</span>
        &nbsp;·&nbsp; Avg corr: <span style="color:#aaa;">${data.avg_correlation?.toFixed(3)}</span>
      </div>
      <div style="margin-bottom:6px;">
        Diversification: <span style="color:${_confColor(data.diversification || 0.5)};">${((data.diversification || 0) * 100).toFixed(1)}%</span>
        ${data.breakdown_detected ? ' &nbsp;<span style="color:#ef5350; font-weight:700;">⚠ Breakdown detected</span>' : ""}
      </div>
      <div style="margin-bottom:6px; color:#667; font-size:11px;">Most central: ${
        Object.entries(data.centrality_rank || {}).slice(0, 3).map(([t]) => t).join(", ")
      }</div>
      <div style="font-size:11px; color:#667;">Top pairs: ${topPairsHtml || "—"}</div>
    `;
  } catch (err) {
    resultEl.textContent = `Error: ${err.message}`;
  }
}

// ── Asset Clustering ──────────────────────────────────────────────────────────

const CLUSTER_COLORS = ["#4488ff", "#00e676", "#ff9100", "#e040fb", "#00bcd4", "#ffea00", "#ef5350", "#80cbc4"];

async function runClusterAnalysis() {
  const tickers   = document.getElementById("cluster-tickers")?.value || "AAPL,MSFT,GOOG";
  const nClusters = parseInt(document.getElementById("cluster-n")?.value || "4", 10);
  const resultEl  = document.getElementById("cluster-result");
  resultEl.textContent = "Clustering assets...";

  try {
    const data = await _apiFetch(
      `/api/correlation/cluster?tickers=${encodeURIComponent(tickers)}&n_clusters=${nClusters}&method=hierarchical&period=6mo`,
      45000
    );

    let html = `
      <div style="margin-bottom:10px; font-size:11px; color:#667;">
        ${data.n_clusters} clusters · silhouette ${data.silhouette_score?.toFixed(3)} ·
        inter-cluster corr ${data.inter_cluster_corr?.toFixed(3)}
      </div>
    `;

    Object.entries(data.cluster_members || {}).forEach(([cid, members]) => {
      const col  = CLUSTER_COLORS[parseInt(cid, 10) % CLUSTER_COLORS.length];
      const intr = data.intra_cluster_corr?.[cid];
      html += `
        <div style="margin-bottom:8px; padding:8px 10px; border-radius:6px; border-left:3px solid ${col}; background:#0b0e1a;">
          <div style="color:${col}; font-size:11px; margin-bottom:4px; font-weight:600;">
            Cluster ${parseInt(cid, 10) + 1}
            ${intr != null ? `<span style="color:#667; font-weight:400;"> · intra-corr ${intr.toFixed(2)}</span>` : ""}
          </div>
          <div style="display:flex; flex-wrap:wrap; gap:4px;">
            ${members.map(t => `<span style="
              padding:2px 7px; border-radius:3px; font-size:11px;
              background:${col}22; color:${col}; border:1px solid ${col}44;
            ">${t}</span>`).join("")}
          </div>
        </div>
      `;
    });

    resultEl.innerHTML = html;
  } catch (err) {
    resultEl.textContent = `Error: ${err.message}`;
  }
}

// ── Pairs Trading ─────────────────────────────────────────────────────────────

async function runPairsAnalysis() {
  const tickers  = document.getElementById("pairs-tickers")?.value || "AAPL,MSFT";
  const resultEl = document.getElementById("pairs-result");
  resultEl.textContent = "Screening for cointegrated pairs...";

  try {
    const data = await _apiFetch(
      `/api/correlation/pairs?tickers=${encodeURIComponent(tickers)}&period=2y&max_pairs=8`,
      60000
    );

    if (!data.pairs || data.pairs.length === 0) {
      resultEl.innerHTML = `<span style="color:#667;">No cointegrated pairs found in the basket. Try more tickers or a longer period.</span>`;
      return;
    }

    let html = `
      <div style="font-size:11px; color:#667; margin-bottom:10px;">
        Screened ${data.tickers_analyzed?.length || 0} assets · ${data.pairs_found} pairs found
      </div>
    `;

    data.pairs.slice(0, 6).forEach(p => {
      const sig     = p.signal;
      const sigType = sig?.type || "NONE";
      const sigColor = {
        LONG_SPREAD:  "#00e676",
        SHORT_SPREAD: "#ef5350",
        EXIT:         "#ffea00",
        STOP:         "#ff9100",
        NONE:         "#667799",
      }[sigType] || "#667799";

      html += `
        <div style="
          padding:8px 10px; margin-bottom:8px; border-radius:6px;
          border:1px solid #1e2030; background:#0b0e1a; font-size:11px;
        ">
          <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
            <span style="color:#ccc; font-weight:600;">${p.ticker_a} / ${p.ticker_b}</span>
            <span style="color:${sigColor}; font-weight:700;">${sigType}</span>
          </div>
          <div style="display:flex; gap:14px; color:#667;">
            <span>corr: <span style="color:#aaa;">${p.correlation?.toFixed(3)}</span></span>
            <span>half-life: <span style="color:#aaa;">${p.half_life?.toFixed(1)}d</span></span>
            ${sig?.z_score != null ? `<span>z-score: <span style="color:${sigColor};">${sig.z_score?.toFixed(2)}</span></span>` : ""}
            ${sig?.confidence != null ? `<span>conf: <span style="color:${_confColor(sig.confidence)};">${Math.round(sig.confidence * 100)}%</span></span>` : ""}
          </div>
        </div>
      `;
    });

    resultEl.innerHTML = html;
  } catch (err) {
    resultEl.textContent = `Error: ${err.message}`;
  }
}
