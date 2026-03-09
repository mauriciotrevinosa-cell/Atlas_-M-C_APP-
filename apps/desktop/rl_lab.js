/* ============================================================
 *  rl_lab.js  —  RL Trading Lab (Browser DQN)
 *  Atlas Ecosystem — FASE 1 Build
 * ============================================================
 *  Full in-browser DQN agent trained on synthetic price series.
 *  Architecture mirrors python/src/atlas/rl/ (same state/action/reward).
 *
 *  Network: FC(16, 32) → ReLU → FC(32, 16) → ReLU → FC(16, 5)
 *  Training: Double DQN + Huber loss + Adam + ε-decay + replay buffer
 * ============================================================ */

window.RLLab = (() => {
  'use strict';

  /* ── Constants ──────────────────────────────────────────────────── */
  const STATE_DIM    = 16;
  const ACTION_DIM   = 5;
  const ACTIONS      = ['HOLD', 'BUY_SM', 'BUY_LG', 'SELL_SM', 'SELL_LG'];
  const EPISODE_LEN  = 126;   // half-year per episode
  const INIT_CAP     = 100_000;
  const TRADE_COST   = 0.001;
  const WARM         = 50;    // warm-up bars for indicators

  /* ── Ticker profiles: [annual_mu, annual_sigma] ─────────────────── */
  const TICKERS = {
    'SPY':  [0.10, 0.16],
    'QQQ':  [0.14, 0.22],
    'TSLA': [0.18, 0.55],
    'BTC':  [0.30, 0.80],
    'GLD':  [0.04, 0.12],
  };

  /* ── Math helpers ───────────────────────────────────────────────── */
  function randn() {
    const u = Math.random() + 1e-10, v = Math.random() + 1e-10;
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function relu(x)           { return Math.max(0, x); }
  function mean(arr)         { return arr.reduce((a, b) => a + b, 0) / (arr.length || 1); }
  function std(arr) {
    const m = mean(arr);
    return Math.sqrt(arr.reduce((s, x) => s + (x - m) ** 2, 0) / (arr.length || 1)) + 1e-9;
  }

  /* ── Price Generator (GBM) ──────────────────────────────────────── */
  function genPrices(mu, sigma, n) {
    const dt    = 1 / 252;
    const drift = (mu - 0.5 * sigma * sigma) * dt;
    const diff  = sigma * Math.sqrt(dt);
    const prices = [100], rets = [0];
    for (let i = 1; i < n; i++) {
      const lr = drift + diff * randn();
      prices.push(prices[i - 1] * Math.exp(lr));
      rets.push(lr);
    }
    return { prices, rets };
  }

  /* ══════════════════════════════════════════════════════════════════
   *  TinyNet — 3-layer MLP (pure JS, no dependencies)
   * ══════════════════════════════════════════════════════════════════ */
  class TinyNet {
    constructor(dims) {
      this.dims = dims;
      this.W = []; this.b = [];
      this.mW = []; this.mb = [];
      this.vW = []; this.vb = [];
      this.t = 0;
      this.lr = 0.001;
      const b1 = 0.9, b2 = 0.999;
      this._b1 = b1; this._b2 = b2;

      for (let l = 0; l < dims.length - 1; l++) {
        const ni = dims[l], no = dims[l + 1];
        const sc = Math.sqrt(2.0 / ni);
        this.W.push(Array.from({ length: ni }, () =>
          Array.from({ length: no }, () => randn() * sc)));
        this.b.push(new Array(no).fill(0));
        this.mW.push(Array.from({ length: ni }, () => new Array(no).fill(0)));
        this.mb.push(new Array(no).fill(0));
        this.vW.push(Array.from({ length: ni }, () => new Array(no).fill(0)));
        this.vb.push(new Array(no).fill(0));
      }
    }

    /* Forward pass — returns { out, layers, pre } */
    forward(x) {
      const layers = [x.slice()], pre = [x.slice()];
      for (let l = 0; l < this.W.length; l++) {
        const W = this.W[l], b = this.b[l];
        const ni = W.length, no = b.length;
        const h = new Array(no).fill(0);
        for (let j = 0; j < no; j++) {
          let s = b[j];
          for (let i = 0; i < ni; i++) s += layers[l][i] * W[i][j];
          h[j] = s;
        }
        pre.push(h.slice());
        // ReLU on all layers except last
        if (l < this.W.length - 1) layers.push(h.map(relu));
        else layers.push(h.slice());
      }
      return { out: layers[layers.length - 1], layers, pre };
    }

    /* Predict (no cache) */
    predict(x) { return this.forward(x).out; }

    /* Backward + Adam */
    backward(gradOut, cache) {
      const { layers, pre } = cache;
      this.t++;
      let grad = gradOut.slice();

      for (let l = this.W.length - 1; l >= 0; l--) {
        const ni = this.W[l].length, no = this.b[l].length;
        const h_in = layers[l];

        // Gradient w.r.t. weights and bias
        const dW = Array.from({ length: ni }, () => new Array(no).fill(0));
        const db = grad.slice();
        for (let i = 0; i < ni; i++)
          for (let j = 0; j < no; j++)
            dW[i][j] = h_in[i] * grad[j];

        // Adam update — W
        for (let i = 0; i < ni; i++) {
          for (let j = 0; j < no; j++) {
            this.mW[l][i][j] = this._b1 * this.mW[l][i][j] + (1 - this._b1) * dW[i][j];
            this.vW[l][i][j] = this._b2 * this.vW[l][i][j] + (1 - this._b2) * dW[i][j] ** 2;
            const mh = this.mW[l][i][j] / (1 - this._b1 ** this.t);
            const vh = this.vW[l][i][j] / (1 - this._b2 ** this.t);
            this.W[l][i][j] -= this.lr * mh / (Math.sqrt(vh) + 1e-8);
          }
        }
        // Adam update — b
        for (let j = 0; j < no; j++) {
          this.mb[l][j] = this._b1 * this.mb[l][j] + (1 - this._b1) * db[j];
          this.vb[l][j] = this._b2 * this.vb[l][j] + (1 - this._b2) * db[j] ** 2;
          const mh = this.mb[l][j] / (1 - this._b1 ** this.t);
          const vh = this.vb[l][j] / (1 - this._b2 ** this.t);
          this.b[l][j] -= this.lr * mh / (Math.sqrt(vh) + 1e-8);
        }

        // Propagate gradient through ReLU to previous layer
        if (l > 0) {
          const newGrad = new Array(ni).fill(0);
          for (let i = 0; i < ni; i++) {
            for (let j = 0; j < no; j++)
              newGrad[i] += this.W[l][i][j] * grad[j];
            if (pre[l][i] <= 0) newGrad[i] = 0; // ReLU gate
          }
          grad = newGrad;
        }
      }
    }

    copyFrom(other) {
      for (let l = 0; l < this.W.length; l++) {
        for (let i = 0; i < this.W[l].length; i++)
          for (let j = 0; j < this.W[l][i].length; j++)
            this.W[l][i][j] = other.W[l][i][j];
        for (let j = 0; j < this.b[l].length; j++)
          this.b[l][j] = other.b[l][j];
      }
    }
  }

  /* ══════════════════════════════════════════════════════════════════
   *  ReplayBuffer — FIFO circular buffer
   * ══════════════════════════════════════════════════════════════════ */
  class ReplayBuffer {
    constructor(cap = 5_000) {
      this.cap = cap; this.buf = []; this.pos = 0;
    }
    push(s, a, r, ns, done) {
      const entry = [s, a, r, ns, done ? 1 : 0];
      if (this.buf.length < this.cap) this.buf.push(entry);
      else { this.buf[this.pos] = entry; this.pos = (this.pos + 1) % this.cap; }
    }
    sample(n) {
      const out = [];
      for (let i = 0; i < n; i++)
        out.push(this.buf[Math.floor(Math.random() * this.buf.length)]);
      return out;
    }
    get size() { return this.buf.length; }
  }

  /* ══════════════════════════════════════════════════════════════════
   *  DQNAgent — Double DQN (browser version)
   * ══════════════════════════════════════════════════════════════════ */
  class DQNAgent {
    constructor() {
      this.pNet = new TinyNet([STATE_DIM, 32, 16, ACTION_DIM]);
      this.tNet = new TinyNet([STATE_DIM, 32, 16, ACTION_DIM]);
      this.tNet.copyFrom(this.pNet);
      this.buf          = new ReplayBuffer(5_000);
      this.eps          = 1.0;
      this.epsMin       = 0.05;
      this.epsDecay     = 0.993;
      this.gamma        = 0.99;
      this.batchSize    = 32;
      this.episode      = 0;
      this.trainStep    = 0;
      this.losses       = [];
      this.actCounts    = new Array(ACTION_DIM).fill(0);
    }

    act(state) {
      let a;
      if (Math.random() < this.eps) {
        a = Math.floor(Math.random() * ACTION_DIM);
      } else {
        const q = this.pNet.predict(state);
        a = q.indexOf(Math.max(...q));
      }
      this.actCounts[a]++;
      return a;
    }

    learn() {
      if (this.buf.size < this.batchSize) return null;
      const batch = this.buf.sample(this.batchSize);
      let loss = 0;

      for (const [s, a, r, ns, done] of batch) {
        const fwd = this.pNet.forward(s);
        const q   = fwd.out.slice();

        // Double DQN: pNet selects action, tNet evaluates
        const qNextP = this.pNet.predict(ns);
        const bestA  = qNextP.indexOf(Math.max(...qNextP));
        const qNextT = this.tNet.predict(ns);
        const target = r + (1 - done) * this.gamma * qNextT[bestA];

        const diff  = target - q[a];
        // Huber gradient (δ=1)
        const grad  = new Array(ACTION_DIM).fill(0);
        grad[a]     = -(Math.abs(diff) <= 1 ? diff : Math.sign(diff));

        this.pNet.backward(grad, fwd);
        loss += diff * diff;
      }

      this.trainStep++;
      const avgL = loss / this.batchSize;
      this.losses.push(avgL);
      if (this.losses.length > 300) this.losses.shift();
      return avgL;
    }

    endEpisode() {
      this.episode++;
      this.eps = Math.max(this.epsMin, this.eps * this.epsDecay);
      if (this.episode % 10 === 0) this.tNet.copyFrom(this.pNet);
    }

    reset() {
      this.pNet  = new TinyNet([STATE_DIM, 32, 16, ACTION_DIM]);
      this.tNet  = new TinyNet([STATE_DIM, 32, 16, ACTION_DIM]);
      this.tNet.copyFrom(this.pNet);
      this.buf       = new ReplayBuffer(5_000);
      this.eps       = 1.0;
      this.episode   = 0;
      this.trainStep = 0;
      this.losses    = [];
      this.actCounts = new Array(ACTION_DIM).fill(0);
    }
  }

  /* ══════════════════════════════════════════════════════════════════
   *  TradingEnv — JS mirror of python trading_env.py
   * ══════════════════════════════════════════════════════════════════ */
  class TradingEnv {
    constructor(ticker = 'SPY') {
      const [mu, sig] = TICKERS[ticker] || [0.10, 0.18];
      this.mu  = mu;
      this.sig = sig;
      this._reset();
    }

    _reset() {
      const { prices, rets } = genPrices(this.mu, this.sig, EPISODE_LEN + WARM + 5);
      this.prices  = prices;
      this.rets    = rets;
      this.step    = 0;
      this.cash    = INIT_CAP;
      this.shares  = 0;
      this.peak    = INIT_CAP;
      this.history = [];
    }

    reset() { this._reset(); return this._state(); }

    _state() {
      const i = this.step + WARM;
      const p = this.prices, r = this.rets;

      const ret1  = clamp(r[i] / 0.03, -1, 1);
      const ret5  = clamp(r.slice(i - 4, i + 1).reduce((a, b) => a + b, 0) / 0.05, -1, 1);
      const ret10 = clamp(r.slice(i - 9, i + 1).reduce((a, b) => a + b, 0) / 0.08, -1, 1);

      // 20d vol
      const last20 = p.slice(i - 19, i + 1);
      const avgP   = mean(last20);
      const volP   = Math.sqrt(last20.reduce((s, x) => s + (x - avgP) ** 2, 0) / 20);
      const vol20  = clamp(volP / (p[i] + 1e-9) / 0.05, 0, 1);

      // SMA
      const sma20 = avgP;
      const sma50 = mean(p.slice(i - 49, i + 1));

      // RSI-like
      const diffs = r.slice(i - 13, i + 1);
      const ups   = diffs.filter(x => x > 0).reduce((a, b) => a + b, 0) / 14;
      const dns   = Math.abs(diffs.filter(x => x < 0).reduce((a, b) => a + b, 0)) / 14 + 1e-9;
      const rsi   = ups / (ups + dns);

      // Bollinger %B
      const std20  = Math.sqrt(last20.reduce((s, x) => s + (x - avgP) ** 2, 0) / 20) + 1e-9;
      const bbPos  = clamp((p[i] - (avgP - 2 * std20)) / (4 * std20), 0, 1);

      // Portfolio
      const pv      = this.cash + this.shares * p[i];
      const posR    = clamp((this.shares * p[i]) / INIT_CAP, -1, 1);
      const cashR   = clamp(this.cash / INIT_CAP, 0, 1);
      const upnl    = clamp((pv - INIT_CAP) / INIT_CAP * 2, -1, 1);
      const dd      = clamp((pv - this.peak) / (this.peak + 1e-9) * -2, 0, 1);
      const stepR   = this.step / EPISODE_LEN;

      // Trend + regime
      const trend   = clamp(Math.sign(ret10) * Math.abs(rsi - 0.5) * 2, -1, 1);
      const volReg  = vol20 > 0.5 ? 1 : 0;

      return [
        ret1, ret5, ret10, vol20,
        clamp((p[i] / sma20 - 1) / 0.1, -1, 1),
        clamp((p[i] / sma50 - 1) / 0.15, -1, 1),
        rsi, bbPos,
        posR, cashR, upnl, stepR, dd,
        trend,
        ret1 > 0 ? 1 : -1,   // direction
        volReg,
      ];
    }

    step_(action) {
      const i     = this.step + WARM;
      const price = this.prices[i];
      const pvPre = this.cash + this.shares * price;

      // Execute action
      if (action === 1) {
        const spend = Math.min(this.cash, 0.10 * INIT_CAP);
        if (spend >= price) {
          this.shares += spend / price * (1 - TRADE_COST);
          this.cash   -= spend;
        }
      } else if (action === 2) {
        const spend = Math.min(this.cash, 0.25 * INIT_CAP);
        if (spend >= price) {
          this.shares += spend / price * (1 - TRADE_COST);
          this.cash   -= spend;
        }
      } else if (action === 3) {
        const sv = Math.min(this.shares * price, 0.10 * INIT_CAP);
        if (sv > 0) { this.shares -= sv / price; this.cash += sv * (1 - TRADE_COST); }
      } else if (action === 4) {
        const sv = Math.min(this.shares * price, 0.25 * INIT_CAP);
        if (sv > 0) { this.shares -= sv / price; this.cash += sv * (1 - TRADE_COST); }
      }

      this.step++;
      const ni  = this.step + WARM;
      const np_ = ni < this.prices.length ? this.prices[ni] : price;
      const pv  = this.cash + this.shares * np_;
      this.peak = Math.max(this.peak, pv);

      const ret    = (pv - pvPre) / INIT_CAP;
      let reward   = ret;
      const dd     = (pv - this.peak) / this.peak;
      if (dd < -0.05) reward += 0.5 * dd;

      this.history.push({ val: pv, action, price });
      const done    = this.step >= EPISODE_LEN;
      const nextSt  = done ? new Array(STATE_DIM).fill(0) : this._state();
      return { nextSt, reward, done, val: pv, totalRet: (pv - INIT_CAP) / INIT_CAP };
    }
  }

  /* ══════════════════════════════════════════════════════════════════
   *  Module state
   * ══════════════════════════════════════════════════════════════════ */
  let _env    = null;
  let _agent  = null;
  let _raf    = null;
  let _running   = false;
  let _ticker    = 'SPY';
  let _maxEp     = 200;
  let _speed     = 5;      // episodes per animation frame
  let _returns   = [];
  let _losses    = [];
  let _sharpes   = [];
  let _initialized = false;

  /* ── HTML template ──────────────────────────────────────────────── */
  function _html() {
    return `
<div class="rll-root">
  <div class="rll-header">
    <span class="rll-title">🧠 RL Trading Lab</span>
    <span class="rll-sub">Browser DQN — Double Q-Network · Adam · ε-Greedy</span>
  </div>

  <div class="rll-body">
    <!-- ── Left Panel ───────────────────────────── -->
    <div class="rll-left">

      <div class="rll-panel">
        <div class="rll-panel-title">⚙ Configuration</div>

        <div class="rll-cfg-row">
          <label>Ticker</label>
          <select id="rll-ticker" onchange="RLLab._setTicker(this.value)">
            ${Object.keys(TICKERS).map(t => `<option value="${t}"${t === 'SPY' ? ' selected' : ''}>${t}</option>`).join('')}
          </select>
        </div>

        <div class="rll-cfg-row">
          <label>Max Episodes</label>
          <select id="rll-maxep" onchange="RLLab._setMaxEp(+this.value)">
            <option value="100">100</option>
            <option value="200" selected>200</option>
            <option value="500">500</option>
          </select>
        </div>

        <div class="rll-cfg-row">
          <label>Speed&nbsp;<span id="rll-spd-val" style="color:#4daaff">5 ep/frame</span></label>
          <input type="range" id="rll-speed" min="1" max="25" value="5"
                 oninput="RLLab._setSpeed(+this.value)"
                 style="width:100%;accent-color:#4daaff;margin-top:4px">
        </div>

        <div class="rll-btns">
          <button class="rll-btn rll-start" id="rll-start" onclick="RLLab.startTraining()">▶ Start</button>
          <button class="rll-btn rll-stop"  id="rll-stop"  onclick="RLLab.stopTraining()" disabled>■ Stop</button>
          <button class="rll-btn rll-reset" onclick="RLLab.reset()">↺ Reset</button>
        </div>
      </div>

      <!-- Live Metrics -->
      <div class="rll-panel">
        <div class="rll-panel-title">📊 Live Metrics</div>
        <div class="rll-metric-grid">
          <div class="rll-m"><span>Episode</span>   <strong id="rm-ep">0</strong></div>
          <div class="rll-m"><span>Return</span>    <strong id="rm-ret" style="color:#00ff88">+0.00%</strong></div>
          <div class="rll-m"><span>Sharpe</span>    <strong id="rm-shr">0.000</strong></div>
          <div class="rll-m"><span>ε Epsilon</span><strong id="rm-eps">1.000</strong></div>
          <div class="rll-m"><span>Win Rate</span>  <strong id="rm-wr">—</strong></div>
          <div class="rll-m"><span>Avg Loss</span>  <strong id="rm-loss">—</strong></div>
          <div class="rll-m"><span>Trades</span>    <strong id="rm-trd">0</strong></div>
          <div class="rll-m"><span>Buffer</span>    <strong id="rm-buf">0</strong></div>
        </div>

        <div class="rll-panel-title" style="margin-top:14px">Action Distribution</div>
        <div id="rll-act-dist">
          ${ACTIONS.map((n, i) => `
          <div class="rll-act-row">
            <span class="rll-act-name">${n}</span>
            <div class="rll-act-bg"><div class="rll-act-bar" id="rll-ab-${i}" style="width:20%"></div></div>
            <span class="rll-act-pct" id="rll-ap-${i}">20%</span>
          </div>`).join('')}
        </div>
      </div>

    </div><!-- end left -->

    <!-- ── Right Panel ──────────────────────────── -->
    <div class="rll-right">

      <div class="rll-panel rll-chart-panel">
        <div class="rll-panel-title">
          📈 Episode Returns
          <span style="color:#4daaff;font-size:10px;margin-left:8px">— rolling 10-ep avg</span>
          <span style="color:#5a5a8a;font-size:10px;margin-left:8px">| bars = individual episodes</span>
        </div>
        <canvas id="rll-ret-cv" width="620" height="200" style="width:100%;display:block"></canvas>
      </div>

      <div class="rll-panel rll-chart-panel">
        <div class="rll-panel-title">
          📉 Q-Loss &amp; ε Decay
          <span style="color:#ff7832;font-size:10px;margin-left:8px">— loss</span>
          <span style="color:#a060ff;font-size:10px;margin-left:8px">— ε decay</span>
        </div>
        <canvas id="rll-loss-cv" width="620" height="150" style="width:100%;display:block"></canvas>
      </div>

      <div class="rll-panel" id="rll-summary" style="display:none">
        <div class="rll-panel-title">🏆 Training Summary</div>
        <div class="rll-sum-grid" id="rll-sum-content"></div>
      </div>

    </div><!-- end right -->
  </div><!-- end body -->
</div>`;
  }

  /* ── Chart: Episode Returns ─────────────────────────────────────── */
  function _drawReturns() {
    const cv = document.getElementById('rll-ret-cv');
    if (!cv) return;
    const ctx = cv.getContext('2d');
    const W = cv.width, H = cv.height;
    const pad = { t: 15, r: 15, b: 28, l: 44 };
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#06060f'; ctx.fillRect(0, 0, W, H);

    const data = _returns;
    if (data.length < 2) {
      ctx.fillStyle = '#2a2a4a'; ctx.font = '11px monospace';
      ctx.fillText('Start training to see results...', W / 2 - 90, H / 2);
      return;
    }

    // Rolling 10-ep avg
    const roll = data.map((_, i) => {
      const sl = data.slice(Math.max(0, i - 9), i + 1);
      return mean(sl);
    });

    const minV = Math.min(...data, -5);
    const maxV = Math.max(...data,  5);
    const range = maxV - minV || 1;
    const cW   = W - pad.l - pad.r;
    const cH   = H - pad.t - pad.b;
    const xSc  = cW / Math.max(data.length - 1, 1);
    const yMap = v => pad.t + (1 - (v - minV) / range) * cH;

    // Zero line
    const y0 = yMap(0);
    ctx.strokeStyle = '#1a1a3a'; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(pad.l, y0); ctx.lineTo(W - pad.r, y0); ctx.stroke();
    ctx.setLineDash([]);

    // Episode bars
    for (let i = 0; i < data.length; i++) {
      const x  = pad.l + i * xSc;
      const yT = yMap(Math.max(data[i], 0));
      const yB = yMap(Math.min(data[i], 0));
      ctx.fillStyle = data[i] >= 0 ? 'rgba(0,255,136,0.28)' : 'rgba(255,80,80,0.28)';
      ctx.fillRect(x - 1, Math.min(yT, yB), 2, Math.abs(yT - yB) + 1);
    }

    // Rolling avg line
    ctx.strokeStyle = '#4daaff'; ctx.lineWidth = 2;
    ctx.beginPath();
    roll.forEach((v, i) => {
      const x = pad.l + i * xSc, y = yMap(v);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Y labels
    ctx.fillStyle = '#555577'; ctx.font = '9px monospace';
    ctx.fillText(`${maxV.toFixed(1)}%`, 2, pad.t + 6);
    ctx.fillText('0%', 2, y0 + 4);
    ctx.fillText(`${minV.toFixed(1)}%`, 2, H - pad.b + 1);

    // X labels
    const xstep = Math.max(1, Math.floor(data.length / 6));
    for (let i = 0; i < data.length; i += xstep) {
      ctx.fillText(`${i}`, pad.l + i * xSc - 6, H - 5);
    }
  }

  /* ── Chart: Q-Loss & ε ──────────────────────────────────────────── */
  function _drawLoss() {
    const cv = document.getElementById('rll-loss-cv');
    if (!cv) return;
    const ctx = cv.getContext('2d');
    const W = cv.width, H = cv.height;
    const pad = { t: 12, r: 15, b: 24, l: 44 };
    ctx.clearRect(0, 0, W, H); ctx.fillStyle = '#06060f'; ctx.fillRect(0, 0, W, H);

    const data = _losses;
    if (data.length < 2) return;

    const maxV = Math.max(...data) || 1;
    const cW   = W - pad.l - pad.r;
    const cH   = H - pad.t - pad.b;
    const xSc  = cW / Math.max(data.length - 1, 1);
    const yMap = v => pad.t + (1 - v / maxV) * cH;

    // Loss fill
    const grd = ctx.createLinearGradient(0, pad.t, 0, H - pad.b);
    grd.addColorStop(0, 'rgba(255,120,50,0.55)');
    grd.addColorStop(1, 'rgba(255,120,50,0.03)');
    ctx.beginPath();
    ctx.moveTo(pad.l, H - pad.b);
    data.forEach((v, i) => ctx.lineTo(pad.l + i * xSc, yMap(v)));
    ctx.lineTo(pad.l + (data.length - 1) * xSc, H - pad.b);
    ctx.closePath(); ctx.fillStyle = grd; ctx.fill();

    // Loss line
    ctx.strokeStyle = '#ff7832'; ctx.lineWidth = 1.5;
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = pad.l + i * xSc, y = yMap(v);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    // ε curve overlay (right axis 0-1)
    if (_agent) {
      const epsArr = data.map((_, i) =>
        Math.max(0.05, 1.0 * Math.pow(0.993, Math.floor(i * _agent.episode / data.length)))
      );
      ctx.strokeStyle = 'rgba(160,90,255,0.7)'; ctx.lineWidth = 1.5; ctx.setLineDash([3, 3]);
      ctx.beginPath();
      epsArr.forEach((v, i) => {
        const x = pad.l + i * xSc, y = pad.t + (1 - v) * cH;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.stroke(); ctx.setLineDash([]);
    }

    ctx.fillStyle = '#555577'; ctx.font = '9px monospace';
    ctx.fillText(maxV.toFixed(4), 2, pad.t + 6);
    ctx.fillText('0', 6, H - pad.b + 1);
  }

  /* ── Metrics UI update ──────────────────────────────────────────── */
  function _updateUI(ret, sharpe, nTrades) {
    const $ = id => document.getElementById(id);
    if (!$('rm-ep')) return;

    $('rm-ep').textContent  = _agent.episode;
    const rs = `${ret >= 0 ? '+' : ''}${ret.toFixed(2)}%`;
    $('rm-ret').textContent = rs;
    $('rm-ret').style.color = ret >= 0 ? '#00ff88' : '#ff5555';
    $('rm-shr').textContent  = sharpe.toFixed(3);
    $('rm-eps').textContent  = _agent.eps.toFixed(3);
    $('rm-trd').textContent  = nTrades;
    $('rm-buf').textContent  = _agent.buf.size;

    const wins = _returns.filter(r => r > 0).length;
    $('rm-wr').textContent  = _returns.length ? `${(wins / _returns.length * 100).toFixed(1)}%` : '—';

    const avgL = _agent.losses.length
      ? mean(_agent.losses.slice(-20)).toFixed(5)
      : '—';
    $('rm-loss').textContent = avgL;

    // Action distribution bars
    const total = _agent.actCounts.reduce((a, b) => a + b, 0) || 1;
    for (let i = 0; i < ACTION_DIM; i++) {
      const pct = (_agent.actCounts[i] / total * 100);
      const bar = $(`rll-ab-${i}`), pctEl = $(`rll-ap-${i}`);
      if (bar)   bar.style.width = pct.toFixed(0) + '%';
      if (pctEl) pctEl.textContent = pct.toFixed(0) + '%';
    }
  }

  /* ── Training tick (runs via requestAnimationFrame) ─────────────── */
  function _tick() {
    if (!_running) return;

    const batch = Math.min(_speed, _maxEp - _agent.episode);
    for (let b = 0; b < batch; b++) {
      let state    = _env.reset();
      let nTrades  = 0;
      let lastInfo = null;
      const stepRets = [];

      for (let s = 0; s < EPISODE_LEN; s++) {
        const a               = _agent.act(state);
        const { nextSt, reward, done, totalRet } = _env.step_(a);
        _agent.buf.push(state, a, reward, nextSt, done);
        _agent.learn();
        if (a !== 0) nTrades++;
        stepRets.push(totalRet * 100);
        state    = nextSt;
        lastInfo = { totalRet };
        if (done) break;
      }

      _agent.endEpisode();
      const ret  = (lastInfo?.totalRet ?? 0) * 100;
      _returns.push(ret);

      // Sharpe estimate
      const diffs = stepRets.map((r, i) => i > 0 ? r - stepRets[i - 1] : 0).slice(1);
      const shr   = diffs.length > 1 ? mean(diffs) / std(diffs) * Math.sqrt(252) : 0;
      _sharpes.push(shr);

      if (_agent.losses.length)
        _losses.push(_agent.losses[_agent.losses.length - 1]);

      _updateUI(ret, shr, nTrades);
    }

    _drawReturns();
    _drawLoss();

    if (_agent.episode >= _maxEp) {
      stopTraining();
      _showSummary();
      return;
    }

    _raf = requestAnimationFrame(_tick);
  }

  /* ── Summary ────────────────────────────────────────────────────── */
  function _showSummary() {
    const panel = document.getElementById('rll-summary');
    const grid  = document.getElementById('rll-sum-content');
    if (!panel || !grid) return;

    const wins = _returns.filter(r => r > 0).length;
    const avgR = mean(_returns);
    const avgS = mean(_sharpes);

    grid.innerHTML = `
      <div class="rll-si"><span>Episodes</span><strong>${_returns.length}</strong></div>
      <div class="rll-si"><span>Win Rate</span><strong>${(_returns.length ? wins/_returns.length*100 : 0).toFixed(1)}%</strong></div>
      <div class="rll-si"><span>Avg Return</span><strong style="color:${avgR>=0?'#00ff88':'#ff5555'}">${avgR>=0?'+':''}${avgR.toFixed(2)}%</strong></div>
      <div class="rll-si"><span>Best Episode</span><strong style="color:#00ff88">+${Math.max(..._returns).toFixed(2)}%</strong></div>
      <div class="rll-si"><span>Worst Episode</span><strong style="color:#ff5555">${Math.min(..._returns).toFixed(2)}%</strong></div>
      <div class="rll-si"><span>Avg Sharpe</span><strong>${avgS.toFixed(3)}</strong></div>
      <div class="rll-si"><span>Final ε</span><strong>${_agent.eps.toFixed(4)}</strong></div>
      <div class="rll-si"><span>Train Steps</span><strong>${_agent.trainStep.toLocaleString()}</strong></div>
    `;
    panel.style.display = 'block';
  }

  /* ── Public API ─────────────────────────────────────────────────── */
  function init() {
    const view = document.getElementById('view-rl');
    if (!view) return;
    if (view.dataset.rlInit) return;
    view.dataset.rlInit = '1';

    view.innerHTML = _html();
    _env   = new TradingEnv(_ticker);
    _agent = new DQNAgent();
    _initialized = true;

    // Initial blank charts
    setTimeout(() => { _drawReturns(); _drawLoss(); }, 50);
  }

  function startTraining() {
    if (!_initialized) init();
    if (_running) return;
    _running = true;

    const s = document.getElementById('rll-start');
    const t = document.getElementById('rll-stop');
    if (s) s.disabled = true;
    if (t) t.disabled = false;

    _raf = requestAnimationFrame(_tick);
  }

  function stopTraining() {
    _running = false;
    if (_raf) { cancelAnimationFrame(_raf); _raf = null; }

    const s = document.getElementById('rll-start');
    const t = document.getElementById('rll-stop');
    if (s) s.disabled = false;
    if (t) t.disabled = true;
  }

  function reset() {
    stopTraining();
    if (_agent) _agent.reset();
    _env      = new TradingEnv(_ticker);
    _returns  = [];
    _losses   = [];
    _sharpes  = [];
    document.getElementById('rll-summary') &&
      (document.getElementById('rll-summary').style.display = 'none');
    _drawReturns(); _drawLoss();
    _updateUI(0, 0, 0);
  }

  function _setTicker(t) {
    _ticker = t;
    _env    = new TradingEnv(t);
  }
  function _setMaxEp(n) { _maxEp = n; }
  function _setSpeed(v) {
    _speed = v;
    const el = document.getElementById('rll-spd-val');
    if (el) el.textContent = `${v} ep/frame`;
  }

  return { init, startTraining, stopTraining, reset, _setTicker, _setMaxEp, _setSpeed };

})();
