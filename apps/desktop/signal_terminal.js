/**
 * Signal Terminal — Atlas v1.0
 * ============================
 * Real-time market signal feed with watchlist, whale events, and source management.
 *
 * Tabs: Feed | Watchlist | Whales | Sources | Stats
 * Backend: /api/signals/* (Atlas Signal Terminal Python module)
 */

'use strict';

window.SignalTerminal = (() => {

  const API   = '/api/signals';
  const POLL  = 60_000;   // auto-refresh interval ms

  let _initialized = false;
  let _pollId      = null;
  let _state = {
    tab:       'feed',
    signals:   [],
    watchlist: [],
    whales:    [],
    sources:   [],
    stats:     null,
    filters: { ticker: '', category: '', sentiment: '', limit: 50 },
    loading:   false,
    serverUp:  null,
  };

  // ── Category / sentiment colour maps ─────────────────────────────────────
  const CAT_COLOR = {
    earnings:  '#3498db',
    macro:     '#e74c3c',
    whale:     '#9b59b6',
    technical: '#f39c12',
    crypto:    '#2ecc71',
    sentiment: '#1abc9c',
    news:      '#7f8c8d',
    unknown:   '#445',
  };
  const SENT_COLOR = {
    bullish: 'var(--accent-green)',
    bearish: '#e74c3c',
    neutral: 'var(--txt-muted)',
  };
  const URGENCY_COLOR = {
    critical: '#e74c3c',
    high:     '#f39c12',
    medium:   'var(--accent-green)',
    low:      '#445',
  };

  // ── Public API ────────────────────────────────────────────────────────────

  function init() {
    const root = document.getElementById('view-signal-terminal');
    if (!root) return;
    if (!_initialized) {
      _build(root);
      _initialized = true;
    }
    _activateTab(_state.tab);
    _startPoll();
  }

  function cleanup() {
    if (_pollId) { clearInterval(_pollId); _pollId = null; }
  }

  // ── Build shell ───────────────────────────────────────────────────────────

  function _build(root) {
    root.innerHTML = `
      <div class="st-header-row">
        <div class="st-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
          </svg>
          Signal Terminal
        </div>
        <div class="st-header-right">
          <span id="st-server-badge" class="st-badge st-badge-off">●&nbsp;offline</span>
          <button class="st-ctrl-btn" onclick="SignalTerminal._collectNow()" title="Collect now">⟳ Collect</button>
          <button class="btn link-btn" type="button" onclick="switchView('dashboard')">Home</button>
        </div>
      </div>

      <!-- Stats strip -->
      <div id="st-stats-strip" class="st-stats-strip">
        <div class="st-stat"><span id="ss-total">—</span><span>Total</span></div>
        <div class="st-stat"><span id="ss-recent">—</span><span>24h</span></div>
        <div class="st-stat"><span id="ss-sources">—</span><span>Sources</span></div>
        <div class="st-stat"><span id="ss-watch">—</span><span>Watching</span></div>
        <div class="st-stat"><span id="ss-whales">—</span><span>Whales</span></div>
        <div class="st-stat"><span id="ss-alerts">—</span><span>Alert fires</span></div>
      </div>

      <!-- Tabs -->
      <div class="st-tabs">
        <button class="st-tab active" data-tab="feed"      onclick="SignalTerminal._tab('feed')">Feed</button>
        <button class="st-tab"        data-tab="watchlist" onclick="SignalTerminal._tab('watchlist')">Watchlist</button>
        <button class="st-tab"        data-tab="whales"    onclick="SignalTerminal._tab('whales')">Whales</button>
        <button class="st-tab"        data-tab="sources"   onclick="SignalTerminal._tab('sources')">Sources</button>
      </div>

      <!-- ── Feed tab ─────────────────────────────────────────────────── -->
      <div id="st-pane-feed" class="st-pane">
        <div class="st-filter-row">
          <input  class="st-input" id="st-f-ticker"   placeholder="Ticker (e.g. AAPL)" oninput="SignalTerminal._filterChange()"/>
          <select class="st-select" id="st-f-cat"     onchange="SignalTerminal._filterChange()">
            <option value="">All categories</option>
            <option value="earnings">Earnings</option>
            <option value="macro">Macro</option>
            <option value="whale">Whale</option>
            <option value="technical">Technical</option>
            <option value="crypto">Crypto</option>
            <option value="sentiment">Sentiment</option>
            <option value="news">News</option>
          </select>
          <select class="st-select" id="st-f-sent"    onchange="SignalTerminal._filterChange()">
            <option value="">All sentiment</option>
            <option value="bullish">Bullish</option>
            <option value="bearish">Bearish</option>
            <option value="neutral">Neutral</option>
          </select>
          <button class="st-ctrl-btn" onclick="SignalTerminal._loadFeed()">Refresh</button>
        </div>
        <div id="st-feed-list" class="st-feed-list">
          <div class="st-placeholder">Loading signals…</div>
        </div>
        <div class="st-load-more-row">
          <button class="st-ctrl-btn" id="st-load-more" onclick="SignalTerminal._loadMore()" style="display:none">Load more</button>
        </div>
      </div>

      <!-- ── Watchlist tab ─────────────────────────────────────────────── -->
      <div id="st-pane-watchlist" class="st-pane" style="display:none">
        <div class="st-add-row">
          <input  class="st-input" id="st-w-ticker"    placeholder="Ticker (AAPL)" style="width:100px"/>
          <input  class="st-input" id="st-w-name"      placeholder="Company name (optional)" style="flex:1"/>
          <select class="st-select" id="st-w-type"     >
            <option value="stock">Stock</option>
            <option value="crypto">Crypto</option>
            <option value="etf">ETF</option>
          </select>
          <select class="st-select" id="st-w-priority" >
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="low">Low</option>
          </select>
          <button class="st-ctrl-btn st-ctrl-btn-green" onclick="SignalTerminal._addWatch()">+ Add</button>
        </div>
        <div id="st-watch-list" class="st-watch-list">
          <div class="st-placeholder">Loading…</div>
        </div>
      </div>

      <!-- ── Whales tab ────────────────────────────────────────────────── -->
      <div id="st-pane-whales" class="st-pane" style="display:none">
        <div class="st-filter-row">
          <input  class="st-input" id="st-wh-ticker" placeholder="Filter by ticker" oninput="SignalTerminal._loadWhales()"/>
          <button class="st-ctrl-btn" onclick="SignalTerminal._loadWhales()">Refresh</button>
        </div>
        <div id="st-whale-list" class="st-feed-list">
          <div class="st-placeholder">Loading whale events…</div>
        </div>
      </div>

      <!-- ── Sources tab ───────────────────────────────────────────────── -->
      <div id="st-pane-sources" class="st-pane" style="display:none">
        <div id="st-source-list" class="st-source-list">
          <div class="st-placeholder">Loading sources…</div>
        </div>
      </div>
    `;
  }

  // ── Tab switching ─────────────────────────────────────────────────────────

  function _tab(name) {
    _state.tab = name;
    document.querySelectorAll('.st-tab').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === name);
    });
    _activateTab(name);
  }

  function _activateTab(name) {
    ['feed', 'watchlist', 'whales', 'sources'].forEach(t => {
      const pane = document.getElementById(`st-pane-${t}`);
      if (pane) pane.style.display = t === name ? '' : 'none';
    });
    if (name === 'feed')      _loadFeed();
    if (name === 'watchlist') _loadWatchlist();
    if (name === 'whales')    _loadWhales();
    if (name === 'sources')   _loadSources();
    _loadStats();
  }

  // ── Polling ───────────────────────────────────────────────────────────────

  function _startPoll() {
    if (_pollId) clearInterval(_pollId);
    _pollId = setInterval(() => {
      _loadStats();
      if (_state.tab === 'feed')      _loadFeed(true);
      if (_state.tab === 'watchlist') _loadWatchlist();
      if (_state.tab === 'whales')    _loadWhales();
    }, POLL);
  }

  // ── API helpers ───────────────────────────────────────────────────────────

  async function _api(path, opts = {}) {
    const res = await fetch(API + path, opts);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function _setServerBadge(up) {
    _state.serverUp = up;
    const el = document.getElementById('st-server-badge');
    if (!el) return;
    el.textContent = up ? '● live' : '● offline';
    el.className   = `st-badge ${up ? 'st-badge-on' : 'st-badge-off'}`;
  }

  // ── Stats ─────────────────────────────────────────────────────────────────

  async function _loadStats() {
    try {
      const s = await _api('/stats');
      _state.stats = s;
      _setServerBadge(true);
      _el('ss-total',   s.total_signals);
      _el('ss-recent',  s.recent_24h);
      _el('ss-sources', s.active_sources);
      _el('ss-watch',   s.watchlist_items);
      _el('ss-whales',  s.whale_events);
      _el('ss-alerts',  s.alert_triggers);
    } catch {
      _setServerBadge(false);
    }
  }

  // ── Feed ──────────────────────────────────────────────────────────────────

  async function _loadFeed(silent = false) {
    const list = document.getElementById('st-feed-list');
    if (!list) return;
    if (!silent) list.innerHTML = '<div class="st-placeholder">Loading…</div>';

    const qs = _buildFeedQuery(0);
    try {
      const data = await _api(`?${qs}`);
      _state.signals = data.items || [];
      _renderFeed(list, _state.signals, false);
      const more = document.getElementById('st-load-more');
      if (more) more.style.display = _state.signals.length >= _state.filters.limit ? '' : 'none';
    } catch (e) {
      list.innerHTML = `<div class="st-error">Cannot reach server — is Atlas server running?<br><small>${e.message}</small></div>`;
    }
  }

  async function _loadMore() {
    const list = document.getElementById('st-feed-list');
    if (!list) return;
    const offset = _state.signals.length;
    const qs     = _buildFeedQuery(offset);
    try {
      const data  = await _api(`?${qs}`);
      const extra = data.items || [];
      _state.signals = [..._state.signals, ...extra];
      _renderFeed(list, _state.signals, false);
      const more = document.getElementById('st-load-more');
      if (more) more.style.display = extra.length >= _state.filters.limit ? '' : 'none';
    } catch { /* silent */ }
  }

  function _buildFeedQuery(offset) {
    const f = _state.filters;
    const p = new URLSearchParams({ limit: f.limit, offset });
    if (f.ticker)    p.append('ticker',    f.ticker.toUpperCase());
    if (f.category)  p.append('category',  f.category);
    if (f.sentiment) p.append('sentiment', f.sentiment);
    return p.toString();
  }

  function _filterChange() {
    _state.filters.ticker    = (document.getElementById('st-f-ticker')?.value || '').trim();
    _state.filters.category  = document.getElementById('st-f-cat')?.value || '';
    _state.filters.sentiment = document.getElementById('st-f-sent')?.value || '';
    _loadFeed();
  }

  function _renderFeed(container, items, append) {
    if (!items.length) {
      container.innerHTML = '<div class="st-placeholder">No signals match your filters.</div>';
      return;
    }
    const html = items.map(s => {
      const age    = _age(s.published_at);
      const ticks  = s.tickers.slice(0, 5).map(t =>
        `<span class="st-ticker-chip">${t}</span>`
      ).join('');
      const catCol = CAT_COLOR[s.category] || '#445';
      const sentCol = SENT_COLOR[s.sentiment] || '#445';
      const urgCol  = URGENCY_COLOR[s.urgency] || '#445';
      const score   = Math.round(s.relevance_score * 100);
      return `
        <div class="st-signal-row" onclick="SignalTerminal._expandSignal(this,'${s.id}')">
          <div class="st-sig-meta">
            <span class="st-sig-cat" style="background:${catCol}22;color:${catCol};border-color:${catCol}44">${s.category}</span>
            <span class="st-sig-sent" style="color:${sentCol}">${s.sentiment}</span>
            <span class="st-sig-urgency" style="color:${urgCol}">●</span>
            <span class="st-sig-age">${age}</span>
            <span class="st-sig-score" title="Relevance">${score}%</span>
          </div>
          <div class="st-sig-title">${_esc(s.title)}</div>
          ${ticks ? `<div class="st-sig-tickers">${ticks}</div>` : ''}
          <div class="st-sig-detail" id="st-detail-${s.id}" style="display:none"></div>
        </div>`;
    }).join('');
    container.innerHTML = html;
  }

  async function _expandSignal(row, id) {
    const detail = document.getElementById(`st-detail-${id}`);
    if (!detail) return;
    if (detail.style.display !== 'none') {
      detail.style.display = 'none';
      return;
    }
    detail.style.display = '';
    if (detail.dataset.loaded) return;
    detail.innerHTML = '<span style="color:var(--txt-muted);font-size:11px">Loading…</span>';
    try {
      const s = await _api(`/${id}`);
      detail.dataset.loaded = '1';
      detail.innerHTML = `
        <div class="st-sig-expand">
          ${s.url ? `<a class="st-link" href="${_esc(s.url)}" target="_blank" rel="noopener">↗ Source</a>` : ''}
          ${s.author ? `<span class="st-sig-author">by ${_esc(s.author)}</span>` : ''}
          ${s.body ? `<div class="st-sig-body">${_esc(s.body.slice(0,400))}${s.body.length > 400 ? '…' : ''}</div>` : ''}
          <div class="st-sig-kws">${(s.keywords || []).slice(0,8).map(k => `<span class="st-kw">${_esc(k)}</span>`).join(' ')}</div>
          <div class="st-sig-ids">
            <span>source: ${s.source_id}</span>
            <span>score: ${s.relevance_score.toFixed(3)}</span>
            <span>sent: ${s.sentiment_score.toFixed(3)}</span>
          </div>
        </div>`;
    } catch {
      detail.innerHTML = '<span style="color:#e74c3c;font-size:11px">Could not load detail.</span>';
    }
  }

  // ── Watchlist ─────────────────────────────────────────────────────────────

  async function _loadWatchlist() {
    const list = document.getElementById('st-watch-list');
    if (!list) return;
    try {
      _state.watchlist = await _api('/watchlist');
      _renderWatchlist(list);
    } catch (e) {
      list.innerHTML = `<div class="st-error">${e.message}</div>`;
    }
  }

  function _renderWatchlist(container) {
    const items = _state.watchlist;
    if (!items.length) {
      container.innerHTML = '<div class="st-placeholder">No tickers in watchlist. Add one above.</div>';
      return;
    }
    const PRIO_COLOR = { high: 'var(--accent-green)', medium: '#f39c12', low: '#445' };
    container.innerHTML = items.map(item => `
      <div class="st-watch-row">
        <span class="st-watch-ticker">${_esc(item.ticker)}</span>
        <span class="st-watch-name">${_esc(item.name || '')}</span>
        <span class="st-watch-type">${item.asset_type}</span>
        <span class="st-watch-prio" style="color:${PRIO_COLOR[item.priority] || '#445'}">${item.priority}</span>
        <span class="st-watch-alert" title="${item.alert_enabled ? 'Alerts on' : 'Alerts off'}">${item.alert_enabled ? '🔔' : '🔕'}</span>
        <button class="st-del-btn" onclick="SignalTerminal._removeWatch('${_esc(item.ticker)}')" title="Remove">✕</button>
      </div>
    `).join('');
  }

  async function _addWatch() {
    const ticker = (document.getElementById('st-w-ticker')?.value || '').trim().toUpperCase();
    if (!ticker) return;
    const name     = (document.getElementById('st-w-name')?.value || '').trim();
    const assetType = document.getElementById('st-w-type')?.value    || 'stock';
    const priority  = document.getElementById('st-w-priority')?.value || 'medium';
    try {
      await _api('/watchlist', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ ticker, name, asset_type: assetType, priority }),
      });
      document.getElementById('st-w-ticker').value = '';
      document.getElementById('st-w-name').value   = '';
      await _loadWatchlist();
      await _loadStats();
    } catch (e) {
      alert(`Failed to add ${ticker}: ${e.message}`);
    }
  }

  async function _removeWatch(ticker) {
    try {
      await _api(`/watchlist/${ticker}`, { method: 'DELETE' });
      await _loadWatchlist();
      await _loadStats();
    } catch (e) {
      alert(`Failed to remove ${ticker}: ${e.message}`);
    }
  }

  // ── Whale Events ──────────────────────────────────────────────────────────

  async function _loadWhales() {
    const list = document.getElementById('st-whale-list');
    if (!list) return;
    const ticker = (document.getElementById('st-wh-ticker')?.value || '').trim().toUpperCase();
    const qs     = new URLSearchParams({ limit: 50 });
    if (ticker) qs.append('ticker', ticker);
    try {
      _state.whales = await _api(`/whales?${qs}`);
      _renderWhales(list);
    } catch (e) {
      list.innerHTML = `<div class="st-error">${e.message}</div>`;
    }
  }

  function _renderWhales(container) {
    const events = _state.whales;
    if (!events.length) {
      container.innerHTML = '<div class="st-placeholder">No whale events detected yet.</div>';
      return;
    }
    const TYPE_ICON = {
      large_buy:       '▲',
      large_sell:      '▼',
      unusual_options: '⚡',
      dark_pool:       '◈',
      insider:         '◉',
      short_squeeze:   '↑↑',
      block_trade:     '⬛',
      unknown:         '?',
    };
    container.innerHTML = events.map(e => `
      <div class="st-whale-row">
        <span class="st-whale-type" title="${e.event_type}">${TYPE_ICON[e.event_type] || '?'}</span>
        <span class="st-whale-ticker">${_esc(e.ticker)}</span>
        <span class="st-whale-size">${_esc(e.size_label)}</span>
        <span class="st-whale-desc">${_esc(e.description.slice(0, 90))}</span>
        <span class="st-whale-conf">${Math.round(e.confidence * 100)}%</span>
        <span class="st-whale-date">${_age(e.detected_at)}</span>
      </div>
    `).join('');
  }

  // ── Sources ───────────────────────────────────────────────────────────────

  async function _loadSources() {
    const list = document.getElementById('st-source-list');
    if (!list) return;
    try {
      _state.sources = await _api('/sources/list?enabled_only=false');
      _renderSources(list);
    } catch (e) {
      list.innerHTML = `<div class="st-error">${e.message}</div>`;
    }
  }

  function _renderSources(container) {
    const sources = _state.sources;
    if (!sources.length) {
      container.innerHTML = '<div class="st-placeholder">No sources configured.</div>';
      return;
    }
    const TYPE_COLOR = { rss: '#3498db', reddit: '#ff6314', webhook: '#9b59b6', manual: '#445' };
    container.innerHTML = sources.map(s => {
      const lastFetch = s.last_fetched_at ? _age(s.last_fetched_at) : 'never';
      const errClass  = s.error_count > 0 ? 'st-src-has-error' : '';
      const typeCol   = TYPE_COLOR[s.type] || '#445';
      return `
        <div class="st-source-row ${errClass}">
          <span class="st-src-type" style="background:${typeCol}22;color:${typeCol}">${s.type}</span>
          <span class="st-src-name">${_esc(s.name)}</span>
          <span class="st-src-stats">${s.total_fetched} signals · last ${lastFetch}</span>
          ${s.error_count ? `<span class="st-src-err" title="${_esc(s.last_error || '')}">⚠ ${s.error_count} err</span>` : ''}
          <label class="st-toggle" title="${s.enabled ? 'Disable' : 'Enable'} source">
            <input type="checkbox" ${s.enabled ? 'checked' : ''}
              onchange="SignalTerminal._toggleSource('${s.id}',this.checked)"/>
            <span class="st-toggle-track"></span>
          </label>
        </div>`;
    }).join('');
  }

  async function _toggleSource(id, enabled) {
    try {
      await _api(`/sources/${id}/toggle?enabled=${enabled}`, { method: 'PATCH' });
      await _loadSources();
    } catch (e) {
      alert(`Toggle failed: ${e.message}`);
    }
  }

  // ── Manual collect ────────────────────────────────────────────────────────

  async function _collectNow() {
    const btn = document.querySelector('[onclick="SignalTerminal._collectNow()"]');
    if (btn) { btn.disabled = true; btn.textContent = '⟳ Running…'; }
    try {
      const result = await _api('/collect/now', { method: 'POST' });
      const ins    = result.total_inserted || 0;
      const dup    = result.total_dupes    || 0;
      if (btn) btn.textContent = `✓ +${ins} (${dup} dup)`;
      setTimeout(() => { if (btn) { btn.disabled = false; btn.textContent = '⟳ Collect'; } }, 3000);
      await _loadFeed();
      await _loadStats();
    } catch (e) {
      if (btn) { btn.disabled = false; btn.textContent = '⟳ Collect'; }
      alert(`Collect failed: ${e.message}`);
    }
  }

  // ── Utilities ─────────────────────────────────────────────────────────────

  function _el(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text ?? '—';
  }

  function _esc(s) {
    return String(s)
      .replace(/&/g,'&amp;')
      .replace(/</g,'&lt;')
      .replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;');
  }

  function _age(isoStr) {
    if (!isoStr) return '?';
    const ms = Date.now() - new Date(isoStr + (isoStr.endsWith('Z') ? '' : 'Z')).getTime();
    const s  = Math.floor(ms / 1000);
    if (s < 60)    return `${s}s ago`;
    if (s < 3600)  return `${Math.floor(s/60)}m ago`;
    if (s < 86400) return `${Math.floor(s/3600)}h ago`;
    return `${Math.floor(s/86400)}d ago`;
  }

  // ── Expose internals needed by inline handlers ───────────────────────────
  return {
    init, cleanup,
    _tab, _collectNow,
    _filterChange, _loadFeed, _loadMore,
    _addWatch, _removeWatch,
    _loadWhales,
    _toggleSource,
    _expandSignal,
  };

})();
