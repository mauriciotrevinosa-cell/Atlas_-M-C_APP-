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
 *   GET /api/analytics/summary/{ticker}
 *   GET /api/analytics/correlation?tickers=...
 *   POST /api/risk/portfolio/assess
 *   POST /api/montecarlo/portfolio/simulate
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

async function _apiFetch(path, timeoutMs = 30000, options = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const fetchOptions = { ...options, signal: ctrl.signal };
    const res = await fetch(path, fetchOptions);
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
  ml_xgboost: "🤖 XGBoost ML",
  ml_rf:      "🌲 Random Forest",
};

const ENGINE_WEIGHTS = {
  sma: 0.15, rsi_mr: 0.25, macd: 0.25, bb_squeeze: 0.20, momentum: 0.15,
  ml_xgboost: 0.25, ml_rf: 0.15,
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
  const _diagReset = document.getElementById("strat-diagnostics");
  if (_diagReset) _diagReset.style.display = "none";

  try {
    const data = await _apiFetch(`/api/strategy/analyze/${ticker}?period=${period}`, 40000);
    _renderStrategyResult(data);
    const mlCount = data.ml_signals || 0;
    const mlNote  = mlCount > 0 ? ` · ${mlCount} ML engine${mlCount > 1 ? "s" : ""} active` : " · ML engines untrained";
    statusEl.textContent = `Analysis complete · ${data.bars_used} bars used${mlNote}`;
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

  function _appendEngineRow(key, sectionLabel) {
    if (sectionLabel) {
      const sep = document.createElement("div");
      sep.style.cssText = "font-size:10px; color:#445; text-transform:uppercase; letter-spacing:1px; margin-top:6px; padding:0 2px;";
      sep.textContent = sectionLabel;
      rowsEl.appendChild(sep);
    }
    const sig    = individual[key] || { action: "HOLD", confidence: 0.50, reason: "" };
    const label  = ENGINE_LABELS[key] || key;
    const weight = ENGINE_WEIGHTS[key] || 0;
    const ec     = _actionColor(sig.action);
    const bar    = Math.round(sig.confidence * 100);
    const row = document.createElement("div");
    row.style.cssText = "display:flex; align-items:center; gap:10px; padding:8px 10px; border-radius:6px; border:1px solid #1e2030; background:#0b0e1a; font-size:12px;";
    row.innerHTML = `
      <div style="width:118px; color:#aaa; flex-shrink:0;">${label}</div>
      <div style="min-width:48px; padding:2px 8px; border-radius:4px; text-align:center; font-weight:700; font-family:monospace; font-size:11px; color:${ec.text}; background:${ec.bg}; border:1px solid ${ec.border};">${(sig.action || "HOLD").toUpperCase()}</div>
      <div style="flex:1; height:4px; border-radius:2px; background:#1a2030; overflow:hidden;"><div style="height:100%; width:${bar}%; background:${_confColor(sig.confidence)}; border-radius:2px;"></div></div>
      <div style="color:#667; width:34px; text-align:right;">${bar}%</div>
      <div style="color:#445; width:38px; text-align:right; font-size:10px;">w=${weight}</div>
    `;
    rowsEl.appendChild(row);
  }

  ["sma", "rsi_mr", "macd", "bb_squeeze", "momentum"].forEach((key, i) => {
    _appendEngineRow(key, i === 0 ? "Rule-Based Engines" : null);
  });

  // ML engines — only render if they exist in individual dict
  const mlKeys = ["ml_xgboost", "ml_rf"].filter(k => individual[k]);
  if (mlKeys.length > 0) {
    mlKeys.forEach((key, i) => _appendEngineRow(key, i === 0 ? "ML Engines" : null));
  } else {
    const hint = document.createElement("div");
    hint.style.cssText = "font-size:10px; color:#334; margin-top:8px; padding:6px 10px; border-radius:4px; border:1px dashed #1a2030;";
    hint.textContent = "ML engines not trained — click Train Models to enable XGBoost + RF signals.";
    rowsEl.appendChild(hint);
  }

  // ── Indicator Diagnostics (new: from /api/strategy/analyze diagnostics) ────
  const diag = data.diagnostics;
  if (diag) {
    const diagEl = document.getElementById("strat-diagnostics");
    if (diagEl) {
      const rsiColor  = diag.rsi_zone === 'oversold'   ? '#00e676'
                      : diag.rsi_zone === 'overbought'  ? '#ef5350' : '#9e9e9e';
      const macdColor = diag.macd_bias === 'bullish'   ? '#00e676'
                      : diag.macd_bias === 'bearish'    ? '#ef5350' : '#9e9e9e';
      const smaColor  = diag.sma_bias  === 'bullish'   ? '#00e676'
                      : diag.sma_bias  === 'bearish'    ? '#ef5350' : '#9e9e9e';

      diagEl.style.display = 'flex';
      diagEl.innerHTML = `
        <div style="flex:1; text-align:center;">
          <div style="font-size:10px; color:#556; text-transform:uppercase; letter-spacing:.8px; margin-bottom:3px;">RSI-14</div>
          <div style="font-size:16px; font-weight:700; color:${rsiColor}; font-family:monospace;">${diag.rsi_14 ?? '—'}</div>
          <div style="font-size:10px; color:${rsiColor};">${diag.rsi_zone ?? ''}</div>
        </div>
        <div style="flex:1; text-align:center; border-left:1px solid #1e2030; border-right:1px solid #1e2030;">
          <div style="font-size:10px; color:#556; text-transform:uppercase; letter-spacing:.8px; margin-bottom:3px;">MACD</div>
          <div style="font-size:16px; font-weight:700; color:${macdColor}; font-family:monospace;">${diag.macd ?? '—'}</div>
          <div style="font-size:10px; color:${macdColor};">${diag.macd_bias ?? ''} · hist ${diag.macd_hist ?? '—'}</div>
        </div>
        <div style="flex:1; text-align:center; border-right:1px solid #1e2030;">
          <div style="font-size:10px; color:#556; text-transform:uppercase; letter-spacing:.8px; margin-bottom:3px;">SMA Spread</div>
          <div style="font-size:16px; font-weight:700; color:${smaColor}; font-family:monospace;">${diag.sma_spread_pct != null ? diag.sma_spread_pct + '%' : '—'}</div>
          <div style="font-size:10px; color:${smaColor};">${diag.sma_bias ?? ''}</div>
        </div>
        <div style="flex:1; text-align:center;">
          <div style="font-size:10px; color:#556; text-transform:uppercase; letter-spacing:.8px; margin-bottom:3px;">ATR%</div>
          <div style="font-size:16px; font-weight:700; color:#607d8b; font-family:monospace;">${diag.atr_pct != null ? diag.atr_pct + '%' : '—'}</div>
          <div style="font-size:10px; color:#546e7a;">volatility</div>
        </div>
      `;
    }
  }
}

// ── ML Model Training ─────────────────────────────────────────────────────────

async function trainMLModels() {
  const ticker = (_lastStratTicker ||
    (document.getElementById("strat-ticker")?.value || "AAPL")).trim().toUpperCase();
  const statusEl = document.getElementById("strat-status");
  const btn = document.getElementById("strat-train-btn");
  if (btn) btn.disabled = true;
  statusEl.textContent = `Training ML models for ${ticker}… (may take 10-20s)`;
  try {
    const data = await _apiFetch(`/api/ml/train/${ticker}`, 60000, { method: "POST" });
    const xgb  = data.engines?.ml_xgboost;
    const rf   = data.engines?.ml_rf;
    const xgbLine = xgb?.status === "trained"
      ? `XGBoost val-acc ${Math.round((xgb.val_accuracy || 0) * 100)}%`
      : `XGBoost: ${xgb?.error || "failed"}`;
    const rfLine = rf?.status === "trained"
      ? `RF val-acc ${Math.round((rf.val_accuracy || 0) * 100)}%`
      : `RF: ${rf?.error || "failed"}`;
    statusEl.textContent = `✓ Models trained — ${xgbLine} · ${rfLine} · ${data.n_samples} samples`;
    // Auto-refresh analysis to show ML signals
    if (xgb?.status === "trained" || rf?.status === "trained") {
      setTimeout(runStrategyAnalysis, 500);
    }
  } catch (err) {
    statusEl.textContent = `Train error: ${err.message}`;
  } finally {
    if (btn) btn.disabled = false;
  }
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

// -- Portfolio Intelligence (Recovered Modules) --------------------------------

function _normalizeTickers(raw, fallback = ["AAPL", "MSFT", "SPY"]) {
  const txt = (raw || "").trim();
  const parts = (txt ? txt : fallback.join(",")).split(",");
  const out = [];
  const seen = new Set();
  parts.forEach((p) => {
    const t = (p || "").trim().toUpperCase();
    if (!t || seen.has(t)) return;
    seen.add(t);
    out.push(t);
  });
  return out.slice(0, 20);
}

function _fmtPct(value, digits = 2) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "n/a";
  return `${value.toFixed(digits)}%`;
}

function _fmtNum(value, digits = 3) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "n/a";
  return value.toFixed(digits);
}

function _drawPortIntelMonteCarlo(canvas, p05, p50, p95) {
  if (!canvas || !Array.isArray(p05) || !Array.isArray(p50) || !Array.isArray(p95)) return;
  const n = Math.min(p05.length, p50.length, p95.length);
  if (n < 2) return;

  canvas.style.display = "block";
  const ctx = canvas.getContext("2d");
  const W = Math.max(560, Math.floor(canvas.getBoundingClientRect().width || 760));
  const H = 220;
  canvas.width = W;
  canvas.height = H;

  const all = [...p05, ...p50, ...p95].filter((v) => Number.isFinite(v));
  const minV = Math.min(...all);
  const maxV = Math.max(...all);
  const range = maxV - minV || 1;

  const xAt = (i) => (i / (n - 1)) * (W - 20) + 10;
  const yAt = (v) => H - ((v - minV) / range) * (H - 30) - 12;

  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#0b0f1a";
  ctx.fillRect(0, 0, W, H);

  const bandGrad = ctx.createLinearGradient(0, 0, 0, H);
  bandGrad.addColorStop(0, "rgba(68,136,255,0.24)");
  bandGrad.addColorStop(1, "rgba(68,136,255,0.04)");

  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const x = xAt(i);
    const y = yAt(p95[i]);
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  for (let i = n - 1; i >= 0; i--) {
    const x = xAt(i);
    const y = yAt(p05[i]);
    ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.fillStyle = bandGrad;
  ctx.fill();

  const drawLine = (arr, color, width = 1.6) => {
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const x = xAt(i);
      const y = yAt(arr[i]);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
  };

  drawLine(p05, "#667799", 1.1);
  drawLine(p95, "#667799", 1.1);
  drawLine(p50, "#00e676", 1.8);

  ctx.fillStyle = "#7f8fa6";
  ctx.font = "11px monospace";
  ctx.fillText("P05", 12, yAt(p05[0]) - 4);
  ctx.fillText("P50", 12, yAt(p50[0]) - 4);
  ctx.fillText("P95", 12, yAt(p95[0]) - 4);
}

function _renderPortIntelSummary(summaryData, corrData) {
  const summaryEl = document.getElementById("portintel-summary");
  if (!summaryEl) return;

  if (!summaryData || !corrData) {
    summaryEl.innerHTML = '<span style="color:#ef5350;">Summary data unavailable.</span>';
    return;
  }

  const topPairs = (corrData.top_pairs || [])
    .slice(0, 4)
    .map((p) => `${p.pair} <span style="color:#aaa;">${_fmtNum(p.correlation, 2)}</span>`)
    .join(" &nbsp; ");

  const priceChange = summaryData?.price?.change_pct;
  const priceColor = typeof priceChange === "number" ? (priceChange >= 0 ? "#00e676" : "#ef5350") : "#aaa";

  summaryEl.innerHTML = `
    <div style="margin-bottom:6px;">
      <span style="color:#ccc; font-weight:700;">${summaryData.ticker}</span>
      &nbsp;Â·&nbsp;
      Last <span style="color:#aaa;">$${_fmtNum(summaryData?.price?.last, 2)}</span>
      &nbsp;Â·&nbsp;
      Change <span style="color:${priceColor};">${_fmtPct(priceChange, 2)}</span>
      &nbsp;Â·&nbsp;
      Vol <span style="color:#aaa;">${_fmtNum(summaryData?.volatility?.historical_annualized, 3)}</span>
    </div>
    <div style="margin-bottom:6px; color:#9ab;">
      Sharpe <span style="color:${_confColor(Math.min(1, Math.max(0, (summaryData?.risk?.sharpe || 0) / 2)))};">
      ${_fmtNum(summaryData?.risk?.sharpe, 2)}</span>
      &nbsp;Â·&nbsp; Sortino <span style="color:#aaa;">${_fmtNum(summaryData?.risk?.sortino, 2)}</span>
      &nbsp;Â·&nbsp; Calmar <span style="color:#aaa;">${_fmtNum(summaryData?.risk?.calmar, 2)}</span>
    </div>
    <div style="font-size:11px; color:#667;">
      Correlation top pairs: ${topPairs || "n/a"}
    </div>
  `;
}

function _renderPortIntelRisk(riskData) {
  const riskEl = document.getElementById("portintel-risk");
  if (!riskEl) return;

  if (!riskData || !riskData.risk) {
    riskEl.innerHTML = '<span style="color:#ef5350;">Risk data unavailable.</span>';
    return;
  }

  const risk = riskData.risk;
  const stress = risk.stress_scenarios || {};
  const stressPairs = Object.entries(stress)
    .slice(0, 4)
    .map(([k, v]) => `${k}: <span style="color:#aaa;">${_fmtPct(v * 100, 2)}</span>`)
    .join(" &nbsp; ");

  riskEl.innerHTML = `
    <div style="margin-bottom:6px;">
      VaR95 <span style="color:#ffea00;">${_fmtPct((risk.portfolio_var_95 || 0) * 100, 2)}</span>
      &nbsp;Â·&nbsp; CVaR95 <span style="color:#ff9100;">${_fmtPct((risk.portfolio_cvar_95 || 0) * 100, 2)}</span>
      &nbsp;Â·&nbsp; VaR99 <span style="color:#ef5350;">${_fmtPct((risk.portfolio_var_99 || 0) * 100, 2)}</span>
    </div>
    <div style="margin-bottom:6px; color:#9ab;">
      Max DD <span style="color:#ef5350;">${_fmtPct((risk.max_drawdown || 0) * 100, 2)}</span>
      &nbsp;Â·&nbsp; Sharpe <span style="color:#aaa;">${_fmtNum(risk.sharpe, 2)}</span>
      &nbsp;Â·&nbsp; Sortino <span style="color:#aaa;">${_fmtNum(risk.sortino, 2)}</span>
    </div>
    <div style="font-size:11px; color:#667;">
      Stress: ${stressPairs || "n/a"}
    </div>
  `;
}

function _renderPortIntelMonteCarlo(mcData) {
  const mcEl = document.getElementById("portintel-mc");
  const canvas = document.getElementById("portintel-mc-canvas");
  if (!mcEl) return;

  if (!mcData || !mcData.terminal_distribution) {
    mcEl.innerHTML = '<span style="color:#ef5350;">Monte Carlo data unavailable.</span>';
    if (canvas) canvas.style.display = "none";
    return;
  }

  const td = mcData.terminal_distribution;
  const rm = mcData.risk_metrics || {};
  mcEl.innerHTML = `
    <div style="margin-bottom:6px;">
      Expected Return <span style="color:${(td.expected_return || 0) >= 0 ? "#00e676" : "#ef5350"};">
      ${_fmtPct((td.expected_return || 0) * 100, 2)}</span>
      &nbsp;Â·&nbsp; Prob(loss) <span style="color:#ff9100;">${_fmtPct((td.probability_of_loss || 0) * 100, 2)}</span>
      &nbsp;Â·&nbsp; Median FV <span style="color:#aaa;">${_fmtNum(td.median_final_value, 3)}</span>
    </div>
    <div style="font-size:11px; color:#667;">
      MC VaR95 <span style="color:#ffea00;">${_fmtPct((rm.var_95 || 0) * 100, 2)}</span>
      &nbsp;Â·&nbsp; MC CVaR95 <span style="color:#ff9100;">${_fmtPct((rm.cvar_95 || 0) * 100, 2)}</span>
      &nbsp;Â·&nbsp; Median MaxDD <span style="color:#ef5350;">${_fmtPct((rm.max_drawdown_median || 0) * 100, 2)}</span>
    </div>
  `;

  const p = mcData.percentile_paths || {};
  _drawPortIntelMonteCarlo(canvas, p.p05 || [], p.p50 || [], p.p95 || []);
}

async function runPortfolioIntelligence() {
  const statusEl = document.getElementById("portintel-status");
  const runBtn = document.getElementById("portintel-run-btn");

  const tickersRaw = document.getElementById("portintel-tickers")?.value || "AAPL,MSFT,SPY";
  const period = document.getElementById("portintel-period")?.value || "1y";
  const method = document.getElementById("portintel-method")?.value || "log";
  const nPathsRaw = parseInt(document.getElementById("portintel-paths")?.value || "1200", 10);
  const horizonRaw = parseInt(document.getElementById("portintel-horizon")?.value || "252", 10);

  const tickers = _normalizeTickers(tickersRaw);
  if (tickers.length < 2) {
    if (statusEl) statusEl.textContent = "Need at least 2 tickers.";
    return;
  }

  const nPaths = Math.max(200, Math.min(20000, Number.isFinite(nPathsRaw) ? nPathsRaw : 1200));
  const horizon = Math.max(20, Math.min(756, Number.isFinite(horizonRaw) ? horizonRaw : 252));

  if (statusEl) statusEl.textContent = "Running analytics + risk + Monte Carlo...";
  if (runBtn) runBtn.disabled = true;

  const first = tickers[0];
  const correlationUrl = `/api/analytics/correlation?tickers=${encodeURIComponent(tickers.join(","))}&period=${encodeURIComponent(period)}&return_method=${encodeURIComponent(method)}`;
  const summaryUrl = `/api/analytics/summary/${encodeURIComponent(first)}?period=${encodeURIComponent(period)}`;

  const riskBody = {
    tickers,
    period,
    return_method: method,
    confidence: 0.95,
    risk_free_rate: 0.04,
    horizon_days: 1,
    run_stress: true,
  };
  const mcBody = {
    tickers,
    period,
    return_method: method,
    n_paths: nPaths,
    horizon_days: horizon,
    seed: 7,
  };

  try {
    const [summaryRes, corrRes, riskRes, mcRes] = await Promise.allSettled([
      _apiFetch(summaryUrl, 40000),
      _apiFetch(correlationUrl, 50000),
      _apiFetch(
        "/api/risk/portfolio/assess",
        60000,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(riskBody),
        },
      ),
      _apiFetch(
        "/api/montecarlo/portfolio/simulate",
        90000,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(mcBody),
        },
      ),
    ]);

    const summaryData = summaryRes.status === "fulfilled" ? summaryRes.value : null;
    const corrData = corrRes.status === "fulfilled" ? corrRes.value : null;
    const riskData = riskRes.status === "fulfilled" ? riskRes.value : null;
    const mcData = mcRes.status === "fulfilled" ? mcRes.value : null;

    _renderPortIntelSummary(summaryData, corrData);
    _renderPortIntelRisk(riskData);
    _renderPortIntelMonteCarlo(mcData);

    const failed = [summaryRes, corrRes, riskRes, mcRes].filter((r) => r.status !== "fulfilled").length;
    if (statusEl) {
      if (failed === 0) {
        statusEl.textContent = `Portfolio intelligence updated for ${tickers.join(", ")}.`;
        statusEl.style.color = "#4caf50";
      } else {
        statusEl.textContent = `Partial update (${4 - failed}/4). Some endpoints failed.`;
        statusEl.style.color = "#ff9100";
      }
    }
  } catch (err) {
    if (statusEl) {
      statusEl.textContent = `Portfolio intelligence error: ${err.message}`;
      statusEl.style.color = "#ef5350";
    }
  } finally {
    if (runBtn) runBtn.disabled = false;
  }
}

window.runPortfolioIntelligence = runPortfolioIntelligence;
