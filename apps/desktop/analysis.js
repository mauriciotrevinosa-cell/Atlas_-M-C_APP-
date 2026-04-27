/**
 * analysis.js — Market Analysis View
 * =====================================
 * Candlestick chart + volume bars + MA(20)/MA(50) overlays.
 * Strategy signal badge from /api/strategy/analyze.
 * News feed from /api/market_data.
 */

'use strict';

// ── DOM refs ──────────────────────────────────────────────────────────────────
const analysisTickerInput  = document.getElementById('analysis-ticker');
const analysisLoadBtn      = document.getElementById('analysis-load-btn');
const analysisPriceDisplay = document.getElementById('analysis-price');
const analysisNewsList     = document.getElementById('analysis-news-list');
const analysisChartContainer = document.getElementById('analysis-chart-container');

// ── Chart state ───────────────────────────────────────────────────────────────
let _chart        = null;
let _candleSeries = null;
let _volSeries    = null;
let _ma20Series   = null;
let _ma50Series   = null;

// ── Helpers ───────────────────────────────────────────────────────────────────

function _sma(data, period) {
  return data.map((_, i) => {
    if (i < period - 1) return null;
    const slice = data.slice(i - period + 1, i + 1);
    const avg   = slice.reduce((s, d) => s + d.close, 0) / period;
    return { time: data[i].time, value: parseFloat(avg.toFixed(4)) };
  }).filter(Boolean);
}

function _signal_color(sig) {
  const s = (sig || '').toUpperCase();
  if (s === 'BUY'  || s === 'STRONG_BUY')  return '#00ff88';
  if (s === 'SELL' || s === 'STRONG_SELL') return '#ff4466';
  return '#8892b0';
}

function _signal_icon(sig) {
  const s = (sig || '').toUpperCase();
  if (s === 'BUY'  || s === 'STRONG_BUY')  return '▲';
  if (s === 'SELL' || s === 'STRONG_SELL') return '▼';
  return '●';
}

// ── Chart init ────────────────────────────────────────────────────────────────

function initAnalysisChart() {
  if (!analysisChartContainer || typeof LightweightCharts === 'undefined') return;

  _chart = LightweightCharts.createChart(analysisChartContainer, {
    width:  analysisChartContainer.clientWidth,
    height: analysisChartContainer.clientHeight,
    layout: {
      background:  { type: 'solid', color: '#0d0d1a' },
      textColor:   '#8892b0',
    },
    grid: {
      vertLines: { color: 'rgba(255,255,255,0.04)' },
      horzLines: { color: 'rgba(255,255,255,0.04)' },
    },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    rightPriceScale: { borderColor: 'rgba(255,255,255,0.1)' },
    timeScale: {
      borderColor: 'rgba(255,255,255,0.1)',
      timeVisible: true,
      secondsVisible: false,
    },
  });

  // Candle series
  _candleSeries = _chart.addCandlestickSeries({
    upColor:      '#00ff88',
    downColor:    '#ff4466',
    borderVisible: false,
    wickUpColor:   '#00ff88',
    wickDownColor: '#ff4466',
  });

  // Volume series (histogram, price scale right-2)
  _volSeries = _chart.addHistogramSeries({
    color:    '#334466',
    priceFormat: { type: 'volume' },
    priceScaleId: 'vol',
    scaleMargins: { top: 0.85, bottom: 0 },
  });
  _chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });

  // MA lines (overlaid on main price scale)
  _ma20Series = _chart.addLineSeries({
    color:      '#f39c12',
    lineWidth:  1,
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false,
    title: 'MA20',
  });

  _ma50Series = _chart.addLineSeries({
    color:      '#9b59b6',
    lineWidth:  1,
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false,
    title: 'MA50',
  });

  // Resize observer
  new ResizeObserver(entries => {
    if (!entries[0] || entries[0].target !== analysisChartContainer) return;
    const r = entries[0].contentRect;
    _chart.applyOptions({ width: r.width, height: r.height });
  }).observe(analysisChartContainer);
}

// ── Signal badge ──────────────────────────────────────────────────────────────

function _renderSignalBadge(ticker, signalData) {
  // Find or create badge container in the analysis view
  let badge = document.getElementById('analysis-signal-badge');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'analysis-signal-badge';
    badge.style.cssText = `
      display:inline-flex; align-items:center; gap:6px;
      padding:4px 10px; border-radius:6px; font-size:12px;
      font-weight:700; letter-spacing:0.5px;
      border:1px solid; margin-left:10px;
    `;
    const priceRow = analysisPriceDisplay && analysisPriceDisplay.parentElement;
    if (priceRow) priceRow.appendChild(badge);
  }

  const sig    = (signalData && (signalData.signal || signalData.action)) || 'HOLD';
  const score  = signalData && signalData.composite_score;
  const color  = _signal_color(sig);
  const icon   = _signal_icon(sig);
  badge.style.color       = color;
  badge.style.borderColor = color;
  badge.style.background  = color + '18';
  badge.textContent       = `${icon} ${sig}${score !== undefined ? '  ' + Number(score).toFixed(2) : ''}`;
}

// ── Main load function ────────────────────────────────────────────────────────

async function loadAnalysisData() {
  const ticker = (analysisTickerInput ? analysisTickerInput.value.trim().toUpperCase() : 'SPY') || 'SPY';
  if (analysisLoadBtn) analysisLoadBtn.textContent = 'Loading…';
  if (analysisPriceDisplay) analysisPriceDisplay.textContent = '…';

  if (!_chart) initAnalysisChart();

  // ── Parallel fetch: market data + strategy signal ──────────────────────────
  const [marketRes, stratRes] = await Promise.allSettled([
    fetch(`/api/market_data/${ticker}`).then(r => r.json()),
    fetch(`/api/strategy/analyze/${ticker}`).then(r => r.json()),
  ]);

  // ── Price display ──────────────────────────────────────────────────────────
  if (marketRes.status === 'fulfilled') {
    const data = marketRes.value;

    // Update price KPI
    const price = data.price ?? data.ohlc?.[data.ohlc.length - 1]?.close ?? null;
    if (analysisPriceDisplay && price !== null) {
      analysisPriceDisplay.textContent = `$${Number(price).toFixed(2)}`;
    }

    // ── Candles ────────────────────────────────────────────────────────────
    if (_candleSeries && Array.isArray(data.ohlc) && data.ohlc.length > 0) {
      const sorted = [...data.ohlc].sort((a, b) => a.time - b.time);

      _candleSeries.setData(sorted.map(d => ({
        time:  d.time,
        open:  d.open,
        high:  d.high,
        low:   d.low,
        close: d.close,
      })));

      // ── Volume bars ────────────────────────────────────────────────────
      if (_volSeries) {
        _volSeries.setData(sorted.map(d => ({
          time:  d.time,
          value: d.volume ?? 0,
          color: (d.close >= d.open) ? 'rgba(0,255,136,0.35)' : 'rgba(255,68,102,0.35)',
        })));
      }

      // ── MA overlays ────────────────────────────────────────────────────
      if (_ma20Series && sorted.length >= 20) {
        _ma20Series.setData(_sma(sorted, 20));
      }
      if (_ma50Series && sorted.length >= 50) {
        _ma50Series.setData(_sma(sorted, 50));
      }

      _chart.timeScale().fitContent();
    }

    // ── News feed ──────────────────────────────────────────────────────────
    if (analysisNewsList) {
      analysisNewsList.innerHTML = '';
      const news = data.news || [];
      if (news.length > 0) {
        news.slice(0, 8).forEach(n => {
          const el = document.createElement('div');
          el.className = 'log-entry';
          el.style.cssText = 'border-bottom:1px solid rgba(255,255,255,0.05);padding:6px 0;';
          const time = new Date((n.timestamp || 0) * 1000).toLocaleDateString();
          el.innerHTML = `
            <small style="color:#667;font-size:10px;">${time}${n.publisher ? ' · ' + n.publisher : ''}</small><br>
            <strong>
              <a href="${n.link || '#'}" target="_blank"
                 style="text-decoration:none;color:#c0caf5;font-size:12px;">
                ${n.title || '(no title)'}
              </a>
            </strong>`;
          analysisNewsList.appendChild(el);
        });
      } else {
        analysisNewsList.innerHTML = `<div class='log-entry' style='color:#667;font-size:12px;'>No recent news found.</div>`;
      }
    }
  } else {
    if (analysisPriceDisplay) analysisPriceDisplay.textContent = 'N/A';
    if (analysisNewsList) analysisNewsList.innerHTML =
      `<div style="color:#e74c3c;font-size:12px;padding:10px 0">⚠ Market data unavailable</div>`;
  }

  // ── Strategy signal badge ─────────────────────────────────────────────────
  if (stratRes.status === 'fulfilled') {
    _renderSignalBadge(ticker, stratRes.value);
  }

  if (analysisLoadBtn) analysisLoadBtn.textContent = 'Load Data';
}

// ── Event listeners ───────────────────────────────────────────────────────────

if (analysisLoadBtn) {
  analysisLoadBtn.addEventListener('click', loadAnalysisData);
}

if (analysisTickerInput) {
  analysisTickerInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') loadAnalysisData();
  });
}

// Auto-init when user navigates to the analysis view
document.addEventListener('click', e => {
  if (e.target.closest('[onclick*="analysis"]') || e.target.closest('[data-view="analysis"]')) {
    setTimeout(() => {
      if (analysisChartContainer && !_chart) {
        initAnalysisChart();
        loadAnalysisData();
      }
    }, 120);
  }
});
