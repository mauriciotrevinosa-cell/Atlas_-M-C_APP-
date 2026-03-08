/**
 * Indicator Terminal — Interactive Technical Analysis Lab
 * =========================================================
 * A visual terminal where users can:
 *  - Toggle indicators ON/OFF and overlay them on a candlestick chart
 *  - Configure indicator parameters (period, source, etc.)
 *  - Stack multiple indicators visually
 *  - Launch quick simulations with selected indicators
 *  - See indicator signals (BUY/SELL/NEUTRAL) in real-time
 *
 * Chart: lightweight-charts (already loaded in index.html)
 * Indicators: pure JS — no external TA library dependency
 *
 * @module IndicatorTerminal
 */

'use strict';

/* ═══════════════════════════════════════════════════════════
   STATE
═══════════════════════════════════════════════════════════ */
window.IndicatorTerminal = (() => {

  // Active indicators map: { id: { def, params, series, enabled } }
  const _active = {};
  let _chart      = null;
  let _candleSeries = null;
  let _ticker     = 'AAPL';
  let _data       = [];          // [{time, open, high, low, close, volume}]
  let _initialized = false;

  // ── Colour palette for indicator lines ────────────────────────────────────
  const COLOURS = [
    '#4488ff', '#ff6b6b', '#00e5a0', '#ffd93d', '#a78bfa',
    '#f97316', '#06b6d4', '#ec4899', '#84cc16', '#f43f5e',
  ];
  let _colourIdx = 0;
  function nextColour() { return COLOURS[(_colourIdx++) % COLOURS.length]; }

  /* ═══════════════════════════════════════════════════════════
     INDICATOR REGISTRY
  ═══════════════════════════════════════════════════════════ */
  const INDICATORS = {

    /* ── Trend ──────────────────────────────────────────────────── */
    SMA: {
      label: 'SMA', fullName: 'Simple Moving Average',
      category: 'Trend', overlay: true,
      params: [{ key: 'period', label: 'Period', default: 20, min: 2, max: 200 }],
      compute(data, p) {
        const n = p.period;
        return data.map((_, i) => {
          if (i < n - 1) return null;
          const avg = data.slice(i - n + 1, i + 1).reduce((s, d) => s + d.close, 0) / n;
          return { time: data[i].time, value: avg };
        }).filter(Boolean);
      },
      signal(last, prev) {
        if (!last || !prev) return 'NEUTRAL';
        return last.value > prev.value ? 'BULLISH' : 'BEARISH';
      },
    },

    EMA: {
      label: 'EMA', fullName: 'Exponential Moving Average',
      category: 'Trend', overlay: true,
      params: [{ key: 'period', label: 'Period', default: 21, min: 2, max: 200 }],
      compute(data, p) {
        const k = 2 / (p.period + 1);
        const result = [];
        let ema = data[0].close;
        data.forEach((d, i) => {
          if (i === 0) { result.push({ time: d.time, value: ema }); return; }
          ema = d.close * k + ema * (1 - k);
          result.push({ time: d.time, value: ema });
        });
        return result;
      },
      signal(last, prev) {
        if (!last || !prev) return 'NEUTRAL';
        return last.value > prev.value ? 'BULLISH' : 'BEARISH';
      },
    },

    BBANDS: {
      label: 'BB', fullName: 'Bollinger Bands',
      category: 'Trend', overlay: true,
      params: [
        { key: 'period', label: 'Period', default: 20, min: 5, max: 100 },
        { key: 'stdDev', label: 'Std Dev', default: 2, min: 1, max: 4 },
      ],
      compute(data, p) {
        const { period, stdDev } = p;
        const mid = [], upper = [], lower = [];
        for (let i = period - 1; i < data.length; i++) {
          const slice = data.slice(i - period + 1, i + 1).map(d => d.close);
          const mean  = slice.reduce((s, v) => s + v, 0) / period;
          const std   = Math.sqrt(slice.reduce((s, v) => s + (v - mean) ** 2, 0) / period);
          const t     = data[i].time;
          mid.push({ time: t, value: mean });
          upper.push({ time: t, value: mean + stdDev * std });
          lower.push({ time: t, value: mean - stdDev * std });
        }
        return { mid, upper, lower, multi: true };
      },
      signal(result) {
        if (!result || !result.upper || !result.lower) return 'NEUTRAL';
        const u = result.upper; const l = result.lower;
        if (!u.length || !l.length) return 'NEUTRAL';
        const lu = u[u.length - 1].value;
        const ll = l[l.length - 1].value;
        const lm = result.mid[result.mid.length - 1].value;
        const dist = lu - ll;
        if (dist < lm * 0.02) return 'SQUEEZE';
        return 'NEUTRAL';
      },
    },

    /* ── Momentum ────────────────────────────────────────────────── */
    RSI: {
      label: 'RSI', fullName: 'Relative Strength Index',
      category: 'Momentum', overlay: false,
      params: [{ key: 'period', label: 'Period', default: 14, min: 2, max: 50 }],
      compute(data, p) {
        const n = p.period;
        const gains = [], losses = [];
        for (let i = 1; i < data.length; i++) {
          const d = data[i].close - data[i - 1].close;
          gains.push(d > 0 ? d : 0);
          losses.push(d < 0 ? -d : 0);
        }
        const result = [];
        let avgG = gains.slice(0, n).reduce((a, b) => a + b, 0) / n;
        let avgL = losses.slice(0, n).reduce((a, b) => a + b, 0) / n;
        for (let i = n; i < data.length; i++) {
          avgG = (avgG * (n - 1) + gains[i - 1]) / n;
          avgL = (avgL * (n - 1) + losses[i - 1]) / n;
          const rs  = avgL === 0 ? 100 : avgG / avgL;
          const rsi = 100 - 100 / (1 + rs);
          result.push({ time: data[i].time, value: rsi });
        }
        return result;
      },
      signal(last) {
        if (!last) return 'NEUTRAL';
        if (last.value >= 70) return 'OVERBOUGHT';
        if (last.value <= 30) return 'OVERSOLD';
        return 'NEUTRAL';
      },
    },

    MACD: {
      label: 'MACD', fullName: 'MACD (12,26,9)',
      category: 'Momentum', overlay: false,
      params: [
        { key: 'fast',   label: 'Fast EMA',   default: 12, min: 2, max: 50 },
        { key: 'slow',   label: 'Slow EMA',   default: 26, min: 5, max: 100 },
        { key: 'signal', label: 'Signal EMA', default: 9,  min: 2, max: 20 },
      ],
      compute(data, p) {
        const ema = (arr, n) => {
          const k = 2 / (n + 1); let e = arr[0];
          return arr.map((v, i) => { if (i === 0) return e; e = v * k + e * (1 - k); return e; });
        };
        const closes   = data.map(d => d.close);
        const fastEMA  = ema(closes, p.fast);
        const slowEMA  = ema(closes, p.slow);
        const macdLine = fastEMA.map((v, i) => v - slowEMA[i]);
        const sigLine  = ema(macdLine.slice(p.slow), p.signal);
        const offset   = p.slow;
        const macdOut = [], sigOut = [], histOut = [];
        sigLine.forEach((sv, i) => {
          const idx = i + offset;
          const t   = data[idx] ? data[idx].time : null;
          if (!t) return;
          macdOut.push({ time: t, value: macdLine[idx] });
          sigOut.push({ time: t, value: sv });
          histOut.push({ time: t, value: macdLine[idx] - sv });
        });
        return { macd: macdOut, signal: sigOut, hist: histOut, multi: true };
      },
      signal(result) {
        if (!result || !result.hist || !result.hist.length) return 'NEUTRAL';
        const last = result.hist[result.hist.length - 1].value;
        const prev = result.hist.length > 1 ? result.hist[result.hist.length - 2].value : 0;
        if (last > 0 && prev <= 0) return 'BULLISH CROSS';
        if (last < 0 && prev >= 0) return 'BEARISH CROSS';
        return last > 0 ? 'BULLISH' : 'BEARISH';
      },
    },

    STOCH: {
      label: 'STOCH', fullName: 'Stochastic Oscillator',
      category: 'Momentum', overlay: false,
      params: [
        { key: 'kPeriod', label: '%K Period', default: 14, min: 3, max: 50 },
        { key: 'dPeriod', label: '%D Period', default: 3,  min: 1, max: 10 },
      ],
      compute(data, p) {
        const kOut = [], dOut = [];
        for (let i = p.kPeriod - 1; i < data.length; i++) {
          const slice = data.slice(i - p.kPeriod + 1, i + 1);
          const lo = Math.min(...slice.map(d => d.low));
          const hi = Math.max(...slice.map(d => d.high));
          const k  = hi === lo ? 50 : ((data[i].close - lo) / (hi - lo)) * 100;
          kOut.push({ time: data[i].time, value: k });
        }
        const dSMA = (arr, n) => arr.map((v, i) => {
          if (i < n - 1) return null;
          const avg = arr.slice(i - n + 1, i + 1).reduce((s, x) => s + x.value, 0) / n;
          return { time: v.time, value: avg };
        }).filter(Boolean);
        return { k: kOut, d: dSMA(kOut, p.dPeriod), multi: true };
      },
      signal(result) {
        if (!result || !result.k || !result.k.length) return 'NEUTRAL';
        const kv = result.k[result.k.length - 1].value;
        if (kv >= 80) return 'OVERBOUGHT';
        if (kv <= 20) return 'OVERSOLD';
        return 'NEUTRAL';
      },
    },

    /* ── Volatility ──────────────────────────────────────────────── */
    ATR: {
      label: 'ATR', fullName: 'Average True Range',
      category: 'Volatility', overlay: false,
      params: [{ key: 'period', label: 'Period', default: 14, min: 2, max: 50 }],
      compute(data, p) {
        const result = [];
        let atr = 0;
        for (let i = 1; i < data.length; i++) {
          const tr = Math.max(
            data[i].high - data[i].low,
            Math.abs(data[i].high - data[i - 1].close),
            Math.abs(data[i].low  - data[i - 1].close),
          );
          if (i < p.period) { atr += tr / p.period; }
          else if (i === p.period) { result.push({ time: data[i].time, value: atr }); }
          else {
            atr = (atr * (p.period - 1) + tr) / p.period;
            result.push({ time: data[i].time, value: atr });
          }
        }
        return result;
      },
      signal(last, prev) {
        if (!last || !prev) return 'NEUTRAL';
        return last.value > prev.value * 1.1 ? 'EXPANDING' : 'CONTRACTING';
      },
    },

    /* ── Volume ──────────────────────────────────────────────────── */
    VWAP: {
      label: 'VWAP', fullName: 'Volume Weighted Avg Price',
      category: 'Volume', overlay: true,
      params: [],
      compute(data) {
        let cumPV = 0, cumV = 0;
        return data.map(d => {
          const typicalPrice = (d.high + d.low + d.close) / 3;
          cumPV += typicalPrice * (d.volume || 1);
          cumV  += (d.volume || 1);
          return { time: d.time, value: cumV > 0 ? cumPV / cumV : d.close };
        });
      },
      signal(last, data) {
        if (!last || !data || !data.length) return 'NEUTRAL';
        const lastClose = data[data.length - 1].close;
        return lastClose > last.value ? 'ABOVE VWAP' : 'BELOW VWAP';
      },
    },

    /* ── Additional ──────────────────────────────────────────────── */
    ADX: {
      label: 'ADX', fullName: 'Avg Directional Index',
      category: 'Trend', overlay: false,
      params: [{ key: 'period', label: 'Period', default: 14, min: 2, max: 50 }],
      compute(data, p) {
        const n = p.period;
        const result = [];
        for (let i = n; i < data.length; i++) {
          const slice = data.slice(i - n, i + 1);
          let plusDM = 0, minusDM = 0, trSum = 0;
          for (let j = 1; j < slice.length; j++) {
            const upMove   = slice[j].high - slice[j - 1].high;
            const downMove = slice[j - 1].low - slice[j].low;
            plusDM  += (upMove > downMove && upMove > 0) ? upMove : 0;
            minusDM += (downMove > upMove && downMove > 0) ? downMove : 0;
            trSum   += Math.max(
              slice[j].high - slice[j].low,
              Math.abs(slice[j].high - slice[j - 1].close),
              Math.abs(slice[j].low  - slice[j - 1].close),
            );
          }
          if (trSum === 0) { result.push({ time: data[i].time, value: 0 }); continue; }
          const diPlus  = (plusDM / trSum) * 100;
          const diMinus = (minusDM / trSum) * 100;
          const dx      = (diPlus + diMinus) === 0 ? 0 : Math.abs(diPlus - diMinus) / (diPlus + diMinus) * 100;
          result.push({ time: data[i].time, value: dx });
        }
        return result;
      },
      signal(last) {
        if (!last) return 'NEUTRAL';
        if (last.value >= 40) return 'STRONG TREND';
        if (last.value >= 25) return 'TRENDING';
        return 'RANGING';
      },
    },

    /* ── Additional Trend ────────────────────────────────────────── */
    TEMA: {
      label: 'TEMA', fullName: 'Triple Exponential MA',
      category: 'Trend', overlay: true,
      params: [{ key: 'period', label: 'Period', default: 21, min: 2, max: 100 }],
      compute(data, p) {
        const ema = (arr, n) => {
          const k = 2 / (n + 1); let e = arr[0];
          return arr.map((v, i) => { if (i === 0) return e; e = v * k + e * (1 - k); return e; });
        };
        const c = data.map(d => d.close);
        const e1 = ema(c, p.period);
        const e2 = ema(e1, p.period);
        const e3 = ema(e2, p.period);
        return data.map((d, i) => ({ time: d.time, value: 3 * e1[i] - 3 * e2[i] + e3[i] }));
      },
      signal(last, prev) {
        if (!last || !prev) return 'NEUTRAL';
        return last.value > prev.value ? 'BULLISH' : 'BEARISH';
      },
    },

    HULL: {
      label: 'HMA', fullName: 'Hull Moving Average',
      category: 'Trend', overlay: true,
      params: [{ key: 'period', label: 'Period', default: 16, min: 4, max: 100 }],
      compute(data, p) {
        const n = p.period;
        const wma = (arr, len) => {
          const out = [];
          for (let i = len - 1; i < arr.length; i++) {
            let num = 0, den = 0;
            for (let j = 0; j < len; j++) { const w = len - j; num += w * arr[i - j]; den += w; }
            out.push(num / den);
          }
          return out;
        };
        const c = data.map(d => d.close);
        const half  = Math.max(2, Math.floor(n / 2));
        const sqrtN = Math.max(2, Math.round(Math.sqrt(n)));
        const w1 = wma(c, half);
        const w2 = wma(c, n);
        const raw = w1.slice(n - half).map((v, i) => 2 * v - w2[i]);
        const hull = wma(raw, sqrtN);
        const start = n - 1 + sqrtN - 1;
        return hull.map((v, i) => ({
          time: data[Math.min(start + i, data.length - 1)].time,
          value: v,
        }));
      },
      signal(last, prev) {
        if (!last || !prev) return 'NEUTRAL';
        return last.value > prev.value ? 'BULLISH' : 'BEARISH';
      },
    },

    SUPERTREND: {
      label: 'SUPTRD', fullName: 'Supertrend',
      category: 'Trend', overlay: true,
      params: [
        { key: 'period', label: 'ATR Period', default: 10, min: 2, max: 50 },
        { key: 'mult',   label: 'Multiplier', default: 3,  min: 1, max: 10 },
      ],
      compute(data, p) {
        const n = p.period, m = p.mult;
        // Wilder ATR
        const atrs = [0];
        for (let i = 1; i < data.length; i++) {
          const tr = Math.max(
            data[i].high - data[i].low,
            Math.abs(data[i].high - data[i - 1].close),
            Math.abs(data[i].low  - data[i - 1].close),
          );
          atrs.push(i < n ? (atrs[i - 1] * (i - 1) + tr) / i : (atrs[i - 1] * (n - 1) + tr) / n);
        }
        // Supertrend bands
        let finalUpper = 0, finalLower = 0, superTrend = 0;
        const result = [];
        for (let i = n; i < data.length; i++) {
          const hl2 = (data[i].high + data[i].low) / 2;
          const bu  = hl2 + m * atrs[i];
          const bl  = hl2 - m * atrs[i];
          finalUpper = (bu < finalUpper || data[i - 1].close > finalUpper) ? bu : finalUpper;
          finalLower = (bl > finalLower || data[i - 1].close < finalLower) ? bl : finalLower;
          superTrend = data[i].close <= finalUpper ? finalUpper : finalLower;
          result.push({ time: data[i].time, value: superTrend });
        }
        return result;
      },
      signal(last, _prev, data) {
        if (!last || !data || !data.length) return 'NEUTRAL';
        return data[data.length - 1].close > last.value ? 'BUY ▲' : 'SELL ▼';
      },
    },

    ICHIMOKU: {
      label: 'ICHI', fullName: 'Ichimoku Cloud',
      category: 'Trend', overlay: true,
      params: [
        { key: 'tenkan',  label: 'Tenkan',  default: 9,  min: 3, max: 30 },
        { key: 'kijun',   label: 'Kijun',   default: 26, min: 5, max: 60 },
        { key: 'senkou',  label: 'Senkou B', default: 52, min: 10, max: 120 },
      ],
      compute(data, p) {
        const midpoint = (d, n, i) => {
          const sl = d.slice(Math.max(0, i - n + 1), i + 1);
          return (Math.max(...sl.map(x => x.high)) + Math.min(...sl.map(x => x.low))) / 2;
        };
        const tenkan = [], kijun = [], senkouA = [], senkouB = [];
        for (let i = 0; i < data.length; i++) {
          if (i >= p.tenkan - 1) tenkan.push({ time: data[i].time, value: midpoint(data, p.tenkan, i) });
          if (i >= p.kijun  - 1) kijun.push( { time: data[i].time, value: midpoint(data, p.kijun,  i) });
          if (i >= p.kijun  - 1) {
            const t = tenkan[tenkan.length - 1]?.value || 0;
            const k = kijun[kijun.length   - 1]?.value || 0;
            senkouA.push({ time: data[i].time, value: (t + k) / 2 });
          }
          if (i >= p.senkou - 1) senkouB.push({ time: data[i].time, value: midpoint(data, p.senkou, i) });
        }
        return { tenkan, kijun, senkouA, senkouB, multi: true };
      },
      signal(result, _prev, data) {
        if (!result || !data || !data.length) return 'NEUTRAL';
        const close  = data[data.length - 1].close;
        const kLast  = result.kijun?.[result.kijun.length   - 1]?.value;
        const saLast = result.senkouA?.[result.senkouA.length - 1]?.value;
        const sbLast = result.senkouB?.[result.senkouB.length - 1]?.value;
        if (!kLast) return 'NEUTRAL';
        const cloudTop = Math.max(saLast || 0, sbLast || 0);
        const cloudBot = Math.min(saLast || 0, sbLast || 0);
        if (close > cloudTop && close > kLast) return 'STRONG BULL';
        if (close < cloudBot && close < kLast) return 'STRONG BEAR';
        if (close > kLast) return 'BULLISH';
        return 'BEARISH';
      },
    },

    /* ── Additional Momentum ─────────────────────────────────────── */
    CCI: {
      label: 'CCI', fullName: 'Commodity Channel Index',
      category: 'Momentum', overlay: false,
      params: [{ key: 'period', label: 'Period', default: 20, min: 5, max: 100 }],
      compute(data, p) {
        const n = p.period;
        const result = [];
        for (let i = n - 1; i < data.length; i++) {
          const sl  = data.slice(i - n + 1, i + 1);
          const tp  = sl.map(d => (d.high + d.low + d.close) / 3);
          const mean = tp.reduce((s, v) => s + v, 0) / n;
          const mad  = tp.reduce((s, v) => s + Math.abs(v - mean), 0) / n;
          result.push({ time: data[i].time, value: mad === 0 ? 0 : (tp[n - 1] - mean) / (0.015 * mad) });
        }
        return result;
      },
      signal(last) {
        if (!last) return 'NEUTRAL';
        if (last.value >  100) return 'OVERBOUGHT';
        if (last.value < -100) return 'OVERSOLD';
        return last.value > 0 ? 'BULLISH' : 'BEARISH';
      },
    },

    WILLR: {
      label: '%R', fullName: "Williams %R",
      category: 'Momentum', overlay: false,
      params: [{ key: 'period', label: 'Period', default: 14, min: 2, max: 50 }],
      compute(data, p) {
        const n = p.period;
        const result = [];
        for (let i = n - 1; i < data.length; i++) {
          const sl = data.slice(i - n + 1, i + 1);
          const hi = Math.max(...sl.map(d => d.high));
          const lo = Math.min(...sl.map(d => d.low));
          result.push({ time: data[i].time, value: hi === lo ? -50 : ((hi - data[i].close) / (hi - lo)) * -100 });
        }
        return result;
      },
      signal(last) {
        if (!last) return 'NEUTRAL';
        if (last.value >= -20) return 'OVERBOUGHT';
        if (last.value <= -80) return 'OVERSOLD';
        return 'NEUTRAL';
      },
    },

    ROC: {
      label: 'ROC', fullName: 'Rate of Change %',
      category: 'Momentum', overlay: false,
      params: [{ key: 'period', label: 'Period', default: 12, min: 1, max: 50 }],
      compute(data, p) {
        const n = p.period;
        return data.slice(n).map((d, i) => ({
          time:  d.time,
          value: data[i].close === 0 ? 0 : ((d.close - data[i].close) / data[i].close) * 100,
        }));
      },
      signal(last) {
        if (!last) return 'NEUTRAL';
        if (last.value >  5) return 'STRONG UP';
        if (last.value >  0) return 'BULLISH';
        if (last.value < -5) return 'STRONG DOWN';
        return 'BEARISH';
      },
    },

    MOM: {
      label: 'MOM', fullName: 'Momentum Oscillator',
      category: 'Momentum', overlay: false,
      params: [{ key: 'period', label: 'Period', default: 10, min: 1, max: 50 }],
      compute(data, p) {
        const n = p.period;
        return data.slice(n).map((d, i) => ({ time: d.time, value: d.close - data[i].close }));
      },
      signal(last, prev) {
        if (!last) return 'NEUTRAL';
        if (last.value > 0 && prev && prev.value <= 0) return 'TURNING UP';
        if (last.value < 0 && prev && prev.value >= 0) return 'TURNING DOWN';
        return last.value > 0 ? 'BULLISH' : 'BEARISH';
      },
    },

    /* ── Additional Volume ───────────────────────────────────────── */
    OBV: {
      label: 'OBV', fullName: 'On Balance Volume',
      category: 'Volume', overlay: false,
      params: [],
      compute(data) {
        let obv = 0;
        return data.map((d, i) => {
          if (i > 0) {
            if (d.close > data[i - 1].close)      obv += (d.volume || 0);
            else if (d.close < data[i - 1].close) obv -= (d.volume || 0);
          }
          return { time: d.time, value: obv };
        });
      },
      signal(last, prev) {
        if (!last || !prev) return 'NEUTRAL';
        return last.value > prev.value ? 'ACCUMULATION' : 'DISTRIBUTION';
      },
    },

    CMF: {
      label: 'CMF', fullName: 'Chaikin Money Flow',
      category: 'Volume', overlay: false,
      params: [{ key: 'period', label: 'Period', default: 20, min: 5, max: 50 }],
      compute(data, p) {
        const n = p.period;
        const mfv = data.map(d => {
          const hl = d.high - d.low;
          if (hl === 0) return 0;
          return ((d.close - d.low) - (d.high - d.close)) / hl * (d.volume || 1);
        });
        const result = [];
        for (let i = n - 1; i < data.length; i++) {
          const mfvSum = mfv.slice(i - n + 1, i + 1).reduce((s, v) => s + v, 0);
          const volSum = data.slice(i - n + 1, i + 1).reduce((s, d) => s + (d.volume || 1), 0);
          result.push({ time: data[i].time, value: volSum === 0 ? 0 : mfvSum / volSum });
        }
        return result;
      },
      signal(last) {
        if (!last) return 'NEUTRAL';
        if (last.value >  0.1) return 'BUYING PRESSURE';
        if (last.value < -0.1) return 'SELLING PRESSURE';
        return 'NEUTRAL';
      },
    },

    MFI: {
      label: 'MFI', fullName: 'Money Flow Index',
      category: 'Volume', overlay: false,
      params: [{ key: 'period', label: 'Period', default: 14, min: 2, max: 50 }],
      compute(data, p) {
        const n   = p.period;
        const tp  = data.map(d => (d.high + d.low + d.close) / 3);
        const rmf = data.map((d, i) => tp[i] * (d.volume || 1));
        const result = [];
        for (let i = n; i < data.length; i++) {
          let pos = 0, neg = 0;
          for (let j = i - n + 1; j <= i; j++) {
            (tp[j] >= tp[j - 1] ? pos : neg) && (tp[j] >= tp[j - 1] ? (pos += rmf[j]) : (neg += rmf[j]));
            if (tp[j] >= tp[j - 1]) pos += rmf[j]; else neg += rmf[j];
          }
          // Fix double-count: divide by 2
          pos /= 2; neg /= 2;
          result.push({ time: data[i].time, value: neg === 0 ? 100 : 100 - 100 / (1 + pos / neg) });
        }
        return result;
      },
      signal(last) {
        if (!last) return 'NEUTRAL';
        if (last.value >= 80) return 'OVERBOUGHT';
        if (last.value <= 20) return 'OVERSOLD';
        return 'NEUTRAL';
      },
    },

    /* ── Additional Volatility ───────────────────────────────────── */
    KELTNER: {
      label: 'KELT', fullName: 'Keltner Channels',
      category: 'Volatility', overlay: true,
      params: [
        { key: 'period', label: 'EMA Period', default: 20, min: 5, max: 100 },
        { key: 'mult',   label: 'ATR Mult',   default: 2,  min: 1, max: 5   },
      ],
      compute(data, p) {
        const n = p.period, m = p.mult;
        const k = 2 / (n + 1);
        let ema = data[0].close, atr = 0;
        const mid = [], upper = [], lower = [];
        data.forEach((d, i) => {
          ema = i === 0 ? d.close : d.close * k + ema * (1 - k);
          if (i > 0) {
            const tr = Math.max(d.high - d.low, Math.abs(d.high - data[i-1].close), Math.abs(d.low - data[i-1].close));
            atr = i < n ? (atr * (i - 1) + tr) / i : (atr * (n - 1) + tr) / n;
          }
          if (i >= n) {
            mid.push({ time: d.time, value: ema });
            upper.push({ time: d.time, value: ema + m * atr });
            lower.push({ time: d.time, value: ema - m * atr });
          }
        });
        return { mid, upper, lower, multi: true };
      },
      signal(result, _prev, data) {
        if (!result || !result.upper || !data || !data.length) return 'NEUTRAL';
        const close = data[data.length - 1].close;
        const u = result.upper[result.upper.length - 1]?.value;
        const l = result.lower[result.lower.length - 1]?.value;
        if (!u || !l) return 'NEUTRAL';
        if (close > u) return 'ABOVE UPPER';
        if (close < l) return 'BELOW LOWER';
        return 'WITHIN BANDS';
      },
    },

  };


  /* ═══════════════════════════════════════════════════════════
     SYNTHETIC DATA GENERATOR
  ═══════════════════════════════════════════════════════════ */
  function _generateData(ticker, bars = 200) {
    // Fetch from backend API — fallback to synthetic if unavailable
    const START_PRICE = { AAPL: 185, MSFT: 375, NVDA: 480, TSLA: 245, SPY: 445 }[ticker] || 100;
    const data = [];
    let price = START_PRICE;
    const now  = Math.floor(Date.now() / 1000);
    const DAY  = 86400;

    for (let i = bars - 1; i >= 0; i--) {
      const t = now - i * DAY;
      const change  = (Math.random() - 0.48) * price * 0.025;
      const open    = price;
      const close   = Math.max(1, price + change);
      const hi      = Math.max(open, close) * (1 + Math.random() * 0.01);
      const lo      = Math.min(open, close) * (1 - Math.random() * 0.01);
      const volume  = Math.floor(Math.random() * 5_000_000 + 1_000_000);
      data.push({ time: t, open, high: hi, low: lo, close, volume });
      price = close;
    }
    return data;
  }

  /* ═══════════════════════════════════════════════════════════
     BUILD UI
  ═══════════════════════════════════════════════════════════ */
  function _buildUI() {
    const el = document.getElementById('view-indicators');
    if (!el) return;
    el.innerHTML = `
<div class="ind-terminal">

  <!-- Header -->
  <div class="ind-header">
    <div class="ind-brand">
      <span class="ind-logo">📊</span>
      <div>
        <div class="ind-title">Indicator Terminal</div>
        <div class="ind-sub">Visual Technical Analysis Lab</div>
      </div>
    </div>

    <!-- Ticker + controls -->
    <div class="ind-controls">
      <input id="ind-ticker-input" class="ind-input" type="text" value="AAPL" maxlength="6" placeholder="Ticker…" />
      <button class="ind-btn" onclick="IndicatorTerminal.loadTicker()">Load ▶</button>
      <button class="ind-btn secondary" onclick="IndicatorTerminal.clearAll()">Clear All ✕</button>
      <span id="ind-data-badge" style="font-size:10px;font-family:monospace;padding:3px 8px;border:1px solid #2ecc71;border-radius:10px;color:#2ecc71;margin-left:4px">LIVE</span>
    </div>

    <!-- Signal badges row -->
    <div id="ind-signals" class="ind-signals"></div>
  </div>

  <!-- Body: sidebar + chart -->
  <div class="ind-body">

    <!-- Sidebar: indicator picker -->
    <div class="ind-sidebar">
      <div class="ind-sidebar-title">Indicators</div>

      ${['Trend','Momentum','Volatility','Volume'].map(cat => `
        <div class="ind-category">${cat}</div>
        ${Object.entries(INDICATORS)
          .filter(([,d]) => d.category === cat)
          .map(([id, def]) => `
          <div class="ind-item" id="ind-item-${id}">
            <div class="ind-item-left">
              <div class="ind-toggle" id="ind-toggle-${id}" onclick="IndicatorTerminal.toggle('${id}')">
                <span class="ind-toggle-knob"></span>
              </div>
              <div>
                <div class="ind-item-label">${def.label}</div>
                <div class="ind-item-desc">${def.fullName}</div>
              </div>
            </div>
            <button class="ind-config-btn" onclick="IndicatorTerminal.openConfig('${id}')">⚙</button>
          </div>
        `).join('')}
      `).join('')}

      <div style="height:8px;"></div>
      <button class="ind-sim-btn" onclick="IndicatorTerminal.enableAll()">◈ Enable All</button>
      <button class="ind-sim-btn" style="margin-top:0;background:linear-gradient(135deg,#1e3a5f,#0d2040);" onclick="IndicatorTerminal.runSimulation()">⚡ Run Simulation</button>
    </div>

    <!-- Chart area -->
    <div class="ind-chart-wrap">
      <div id="ind-chart" class="ind-chart"></div>

      <!-- Config panel (overlaid) -->
      <div id="ind-config-panel" class="ind-config-panel" style="display:none;">
        <div id="ind-config-content"></div>
        <button class="ind-btn" onclick="IndicatorTerminal.applyConfig()">Apply</button>
        <button class="ind-btn secondary" onclick="IndicatorTerminal.closeConfig()">Cancel</button>
      </div>
    </div>

    <!-- Signal Diagnostics Panel (right side) -->
    <div id="ind-signal-panel" style="
      width:180px;flex-shrink:0;background:#0c0c18;border-left:1px solid #1a1a30;
      padding:12px 10px;font-family:monospace;color:#bdc3c7;overflow-y:auto;
    ">
      <div style="font-size:10px;color:#7f8c8d;text-transform:uppercase;letter-spacing:1px">
        Loading signal…
      </div>
    </div>

  </div>

  <!-- Simulation output -->
  <div id="ind-sim-output" class="ind-sim-output" style="display:none;"></div>

  <!-- Trend Scorecard -->
  <div id="ind-scorecard" class="ind-scorecard"></div>

</div>

<style>
/* ── Indicator Terminal Styles ───────────────────────────── */
.ind-terminal { display:flex; flex-direction:column; height:100%; background:#0a0a0f; overflow:hidden; }
.ind-header { padding:12px 16px; background:#0e0e1a; border-bottom:1px solid #1a1a30; display:flex; flex-direction:column; gap:8px; }
.ind-brand { display:flex; align-items:center; gap:10px; }
.ind-logo { font-size:22px; }
.ind-title { font-size:15px; font-weight:700; color:#fff; font-family:monospace; }
.ind-sub { font-size:11px; color:#556; font-family:monospace; }
.ind-controls { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.ind-input { background:#141420; border:1px solid #2a2a44; color:#e8eaf6; padding:6px 10px; font-size:13px; font-family:monospace; border-radius:6px; width:90px; text-transform:uppercase; }
.ind-btn { background:#1e3a5f; border:1px solid #2a5a8f; color:#7ec8ff; padding:6px 12px; font-size:12px; font-family:monospace; border-radius:6px; cursor:pointer; }
.ind-btn:hover { background:#1e4a7f; }
.ind-btn.secondary { background:#1a1a2a; border-color:#334; color:#889; }
.ind-signals { display:flex; gap:8px; flex-wrap:wrap; min-height:22px; }
.ind-signal-badge { padding:3px 10px; border-radius:12px; font-size:11px; font-family:monospace; font-weight:600; }
.ind-body { display:flex; flex:1; overflow:hidden; }
.ind-sidebar { width:220px; flex-shrink:0; overflow-y:auto; background:#0c0c18; border-right:1px solid #1a1a30; padding:8px 0; }
.ind-sidebar-title { color:#445; font-size:10px; font-family:monospace; padding:4px 12px; letter-spacing:1px; text-transform:uppercase; }
.ind-category { color:#4488ff; font-size:10px; font-family:monospace; padding:8px 12px 2px; letter-spacing:1px; text-transform:uppercase; border-top:1px solid #1a1a30; margin-top:4px; }
.ind-category:first-child { border-top:none; }
.ind-item { display:flex; align-items:center; justify-content:space-between; padding:6px 10px; }
.ind-item:hover { background:#121224; }
.ind-item-left { display:flex; align-items:center; gap:8px; }
.ind-toggle { width:32px; height:17px; background:#1a1a2e; border:1px solid #334; border-radius:9px; cursor:pointer; position:relative; transition:background .2s; flex-shrink:0; }
.ind-toggle.on { background:#1e5a3f; border-color:#00e5a0; }
.ind-toggle-knob { position:absolute; top:2px; left:2px; width:11px; height:11px; border-radius:50%; background:#445; transition:left .2s, background .2s; }
.ind-toggle.on .ind-toggle-knob { left:17px; background:#00e5a0; }
.ind-item-label { font-size:12px; color:#c8d0e0; font-family:monospace; font-weight:600; }
.ind-item-desc { font-size:10px; color:#445; font-family:monospace; }
.ind-config-btn { background:none; border:none; color:#445; font-size:14px; cursor:pointer; padding:2px 4px; }
.ind-config-btn:hover { color:#7ec8ff; }
.ind-sim-btn { margin:12px; width:calc(100% - 24px); background:linear-gradient(135deg,#1e3a5f,#0d2040); border:1px solid #2a5a8f; color:#7ec8ff; padding:10px 0; font-size:13px; font-family:monospace; border-radius:8px; cursor:pointer; }
.ind-sim-btn:hover { background:linear-gradient(135deg,#1e4a7f,#0d2a50); }
.ind-chart-wrap { flex:1; position:relative; }
.ind-chart { width:100%; height:100%; }
.ind-config-panel { position:absolute; top:10px; right:10px; background:#0e0e1e; border:1px solid #334; border-radius:10px; padding:16px; min-width:200px; z-index:100; }
.ind-config-panel label { color:#aab; font-size:12px; font-family:monospace; display:block; margin-top:8px; }
.ind-config-panel input[type=number] { background:#141420; border:1px solid #334; color:#e8eaf6; padding:4px 8px; font-size:12px; font-family:monospace; border-radius:5px; width:80px; margin-top:3px; }
.ind-sim-output { padding:12px 16px; background:#0c0c18; border-top:1px solid #1a1a30; font-family:monospace; font-size:12px; color:#aab; max-height:120px; overflow-y:auto; }

/* ── Trend Scorecard ─────────────────────────────────────── */
.ind-scorecard { background:#09090f; border-top:1px solid #1a1a30; padding:12px 16px; display:flex; flex-wrap:wrap; gap:10px; align-items:flex-start; min-height:48px; }
.ind-sc-section { flex:1; min-width:160px; }
.ind-sc-title { font-size:9px; color:#445; font-family:monospace; letter-spacing:.1em; text-transform:uppercase; margin-bottom:6px; }
.ind-sc-pills { display:flex; flex-wrap:wrap; gap:4px; }
.ind-sc-pill { padding:2px 8px; border-radius:10px; font-size:10px; font-family:monospace; font-weight:600; border:1px solid transparent; }
.ind-sc-pill.bull  { color:#00ff88; background:rgba(0,255,136,0.08); border-color:rgba(0,255,136,0.2); }
.ind-sc-pill.bear  { color:#ff4757; background:rgba(255,71,87,0.08);  border-color:rgba(255,71,87,0.2);  }
.ind-sc-pill.neut  { color:#778;    background:rgba(100,100,120,0.1); border-color:rgba(100,100,120,0.2); }
.ind-sc-pill.overbought { color:#ff9500; background:rgba(255,149,0,0.08); border-color:rgba(255,149,0,0.2); }
.ind-sc-pill.oversold   { color:#00d4ff; background:rgba(0,212,255,0.08);  border-color:rgba(0,212,255,0.2);  }
.ind-sc-composite { display:flex; flex-direction:column; align-items:center; justify-content:center; min-width:120px; padding:8px 16px; border:1px solid #1a1a30; border-radius:8px; background:#0d0d1a; }
.ind-sc-score { font-size:26px; font-weight:800; font-family:monospace; }
.ind-sc-label { font-size:10px; font-family:monospace; margin-top:2px; }
.ind-sc-bar { width:100%; height:5px; border-radius:3px; background:#1a1a30; margin-top:6px; overflow:hidden; }
.ind-sc-bar-fill { height:100%; border-radius:3px; transition:width .5s ease; }
</style>
    `;
  }

  /* ═══════════════════════════════════════════════════════════
     CHART INIT
  ═══════════════════════════════════════════════════════════ */
  function _initChart() {
    const container = document.getElementById('ind-chart');
    if (!container || !window.LightweightCharts) return;

    _chart = LightweightCharts.createChart(container, {
      layout:     { background: { color: '#0a0a0f' }, textColor: '#778' },
      grid:       { vertLines: { color: '#12122a' }, horzLines: { color: '#12122a' } },
      crosshair:  { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#1a1a3a' },
      timeScale:  { borderColor: '#1a1a3a', timeVisible: true },
      width:  container.offsetWidth,
      height: container.offsetHeight,
    });

    _candleSeries = _chart.addCandlestickSeries({
      upColor:   '#00e5a0', downColor: '#ff4d4d',
      borderUpColor: '#00e5a0', borderDownColor: '#ff4d4d',
      wickUpColor:   '#00e5a0', wickDownColor:   '#ff4d4d',
    });

    // Resize observer
    new ResizeObserver(() => {
      if (_chart && container) {
        _chart.applyOptions({ width: container.offsetWidth, height: container.offsetHeight });
      }
    }).observe(container);
  }

  /* ═══════════════════════════════════════════════════════════
     DATA & RENDERING
  ═══════════════════════════════════════════════════════════ */
  async function _loadData(ticker) {
    _ticker = ticker.toUpperCase();
    const base = (window.CONFIG && CONFIG.serverUrl) ? CONFIG.serverUrl : '';

    // ── 1. Fetch real OHLC from market_data API (fallback to synthetic) ──
    try {
      const r = await fetch(`${base}/api/market_data/${_ticker}`);
      if (r.ok) {
        const d = await r.json();
        if (d.ohlc && d.ohlc.length > 20) {
          // Convert YYYY-MM-DD strings to Unix timestamps for lightweight-charts
          _data = d.ohlc.map(bar => ({
            time:   bar.time,   // lightweight-charts accepts 'YYYY-MM-DD' strings
            open:   bar.open,
            high:   bar.high,
            low:    bar.low,
            close:  bar.close,
            volume: bar.volume,
          }));
          _updateDataBadge('LIVE', '#2ecc71');
        } else {
          throw new Error('empty ohlc');
        }
      } else {
        throw new Error(`HTTP ${r.status}`);
      }
    } catch (e) {
      console.warn('[IndicatorTerminal] market_data fallback to synthetic:', e.message);
      _data = _generateData(_ticker);
      _updateDataBadge('SYNTHETIC', '#f39c12');
    }

    if (!_candleSeries) return;
    _candleSeries.setData(_data);
    _chart && _chart.timeScale().fitContent();
    _refreshActiveIndicators();

    // ── 2. Fetch signal diagnostics from strategy/analyze ──────────────
    try {
      const sr = await fetch(`${base}/api/strategy/analyze/${_ticker}`);
      if (sr.ok) {
        const sd = await sr.json();
        _renderSignalDiagnostics(sd);
      }
    } catch (e) {
      console.warn('[IndicatorTerminal] strategy/analyze unavailable:', e.message);
    }
  }

  function _updateDataBadge(label, color) {
    const badge = document.getElementById('ind-data-badge');
    if (badge) {
      badge.textContent = label;
      badge.style.color = color;
      badge.style.borderColor = color;
    }
  }

  function _renderSignalDiagnostics(sd) {
    const panel = document.getElementById('ind-signal-panel');
    if (!panel || !sd) return;
    const diag = sd.diagnostics || {};
    const sig  = sd.signal || sd.consensus?.action || 'HOLD';
    const conf = sd.confidence ?? sd.consensus?.confidence ?? 0.5;
    const sigColor = sig === 'BUY' ? '#2ecc71' : sig === 'SELL' ? '#e74c3c' : '#95a5a6';

    const rsiZoneColor = diag.rsi_zone === 'oversold' ? '#2ecc71'
                       : diag.rsi_zone === 'overbought' ? '#e74c3c' : '#95a5a6';
    const macdColor    = diag.macd_bias === 'bullish' ? '#2ecc71'
                       : diag.macd_bias === 'bearish' ? '#e74c3c' : '#95a5a6';
    const smaColor     = diag.sma_bias  === 'bullish' ? '#2ecc71'
                       : diag.sma_bias  === 'bearish' ? '#e74c3c' : '#95a5a6';

    panel.innerHTML = `
      <div style="font-size:10px;color:#7f8c8d;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">
        Server Signal · ${sd.ticker || _ticker}
      </div>
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:18px;font-weight:700;color:${sigColor}">${sig}</span>
        <span style="font-size:11px;color:#bdc3c7">${(conf * 100).toFixed(0)}% conf</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;font-size:11px">
        <div><span style="color:#7f8c8d">RSI-14</span>
          <span style="float:right;color:${rsiZoneColor}">${diag.rsi_14 ?? '—'}</span></div>
        <div><span style="color:#7f8c8d">Zone</span>
          <span style="float:right;color:${rsiZoneColor}">${diag.rsi_zone ?? '—'}</span></div>
        <div><span style="color:#7f8c8d">MACD</span>
          <span style="float:right;color:${macdColor}">${diag.macd ?? '—'}</span></div>
        <div><span style="color:#7f8c8d">Hist</span>
          <span style="float:right;color:${macdColor}">${diag.macd_hist ?? '—'}</span></div>
        <div><span style="color:#7f8c8d">SMA Spr%</span>
          <span style="float:right;color:${smaColor}">${diag.sma_spread_pct ?? '—'}</span></div>
        <div><span style="color:#7f8c8d">ATR%</span>
          <span style="float:right;color:#bdc3c7">${diag.atr_pct ?? '—'}</span></div>
      </div>
      <div style="margin-top:6px;font-size:10px;color:#7f8c8d;display:flex;gap:6px">
        <span style="color:${macdColor}">MACD ${diag.macd_bias ?? ''}</span> ·
        <span style="color:${smaColor}">SMA ${diag.sma_bias ?? ''}</span>
      </div>
    `;
  }

  function _refreshActiveIndicators() {
    Object.keys(_active).forEach(id => {
      if (_active[id].enabled) _renderIndicator(id);
    });
    _updateSignals();
  }

  function _renderIndicator(id) {
    const state = _active[id];
    if (!state || !_chart) return;
    const def = INDICATORS[id];

    // Remove existing series
    _removeSeries(id);

    try {
      const computed = def.compute(_data, state.params);

      if (computed && computed.multi) {
        // Multi-series indicator
        state.series = {};
        const seriesColours = [state.colour, _adjustAlpha(state.colour, 0.6), '#ff6b6b'];
        Object.entries(computed).forEach(([key, vals], i) => {
          if (!Array.isArray(vals)) return;
          const series = _chart.addLineSeries({
            color: seriesColours[i] || nextColour(),
            lineWidth: key === 'hist' ? 2 : 1.5,
            priceScaleId: def.overlay ? 'right' : `osc_${id}`,
          });
          series.setData(vals);
          state.series[key] = series;
        });
      } else {
        // Single series
        const series = _chart.addLineSeries({
          color: state.colour,
          lineWidth: 1.5,
          priceScaleId: def.overlay ? 'right' : `osc_${id}`,
        });
        series.setData(computed);
        state.series = { main: series };
      }
    } catch (e) {
      console.warn(`IndicatorTerminal: ${id} render error`, e);
    }
  }

  function _removeSeries(id) {
    const state = _active[id];
    if (!state || !state.series || !_chart) return;
    Object.values(state.series).forEach(s => {
      try { _chart.removeSeries(s); } catch (e) {}
    });
    state.series = null;
  }

  function _adjustAlpha(hex, alpha) {
    const [, r, g, b] = hex.match(/#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})/i) || [];
    if (!r) return hex;
    return `rgba(${parseInt(r,16)},${parseInt(g,16)},${parseInt(b,16)},${alpha})`;
  }

  /* ═══════════════════════════════════════════════════════════
     SIGNALS
  ═══════════════════════════════════════════════════════════ */
  function _updateSignals() {
    const container = document.getElementById('ind-signals');
    if (!container) return;
    const badges = [];

    Object.entries(_active).forEach(([id, state]) => {
      if (!state.enabled) return;
      const def = INDICATORS[id];
      const computed = def.compute(_data, state.params);
      let sig = 'NEUTRAL';

      try {
        if (computed && computed.multi) {
          sig = def.signal(computed);
        } else if (Array.isArray(computed) && computed.length >= 2) {
          sig = def.signal(computed[computed.length - 1], computed[computed.length - 2], _data);
        } else if (Array.isArray(computed) && computed.length >= 1) {
          sig = def.signal(computed[computed.length - 1], null, _data);
        }
      } catch (e) {}

      const colour = _signalColour(sig);
      badges.push(`<span class="ind-signal-badge" style="background:${colour}22;color:${colour};border:1px solid ${colour}44;">${def.label}: ${sig}</span>`);
    });

    container.innerHTML = badges.join('') || '<span style="color:#334;font-size:11px;font-family:monospace;">Toggle indicators to see signals</span>';
    _renderScorecard();
  }

  function _signalColour(sig) {
    if (/STRONG BULL|STRONG UP|BUY ▲|ACCUMULATION|BUYING/.test(sig)) return '#00ff88';
    if (/BULL|BUY|ABOVE VWAP|ABOVE UPPER|TURNING UP/.test(sig))       return '#00e5a0';
    if (/STRONG BEAR|STRONG DOWN|SELL ▼|DISTRIBUTION|SELLING/.test(sig)) return '#ff4757';
    if (/BEAR|SELL|BELOW|TURNING DOWN/.test(sig))                      return '#ff6b6b';
    if (/OVERBOUGHT/.test(sig)) return '#ff9500';
    if (/OVERSOLD/.test(sig))   return '#00d4ff';
    if (/SQUEEZE|RANGING/.test(sig)) return '#f1fa8c';
    if (/TRENDING|STRONG TREND/.test(sig)) return '#cc99ff';
    return '#4488ff';
  }

  /* ── TREND SCORECARD ─────────────────────────────────────────────
     Computes signal scores from ALL active indicators and renders
     a consolidated heatmap + composite score below the chart.
  ──────────────────────────────────────────────────────────────── */
  function _renderScorecard() {
    const el = document.getElementById('ind-scorecard');
    if (!el) return;

    const cats = { Trend: [], Momentum: [], Volume: [], Volatility: [] };
    const allSigs = [];

    Object.entries(_active).forEach(([id, state]) => {
      if (!state.enabled) return;
      const def = INDICATORS[id];
      if (!def) return;
      const cat = def.category;
      let sig = 'NEUTRAL';
      try {
        const computed = def.compute(_data, state.params);
        if (computed && computed.multi) {
          sig = def.signal(computed, null, _data) || 'NEUTRAL';
        } else if (Array.isArray(computed) && computed.length >= 2) {
          sig = def.signal(computed[computed.length - 1], computed[computed.length - 2], _data) || 'NEUTRAL';
        } else if (Array.isArray(computed) && computed.length >= 1) {
          sig = def.signal(computed[computed.length - 1], null, _data) || 'NEUTRAL';
        }
      } catch (e) { sig = 'NEUTRAL'; }

      const score = _sigScore(sig);
      if (cats[cat]) cats[cat].push({ id, label: def.label, sig, score });
      allSigs.push(score);
    });

    // Composite score (-1 to +1)
    const composite = allSigs.length ? allSigs.reduce((a, b) => a + b, 0) / allSigs.length : 0;
    const compPct    = Math.round((composite + 1) / 2 * 100);
    const compCol    = composite > 0.3 ? '#00ff88' : composite < -0.3 ? '#ff4757' : '#f1fa8c';
    const compLabel  = composite > 0.5 ? 'STRONG BULL' : composite > 0.2 ? 'BULLISH'
                     : composite < -0.5 ? 'STRONG BEAR' : composite < -0.2 ? 'BEARISH' : 'NEUTRAL';

    // Pill CSS class from signal
    const pillClass = sig => {
      if (/STRONG BULL|STRONG UP|BUY|ACCUMULATION|BUYING/.test(sig)) return 'bull';
      if (/BULL|ABOVE/.test(sig)) return 'bull';
      if (/STRONG BEAR|STRONG DOWN|SELL|DISTRIBUTION|SELLING/.test(sig)) return 'bear';
      if (/BEAR|BELOW/.test(sig)) return 'bear';
      if (/OVERBOUGHT/.test(sig)) return 'overbought';
      if (/OVERSOLD/.test(sig))   return 'oversold';
      return 'neut';
    };

    const catHtml = Object.entries(cats).map(([name, items]) => {
      if (!items.length) return '';
      const avgScore = items.reduce((s, x) => s + x.score, 0) / items.length;
      const catCol   = avgScore > 0.2 ? '#00ff88' : avgScore < -0.2 ? '#ff4757' : '#778';
      return `
<div class="ind-sc-section">
  <div class="ind-sc-title" style="color:${catCol}">${name} <span style="color:#445">(${items.length})</span></div>
  <div class="ind-sc-pills">
    ${items.map(x => `<span class="ind-sc-pill ${pillClass(x.sig)}">${x.label} ${x.sig}</span>`).join('')}
  </div>
</div>`;
    }).join('');

    const noActive = allSigs.length === 0;

    el.innerHTML = noActive
      ? `<span style="color:#334;font-size:11px;font-family:monospace;padding:6px 0;">Enable indicators to see the scorecard</span>`
      : `
${catHtml}
<div class="ind-sc-composite">
  <div class="ind-sc-score" style="color:${compCol}">${composite >= 0 ? '+' : ''}${composite.toFixed(2)}</div>
  <div class="ind-sc-label" style="color:${compCol}">${compLabel}</div>
  <div class="ind-sc-bar">
    <div class="ind-sc-bar-fill" style="width:${compPct}%;background:${compCol}"></div>
  </div>
  <div style="font-size:8px;color:#445;margin-top:4px;font-family:monospace">${allSigs.length} signal${allSigs.length !== 1 ? 's' : ''}</div>
</div>`;
  }

  function _sigScore(sig) {
    if (/STRONG BULL|STRONG UP|BUY ▲|ACCUMULATION|BUYING PRESSURE/.test(sig)) return  1.0;
    if (/BULL|BUY|ABOVE VWAP|ABOVE UPPER|TURNING UP|TRENDING|STRONG TREND/.test(sig)) return  0.6;
    if (/OVERBOUGHT/.test(sig))  return  0.3;
    if (/OVERSOLD/.test(sig))    return -0.3;
    if (/STRONG BEAR|STRONG DOWN|SELL ▼|DISTRIBUTION|SELLING PRESSURE/.test(sig)) return -1.0;
    if (/BEAR|SELL|BELOW LOWER|TURNING DOWN/.test(sig)) return -0.6;
    if (/BELOW VWAP/.test(sig))  return -0.4;
    if (/RANGING|SQUEEZE|NEUTRAL/.test(sig)) return 0;
    return 0;
  }

  /* ═══════════════════════════════════════════════════════════
     CONFIG PANEL
  ═══════════════════════════════════════════════════════════ */
  let _configId = null;

  function _openConfig(id) {
    _configId = id;
    const def   = INDICATORS[id];
    const state = _active[id] || {};
    const params = state.params || {};
    const panel  = document.getElementById('ind-config-panel');
    const content = document.getElementById('ind-config-content');
    if (!panel || !content) return;

    content.innerHTML = `<div style="color:#e8eaf6;font-size:13px;font-weight:700;font-family:monospace;margin-bottom:12px;">${def.fullName}</div>` +
      (def.params || []).map(p => `
        <label>${p.label}
          <br><input type="number" id="cfg-${p.key}" value="${params[p.key] ?? p.default}" min="${p.min}" max="${p.max}" step="1" />
        </label>
      `).join('');

    panel.style.display = 'block';
  }

  function _applyConfig() {
    if (!_configId) return;
    const def  = INDICATORS[_configId];
    const newParams = {};
    (def.params || []).forEach(p => {
      const el = document.getElementById(`cfg-${p.key}`);
      newParams[p.key] = el ? +el.value : p.default;
    });
    if (!_active[_configId]) {
      _active[_configId] = { def, params: newParams, series: null, enabled: false, colour: nextColour() };
    } else {
      _active[_configId].params = newParams;
    }
    _closeConfig();
    if (_active[_configId].enabled) _renderIndicator(_configId);
    _updateSignals();
  }

  function _closeConfig() {
    const panel = document.getElementById('ind-config-panel');
    if (panel) panel.style.display = 'none';
    _configId = null;
  }

  /* ═══════════════════════════════════════════════════════════
     SIMULATION
  ═══════════════════════════════════════════════════════════ */
  function _runSimulation() {
    const activeIds = Object.keys(_active).filter(id => _active[id].enabled);
    if (activeIds.length === 0) {
      _showSim('⚠ Enable at least one indicator to run a simulation.');
      return;
    }

    const signals = activeIds.map(id => {
      const def = INDICATORS[id];
      const computed = def.compute(_data, _active[id].params);
      let sig = 'NEUTRAL';
      try {
        if (computed && computed.multi) sig = def.signal(computed);
        else if (Array.isArray(computed) && computed.length >= 2)
          sig = def.signal(computed[computed.length - 1], computed[computed.length - 2]);
        else if (Array.isArray(computed) && computed.length >= 1)
          sig = def.signal(computed[computed.length - 1]);
      } catch (e) {}
      return { id, label: def.label, signal: sig };
    });

    const bullish  = signals.filter(s => /BULL|BUY|ABOVE/.test(s.signal)).length;
    const bearish  = signals.filter(s => /BEAR|SELL|BELOW/.test(s.signal)).length;
    const total    = signals.length;
    const score    = (bullish - bearish) / total;
    const verdict  = score >= 0.4 ? '🟢 LONG' : score <= -0.4 ? '🔴 SHORT' : '🟡 NEUTRAL';

    const lines = [
      `📊 SIMULATION — ${_ticker}  |  ${new Date().toLocaleTimeString()}`,
      `Active Indicators: ${activeIds.join(', ')}`,
      `─`.repeat(60),
      ...signals.map(s => `  ${s.label.padEnd(8)} → ${s.signal}`),
      `─`.repeat(60),
      `Bullish signals: ${bullish}/${total}  |  Bearish: ${bearish}/${total}`,
      `Composite Score: ${(score * 100).toFixed(1)}  |  Verdict: ${verdict}`,
    ];

    _showSim(lines.join('\n'));
  }

  function _showSim(text) {
    const el = document.getElementById('ind-sim-output');
    if (!el) return;
    el.style.display = 'block';
    el.textContent = text;
  }

  /* ═══════════════════════════════════════════════════════════
     PUBLIC API
  ═══════════════════════════════════════════════════════════ */
  function init() {
    if (_initialized) return;
    _buildUI();
    _initChart();
    _loadData('AAPL');
    _initialized = true;
    // Allow Enter key in ticker input to load data
    const inp = document.getElementById('ind-ticker-input');
    if (inp) inp.addEventListener('keydown', e => { if (e.key === 'Enter') loadTicker(); });
    console.log('[IndicatorTerminal] init OK');
  }

  function toggle(id) {
    const def = INDICATORS[id];
    if (!def) return;

    if (!_active[id]) {
      // First enable: create with defaults
      const params = {};
      (def.params || []).forEach(p => { params[p.key] = p.default; });
      _active[id] = { def, params, series: null, enabled: true, colour: nextColour() };
    } else {
      _active[id].enabled = !_active[id].enabled;
    }

    // Update toggle UI
    const toggleEl = document.getElementById(`ind-toggle-${id}`);
    if (toggleEl) {
      toggleEl.classList.toggle('on', _active[id].enabled);
    }

    if (_active[id].enabled) {
      _renderIndicator(id);
    } else {
      _removeSeries(id);
    }
    _updateSignals();
  }

  function loadTicker() {
    const input = document.getElementById('ind-ticker-input');
    const t = (input ? input.value : '').trim().toUpperCase() || 'AAPL';
    _loadData(t);
  }

  function clearAll() {
    Object.keys(_active).forEach(id => {
      _active[id].enabled = false;
      _removeSeries(id);
      const toggleEl = document.getElementById(`ind-toggle-${id}`);
      if (toggleEl) toggleEl.classList.remove('on');
    });
    _updateSignals();
  }

  function enableAll() {
    Object.keys(INDICATORS).forEach(id => {
      if (!_active[id]) {
        const def = INDICATORS[id];
        const params = {};
        (def.params || []).forEach(p => { params[p.key] = p.default; });
        _active[id] = { def, params, series: null, enabled: false, colour: nextColour() };
      }
      _active[id].enabled = true;
      const toggleEl = document.getElementById(`ind-toggle-${id}`);
      if (toggleEl) toggleEl.classList.add('on');
      _renderIndicator(id);
    });
    _updateSignals();
  }

  function openConfig(id) { _openConfig(id); }
  function applyConfig()  { _applyConfig(); }
  function closeConfig()  { _closeConfig(); }
  function runSimulation(){ _runSimulation(); }

  return { init, toggle, loadTicker, clearAll, enableAll, openConfig, applyConfig, closeConfig, runSimulation };

})();
