/**
 * Atlas Info Module — v1.0
 * ========================
 * Searchable, filterable documentation for every Atlas module,
 * data source, feature, visualization, and algorithm.
 *
 * Each entry explains:
 *   • What it does
 *   • Where it gets its data
 *   • How it measures / computes the result
 */

'use strict';

window.InfoModule = (() => {

  /* ─────────────────────────────────────────────────────────
     CATEGORY DEFINITIONS
  ───────────────────────────────────────────────────────── */
  const CATEGORIES = [
    { id: 'all',         label: 'All',              icon: '⬡' },
    { id: 'data',        label: 'Data Sources',     icon: '🗄' },
    { id: 'strategy',    label: 'Strategies',       icon: '⚡' },
    { id: 'feature',     label: 'Features',         icon: '🔬' },
    { id: 'correlation', label: 'Correlation',      icon: '🔗' },
    { id: 'viz',         label: 'Visualizations',   icon: '🎨' },
    { id: 'ai',          label: 'AI / ML',          icon: '🧠' },
    { id: 'infra',       label: 'Infrastructure',   icon: '⚙' },
  ];

  /* ─────────────────────────────────────────────────────────
     ITEM CATALOGUE
     Each entry: { id, category, name, icon, desc,
                   source, how, tags[], api? }
  ───────────────────────────────────────────────────────── */
  const ITEMS = [

    /* ══════════════════════ DATA SOURCES ══════════════════════ */
    {
      id: 'yfinance',
      category: 'data',
      name: 'Yahoo Finance (yfinance)',
      icon: '📈',
      desc: 'Primary market data provider for all live analysis. Supplies OHLCV price history, dividends, splits, and basic ticker metadata for equities, ETFs, indices, crypto, and FX pairs.',
      source: 'Yahoo Finance public API via the yfinance Python library.',
      how: 'Calls yfinance.Ticker(symbol).history(period, auto_adjust=True). Auto-adjust corrects for splits and dividends so all prices are on a comparable scale. Returns a pandas DataFrame with columns Open, High, Low, Close, Volume indexed by date.',
      tags: ['OHLCV', 'Live', 'Free', 'Requires Internet'],
      api: '/api/quote/{ticker}',
    },
    {
      id: 'synthetic',
      category: 'data',
      name: 'Synthetic GBM Data (Local Fallback)',
      icon: '🎲',
      desc: 'Offline data generator that produces realistic OHLCV price series using Geometric Brownian Motion. Used automatically when yfinance is unavailable (no internet, rate-limited, unknown ticker).',
      source: 'Locally generated — no external dependency.',
      how: 'Simulates price as: S(t+1) = S(t) × exp((μ − ½σ²)dt + σ√dt × Z). Parameters μ and σ are seeded deterministically by the ticker name hash, so results are reproducible per symbol. OHLC spread is generated as ±0.3–1.5% of close. Volume follows a log-normal distribution. All routes return "synthetic: true" in the response when using this fallback.',
      tags: ['Offline', 'Deterministic', 'GBM', 'No Internet Needed'],
    },
    {
      id: 'ollama',
      category: 'data',
      name: 'Ollama (Local LLM)',
      icon: '🦙',
      desc: 'Local Large Language Model server that powers ARIA\'s conversational intelligence. Runs entirely on your machine — no data sent to the cloud.',
      source: 'Localhost Ollama server (http://localhost:11434). Models: llama3.2:1b (default), qwen2.5:7b, deepseek-coder:6.7b.',
      how: 'Atlas server POSTs to Ollama\'s /api/generate or /api/chat endpoint with the user message + ARIA system prompt. ARIA\'s tool-calling layer intercepts structured JSON responses and routes them to Python handlers (data fetch, backtest, risk analysis). Response streams back token by token via the WebSocket.',
      tags: ['LLM', 'Local', 'No Cloud', 'ARIA'],
    },

    /* ══════════════════════ STRATEGY ENGINES ══════════════════════ */
    {
      id: 'sma_crossover',
      category: 'strategy',
      name: 'SMA Crossover Engine',
      icon: '📊',
      desc: 'Trend-following strategy based on the crossover of a fast and slow simple moving average. Generates LONG signals when the fast MA crosses above the slow MA, SHORT signals on the opposite cross.',
      source: 'Close prices from yfinance (or synthetic fallback).',
      how: 'Computes SMA(fast=20) and SMA(slow=50) on daily Close prices. Signal = LONG if SMA20 > SMA50 and the cross happened within the last 3 bars; SHORT on the reverse. Confidence scales with the magnitude of the spread: |SMA_fast − SMA_slow| / SMA_slow. Part of the MultiStrategy consensus.',
      tags: ['Trend', 'Moving Average', 'Rule-Based'],
      api: '/api/strategy/analyze/{ticker}',
    },
    {
      id: 'rsi_mean_reversion',
      category: 'strategy',
      name: 'RSI Mean Reversion Engine',
      icon: '↩',
      desc: 'Counter-trend strategy that identifies extreme overbought/oversold conditions using RSI, confirmed by Bollinger Bands and filtered by ADX trend strength. Avoids trading in strong trending markets.',
      source: 'Close prices; optionally High/Low for ATR.',
      how: 'RSI-14: uses Wilder\'s smoothed average gains/losses. Oversold: RSI < 30 AND price near lower BB → LONG. Overbought: RSI > 70 AND price near upper BB → SHORT. ADX-14 filter: if ADX > 25 (strong trend), confidence is halved to avoid false mean-reversion trades in trending regimes.',
      tags: ['Mean Reversion', 'RSI', 'Bollinger Bands', 'ADX'],
      api: '/api/strategy/analyze/{ticker}',
    },
    {
      id: 'macd_engine',
      category: 'strategy',
      name: 'MACD Engine',
      icon: '〰',
      desc: 'Momentum strategy using three independent MACD triggers that vote on direction. Uses classic MACD(12,26,9) with signal line crossover, zero-line cross, and histogram momentum.',
      source: 'Close prices.',
      how: 'MACD Line = EMA(12) − EMA(26). Signal Line = EMA(9) of MACD. Histogram = MACD − Signal. Three sub-signals: (1) Signal Crossover: MACD crosses Signal line. (2) Zero-Line Cross: MACD line crosses zero. (3) Histogram Momentum: histogram increasing (bullish) or decreasing (bearish). Final signal is a weighted vote of all three; direction must agree on 2/3.',
      tags: ['Momentum', 'MACD', 'EMA', 'Rule-Based'],
      api: '/api/strategy/analyze/{ticker}',
    },
    {
      id: 'bb_squeeze',
      category: 'strategy',
      name: 'Bollinger Band Squeeze Engine',
      icon: '🤏',
      desc: 'Volatility breakout strategy. Detects when the Bollinger Bands narrow inside the Keltner Channels (the "squeeze"), then fires directional breakout signals when volatility expands.',
      source: 'Close, High, Low prices.',
      how: 'Bollinger Bands: SMA(20) ± 2σ. Keltner Channels: EMA(20) ± 1.5 × ATR(10). Squeeze = BB width < KC width. When squeeze releases (BB width expands beyond KC), the momentum of the close relative to midpoint determines direction: above midpoint → LONG, below → SHORT. Confidence = normalized BB width expansion ratio.',
      tags: ['Volatility', 'Breakout', 'Squeeze', 'Bollinger'],
      api: '/api/strategy/analyze/{ticker}',
    },
    {
      id: 'momentum_engine',
      category: 'strategy',
      name: 'Momentum Engine (TSMOM)',
      icon: '🚀',
      desc: 'Time-series momentum strategy based on Moskowitz, Ooi & Pedersen (2012). Combines multi-period lookback momentum with volume price trend and moving average alignment for institutional-grade momentum signals.',
      source: 'Close and Volume prices.',
      how: 'TSMOM: sign(ret_21d) × |ret_21d| + sign(ret_63d) × |ret_63d| + sign(ret_126d) × |ret_126d|. VPT: Volume Price Trend = Σ(Volume × ΔPrice/Price). MA alignment: Close > SMA20 > SMA50. Signal is LONG when all three agree bullish, SHORT when all three agree bearish. Confidence = agreement score / 3.',
      tags: ['Momentum', 'TSMOM', 'Multi-Period', 'Volume'],
      api: '/api/strategy/analyze/{ticker}',
    },
    {
      id: 'multistrategy',
      category: 'strategy',
      name: 'Multi-Strategy Consensus',
      icon: '🗳',
      desc: 'Combines signals from all 5 rule-based engines into a single weighted consensus signal. When engines agree, confidence is amplified. When they disagree, the discrepancy is flagged.',
      source: 'Runs all 5 engines on the same OHLCV data.',
      how: 'Each engine emits: action (LONG/SHORT/HOLD), confidence (0–1), and weight (fixed per engine). Consensus = weighted sum of signed confidences. Agreement multiplier: if ≥4/5 engines agree on direction, confidence is boosted by 1.2×. If ≤2/5 agree, signal confidence is halved. Final output: action + confidence + per-engine breakdown.',
      tags: ['Consensus', 'Weighted Vote', 'Meta-Strategy'],
      api: '/api/strategy/analyze/{ticker}',
    },

    /* ══════════════════════ CHAOS & ENTROPY FEATURES ══════════════════════ */
    {
      id: 'hurst',
      category: 'feature',
      name: 'Hurst Exponent (R/S Analysis)',
      icon: 'H',
      desc: 'Measures long-range memory in the price series. Indicates whether a market is trending, mean-reverting, or behaving like a random walk.',
      source: 'Log price series (Close).',
      how: 'Rescaled Range (R/S) analysis: for each lag τ, compute R(τ)/S(τ) where R = max(cumdev) − min(cumdev) and S = std(increments). H = slope of log(R/S) vs log(τ) via OLS. H > 0.55 = persistent/trending. H < 0.45 = anti-persistent/mean-reverting. H ≈ 0.5 = random walk (Efficient Market).',
      tags: ['Chaos', 'Long Memory', 'Trending', 'H-exponent'],
      api: '/api/chaos/{ticker}',
    },
    {
      id: 'dfa',
      category: 'feature',
      name: 'DFA Exponent (Detrended Fluctuation Analysis)',
      icon: 'α',
      desc: 'More robust alternative to Hurst for non-stationary series. Detects fractal scaling properties and long-range correlations without being fooled by polynomial trends.',
      source: 'Log price series (Close).',
      how: 'Cumulative sum of mean-subtracted returns forms the profile. For each scale s, divide into non-overlapping windows, fit linear detrend within each, compute RMS of residuals F(s). DFA exponent α = slope of log(F(s)) vs log(s). α > 0.5 = long-range correlation (trending), α < 0.5 = anti-correlated (mean-reverting), α ≈ 0.5 = uncorrelated noise.',
      tags: ['Chaos', 'DFA', 'Non-Stationary', 'Scaling'],
      api: '/api/chaos/{ticker}',
    },
    {
      id: 'fractal_dim',
      category: 'feature',
      name: 'Fractal Dimension (Higuchi Method)',
      icon: '🌿',
      desc: 'Quantifies the geometric complexity of a price time series. Higher fractal dimension means more jagged, chaotic price movement; lower means smoother trends.',
      source: 'Close prices.',
      how: 'Higuchi FD: constructs k sub-series with delay m, computes length L(k,m) for each. FD = slope of log(L) vs log(1/k). Range [1, 2]: FD=1 means perfectly smooth straight line, FD=1.5 matches Brownian motion (random walk), FD approaching 2 means maximally complex/chaotic series.',
      tags: ['Chaos', 'Fractal', 'Complexity'],
      api: '/api/chaos/{ticker}',
    },
    {
      id: 'approx_entropy',
      category: 'feature',
      name: 'Approximate Entropy (ApEn)',
      icon: 'Ap',
      desc: 'Measures the predictability of a time series. Low ApEn means the series is highly repetitive and predictable. High ApEn means complex and unpredictable. Useful for regime detection.',
      source: 'Return series derived from Close prices.',
      how: 'For template length m=2 and tolerance r=0.2×σ: counts how often a m-length template repeats within tolerance, divided by how often the (m+1)-length version repeats. ApEn = −log(conditional repeat probability). Lower = more predictable structure. O(n²) complexity — used on windows ≤200 bars.',
      tags: ['Entropy', 'Predictability', 'ApEn'],
      api: '/api/chaos/{ticker}',
    },
    {
      id: 'perm_entropy',
      category: 'feature',
      name: 'Permutation Entropy (Bandt-Pompe)',
      icon: 'PE',
      desc: 'Captures ordinal structure of price movements using the relative ordering of consecutive values. More robust to noise and outliers than amplitude-based entropy measures.',
      source: 'Return series.',
      how: 'For order d=3 and lag τ=1: extract all d-length sub-sequences, sort each by value to get ordinal patterns. Count relative frequency p(π) of each permutation π. PE = −Σ p(π) × log₂(p(π)) / log₂(d!). Normalized ∈ [0,1]. 0 = perfectly ordered (one pattern dominates). 1 = maximally disordered (all patterns equally likely).',
      tags: ['Entropy', 'Ordinal', 'Robust'],
      api: '/api/chaos/{ticker}',
    },
    {
      id: 'lyapunov',
      category: 'feature',
      name: 'Lyapunov Proxy (NN Divergence)',
      icon: 'λ',
      desc: 'Estimates the largest Lyapunov exponent — the rate at which nearby trajectories in the reconstructed phase space diverge. Positive value indicates sensitive dependence on initial conditions (chaos).',
      source: 'Close prices reconstructed into embedding space.',
      how: 'Phase space reconstruction via Takens embedding theorem: embedding dimension d=3, lag τ=1. For each point, find nearest neighbor (excluding temporal neighbors). Track divergence rate: λ ≈ (1/T) × Σ log(d(t+1)/d(t)). Positive λ = exponential divergence (chaotic). Negative λ = trajectories converging (stable). Near zero = boundary.',
      tags: ['Chaos', 'Lyapunov', 'Phase Space'],
      api: '/api/chaos/{ticker}',
    },
    {
      id: 'transfer_entropy',
      category: 'feature',
      name: 'Transfer Entropy (Schreiber 2000)',
      icon: 'TE',
      desc: 'Measures the directed information flow from asset A to asset B. Captures asymmetric causal influence that correlation (symmetric) cannot detect. Useful for lead-lag detection between assets.',
      source: 'Return series from two assets.',
      how: 'Discretizes returns into 5 quantile bins. Computes joint probability tables p(B_t+1, B_t, A_t) and p(B_t+1, B_t) via frequency counting. TE(A→B) = Σ p(b\', b, a) × log₂[p(b\'|b,a) / p(b\'|b)]. Represents the extra predictive information that knowing A\'s past gives about B\'s future, beyond what B\'s own past already provides.',
      tags: ['Entropy', 'Causality', 'Information Flow', 'Lead-Lag'],
      api: '/api/chaos/{ticker}',
    },
    {
      id: 'yang_zhang',
      category: 'feature',
      name: 'Yang-Zhang Volatility (2000)',
      icon: 'YZ',
      desc: 'The most efficient OHLC volatility estimator. Handles overnight price gaps (open ≠ previous close) and is unbiased and consistent under Brownian motion with drift.',
      source: 'Full OHLCV data (Open, High, Low, Close).',
      how: 'YZ = σ²_open + k × σ²_close + (1−k) × σ²_RS where: σ²_open = variance of log(Open_t/Close_{t−1}), σ²_close = variance of log(Close_t/Open_t), σ²_RS = Rogers-Satchell estimator = Σ[log(H/C)×log(H/O) + log(L/C)×log(L/O)]/n, k = 0.34/(1.34+(n+1)/(n−1)). Annualised × √252.',
      tags: ['Volatility', 'OHLC', 'Yang-Zhang', 'Efficient'],
      api: '/api/volatility/{ticker}',
    },
    {
      id: 'garman_klass',
      category: 'feature',
      name: 'Garman-Klass Volatility',
      icon: 'GK',
      desc: 'OHLC volatility estimator that uses the full daily price range (High and Low) to extract more information about intraday volatility than close-to-close estimation alone.',
      source: 'Open, High, Low, Close prices.',
      how: 'GK² = (1/n) × Σ[0.5×(log H/L)² − (2log2−1)×(log C/O)²]. The first term captures intraday range variance; the second corrects for the drift component using open-to-close returns. Roughly 5–8× more efficient than close-to-close σ².',
      tags: ['Volatility', 'OHLC', 'Garman-Klass'],
      api: '/api/volatility/{ticker}',
    },
    {
      id: 'vol_of_vol',
      category: 'feature',
      name: 'Vol-of-Vol (Volatility of Volatility)',
      icon: 'VoV',
      desc: 'Second-order measure of volatility instability. High Vol-of-Vol means the market\'s risk level is itself changing rapidly — a warning sign for regime transitions.',
      source: 'Close prices (rolling returns).',
      how: 'Step 1: compute rolling realized vol over a short window (10 bars) → vol_series. Step 2: compute rolling standard deviation of vol_series over a longer window (30 bars) → vol-of-vol. Both steps are annualised: ×√252. High values indicate unstable vol regimes (e.g., VIX spikes above spikes).',
      tags: ['Volatility', 'Second-Order', 'Regime'],
      api: '/api/volatility/{ticker}',
    },
    {
      id: 'vol_regime',
      category: 'feature',
      name: 'Volatility Regime Classifier',
      icon: '🚦',
      desc: 'Classifies the current market volatility environment into one of four states based on its position within the historical percentile distribution.',
      source: 'Rolling realized volatility series.',
      how: 'Computes rolling 20-bar realized vol σ. Ranks the current σ against the last 252 bars (1 year). LOW = < 33rd percentile. NORMAL = 33rd–67th percentile. HIGH = 67th–95th percentile. SPIKE = > 95th percentile. All thresholds are configurable (low_pct, high_pct parameters).',
      tags: ['Volatility', 'Regime', 'Classification'],
      api: '/api/volatility/{ticker}',
    },

    /* ══════════════════════ FACTOR MODELS ══════════════════════ */
    {
      id: 'pca_factors',
      category: 'feature',
      name: 'PCA Factor Decomposition',
      icon: '🔩',
      desc: 'Extracts the dominant statistical risk factors that explain co-movement across a portfolio of assets. Identifies market-wide, sector, and idiosyncratic sources of return variance.',
      source: 'Daily returns matrix (T × N) from yfinance or synthetic fallback.',
      how: 'Z-scores return matrix by column. Computes covariance matrix C = XᵀX/(T−1). Eigendecomposition (numpy.linalg.eigh) of C → eigenvalues λ and eigenvectors V. Factors F = X × V[:,:k] (T×k). Loadings L = Vᵀ[:k,:] (k×N). Explained variance = λ_i / Σλ. Pure numpy SVD — no scipy required.',
      tags: ['Factor Model', 'PCA', 'SVD', 'Multi-Asset'],
      api: '/api/factors/decompose',
    },
    {
      id: 'factor_attribution',
      category: 'feature',
      name: 'Factor Attribution (OLS)',
      icon: 'β',
      desc: 'Decomposes an asset\'s return variance into the portion explained by statistical factors (systematic) vs. what is unique to that asset (idiosyncratic / alpha).',
      source: 'Asset return series + factor scores from PCA decomposition.',
      how: 'OLS regression: y_t = α + β₁F₁_t + β₂F₂_t + … + βₖFₖ_t + ε_t. Solved via numpy.linalg.lstsq. R² = 1 − SS_res/SS_tot. Systematic vol = std(ŷ) × √252. Idiosyncratic vol = std(ε) × √252. Alpha = α × 252 (annualised intercept). Beta vector = [β₁…βₖ].',
      tags: ['Factor Model', 'OLS', 'Attribution', 'R²'],
      api: '/api/factors/attribution/{ticker}',
    },
    {
      id: 'factor_timing',
      category: 'feature',
      name: 'Factor Timing Signal',
      icon: '⏱',
      desc: 'Mean-reversion signal on individual factor returns. When a factor has moved far from its recent average (high z-score), fades the exposure; when depressed, increases it.',
      source: 'Day-over-day changes in PCA factor scores.',
      how: 'For each factor F: compute z-score of the latest day-over-day return relative to a rolling 20-bar window: z = (F_t − μ_20) / σ_20. Signal: z > 1.5 → SHORT (fade the factor). z < −1.5 → LONG (chase). |z| ≤ 1.5 → NEUTRAL. Strength = min(2.0, |z| / 1.5).',
      tags: ['Factor Model', 'Timing', 'Mean Reversion'],
      api: '/api/factors/decompose',
    },

    /* ══════════════════════ CORRELATION PORTFOLIO ══════════════════════ */
    {
      id: 'market_structure',
      category: 'correlation',
      name: 'Market Structure Analyzer',
      icon: '🕸',
      desc: 'Monitors the overall correlation regime of a multi-asset universe. Detects correlation breakdowns (crisis), identifies the most systemically central assets, and measures portfolio diversification.',
      source: 'Multi-asset Close prices (yfinance).',
      how: 'Rolling 60-day Pearson correlation matrix. Average correlation → regime: < 0.3 = LOW, 0.3–0.5 = NORMAL, 0.5–0.7 = HIGH, > 0.7 = CRISIS. Centrality = mean absolute correlation of each asset vs all others (most central = highest). Diversification score = 1 − avg_corr (1 = perfect diversification). Breakdown alert when avg_corr spikes > 1.5× its 20-day average.',
      tags: ['Correlation', 'Regime', 'Diversification', 'Network'],
      api: '/api/correlation/structure',
    },
    {
      id: 'pairs_trading',
      category: 'correlation',
      name: 'Pairs Trading Engine',
      icon: '↔',
      desc: 'Identifies statistically cointegrated asset pairs and generates mean-reversion spread signals. When the spread diverges beyond its historical norm, a trade is triggered expecting convergence.',
      source: 'Multi-asset Close prices for cointegration testing.',
      how: 'Cointegration: Augmented Dickey-Fuller test on the spread (custom pure-numpy ADF). OLS hedge ratio β = Cov(X,Y)/Var(X). Spread = Y − βX. Z-score = (spread − μ_spread) / σ_spread. Signals: z > 2 → SHORT spread (short Y, long X). z < −2 → LONG spread. |z| < 0.5 → EXIT. |z| > 3.5 → STOP (pairs diverging). Half-life = −log(2) / OLS AR(1) coefficient.',
      tags: ['Pairs', 'Cointegration', 'ADF', 'Spread', 'Mean Reversion'],
      api: '/api/correlation/pairs',
    },
    {
      id: 'regime_clustering',
      category: 'correlation',
      name: 'Regime Clustering Engine',
      icon: '🧩',
      desc: 'Groups assets into clusters based on the similarity of their return patterns. Reveals hidden sector structure, detects regime shifts, and enables cluster-aware portfolio construction.',
      source: 'Multi-asset return matrix.',
      how: 'Two methods available: (1) Ward Hierarchical: agglomerative clustering minimizing within-cluster variance. Linkage matrix computed from correlation distance (d = 1 − |ρ|). (2) K-Means++: initialises centroids via k-means++ seeding, iterates until convergence. Both methods evaluated on silhouette score = (b−a)/max(a,b). PCA 2D projection for visualization. Optimal k selected by max silhouette across k=2..6.',
      tags: ['Clustering', 'Ward', 'K-Means', 'Silhouette', 'PCA'],
      api: '/api/correlation/cluster',
    },

    /* ══════════════════════ VISUALIZATIONS ══════════════════════ */
    {
      id: 'viz_particle',
      category: 'viz',
      name: '#1 — Particle Market Universe',
      icon: '⚛',
      desc: '15,000 particles morphing between 5 shapes based on the current market regime. Each regime (BULL, BEAR, SIDEWAYS, VOLATILE, TRENDING) maps to a distinct geometric form.',
      source: 'Live regime from /api/vizlab/regime/{ticker}. Falls back to animated auto-cycle.',
      how: 'Three.js BufferGeometry with vertex colors. Each regime defines a target position array. Every frame, particle positions lerp toward target at speed 0.035. Mouse repulsion computed per-particle (2.5-unit radius). Auto-cycles every 8 seconds. BULL=sphere, BEAR=inverted cone, SIDEWAYS=Saturn rings, VOLATILE=explosion, TRENDING=double helix.',
      tags: ['Three.js', 'WebGL', 'Particle', 'Regime', '3D'],
    },
    {
      id: 'viz_brain',
      category: 'viz',
      name: '#2 — ARIA Neural Brain',
      icon: '🧠',
      desc: 'Animated force-directed graph showing ARIA\'s 12 internal modules and their live information pathways. Glowing pulses travel along edges representing active data flow.',
      source: 'Static module graph (+ /api/vizlab/brain for live activity).',
      how: 'Canvas 2D. Nodes use repulsion force (F = 1800/d²) + spring force along edges (k=0.006, rest length=130px) + weak gravity toward center. Velocity damping = 0.88. Pulse particles travel along edges at random intervals. ARIA heartbeat fires every 60 frames, activating the central node.',
      tags: ['Canvas', 'Force-Directed', 'Graph', 'ARIA'],
    },
    {
      id: 'viz_forcegraph',
      category: 'viz',
      name: '#3 — Market Force Graph',
      icon: '🌌',
      desc: '14 assets represented as glowing stars, connected by gravitational forces proportional to their pairwise correlation. Highly correlated assets cluster together; uncorrelated assets repel.',
      source: 'Simulated sector-based correlation matrix (sector same = 0.55–0.92, cross-sector = −0.1–0.45).',
      how: 'Canvas 2D physics. Force = corr × 0.7 − 0.1 (positive = attract, negative = repel). Collision avoidance radius = 60px. Center gravity = 0.001 × distance. Damping = 0.9. Edge drawn only for corr > 0.4 with opacity ∝ correlation strength.',
      tags: ['Canvas', 'Force Physics', 'Correlation', 'Network'],
    },
    {
      id: 'viz_montecarlo',
      category: 'viz',
      name: '#4 — Monte Carlo Paths',
      icon: '📉',
      desc: '150 animated GBM price paths fanning into the future. Shows the distribution of possible price outcomes with P5, P50, and P95 percentile bands.',
      source: 'Synthetic GBM locally (μ=0.0003/day, σ=0.018/day).',
      how: 'GBM: S(t+1) = S(t) × exp((μ−½σ²)/252 + σ × N(0,1/√252)). Box-Muller approximated via 3-uniform sum. 200 forward steps per path. Paths colored by final return (green=positive, red=negative). Percentile bands recomputed at current draw position each frame. Auto-loops.',
      tags: ['Canvas', 'Monte Carlo', 'GBM', 'Probability'],
    },
    {
      id: 'viz_radar',
      category: 'viz',
      name: '#5 — Signal Radar',
      icon: '📡',
      desc: 'Multi-indicator spider/radar chart showing 10 market indicators simultaneously. Each axis represents an indicator (RSI, MACD, BB%, etc.), and the filled polygon shows current signal strength.',
      source: 'Simulated live indicator values (interpolated toward random targets every 80 frames).',
      how: 'Canvas 2D polar coordinate rendering. N=10 axes evenly spaced. For each indicator value v ∈ [0,1], vertex plotted at radius = R × v from center. Polygon filled with radial gradient. Color of vertex dot: green if v>0.65, amber if v>0.35, red otherwise. Central score = mean(v) × 100.',
      tags: ['Canvas', 'Radar', 'Spider Chart', 'Indicators'],
    },
    {
      id: 'viz_terrain',
      category: 'viz',
      name: '#6 — Risk Terrain',
      icon: '🏔',
      desc: 'Animated procedural isometric terrain where elevation represents risk level. Red mountain peaks = high risk zones; green valleys = safe zones.',
      source: 'Procedurally generated (sin/cos noise functions, time-evolving).',
      how: 'Canvas 2D. 32×32 grid. Each cell height = weighted sum of 3 sine/cosine octaves with different frequencies and phases animated with time. Isometric projection: screenX = W/2 + (gx−gy)×cellW×0.6, screenY = H×0.55 + (gx+gy)×cellH×0.3 − height×80. Painter\'s algorithm (back-to-front). Color = HSL mapped from height.',
      tags: ['Canvas', 'Procedural', 'Isometric', 'Risk'],
    },
    {
      id: 'viz_flowfield',
      category: 'viz',
      name: '#7 — Price Flow Field',
      icon: '🌊',
      desc: '600 particles flowing through a vector field driven by market momentum. The field angle is computed from oscillating sine functions, creating organic flowing patterns.',
      source: 'Procedurally generated flow field (angle = f(x, y, time)).',
      how: 'Canvas 2D. Vector field: angle = (sin(nx+t×0.6) × cos(ny−t×0.4) + sin(nx×2.1+t)×0.5) × π. Particles follow the field: velocity lerps toward field direction at rate 0.12. Particle trails fade via semi-transparent overlay (alpha=0.08). Age-based lifecycle: particles reset when they exit bounds or exceed maxAge.',
      tags: ['Canvas', 'Particle', 'Flow Field', 'Momentum'],
    },
    {
      id: 'viz_galaxy',
      category: 'viz',
      name: '#8 — Correlation Galaxy',
      icon: '🌠',
      desc: 'Milky Way style galaxy with 800 stars arranged in 3 spiral arms. Market sector clusters (TECH, FINANCE, ENERGY, CRYPTO) appear as glowing nebulae. The entire galaxy slowly rotates.',
      source: 'Static sector definitions + animated rotation.',
      how: 'Canvas 2D. 3 spiral arms: for each star, arm angle = (arm/3)×2π, theta = armAngle + t×3π + noise. Radius = t × minDim × 0.38 + noise. Stars twinkle via sine-modulated brightness. Rotation via 2D rotation matrix applied each frame. Sector glows are radial gradient circles.',
      tags: ['Canvas', 'Galaxy', 'Correlation', 'Sector'],
    },
    {
      id: 'viz_rltrack',
      category: 'viz',
      name: '#9 — RL Agent Racing Track',
      icon: '🏎',
      desc: 'A DQN RL agent drives a portfolio around an oval track. 13 LIDAR rays measure track clearance. Episode reward history is charted at the bottom. Inspired by speed-racer-rl.',
      source: 'Simulated agent (deterministic oval track + random DQN action labels).',
      how: 'Canvas 2D. Track defined as 80 waypoints on an ellipse. Car interpolates between waypoints at fixed speed. 13 LIDAR rays cast ±55° around heading direction; ray length = rand(25–65px) simulating obstacle distance. Reward history = circular buffer of 120 values, chart rendered as line graph. Actions: HOLD/GAS/BRAKE/STEER L/STEER R/ACC+L/ACC+R.',
      tags: ['Canvas', 'RL', 'DQN', 'Racing', 'LIDAR'],
    },
    {
      id: 'viz_quantum',
      category: 'viz',
      name: '#10 — Quantum Market Superposition',
      icon: '🔬',
      desc: 'Price exists in quantum superposition as overlapping probability waves until a signal fires and collapses the wave function. Click anywhere to trigger a signal collapse.',
      source: 'Procedurally generated wave interference. Auto-collapses every 280 frames.',
      how: 'Canvas 2D. 4 overlapping sine waves with different amplitudes (20–60px), frequencies (0.02–0.08), phases evolving at different rates. Probability density = √(Σ wave²). On collapse: all waves replaced by a vertical spike at click x-coordinate. Position left of center → SHORT, right → LONG. Spike fades over 90–120 frames then returns to superposition.',
      tags: ['Canvas', 'Quantum', 'Wave Function', 'Interactive'],
    },
    {
      id: 'viz_lorenz',
      category: 'viz',
      name: '#11 — Lorenz Attractor',
      icon: '🌀',
      desc: 'Two trajectories in the Lorenz chaotic system representing Bull and Bear market attractors. The butterfly-shaped attractor shows how tiny differences in initial conditions lead to completely different market paths.',
      source: 'Lorenz differential equations integrated locally (σ=10, ρ=28, β=8/3).',
      how: 'Canvas 2D. Euler integration of dx=σ(y−x), dy=x(ρ−z)−y, dz=xy−βz with dt=0.005. Two trajectories with slightly different initial conditions (y₀=0 vs y₀=0.1). Isometric 3D→2D projection: pX = W/2+(x−y)×scale×0.8, pY = H/2−z×scale×0.9+... Trail of 600 points with alpha fade.',
      tags: ['Canvas', 'Chaos', 'Lorenz', 'Phase Space'],
    },
    {
      id: 'viz_heatmap',
      category: 'viz',
      name: '#12 — Return Heatmap Calendar',
      icon: '📅',
      desc: 'GitHub contribution-style calendar showing a full year of daily returns color-coded by magnitude and direction. Hover over any day for the exact return.',
      source: 'Synthetic GBM annual return series (locally generated).',
      how: 'Canvas 2D. 52-week × 7-day grid. Each cell colored by return: green intensity ∝ positive return magnitude (HSL 120, s=80%), red intensity ∝ negative magnitude (HSL 0). Tooltip rendered on hover. Summary bar shows total annual return and win rate. Grid layout from top-left (Monday Jan 1) to bottom-right.',
      tags: ['Canvas', 'Heatmap', 'Calendar', 'Returns', 'Interactive'],
    },
    {
      id: 'viz_orderbook',
      category: 'viz',
      name: '#13 — Live Order Book',
      icon: '📖',
      desc: 'Simulated real-time L2 order book showing 18 bid and ask levels with bar widths proportional to size. Price chart at the bottom shows the mid-price history.',
      source: 'Locally simulated order book. Price drifts via random walk; spread widens randomly.',
      how: 'Canvas 2D. Bids below mid-line (green bars extending left), asks above (red bars extending right). Bar width = (size/maxSize) × maxBarWidth. Mid-price updates every 8 frames via: midPrice += imbalance × 0.03. Spread = clamp(spread + noise, 0.02, 0.15). Price history ring buffer of 120 values rendered as sparkline.',
      tags: ['Canvas', 'Order Book', 'L2', 'Spread', 'Market Microstructure'],
    },
    {
      id: 'viz_volsmile',
      category: 'viz',
      name: '#14 — Vol Smile Surface',
      icon: '😊',
      desc: '3D implied volatility surface showing how IV varies across strikes (x-axis) and expiries (z-axis). Mouse movement rotates the surface for better viewing angle.',
      source: 'Synthetic IV computed from parametric smile model (ATM + skew + convexity).',
      how: 'Canvas 2D with 3D perspective projection. IV(strike, expiry, t) = ATM(t) + skew×moneyness + smile×moneyness²/√τ. ATM oscillates with time. 3D→2D: rotate Y axis by mouse X position, then perspective divide by (rz+5). Quads sorted back-to-front (painter\'s algorithm). Color = HSL mapped from IV (low=green, high=red).',
      tags: ['Canvas', '3D Perspective', 'Options', 'IV Surface', 'Smile'],
    },
    {
      id: 'viz_entropy',
      category: 'viz',
      name: '#15 — Entropy Cascade',
      icon: '🌊',
      desc: 'Time-frequency waterfall showing market entropy across 24 frequency bands (from 1-minute to 1-year) over time. Blue = structured/predictable; red = chaotic/random.',
      source: 'Locally simulated entropy matrix (frequency-dependent base entropy + time evolution).',
      how: 'Canvas 2D. 60×24 matrix of entropy values ∈ [0,1]. Each frame shifts matrix left, adds new column. New column = base_entropy[band] + noise. Entropy spikes inserted every ~120 frames. Color: HSL hue = 240 − e×240 (blue→green→red). History line at top shows average entropy over time.',
      tags: ['Canvas', 'Entropy', 'Time-Frequency', 'Waterfall'],
    },
    {
      id: 'viz_treemap',
      category: 'viz',
      name: '#16 — Portfolio Treemap',
      icon: '🌳',
      desc: '11-asset portfolio displayed as nested rectangles where area = portfolio weight and color = PnL. Green = profit, red = loss. Hover for exact weight and return. PnL slowly drifts.',
      source: 'Hardcoded portfolio weights + locally simulated PnL drift (updates every 90 frames).',
      how: 'Canvas 2D. Simplified squarified treemap layout: assets sorted by weight descending, packed row-by-row alternating horizontal/vertical split. Cell color: positive PnL = hsl(120, saturation∝|PnL|, lightness∝|PnL|). Negative = hsl(0, …). Labels sized proportional to cell width. Weighted PnL = Σ(weight × pnl).',
      tags: ['Canvas', 'Treemap', 'Portfolio', 'Allocation', 'Interactive'],
    },
    {
      id: 'viz_candle',
      category: 'viz',
      name: '#17 — Candle River',
      icon: '🕯',
      desc: 'Continuously streaming OHLCV candlestick chart with volume bars and MA20 overlay. New candles are generated locally and scroll from right to left.',
      source: 'Locally generated candle stream (GBM with OHLC spread).',
      how: 'Canvas 2D. Candles scroll left at 0.4px/frame. New candle generated when offset exceeds cellWidth: open=last close, close=open×(1+dir×rand), high/low=±spread. Price scale = dynamic min/max of visible window. Volume bars below. MA20 = trailing 20-bar close average, rendered as gold line. Bull=green, Bear=red.',
      tags: ['Canvas', 'Candlestick', 'OHLCV', 'Volume', 'Streaming'],
    },
    {
      id: 'viz_factorwheel',
      category: 'viz',
      name: '#18 — Factor Wheel',
      icon: '⚙',
      desc: '12 assets arranged around a rotating wheel with 4 concentric rings representing PCA factors. Each asset\'s dot position on each ring shows its loading on that factor. Active factor cycles every 3 seconds.',
      source: 'Synthetic PCA loading matrix (randomly generated, stable per session).',
      how: 'Canvas 2D. 4 rings at radii R×(f+1)/4. 12 assets at evenly spaced angles, rotating slowly. For each asset-factor pair, a dot is placed at: radius = ringR + |loading|×14, dotAngle = assetAngle + loading×0.3. Dot size = 3 + |loading|×4. Active factor ring highlighted with increased opacity and line weight.',
      tags: ['Canvas', 'Factor Model', 'PCA', 'Loadings', 'Animated'],
    },
    {
      id: 'viz_drawdown',
      category: 'viz',
      name: '#19 — Drawdown Mountain',
      icon: '⛰',
      desc: 'Dual-panel visualization: equity curve (top) shows portfolio growth, and the underwater drawdown mountain (bottom) shows how far below the peak the portfolio has fallen at each point.',
      source: 'Locally simulated 600-day equity curve (GBM walk).',
      how: 'Canvas 2D. Equity curve: price series from GBM. Drawdown series: DD(t) = (price(t) − peak(t)) / peak(t) ≤ 0, where peak(t) = max(price[0..t]). Top panel renders equity with blue gradient fill. Bottom panel renders |drawdown| as red mountain fill (y-axis inverted). Max DD dashed line labeled. Panels share the same x-axis scale.',
      tags: ['Canvas', 'Drawdown', 'Equity Curve', 'Risk'],
    },
    {
      id: 'viz_spread',
      category: 'viz',
      name: '#20 — Bid-Ask Spread Live',
      icon: '↔',
      desc: 'Liquidity monitor for 8 assets showing real-time bid-ask spread in basis points, historical sparklines, and estimated market impact. Alerts flash when spreads widen significantly.',
      source: 'Locally simulated spread dynamics (base spreads vary by asset class).',
      how: 'Canvas 2D. Spread updates every 5 frames: target = base_spread×(1 + rand(−0.4, 0.8)); current lerps toward target at 0.12. Spread widening event injected every ~200 frames (×2–4 multiplier). Bar width = (bps/maxBps) × barMaxW. Sparkline = last 120 spread values. Market impact ≈ spread × √(order_size/ADV) (Almgren-Chriss simplified).',
      tags: ['Canvas', 'Spread', 'Liquidity', 'Market Impact', 'L2'],
    },

    // ── Sphere-inspired Particle Visualizations (#21–#23) ──────────────────
    {
      id: 'viz_psaturn',
      category: 'viz',
      name: '#21 — Particle Saturn',
      icon: '🪐',
      desc: 'Fifteen thousand particles arranged in a Saturn-like formation: a central sphere with a glowing equatorial ring. Move your cursor over the canvas to push particles away — they snap back when you leave.',
      source: 'Fully local — no data feed. Inspired by sphere-main (React Three Fiber) adapted to vanilla Three.js.',
      how: 'Three.js Points geometry, 15 000 particles. Inner sphere: uniform spherical distribution (φ = arccos(2r−1), θ = 2πr). Ring: r = 3.5 + rand×1.5, y flattened by ×0.15. Mouse position projected to scene Z=0 plane (NDC→world: x = NDC×7.5). Repulsion: if dist < 3.8, push = (1 − dist/R) × 1.3 in −direction. Particle lerps back to target at rate 0.08/frame. Additive blending (color: #ffdf7e).',
      tags: ['Three.js', 'WebGL', 'Particles', 'Interactive', 'Saturn', '15k'],
    },
    {
      id: 'viz_pheart',
      category: 'viz',
      name: '#22 — Particle Heart',
      icon: '❤',
      desc: 'Fifteen thousand golden-pink particles forming a heart shape. Symbolises a strong bull-market signal. Cursor interaction pushes particles off the heart outline — releasing them causes them to flutter back.',
      source: 'Fully local — no data feed. Heart parametric formula from sphere-main.',
      how: 'Three.js Points, 15 000 particles. Heart: x = 0.22×(16 sin³t), y = 0.22×(13 cos t − 5 cos 2t − 2 cos 3t − cos 4t), z = rand×1.5. t ∈ [0, 2π] uniform random. Same cursor repulsion algorithm as #21. Color: #ff5577 (rose). Additive blending for glow effect.',
      tags: ['Three.js', 'WebGL', 'Particles', 'Heart', 'Interactive', 'Bull Signal'],
    },
    {
      id: 'viz_pmorph',
      category: 'viz',
      name: '#23 — Particle Morph',
      icon: '✨',
      desc: 'All three shapes (Saturn, Heart, Sphere) in a single visualization. Every 4 seconds the 15 000 particles smoothly morph into the next shape. Cursor pushes particles off their trajectory during the transition. Click shape buttons to morph on demand.',
      source: 'Fully local — no data feed. Combines all three generators from #21–#22.',
      how: 'Shared _particleShapeViz() helper. Auto-cycles shapes via morphTimer (4 000 ms). On each shape change: targetPositions replaced with new Float32Array from generator; material.color set to shape colour (#ffdf7e/#ff5577/#88ccff). Per-frame: particles lerp from current pos toward (rotated) target at 0.08/frame. Rotation accumulates at 0.003 rad/frame. Cursor repulsion applied before lerp. All in requestAnimationFrame.',
      tags: ['Three.js', 'WebGL', 'Particles', 'Morph', 'Interactive', 'Saturn', 'Heart', 'Sphere'],
    },

    // ── Nexus Core Particle System (#24–#28) ──────────────────────────────
    {
      id: 'viz_pmobius',
      category: 'viz',
      name: '#24 — Möbius Strip',
      icon: '∞',
      desc: 'Fifty thousand particles arranged on a Möbius band — a single-sided non-orientable surface. Drag to orbit. Click topology buttons to morph into any of the 5 Nexus shapes. Color palette and morph speed sliders included.',
      source: 'Fully local — no data feed. Adapted from nexus-core-particle-system (React Three Fiber → vanilla Three.js).',
      how: 'Three.js Points with 50 000 particles. Möbius: for t ∈ [0,1], u = 4πt; v = rand∈[−1,1]; x = (R + v·cos(u/2))·cos u; y = (R + v·cos(u/2))·sin u; z = v·sin(u/2). R=3. Morphing uses frame-rate-independent lerp: factor = 1 − exp(−speed · dt · 5). Shapes pre-cached as Float32Array at init to avoid recomputation. Auto-rotates at 0.1 rad/s; drag overrides rotation.',
      tags: ['Three.js', 'WebGL', 'Particles', 'Möbius', '50k', 'Topology', 'Nexus', 'Morphing'],
    },
    {
      id: 'viz_ptoroidal',
      category: 'viz',
      name: '#25 — Toroidal Vortex',
      icon: '🍩',
      desc: 'Fifty thousand particles on a knotted torus with ripple surface deformation. The torus represents cyclic market regimes — trending, reverting, trending again. Drag to orbit, use sliders to control morph speed and particle size.',
      source: 'Fully local — no data feed. Adapted from nexus-core-particle-system.',
      how: 'Toroidal: u,v ∈ [0,2π] uniform random; R=3; r = 1 + 0.2·sin(8u)·cos(4v) (ripple). x = (R+r·cos v)·cos u; y = (R+r·cos v)·sin u; z = r·sin v. Same lerp engine as #24. Default color: magenta (#ff00ff) for volatility-spike visual language.',
      tags: ['Three.js', 'WebGL', 'Particles', 'Torus', '50k', 'Topology', 'Nexus'],
    },
    {
      id: 'viz_pspherical',
      category: 'viz',
      name: '#26 — Spherical Harmonics',
      icon: '🔮',
      desc: 'Fifty thousand particles on a bumpy sphere defined by spherical harmonic deformation. The bumps represent multi-factor volatility surface — smooth = calm, spiky = stressed. Color: deep blue (#4499ff).',
      source: 'Fully local — no data feed. Adapted from nexus-core-particle-system.',
      how: 'Spherical harmonics: θ = arccos(2r−1), φ = 2πr (uniform sphere sampling); r = 3 + 1.5·sin(4φ)·sin(5θ). Standard sphere point-in-sphere distribution ensures even surface coverage. Same lerp/orbit engine. Analogy: the IV surface in options pricing has similar non-spherical deformation geometry.',
      tags: ['Three.js', 'WebGL', 'Particles', 'Sphere', 'Harmonics', '50k', 'Nexus', 'Volatility'],
    },
    {
      id: 'viz_plissajous',
      category: 'viz',
      name: '#27 — Lissajous 3D',
      icon: '〰',
      desc: 'Fifty thousand particles tracing 3D Lissajous curves — the superposition of three sinusoids at different frequencies. Represents multi-timeframe signal interference: hourly, daily, and weekly cycles layered.',
      source: 'Fully local — no data feed. Adapted from nexus-core-particle-system.',
      how: 'Lissajous: for i ∈ [0,N), u = (i/N)·200π; x = 4·sin(3u) + ε; y = 4·sin(2u+π/4) + ε; z = 4·sin(5u) + ε. Noise ε ∈ ±0.18 adds particle spread. Frequency ratios 3:2:5 create Lissajous figures that never exactly repeat — like price action at different timeframes. Color: amber (#ffaa00).',
      tags: ['Three.js', 'WebGL', 'Particles', 'Lissajous', '50k', 'Nexus', 'Sinusoid', 'Signal'],
    },
    {
      id: 'viz_plorenzp',
      category: 'viz',
      name: '#28 — Lorenz Attractor 3D',
      icon: '🌀',
      desc: 'Fifty thousand particles tracing the Lorenz strange attractor — the canonical example of deterministic chaos. The butterfly shape visualises how small differences in initial conditions (regime or sentiment) produce wildly divergent paths.',
      source: 'Fully local — no data feed. Adapted from nexus-core-particle-system.',
      how: 'Lorenz: σ=10, ρ=28, β=8/3. Each particle i integrates from the previous state (lx,ly,lz) with dt=0.005: dx=σ(y−x)dt; dy=(xρ−xz−y)dt; dz=(xy−βz)dt. Scaled by 0.22; z centred by −28. This is the same equation Atlas\'s 2D Lorenz viz uses, but here expressed as 50k sequential points on the attractor curve, revealing the fractal folding structure in 3D. Color: neon-green (#44ff88).',
      tags: ['Three.js', 'WebGL', 'Particles', 'Lorenz', 'Chaos', '50k', 'Attractor', 'Nexus'],
    },
    {
      id: 'viz_speedracer',
      category: 'viz',
      name: '#29 — DQN Speed Racer',
      icon: '🏎',
      desc: 'A simulated Deep Q-Network agent learning to lap an oval track in real time. Watch epsilon decay from 1.0 (random) to 0.05 (expert), the training loss curve converge, and the car transition from crashing erratically to clean hot laps.',
      source: 'Fully local simulation. Inspired by speed-racer-rl-main (C++ DQN, libtorch, SDL2). Adapted to Canvas 2D without pre-trained weights.',
      how: 'State: 5 LIDAR rays at −70/−35/0/+35/+70° from heading, normalized to [0,1]. Actions: turn-left, straight, turn-right. Q-values simulated: qStr ≈ skillLevel·frontRay + (1−skill)·rand where skill=1−ε. Policy: argmax Q with ε-greedy exploration. Car speed adapts: crash detected when minRay<0.22 → speed decay + reward penalty. Episode ends after epLen steps ∝ skill. Each episode: lossHistory.push(1.4·exp(−ep·0.018)+noise), rewardHistory updated. ε ×= 0.94 per episode → inference mode at ep>80. Canvas 2D rendering: oval track via ctx.ellipse(), car as roundRect, LIDAR rays, Q-value bar chart, loss+reward dual curve.',
      tags: ['Canvas', 'DQN', 'RL', 'Q-Learning', 'Simulation', 'Racing', 'Speed-Racer'],
    },

    /* ══════════════════════ AI / ML ══════════════════════ */
    {
      id: 'aria',
      category: 'ai',
      name: 'ARIA — AI Research & Intelligence Agent',
      icon: '🤖',
      desc: 'The conversational AI core of Atlas. ARIA answers financial questions, fetches live data, runs backtests, and explains signals — all powered by a local LLM. Zero cloud dependency.',
      source: 'Ollama local LLM server. User messages → FastAPI /query → Ollama → tool calls → Python handlers → response.',
      how: 'System prompt instructs ARIA to respond in JSON when triggering tools: {tool, params}. The Python server intercepts tool calls and routes them to registered handlers: get_data (yfinance), get_market_state, analyze_risk, run_backtest, explain_signal, run_simulation. Results injected back into context. Streams via WebSocket /ws/{session_id} for real-time output.',
      tags: ['LLM', 'Tool Calling', 'Local', 'Conversational', 'Ollama'],
    },
    {
      id: 'ml_adapter',
      category: 'ai',
      name: 'ML Signal Adapter (Bridge)',
      icon: '🔌',
      desc: 'A bridge layer that wraps untrained ML models (XGBoost, LSTM, RandomForest) and connects them to Atlas\'s signal engine. Returns HOLD when models are not yet trained.',
      source: 'Atlas feature pipeline (lowercase OHLCV) feeding into ML model predict().',
      how: 'MLSignalAdapter normalizes column names (Capitalize→lowercase) before calling FeaturePipeline. FeaturePipeline computes technical features. If model.is_trained is False or predict() raises, returns Signal(action=HOLD, confidence=0.0). MLAgentBridge is a factory: bridge.get_adapter("xgboost") returns the appropriate adapter with lazy imports (missing packages never crash).',
      tags: ['ML', 'XGBoost', 'LSTM', 'RandomForest', 'Bridge', 'Lazy Import'],
    },
    {
      id: 'rl_agent',
      category: 'ai',
      name: 'RL Trading Agent (DQN)',
      icon: '🕹',
      desc: 'A Deep Q-Network reinforcement learning agent that learns to trade by interacting with a simulated market environment. Uses experience replay and target network for stable training.',
      source: 'Historical OHLCV data forms the environment. Reward = daily portfolio return.',
      how: 'State space: 13 features (OHLCV ratios, RSI, MACD, position, cash ratio). Action space: 7 discrete actions (BUY_10%, BUY_25%, BUY_50%, HOLD, SELL_10%, SELL_25%, SELL_ALL). Q-network: 2-layer MLP (128→64). Experience replay buffer of 10,000 transitions. Target network updated every 100 steps. ε-greedy exploration: ε decays 1.0→0.01 over training. Untrained → always HOLD.',
      tags: ['RL', 'DQN', 'Q-Network', 'Experience Replay', 'PyTorch'],
    },

    /* ══════════════════════ INFRASTRUCTURE ══════════════════════ */
    {
      id: 'backtest',
      category: 'infra',
      name: 'Backtest Runner (Walk-Forward)',
      icon: '⏪',
      desc: 'Simulates strategy performance on historical data. Produces equity curve, Sharpe ratio, maximum drawdown, and win rate without look-ahead bias.',
      source: 'Historical OHLCV from yfinance (or synthetic fallback).',
      how: 'For each bar: run strategy engine on data up to and including that bar. If signal = LONG and not in position → BUY at next open. If signal = SHORT/HOLD and in position → SELL at next open. Equity = initial_capital × Π(1 + daily_ret). Sharpe = mean(daily_ret) / std(daily_ret) × √252. MaxDD = max((peak−equity)/peak). All computed in pure Python with no data peeking forward.',
      tags: ['Backtest', 'Equity Curve', 'Sharpe', 'Walk-Forward'],
      api: '/api/strategy/backtest/{ticker}',
    },
    {
      id: 'monte_carlo_engine',
      category: 'infra',
      name: 'Monte Carlo Engine (GBM + Extensions)',
      icon: '🎰',
      desc: 'Server-side path simulation engine supporting multiple stochastic processes: standard GBM, Heston stochastic volatility, and Jump-Diffusion (Merton model).',
      source: 'Parameters estimated from historical returns (μ, σ) or user-specified.',
      how: 'GBM: dS = μSdt + σSdW. Heston: stochastic vol with mean-reversion κ(θ−v)dt + ξ√v dW_v; corr(dW_S, dW_v) = ρ. Jump-Diffusion: GBM + Poisson jumps with normal jump size distribution N(μ_J, σ_J). Variance reduction: antithetic variates (simulate dW and −dW pairs). Returns P5/P50/P95 percentile bands from N paths.',
      tags: ['Monte Carlo', 'GBM', 'Heston', 'Jump-Diffusion', 'Paths'],
      api: '/api/vizlab/montecarlo/{ticker}',
    },
    {
      id: 'discrepancy',
      category: 'infra',
      name: 'Discrepancy Analyzer',
      icon: '⚖',
      desc: 'Measures how much the 5 strategy engines disagree with each other. High discrepancy = engines are conflicted → reduce position size. Low discrepancy = engines aligned → higher confidence.',
      source: 'Output of all 5 strategy engines run on the same OHLCV data.',
      how: 'Maps actions to numeric values (LONG=1, HOLD=0, SHORT=−1). Discrepancy score = standard deviation of all engine actions. Level: < 0.3 = LOW, 0.3–0.6 = MEDIUM, > 0.6 = HIGH. Outlier detection: engines whose signal deviates > 1.5σ from the group mean are flagged as outliers. Recommended action = modal action of non-outlier engines.',
      tags: ['Discrepancy', 'Signal Quality', 'Agreement', 'Risk'],
      api: '/api/discrepancy/{ticker}',
    },
    {
      id: 'data_layer',
      category: 'infra',
      name: 'Data Layer (Cache + Normalize)',
      icon: '💾',
      desc: 'Manages all data fetching, caching, and normalization. Prevents redundant API calls and ensures consistent column formats across all analysis modules.',
      source: 'Primary: yfinance. Cache: local filesystem (JSON/Parquet). Fallback: synthetic GBM.',
      how: 'Fetched data cached locally by (ticker, period, date) key. Cache TTL = 1 day for historical, 5 minutes for intraday. Column normalization: yfinance returns capitalized (Open/High/Low/Close/Volume) → rule-based engines consume capitalized columns; FeaturePipeline (ML layer) expects lowercase → MLSignalAdapter normalizes at boundary. Point-in-time manager prevents future data leaking into historical analysis.',
      tags: ['Cache', 'Normalize', 'Point-in-Time', 'Data Pipeline'],
    },
    {
      id: 'server',
      category: 'infra',
      name: 'FastAPI Server',
      icon: '⚡',
      desc: 'The central API server that connects the JavaScript UI to all Python backend modules. Serves static files, handles REST requests, manages WebSocket sessions, and routes all data flows.',
      source: 'Python FastAPI running on port 8088. Launch: python run_atlas.py',
      how: 'Startup: loads config, initializes ARIA session store, registers all API routes. Static files: serves apps/desktop/ directly. API routes: grouped by module (strategy, correlation, vizlab, chaos, volatility, factors, discrepancy). WebSocket /ws/{session_id} streams ARIA responses. CORS: localhost only. All Python modules are lazily imported inside route handlers via _add_sys_path().',
      tags: ['FastAPI', 'REST', 'WebSocket', 'Python', 'Server'],
    },
  ];

  /* ─────────────────────────────────────────────────────────
     STATE
  ───────────────────────────────────────────────────────── */
  let _query    = '';
  let _category = 'all';

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
  };

  function _catColor(cat) {
    return CAT_COLORS[cat] || CAT_COLORS['infra'];
  }

  function _filteredItems() {
    return ITEMS.filter(item => {
      const matchCat = _category === 'all' || item.category === _category;
      if (!matchCat) return false;
      if (!_query) return true;
      const q = _query.toLowerCase();
      return (
        item.name.toLowerCase().includes(q) ||
        item.desc.toLowerCase().includes(q) ||
        item.tags.some(t => t.toLowerCase().includes(q)) ||
        item.how.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
      );
    });
  }

  /* ─────────────────────────────────────────────────────────
     RENDER
  ───────────────────────────────────────────────────────── */
  function _renderCategoryTabs(container) {
    const tabRow = container.querySelector('#info-cat-tabs');
    if (!tabRow) return;
    tabRow.innerHTML = CATEGORIES.map(c => {
      const count = c.id === 'all' ? ITEMS.length : ITEMS.filter(i => i.category === c.id).length;
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
      grid.innerHTML = `<div class="info-empty">
        <div style="font-size:2rem;margin-bottom:8px;">🔍</div>
        <div>No results for "<strong>${_escHtml(_query)}</strong>"</div>
        <div style="color:#555;margin-top:6px;font-size:11px;">Try a different keyword or category</div>
      </div>`;
      return;
    }

    grid.innerHTML = items.map(item => {
      const col = _catColor(item.category);
      const catLabel = CATEGORIES.find(c => c.id === item.category)?.label || item.category;
      const tagsHtml = item.tags.map(t =>
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
      countEl.textContent = `${n} ${n === 1 ? 'entry' : 'entries'}`;
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
  }

  function init() {
    // Inject styles
    _injectStyles();
    // Initial render
    _render();
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
