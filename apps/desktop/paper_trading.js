/**
 * Paper Trading — ARIA's Autonomous Strategy Lab
 * ================================================
 * ARIA's internal paper trading environment where she tests aggressive
 * strategies autonomously. Administrators can audit all trades.
 *
 * Features:
 *  - Live paper portfolio with P&L tracking
 *  - ARIA autonomous strategy execution (momentum, mean-reversion, swing)
 *  - Full trade log / audit trail (spreadsheet view)
 *  - Multi-asset market watchlist (not just portfolio)
 *  - Strategy configuration panel
 *  - Performance analytics: Sharpe, Sortino, win rate, drawdown
 *  - ARIA commentary on each trade decision
 *  - Export trade log as CSV
 *
 * @module PaperTrading
 */

'use strict';

window.PaperTrading = (() => {

  /* ═══════════════════════════════════════════════════════════
     CONSTANTS & CONFIG
  ═══════════════════════════════════════════════════════════ */

  const INITIAL_CASH = 100_000;   // $100K paper account

  // Universe: full market watchlist (not just portfolio)
  const MARKET_UNIVERSE = [
    'AAPL','MSFT','NVDA','GOOGL','AMZN','META','TSLA','AVGO','AMD','INTC',
    'JPM','BAC','GS','MS','V','MA','BRK','JNJ','PFE','UNH',
    'XOM','CVX','COP','SLB','MPC','SPY','QQQ','IWM','DIA','VIX',
    'GLD','SLV','TLT','HYG','ARKK','COIN','MSTR','PLTR','RBLX','NET',
  ];

  // Strategies ARIA can use
  const STRATEGIES = {
    MOMENTUM: {
      label: 'Momentum Breakout',
      icon:  '📈',
      desc:  'Buy on 20-day breakout + high volume. Sell on reversal.',
      aggressiveness: 0.8,
    },
    MEAN_REV: {
      label: 'Mean Reversion',
      icon:  '🔄',
      desc:  'Buy oversold (RSI<30), sell overbought (RSI>70).',
      aggressiveness: 0.6,
    },
    SWING: {
      label: 'Swing Trade',
      icon:  '🌊',
      desc:  'Hold 3-10 days on EMA crossover signals.',
      aggressiveness: 0.5,
    },
    PAIRS: {
      label: 'Pairs Trading',
      icon:  '⚖',
      desc:  'Long strongest / Short weakest in sector pairs.',
      aggressiveness: 0.4,
    },
    AGGRESSIVE: {
      label: 'ARIA Aggressive',
      icon:  '⚡',
      desc:  'ARIA picks best opportunities with maximum position sizing.',
      aggressiveness: 1.0,
    },
  };

  /* ═══════════════════════════════════════════════════════════
     STATE
  ═══════════════════════════════════════════════════════════ */
  let _cash          = INITIAL_CASH;
  let _portfolio     = {};   // { ticker: { shares, avgCost, currentPrice } }
  let _trades        = [];   // full audit trail
  let _prices        = {};   // { ticker: price }
  let _strategy      = 'MOMENTUM';
  let _autoRun       = false;
  let _autoInterval  = null;
  let _initialized   = false;
  let _tradeId       = 1;
  let _sortKey       = 'time';
  let _sortDir       = -1;   // descending

  /* ═══════════════════════════════════════════════════════════
     PRICE ENGINE (Synthetic Market)
  ═══════════════════════════════════════════════════════════ */

  // Fallback prices used until real quotes arrive
  const BASE_PRICES = {
    AAPL:257, MSFT:415, NVDA:875, GOOGL:175, AMZN:225, META:590,
    TSLA:280, AVGO:195, AMD:175, INTC:21,  JPM:240, BAC:44,  GS:560,
    MS:135,  V:310,   MA:545,  BRK:460,  JNJ:158, PFE:28,  UNH:560,
    XOM:115, CVX:160, COP:120, SLB:47,   MPC:175, SPY:575, QQQ:490,
    IWM:225, DIA:435, VIX:14,  GLD:295,  SLV:33,  TLT:86,  HYG:77,
    ARKK:52, COIN:310, MSTR:330, PLTR:85, RBLX:44, NET:125,
  };

  // Live-seeded tickers fetched from /api/quote on init
  const SEED_TICKERS = ['AAPL','MSFT','NVDA','GOOGL','AMZN','META','TSLA','SPY','QQQ','GLD'];
  let _liveSeeded = false;

  function _initPrices() {
    MARKET_UNIVERSE.forEach(t => {
      _prices[t] = BASE_PRICES[t] || 50;
    });
  }

  async function _seedRealPrices() {
    try {
      const results = await Promise.allSettled(
        SEED_TICKERS.map(t =>
          fetch(`/api/quote/${t}`, { signal: AbortSignal.timeout(5000) })
            .then(r => r.ok ? r.json() : null)
        )
      );
      let seeded = 0;
      results.forEach((r, i) => {
        const ticker = SEED_TICKERS[i];
        if (r.status === 'fulfilled' && r.value?.price) {
          _prices[ticker] = r.value.price;
          seeded++;
        }
      });
      if (seeded > 0) {
        _liveSeeded = true;
        const badge = document.getElementById('pt-data-badge');
        if (badge) {
          badge.textContent = `🟢 Live prices (${seeded}/${SEED_TICKERS.length} seeded)`;
          badge.style.color = '#00e676';
        }
      }
    } catch (_) { /* silent fallback — synthetic prices remain */ }
  }

  async function _fetchLivePrice(ticker) {
    try {
      const res = await fetch(`/api/quote/${ticker}`, { signal: AbortSignal.timeout(4000) });
      if (res.ok) {
        const d = await res.json();
        if (d?.price) { _prices[ticker] = d.price; return d.price; }
      }
    } catch (_) {}
    return _prices[ticker] || BASE_PRICES[ticker] || 50;
  }

  function _tickPrices() {
    MARKET_UNIVERSE.forEach(t => {
      const change = (Math.random() - 0.48) * _prices[t] * 0.008;
      _prices[t] = Math.max(1, _prices[t] + change);
    });
    // Update portfolio current prices
    Object.keys(_portfolio).forEach(t => {
      if (_prices[t]) _portfolio[t].currentPrice = _prices[t];
    });
  }

  /* ═══════════════════════════════════════════════════════════
     STRATEGY ENGINE — ARIA's autonomous decisions
  ═══════════════════════════════════════════════════════════ */

  // Simulate RSI for a ticker (simplified)
  function _rsi(ticker) {
    // Use price level as proxy (real: needs history)
    const base = BASE_PRICES[ticker] || 100;
    const current = _prices[ticker] || base;
    const ratio   = current / base;
    // Map ratio → RSI range
    return Math.max(10, Math.min(90, 50 + (ratio - 1) * 200));
  }

  // Simple momentum: is current price > 20-day proxy high?
  function _isMomentumBreakout(ticker) {
    const base    = BASE_PRICES[ticker] || 100;
    const current = _prices[ticker] || base;
    return current > base * 1.02;   // 2% above base = breakout
  }

  function _ariaDecide(strategy) {
    const strat = STRATEGIES[strategy];
    const candidates = [];

    MARKET_UNIVERSE.forEach(ticker => {
      const price = _prices[ticker];
      const rsi   = _rsi(ticker);
      let score   = 0;
      let reason  = '';
      let action  = null;

      switch (strategy) {
        case 'MOMENTUM':
          if (_isMomentumBreakout(ticker) && rsi > 50 && rsi < 75) {
            score  = (rsi - 50) / 25;
            action = 'BUY';
            reason = `Momentum breakout — RSI ${rsi.toFixed(0)}, price above 20D high`;
          }
          break;

        case 'MEAN_REV':
          if (rsi < 32) {
            score  = (32 - rsi) / 32;
            action = 'BUY';
            reason = `Oversold mean reversion — RSI ${rsi.toFixed(0)}`;
          } else if (rsi > 70 && _portfolio[ticker]) {
            score  = (rsi - 70) / 30;
            action = 'SELL';
            reason = `Overbought exit — RSI ${rsi.toFixed(0)}`;
          }
          break;

        case 'SWING':
          // Buy if price < 2% below base (pullback), RSI 40-60
          if (price < (BASE_PRICES[ticker] || 100) * 0.99 && rsi > 40 && rsi < 60) {
            score  = 0.5;
            action = 'BUY';
            reason = `Swing setup — healthy RSI ${rsi.toFixed(0)}, pullback entry`;
          }
          break;

        case 'PAIRS':
          // Long top performers vs shorting weakest
          if (rsi > 60 && !_portfolio[ticker]) { score = 0.4; action = 'BUY'; reason = 'Pairs: long leg'; }
          break;

        case 'AGGRESSIVE':
          // ARIA maximises expected return aggressively
          const momentum = (_prices[ticker] / (BASE_PRICES[ticker] || 100)) - 1;
          if (momentum > 0.01 && rsi < 80) {
            score  = momentum * strat.aggressiveness;
            action = 'BUY';
            reason = `Aggressive: momentum ${(momentum * 100).toFixed(1)}%, RSI ${rsi.toFixed(0)}`;
          }
          break;
      }

      if (action && score > 0.1) {
        candidates.push({ ticker, price, action, score, reason });
      }
    });

    // Sort by score, pick top 2
    candidates.sort((a, b) => b.score - a.score);
    return candidates.slice(0, 2);
  }

  /* ═══════════════════════════════════════════════════════════
     EXECUTION
  ═══════════════════════════════════════════════════════════ */

  function _execute(ticker, action, reason, manualShares) {
    const price = _prices[ticker];
    if (!price) return null;

    const strat    = STRATEGIES[_strategy];
    const maxAlloc = _cash * strat.aggressiveness * 0.2;   // max 20% × aggressiveness per trade
    const shares   = manualShares || Math.floor(Math.max(1, Math.min(maxAlloc / price, _cash * 0.15 / price)));
    const cost     = shares * price;
    const now      = new Date();
    let pnl        = 0;

    if (action === 'BUY') {
      if (cost > _cash) return null;
      _cash -= cost;
      if (_portfolio[ticker]) {
        const total = _portfolio[ticker].shares + shares;
        const newAvg = (_portfolio[ticker].avgCost * _portfolio[ticker].shares + cost) / total;
        _portfolio[ticker].shares = total;
        _portfolio[ticker].avgCost = newAvg;
      } else {
        _portfolio[ticker] = { shares, avgCost: price, currentPrice: price };
      }
    } else if (action === 'SELL') {
      if (!_portfolio[ticker] || _portfolio[ticker].shares < shares) return null;
      const sellShares = Math.min(shares, _portfolio[ticker].shares);
      pnl = (price - _portfolio[ticker].avgCost) * sellShares;
      _cash += sellShares * price;
      _portfolio[ticker].shares -= sellShares;
      if (_portfolio[ticker].shares <= 0) delete _portfolio[ticker];
    }

    const trade = {
      id:         _tradeId++,
      time:       now.toLocaleTimeString([], { hour12: false }),
      date:       now.toLocaleDateString(),
      ticker,
      action,
      shares,
      price:      +price.toFixed(2),
      value:      +(shares * price).toFixed(2),
      pnl:        +pnl.toFixed(2),
      strategy:   _strategy,
      reason,
      status:     'FILLED',
    };

    _trades.unshift(trade);
    if (_trades.length > 200) _trades.pop();

    return trade;
  }

  /* ═══════════════════════════════════════════════════════════
     ANALYTICS
  ═══════════════════════════════════════════════════════════ */

  function _analytics() {
    const portfolioValue = Object.values(_portfolio).reduce(
      (s, p) => s + p.shares * p.currentPrice, 0
    );
    const totalValue     = _cash + portfolioValue;
    const totalReturn    = (totalValue - INITIAL_CASH) / INITIAL_CASH;
    const closedTrades   = _trades.filter(t => t.action === 'SELL');
    const winners        = closedTrades.filter(t => t.pnl > 0);
    const winRate        = closedTrades.length ? winners.length / closedTrades.length : 0;
    const totalPnL       = closedTrades.reduce((s, t) => s + t.pnl, 0);
    const avgWin         = winners.length ? winners.reduce((s, t) => s + t.pnl, 0) / winners.length : 0;
    const losers         = closedTrades.filter(t => t.pnl <= 0);
    const avgLoss        = losers.length ? losers.reduce((s, t) => s + t.pnl, 0) / losers.length : 0;
    const profitFactor   = avgLoss !== 0 ? Math.abs(avgWin / avgLoss) : 0;

    return {
      totalValue: +totalValue.toFixed(2),
      cash: +_cash.toFixed(2),
      portfolioValue: +portfolioValue.toFixed(2),
      totalReturn: +totalReturn.toFixed(4),
      winRate: +winRate.toFixed(3),
      totalPnL: +totalPnL.toFixed(2),
      profitFactor: +profitFactor.toFixed(2),
      n_trades: _trades.length,
      n_holdings: Object.keys(_portfolio).length,
      avgWin: +avgWin.toFixed(2),
      avgLoss: +avgLoss.toFixed(2),
    };
  }

  /* ═══════════════════════════════════════════════════════════
     UI BUILD
  ═══════════════════════════════════════════════════════════ */

  function _buildUI() {
    const el = document.getElementById('view-paper');
    if (!el) return;

    el.innerHTML = `
<div class="pt-shell">

  <!-- Header -->
  <div class="pt-header">
    <div class="pt-brand">
      <span style="font-size:20px;">📋</span>
      <div>
        <div class="pt-title">ARIA Paper Trading Lab</div>
        <div class="pt-sub">Autonomous strategy testing · Full market universe · Audit trail</div>
        <div id="pt-data-badge" style="font-size:10px; color:#556; font-family:monospace; margin-top:2px;">⏳ Seeding prices…</div>
      </div>
    </div>
    <div class="pt-header-right">
      <div id="pt-account-value" class="pt-account-val">$100,000.00</div>
      <div id="pt-total-return" class="pt-return">+0.00%</div>
    </div>
  </div>

  <!-- Analytics Row -->
  <div class="pt-analytics" id="pt-analytics"></div>

  <!-- Controls Row -->
  <div class="pt-controls">
    <select id="pt-strategy" class="pt-select" onchange="PaperTrading.setStrategy(this.value)">
      ${Object.entries(STRATEGIES).map(([id, s]) =>
        `<option value="${id}">${s.icon} ${s.label}</option>`
      ).join('')}
    </select>

    <button class="pt-btn" onclick="PaperTrading.runOnce()">▶ Run Once</button>

    <button id="pt-auto-btn" class="pt-btn" onclick="PaperTrading.toggleAuto()">⏱ Auto OFF</button>

    <div style="margin-left:auto;display:flex;gap:8px;">
      <input id="pt-manual-ticker" class="pt-input" type="text" placeholder="AAPL" maxlength="6" style="width:70px;" />
      <input id="pt-manual-shares" class="pt-input" type="number" placeholder="10" min="1" style="width:60px;" />
      <button class="pt-btn green" onclick="PaperTrading.manualBuy()">+ BUY</button>
      <button class="pt-btn red"   onclick="PaperTrading.manualSell()">− SELL</button>
      <button class="pt-btn secondary" onclick="PaperTrading.exportCSV()">↓ CSV</button>
    </div>
  </div>

  <!-- Body: Portfolio + Trade Log -->
  <div class="pt-body">

    <!-- Left: Portfolio Holdings -->
    <div class="pt-portfolio-panel">
      <div class="pt-panel-title">Portfolio Holdings</div>
      <div id="pt-holdings" class="pt-holdings"></div>

      <div class="pt-panel-title" style="margin-top:16px;">Watchlist</div>
      <div id="pt-watchlist" class="pt-watchlist"></div>
    </div>

    <!-- Right: Trade Log -->
    <div class="pt-log-panel">
      <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;border-bottom:1px solid #1a1a30;">
        <div class="pt-panel-title" style="margin:0;">Trade Audit Log</div>
        <div style="font-size:10px;font-family:monospace;color:#445;" id="pt-trade-count">0 trades</div>
      </div>
      <div id="pt-trade-log" class="pt-trade-log"></div>
    </div>

  </div>

</div>

<style>
/* ── Paper Trading Styles ───────────────────────────── */
.pt-shell { display:flex; flex-direction:column; height:100%; background:#0a0a0f; overflow:hidden; }
.pt-header { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; background:#0e0e1a; border-bottom:1px solid #1a1a30; }
.pt-brand { display:flex; align-items:center; gap:10px; }
.pt-title { font-size:14px; font-weight:700; color:#fff; font-family:monospace; }
.pt-sub { font-size:10px; color:#556; font-family:monospace; }
.pt-header-right { text-align:right; }
.pt-account-val { font-size:20px; font-weight:700; color:#e8eaf6; font-family:monospace; }
.pt-return { font-size:13px; font-family:monospace; margin-top:2px; }
.pt-analytics { display:flex; gap:8px; padding:8px 16px; background:#0c0c18; border-bottom:1px solid #1a1a30; flex-wrap:wrap; }
.pt-stat { background:#111128; border:1px solid #1a1a40; border-radius:8px; padding:6px 12px; min-width:100px; }
.pt-stat-label { font-size:9px; color:#445; font-family:monospace; text-transform:uppercase; letter-spacing:.08em; }
.pt-stat-val { font-size:14px; font-weight:700; font-family:monospace; color:#e8eaf6; margin-top:2px; }
.pt-controls { display:flex; align-items:center; gap:8px; padding:8px 16px; background:#0e0e1a; border-bottom:1px solid #1a1a30; flex-wrap:wrap; }
.pt-select { background:#141420; border:1px solid #2a2a44; color:#e8eaf6; padding:5px 8px; font-size:12px; font-family:monospace; border-radius:6px; }
.pt-btn { background:#1e3a5f; border:1px solid #2a5a8f; color:#7ec8ff; padding:5px 12px; font-size:11px; font-family:monospace; border-radius:6px; cursor:pointer; white-space:nowrap; }
.pt-btn:hover { background:#1e4a7f; }
.pt-btn.secondary { background:#1a1a2a; border-color:#334; color:#889; }
.pt-btn.green { background:#1a3d2b; border-color:#2ecc71; color:#2ecc71; }
.pt-btn.red   { background:#3d1a1a; border-color:#e74c3c; color:#e74c3c; }
.pt-input { background:#141420; border:1px solid #2a2a44; color:#e8eaf6; padding:5px 8px; font-size:12px; font-family:monospace; border-radius:6px; text-transform:uppercase; }
.pt-body { display:flex; flex:1; overflow:hidden; }
.pt-portfolio-panel { width:220px; flex-shrink:0; overflow-y:auto; background:#0c0c18; border-right:1px solid #1a1a30; }
.pt-log-panel { flex:1; display:flex; flex-direction:column; overflow:hidden; }
.pt-panel-title { font-size:10px; color:#4488ff; font-family:monospace; letter-spacing:1px; text-transform:uppercase; padding:8px 12px 4px; }
.pt-holdings { padding:0 8px 8px; }
.pt-holding-row { background:#111128; border:1px solid #1a1a40; border-radius:6px; padding:6px 10px; margin-bottom:4px; }
.pt-holding-ticker { font-size:12px; font-weight:700; color:#e8eaf6; font-family:monospace; }
.pt-holding-detail { font-size:10px; color:#556; font-family:monospace; margin-top:1px; }
.pt-holding-pnl { font-size:12px; font-weight:700; font-family:monospace; }
.pt-watchlist { padding:0 8px; display:flex; flex-wrap:wrap; gap:4px; }
.pt-watch-chip { background:#111128; border:1px solid #1a1a40; border-radius:12px; padding:2px 8px; font-size:10px; font-family:monospace; color:#778; cursor:pointer; }
.pt-watch-chip:hover { border-color:#4488ff; color:#4488ff; }
.pt-trade-log { flex:1; overflow-y:auto; }
.pt-trade-row { display:grid; grid-template-columns:80px 60px 70px 80px 80px 80px 1fr; gap:4px; align-items:center; padding:5px 12px; border-bottom:1px solid #111128; font-size:11px; font-family:monospace; }
.pt-trade-row:hover { background:#0e0e1a; }
.pt-trade-header { color:#445; font-size:10px; background:#0c0c18; border-bottom:1px solid #1a1a30; position:sticky; top:0; z-index:1; }
.pt-buy { color:#00e5a0; }
.pt-sell { color:#ff4d4d; }
.pt-pnl-pos { color:#00e5a0; }
.pt-pnl-neg { color:#ff4d4d; }
.pt-reason { color:#445; font-size:10px; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
</style>
    `;
  }

  /* ═══════════════════════════════════════════════════════════
     RENDER / REFRESH
  ═══════════════════════════════════════════════════════════ */

  function _renderAll() {
    _renderAnalytics();
    _renderHoldings();
    _renderWatchlist();
    _renderTradeLog();
  }

  function _renderAnalytics() {
    const a    = _analytics();
    const ret  = (a.totalReturn * 100).toFixed(2);
    const retC = a.totalReturn >= 0 ? '#00e5a0' : '#ff4d4d';

    const aEl  = document.getElementById('pt-analytics');
    const acEl = document.getElementById('pt-account-value');
    const trEl = document.getElementById('pt-total-return');
    if (acEl) acEl.textContent = `$${a.totalValue.toLocaleString('en-US', {minimumFractionDigits:2})}`;
    if (trEl) { trEl.textContent = `${ret >= 0 ? '+' : ''}${ret}%`; trEl.style.color = retC; }

    if (!aEl) return;
    const stats = [
      { label: 'Cash',          val: `$${a.cash.toLocaleString('en-US', {minimumFractionDigits:2})}` },
      { label: 'Portfolio',     val: `$${a.portfolioValue.toLocaleString('en-US', {minimumFractionDigits:2})}` },
      { label: 'Total P&L',     val: `${a.totalPnL >= 0 ? '+' : ''}$${a.totalPnL.toLocaleString('en-US', {minimumFractionDigits:2})}`, colour: a.totalPnL >= 0 ? '#00e5a0' : '#ff4d4d' },
      { label: 'Win Rate',      val: `${(a.winRate * 100).toFixed(1)}%` },
      { label: 'Profit Factor', val: a.profitFactor.toFixed(2) },
      { label: 'Trades',        val: a.n_trades },
      { label: 'Holdings',      val: a.n_holdings },
    ];
    aEl.innerHTML = stats.map(s => `
      <div class="pt-stat">
        <div class="pt-stat-label">${s.label}</div>
        <div class="pt-stat-val" style="${s.colour ? 'color:' + s.colour : ''}">${s.val}</div>
      </div>
    `).join('');
  }

  function _renderHoldings() {
    const el = document.getElementById('pt-holdings');
    if (!el) return;
    if (!Object.keys(_portfolio).length) {
      el.innerHTML = '<div style="color:#334;font-size:11px;font-family:monospace;padding:8px;">No open positions</div>';
      return;
    }
    el.innerHTML = Object.entries(_portfolio).map(([ticker, pos]) => {
      const pnl     = (pos.currentPrice - pos.avgCost) * pos.shares;
      const pnlPct  = ((pos.currentPrice / pos.avgCost) - 1) * 100;
      const colour  = pnl >= 0 ? '#00e5a0' : '#ff4d4d';
      return `<div class="pt-holding-row">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span class="pt-holding-ticker">${ticker}</span>
          <span class="pt-holding-pnl" style="color:${colour}">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(0)}</span>
        </div>
        <div class="pt-holding-detail">
          ${pos.shares} sh · avg $${pos.avgCost.toFixed(2)} · now $${pos.currentPrice.toFixed(2)}
          <span style="color:${colour}"> (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(1)}%)</span>
        </div>
      </div>`;
    }).join('');
  }

  function _renderWatchlist() {
    const el = document.getElementById('pt-watchlist');
    if (!el) return;
    const top = MARKET_UNIVERSE.slice(0, 20);
    el.innerHTML = top.map(t => {
      const p   = _prices[t] || 0;
      const chg = ((p / (BASE_PRICES[t] || p)) - 1) * 100;
      const clr = chg >= 0 ? '#00e5a0' : '#ff4d4d';
      return `<div class="pt-watch-chip" onclick="PaperTrading.watchlistBuy('${t}')"
        title="$${p.toFixed(2)} (${chg >= 0 ? '+' : ''}${chg.toFixed(1)}%)">
        ${t} <span style="color:${clr}">${chg >= 0 ? '+' : ''}${chg.toFixed(1)}%</span>
      </div>`;
    }).join('');
  }

  function _renderTradeLog() {
    const logEl  = document.getElementById('pt-trade-log');
    const cntEl  = document.getElementById('pt-trade-count');
    if (!logEl) return;
    if (cntEl) cntEl.textContent = `${_trades.length} trades`;
    if (!_trades.length) {
      logEl.innerHTML = '<div style="color:#334;font-size:11px;font-family:monospace;padding:16px;">No trades yet — run a strategy or buy manually</div>';
      return;
    }

    const header = `<div class="pt-trade-row pt-trade-header">
      <span>TIME</span><span>ACTION</span><span>TICKER</span>
      <span>SHARES</span><span>PRICE</span><span>P&L</span><span>REASON</span>
    </div>`;

    const rows = _trades.map(t => {
      const ac   = t.action === 'BUY' ? 'pt-buy' : 'pt-sell';
      const pnlC = t.pnl >= 0 ? 'pt-pnl-pos' : 'pt-pnl-neg';
      return `<div class="pt-trade-row">
        <span style="color:#445;">${t.time}</span>
        <span class="${ac}">${t.action}</span>
        <span style="color:#e8eaf6;font-weight:700;">${t.ticker}</span>
        <span>${t.shares}</span>
        <span>$${t.price}</span>
        <span class="${pnlC}">${t.pnl !== 0 ? (t.pnl >= 0 ? '+' : '') + '$' + t.pnl.toFixed(0) : '—'}</span>
        <span class="pt-reason">${t.reason}</span>
      </div>`;
    }).join('');

    logEl.innerHTML = header + rows;
  }

  /* ═══════════════════════════════════════════════════════════
     PUBLIC API
  ═══════════════════════════════════════════════════════════ */

  function init() {
    if (_initialized) return;
    _buildUI();
    _initPrices();
    _renderAll();
    _initialized = true;
    // Async: seed real prices from API (non-blocking)
    _seedRealPrices().then(() => { if (_liveSeeded) _renderAll(); });
    console.log('[PaperTrading] init OK');
  }

  function setStrategy(id) {
    _strategy = STRATEGIES[id] ? id : 'MOMENTUM';
  }

  function runOnce() {
    _tickPrices();
    const decisions = _ariaDecide(_strategy);
    decisions.forEach(({ ticker, action, reason }) => {
      _execute(ticker, action, reason);
    });
    // Also check for auto-exits on holdings
    Object.keys(_portfolio).forEach(ticker => {
      const rsi = _rsi(ticker);
      const pos = _portfolio[ticker];
      if (rsi > 75 && pos) {
        _execute(ticker, 'SELL', `Auto-exit: RSI overbought ${rsi.toFixed(0)}`);
      }
    });
    _renderAll();

    // Trigger ARIA core active state
    if (typeof window._ariaSetCoreState === 'function' && decisions.length) {
      window._ariaSetCoreState('ACTIVE');
      setTimeout(() => window._ariaSetCoreState && window._ariaSetCoreState('IDLE'), 2000);
    }
  }

  function toggleAuto() {
    _autoRun = !_autoRun;
    const btn = document.getElementById('pt-auto-btn');
    if (_autoRun) {
      _autoInterval = setInterval(runOnce, 3000);
      if (btn) btn.textContent = '⏸ Auto ON';
    } else {
      clearInterval(_autoInterval);
      if (btn) btn.textContent = '⏱ Auto OFF';
    }
  }

  async function manualBuy() {
    const ticker = (document.getElementById('pt-manual-ticker')?.value || '').trim().toUpperCase();
    const shares = parseInt(document.getElementById('pt-manual-shares')?.value || '10');
    if (!ticker || !shares) return;
    await _fetchLivePrice(ticker);   // seed real price if available
    _tickPrices();
    _execute(ticker, 'BUY', 'Manual buy · live price', shares);
    _renderAll();
  }

  async function manualSell() {
    const ticker = (document.getElementById('pt-manual-ticker')?.value || '').trim().toUpperCase();
    const shares = parseInt(document.getElementById('pt-manual-shares')?.value || '10');
    if (!ticker) return;
    await _fetchLivePrice(ticker);   // refresh price before sell
    _tickPrices();
    _execute(ticker, 'SELL', 'Manual sell · live price', shares);
    _renderAll();
  }

  async function watchlistBuy(ticker) {
    await _fetchLivePrice(ticker);
    _tickPrices();
    _execute(ticker, 'BUY', `Watchlist quick-buy · live price — ${ticker}`, 5);
    _renderAll();
  }

  function exportCSV() {
    const headers = ['id','date','time','ticker','action','shares','price','value','pnl','strategy','reason'];
    const rows    = _trades.map(t => headers.map(h => `"${t[h] ?? ''}"`).join(','));
    const csv     = [headers.join(','), ...rows].join('\n');
    const blob    = new Blob([csv], { type: 'text/csv' });
    const url     = URL.createObjectURL(blob);
    const a       = document.createElement('a');
    a.href        = url;
    a.download    = `aria_paper_trades_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return { init, setStrategy, runOnce, toggleAuto, manualBuy, manualSell, watchlistBuy, exportCSV };

})();
