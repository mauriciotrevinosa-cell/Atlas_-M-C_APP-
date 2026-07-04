/**
 * Atlas Info Module - Live Runtime Explorer
 *
 * This panel does not ship a local information catalog. It renders only
 * entries returned by the Atlas backend and optional internet enrichment.
 */

'use strict';

window.InfoModule = (() => {

  const CATEGORIES = [
    { id: 'all',         label: 'All',              icon: 'ALL' },
    { id: 'data',        label: 'Data Sources',     icon: 'DB' },
    { id: 'strategy',    label: 'Strategies',       icon: 'ST' },
    { id: 'feature',     label: 'Features',         icon: 'FX' },
    { id: 'correlation', label: 'Correlation',      icon: 'CR' },
    { id: 'viz',         label: 'Visualizations',   icon: 'VZ' },
    { id: 'ai',          label: 'AI / ML',          icon: 'AI' },
    { id: 'infra',       label: 'Infrastructure',   icon: 'API' },
    { id: 'quantum',     label: 'Quantum / MMO',    icon: 'Q' },
  ];

  /* ---------------------------------------------------------
     LIVE DATA ONLY
     The old static module list was removed. Info entries now
     come exclusively from /api/info/catalog and optional web search.
  --------------------------------------------------------- */
  /* ─────────────────────────────────────────────────────────
     STATE
  ───────────────────────────────────────────────────────── */
  let _query    = '';
  let _category = 'all';
  let _items = [];
  let _sourceMode = 'waiting for Atlas API';
  let _loading = false;
  let _loadTimer = null;
  let _loadError = '';

  /* ─────────────────────────────────────────────────────────
     HELPERS
  ───────────────────────────────────────────────────────── */
  const CAT_COLORS = {
    data:        { bg: '#0a2030', border: '#0088cc', badge: '#00aaff' },
    strategy:    { bg: '#0a1a10', border: '#006633', badge: '#00cc66' },
    feature:     { bg: '#0d0a2a', border: '#4422aa', badge: '#8855ff' },
    correlation: { bg: '#1a0a20', border: '#880088', badge: '#cc44cc' },
    viz:         { bg: '#1a100a', border: '#884400', badge: '#ff8800' },
    ai:          { bg: '#0a1a20', border: '#006688', badge: '#00aacc' },
    infra:       { bg: '#141414', border: '#444444', badge: '#888888' },
    quantum:     { bg: '#080a20', border: '#5522cc', badge: '#aa55ff' },
  };

  function _catColor(cat) {
    return CAT_COLORS[cat] || CAT_COLORS['infra'];
  }

  function _filteredItems() {
    return _items.filter(item => {
      const matchCat = _category === 'all' || item.category === _category;
      if (!matchCat) return false;
      if (!_query) return true;
      const q = _query.toLowerCase();
      return (
        String(item.name || '').toLowerCase().includes(q) ||
        String(item.desc || '').toLowerCase().includes(q) ||
        (item.tags || []).some(t => String(t).toLowerCase().includes(q)) ||
        String(item.how || '').toLowerCase().includes(q) ||
        String(item.source || '').toLowerCase().includes(q) ||
        String(item.category || '').toLowerCase().includes(q)
      );
    });
  }

  async function _loadCatalog({ includeWeb = false } = {}) {
    _loading = true;
    _render();
    const params = new URLSearchParams();
    params.set('limit', '160');
    if (_query) params.set('query', _query);
    if (includeWeb && _query.length >= 3) params.set('include_web', 'true');

    try {
      const response = await fetch(`/api/info/catalog?${params.toString()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const apiItems = Array.isArray(payload.items) ? payload.items : [];
      _items = apiItems;
      _loadError = '';
      if (apiItems.length > 0) {
        _sourceMode = includeWeb && _query.length >= 3 ? 'Atlas API + internet' : 'Atlas API';
      } else {
        _sourceMode = 'Atlas API returned no entries';
      }
    } catch (error) {
      _items = [];
      _loadError = error.message || String(error);
      _sourceMode = `Atlas API unavailable: ${_loadError}`;
    } finally {
      _loading = false;
      _render();
    }
  }

  function _scheduleCatalogLoad(includeWeb = false) {
    if (_loadTimer) window.clearTimeout(_loadTimer);
    _loadTimer = window.setTimeout(() => {
      _loadCatalog({ includeWeb });
    }, includeWeb ? 650 : 100);
  }

  /* ─────────────────────────────────────────────────────────
     RENDER
  ───────────────────────────────────────────────────────── */
  function _renderCategoryTabs(container) {
    const tabRow = container.querySelector('#info-cat-tabs');
    if (!tabRow) return;
    tabRow.innerHTML = CATEGORIES.map(c => {
      const count = c.id === 'all' ? _items.length : _items.filter(i => i.category === c.id).length;
      const isActive = _category === c.id;
      return `<button
        class="info-cat-tab${isActive ? ' active' : ''}"
        onclick="InfoModule.setCategory('${c.id}')"
        title="${c.label}"
      >${c.icon} ${c.label} <span class="info-cat-count">${count}</span></button>`;
    }).join('');
  }

  function _renderCards(container) {
    const grid = container.querySelector('#info-cards-grid');
    if (!grid) return;

    const items = _filteredItems();
    if (items.length === 0) {
      const title = _loading
        ? 'Loading live Atlas data...'
        : (_loadError ? 'Live Atlas data unavailable' : 'No live entries returned');
      const detail = _loading
        ? 'Waiting for /api/info/catalog.'
        : (_loadError
          ? _sourceMode
          : (_query ? `No live result for "${_escHtml(_query)}".` : 'The backend returned an empty live dataset.'));
      grid.innerHTML = `<div class="info-empty">
        <div style="font-size:2rem;margin-bottom:8px;">LIVE</div>
        <div>${title}</div>
        <div style="color:#555;margin-top:6px;font-size:11px;">${detail}</div>
      </div>`;
      return;
    }

    grid.innerHTML = items.map(item => {
      const col = _catColor(item.category);
      const catLabel = CATEGORIES.find(c => c.id === item.category)?.label || item.category;
      const tagsHtml = (item.tags || []).map(t =>
        `<span class="info-tag">${_escHtml(t)}</span>`
      ).join('');
      const apiHtml = item.api
        ? `<div class="info-api-row"><span class="info-api-label">API</span><code class="info-api-code">${_escHtml(item.api)}</code></div>`
        : '';

      return `<div class="info-card" style="border-color:${col.border};background:${col.bg};">
        <div class="info-card-header">
          <span class="info-card-icon">${item.icon}</span>
          <div class="info-card-title-group">
            <div class="info-card-name">${_escHtml(item.name)}</div>
            <span class="info-cat-badge" style="background:${col.badge}20;color:${col.badge};border-color:${col.badge}44;">${catLabel}</span>
          </div>
        </div>

        <p class="info-card-desc">${_escHtml(item.desc)}</p>

        <div class="info-detail-row">
          <div class="info-detail-label">📡 Data Source</div>
          <div class="info-detail-value">${_escHtml(item.source)}</div>
        </div>
        <div class="info-detail-row">
          <div class="info-detail-label">📐 How It Works</div>
          <div class="info-detail-value">${_escHtml(item.how)}</div>
        </div>

        ${apiHtml}

        <div class="info-tags-row">${tagsHtml}</div>
      </div>`;
    }).join('');
  }

  function _escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function _render() {
    const container = document.getElementById('view-info');
    if (!container) return;
    _renderCategoryTabs(container);
    _renderCards(container);
    // Update result count
    const countEl = container.querySelector('#info-result-count');
    if (countEl) {
      const n = _filteredItems().length;
      countEl.textContent = `${_loading ? 'loading...' : `${n} ${n === 1 ? 'entry' : 'entries'}`} / ${_sourceMode}`;
    }
  }

  /* ─────────────────────────────────────────────────────────
     PUBLIC API
  ───────────────────────────────────────────────────────── */
  function setCategory(cat) {
    _category = cat;
    _render();
  }

  function setQuery(q) {
    _query = q.trim();
    _render();
    _scheduleCatalogLoad(_query.length >= 3);
  }

  function init() {
    // Inject styles
    _injectStyles();
    // Initial render
    _render();
    _loadCatalog();
  }

  /* ─────────────────────────────────────────────────────────
     STYLES (injected into <head> at init time)
  ───────────────────────────────────────────────────────── */
  function _injectStyles() {
    if (document.getElementById('info-styles')) return;
    const style = document.createElement('style');
    style.id = 'info-styles';
    style.textContent = `
      /* ── Info View Container ── */
      #view-info {
        background: #080812;
        color: #ccc;
        font-family: 'Inter', monospace, sans-serif;
        min-height: 100vh;
        padding-bottom: 80px;
      }
      .info-header-bar {
        padding: 16px 16px 0;
        position: sticky;
        top: 0;
        z-index: 100;
        background: #080812;
        border-bottom: 1px solid #1a1a3a;
        padding-bottom: 10px;
      }
      .info-title-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 12px;
      }
      .info-title {
        font-size: 18px;
        font-weight: 700;
        color: #fff;
        font-family: 'Playfair Display', serif;
        letter-spacing: 0.3px;
      }
      .info-subtitle {
        font-size: 11px;
        color: #556;
        font-family: monospace;
      }
      #info-result-count {
        font-size: 11px;
        color: #445;
        font-family: monospace;
      }

      /* ── Search ── */
      .info-search-wrap {
        position: relative;
        margin-bottom: 10px;
      }
      .info-search-wrap svg {
        position: absolute;
        left: 10px;
        top: 50%;
        transform: translateY(-50%);
        color: #445;
        pointer-events: none;
      }
      #info-search {
        width: 100%;
        box-sizing: border-box;
        background: #0d0d20;
        border: 1px solid #1e1e40;
        color: #ccc;
        font-family: monospace;
        font-size: 12px;
        padding: 8px 10px 8px 34px;
        border-radius: 6px;
        outline: none;
        transition: border-color 0.2s;
      }
      #info-search:focus { border-color: #4488ff; }
      #info-search::placeholder { color: #445; }

      /* ── Category Tabs ── */
      #info-cat-tabs {
        display: flex;
        gap: 6px;
        overflow-x: auto;
        padding-bottom: 2px;
        scrollbar-width: none;
      }
      #info-cat-tabs::-webkit-scrollbar { display: none; }
      .info-cat-tab {
        background: #0d0d20;
        border: 1px solid #1e1e40;
        color: #667;
        font-size: 11px;
        font-family: monospace;
        padding: 5px 10px;
        border-radius: 16px;
        cursor: pointer;
        white-space: nowrap;
        transition: all 0.15s;
        flex-shrink: 0;
      }
      .info-cat-tab:hover { border-color: #4488ff55; color: #aaa; }
      .info-cat-tab.active {
        background: #1a2a50;
        border-color: #4488ff;
        color: #88aaff;
      }
      .info-cat-count {
        display: inline-block;
        background: #1a1a3a;
        border-radius: 8px;
        padding: 0 5px;
        font-size: 10px;
        color: #556;
        margin-left: 3px;
      }
      .info-cat-tab.active .info-cat-count {
        background: #2a3a70;
        color: #8899cc;
      }

      /* ── Cards Grid ── */
      #info-cards-grid {
        padding: 14px 12px;
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
      }
      @media (min-width: 600px) {
        #info-cards-grid { grid-template-columns: 1fr 1fr; }
      }

      /* ── Individual Card ── */
      .info-card {
        border: 1px solid #222240;
        border-radius: 10px;
        padding: 14px;
        background: #0a0a18;
        transition: transform 0.15s, box-shadow 0.15s;
      }
      .info-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 24px rgba(0,0,0,0.5);
      }
      .info-card-header {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 10px;
      }
      .info-card-icon {
        font-size: 20px;
        line-height: 1;
        flex-shrink: 0;
        margin-top: 2px;
        font-style: normal;
        font-family: monospace;
      }
      .info-card-title-group {
        flex: 1;
        min-width: 0;
      }
      .info-card-name {
        font-size: 13px;
        font-weight: 600;
        color: #dde;
        margin-bottom: 4px;
        line-height: 1.3;
      }
      .info-cat-badge {
        display: inline-block;
        font-size: 9px;
        font-family: monospace;
        padding: 2px 7px;
        border-radius: 10px;
        border: 1px solid #333;
        letter-spacing: 0.5px;
        text-transform: uppercase;
      }
      .info-card-desc {
        font-size: 11.5px;
        color: #99a;
        line-height: 1.55;
        margin: 0 0 10px;
      }

      /* ── Detail Rows ── */
      .info-detail-row {
        margin-bottom: 8px;
      }
      .info-detail-label {
        font-size: 9px;
        font-family: monospace;
        color: #556;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 3px;
      }
      .info-detail-value {
        font-size: 10.5px;
        color: #778;
        line-height: 1.5;
        font-family: monospace;
        background: rgba(255,255,255,0.03);
        border-left: 2px solid #1e1e40;
        padding: 4px 8px;
        border-radius: 0 4px 4px 0;
      }

      /* ── API badge ── */
      .info-api-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }
      .info-api-label {
        font-size: 9px;
        font-family: monospace;
        color: #445;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        flex-shrink: 0;
      }
      .info-api-code {
        font-size: 10px;
        font-family: monospace;
        color: #4488ff;
        background: #0a1530;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #1a2a50;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      /* ── Tags ── */
      .info-tags-row {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-top: 8px;
      }
      .info-tag {
        font-size: 9px;
        font-family: monospace;
        color: #556;
        background: #0d0d1e;
        border: 1px solid #1e1e35;
        padding: 2px 6px;
        border-radius: 8px;
        letter-spacing: 0.3px;
      }

      /* ── Empty state ── */
      .info-empty {
        grid-column: 1 / -1;
        text-align: center;
        color: #445;
        padding: 60px 20px;
        font-family: monospace;
        font-size: 13px;
      }

      /* ── Nav item for info ── */
      #nav-info.active { color: #aa88ff; }
    `;
    document.head.appendChild(style);
  }

  return { init, setCategory, setQuery };

})();
