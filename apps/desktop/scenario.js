
/**
 * Scenario Mode Logic
 * Handles the interactive "Time Machine" simulation.
 */

let currentSessionId = null;
let currentTicker = "SPY";
let initialCapital = 10000;
let autoPlayInterval = null;

// DOM Elements
const startBtn = document.getElementById('start-scenario-btn');
const nextBtn = document.getElementById('next-step-btn');
const autoPlayBtn = document.getElementById('auto-play-btn');
const restartBtn = document.getElementById('restart-scenario-btn');
const statusLabel = document.getElementById('scenario-status');
const tickerInput = document.getElementById('sim-ticker'); // NEW

const elDate = document.getElementById('scen-date');
const elPrice = document.getElementById('scen-price');
const elPortfolio = document.getElementById('scen-portfolio');
const elPnL = document.getElementById('scen-pnl'); // NEW
const elLog = document.getElementById('scen-log');
const elNewsLog = document.getElementById('scen-news-log');
const elMcStats = document.getElementById('scen-mc-stats');
const elDecisionBreakdown = document.getElementById('scen-decision-breakdown');
const scenMcCanvas = document.getElementById('scen-mc-canvas');
const scenDecisionCanvas = document.getElementById('scen-decision-canvas');

// Eval Bar Elements
const elEvalBarFill = document.getElementById('eval-bar-fill');
const elEvalScore = document.getElementById('eval-score');

// Chart Elements
const scenChartContainer = document.getElementById('scen-chart-container');
let scenChart = null;
let scenCandleSeries = null;
let scenData = []; // Store accumulated OHLC data for the chart
let scenPortfolioHistory = [];
let scenReturnHistory = [];
let scenDecisionHistory = [];

function initScenChart() {
    if (!scenChartContainer) return;

    scenChart = LightweightCharts.createChart(scenChartContainer, {
        width: scenChartContainer.clientWidth,
        height: scenChartContainer.clientHeight,
        layout: {
            background: { type: 'solid', color: 'white' },
            textColor: 'black',
        },
        grid: {
            vertLines: { color: '#f0f0f0' },
            horzLines: { color: '#f0f0f0' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#cccccc',
        },
        timeScale: {
            borderColor: '#cccccc',
            timeVisible: true,
        },
    });
    scenCandleSeries = scenChart.addCandlestickSeries({
        upColor:   '#4caf50',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor:   '#4caf50',
        wickDownColor: '#ef5350',
    });
    // Resizer
    new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== scenChartContainer) { return; }
        if (scenChart) {
            const newRect = entries[0].contentRect;
            scenChart.applyOptions({ width: newRect.width, height: newRect.height });
        }
    }).observe(scenChartContainer);
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function randomNormal(mu = 0, sigma = 1) {
    let u = 0;
    let v = 0;
    while (u === 0) u = Math.random();
    while (v === 0) v = Math.random();
    const z = Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    return mu + z * sigma;
}

function parseConfidenceFromReasoning(reasoning) {
    if (!Array.isArray(reasoning)) return 0.5;
    for (const line of reasoning) {
        const m = line.match(/Conf:\s*(\d+)%/i);
        if (m) return clamp(Number(m[1]) / 100, 0, 1);
    }
    return 0.5;
}

function resetScenarioAnalytics() {
    scenPortfolioHistory = [];
    scenReturnHistory = [];
    scenDecisionHistory = [];

    if (elMcStats) elMcStats.textContent = "Waiting for data...";
    if (elDecisionBreakdown) elDecisionBreakdown.textContent = "Waiting for first decision...";

    if (scenMcCanvas) {
        const ctx = scenMcCanvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, scenMcCanvas.width, scenMcCanvas.height);
    }
    if (scenDecisionCanvas) {
        const ctx = scenDecisionCanvas.getContext('2d');
        if (ctx) ctx.clearRect(0, 0, scenDecisionCanvas.width, scenDecisionCanvas.height);
    }
}

function runMonteCarloProjection(currentValue, returnHistory, horizon = 20, paths = 300) {
    const usable = returnHistory.slice(-120);
    const mu = usable.length > 0 ? usable.reduce((s, r) => s + r, 0) / usable.length : 0;
    const variance = usable.length > 1
        ? usable.reduce((s, r) => s + (r - mu) * (r - mu), 0) / (usable.length - 1)
        : 0.0001;
    const sigma = Math.max(Math.sqrt(Math.max(variance, 0.000001)), 0.004);

    const samplesByStep = Array.from({ length: horizon + 1 }, () => []);
    for (let p = 0; p < paths; p++) {
        let value = currentValue;
        samplesByStep[0].push(value);
        for (let t = 1; t <= horizon; t++) {
            value *= (1 + randomNormal(mu, sigma));
            samplesByStep[t].push(value);
        }
    }

    function percentile(arr, q) {
        const sorted = [...arr].sort((a, b) => a - b);
        const idx = clamp(Math.floor((sorted.length - 1) * q), 0, sorted.length - 1);
        return sorted[idx];
    }

    const p05 = [];
    const p50 = [];
    const p95 = [];
    const mean = [];

    for (let t = 0; t <= horizon; t++) {
        const step = samplesByStep[t];
        p05.push(percentile(step, 0.05));
        p50.push(percentile(step, 0.50));
        p95.push(percentile(step, 0.95));
        mean.push(step.reduce((s, v) => s + v, 0) / step.length);
    }

    const terminal = samplesByStep[horizon];
    const winProb = terminal.filter(v => v > currentValue).length / terminal.length;
    const drop10Prob = terminal.filter(v => v < currentValue * 0.9).length / terminal.length;

    return { horizon, p05, p50, p95, mean, winProb, drop10Prob, mu, sigma };
}

function computeBacktestMetrics(portfolioHistory) {
    if (portfolioHistory.length < 2) {
        return { cumReturn: 0, sharpe: 0, maxDD: 0, vol: 0 };
    }
    const initial = portfolioHistory[0];
    const last = portfolioHistory[portfolioHistory.length - 1];
    const cumReturn = (last / initial) - 1;

    const returns = [];
    for (let i = 1; i < portfolioHistory.length; i++) {
        const prev = portfolioHistory[i - 1];
        const curr = portfolioHistory[i];
        if (prev > 0) returns.push((curr - prev) / prev);
    }

    const mean = returns.length ? returns.reduce((s, r) => s + r, 0) / returns.length : 0;
    const variance = returns.length > 1
        ? returns.reduce((s, r) => s + (r - mean) * (r - mean), 0) / (returns.length - 1)
        : 0;
    const vol = Math.sqrt(Math.max(variance, 0));
    const sharpe = vol > 0 ? (mean / vol) * Math.sqrt(252) : 0;

    let peak = initial;
    let maxDD = 0;
    for (const v of portfolioHistory) {
        peak = Math.max(peak, v);
        const dd = (v - peak) / peak;
        maxDD = Math.min(maxDD, dd);
    }

    return { cumReturn, sharpe, maxDD, vol };
}

function drawMonteCarloCanvas(proj) {
    if (!scenMcCanvas || !proj) return;
    const ctx = scenMcCanvas.getContext('2d');
    if (!ctx) return;

    const width = Math.max(520, Math.floor(scenMcCanvas.getBoundingClientRect().width || 620));
    const height = 220;
    if (scenMcCanvas.width !== width || scenMcCanvas.height !== height) {
        scenMcCanvas.width = width;
        scenMcCanvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#101828';
    ctx.fillRect(0, 0, width, height);

    const m = { l: 52, t: 14, r: 12, b: 28 };
    const plotW = width - m.l - m.r;
    const plotH = height - m.t - m.b;
    const yMin = Math.min(...proj.p05);
    const yMax = Math.max(...proj.p95);
    const yRange = Math.max(1, yMax - yMin);

    const x = i => m.l + (i / proj.horizon) * plotW;
    const y = v => m.t + (1 - ((v - yMin) / yRange)) * plotH;

    ctx.strokeStyle = '#2a3e5f';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const gy = m.t + (i / 4) * plotH;
        ctx.beginPath();
        ctx.moveTo(m.l, gy);
        ctx.lineTo(m.l + plotW, gy);
        ctx.stroke();
    }

    ctx.fillStyle = 'rgba(56, 119, 234, 0.20)';
    ctx.beginPath();
    ctx.moveTo(x(0), y(proj.p95[0]));
    for (let i = 1; i <= proj.horizon; i++) ctx.lineTo(x(i), y(proj.p95[i]));
    for (let i = proj.horizon; i >= 0; i--) ctx.lineTo(x(i), y(proj.p05[i]));
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = '#63c5ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(x(0), y(proj.p50[0]));
    for (let i = 1; i <= proj.horizon; i++) ctx.lineTo(x(i), y(proj.p50[i]));
    ctx.stroke();

    ctx.strokeStyle = '#7f8fa6';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(x(0), y(proj.mean[0]));
    for (let i = 1; i <= proj.horizon; i++) ctx.lineTo(x(i), y(proj.mean[i]));
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = '#9ab0cc';
    ctx.font = '10px Inter, Arial, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText('Today', x(0), height - 8);
    ctx.textAlign = 'right';
    ctx.fillText(`+${proj.horizon}d`, x(proj.horizon), height - 8);
}

function computeDecisionFactors(state) {
    const sma200 = Number(state?.indicators?.SMA_200 || state?.price || 1);
    const rsi = Number(state?.indicators?.RSI || 50);
    const trend = clamp(((state.price - sma200) / Math.max(1, sma200)) * 8, -1, 1);
    const rsiScore = clamp((50 - rsi) / 25, -1, 1);

    let momentum = 0;
    if (scenData.length > 1) {
        const prev = scenData[scenData.length - 2].close;
        momentum = clamp(((state.price - prev) / Math.max(1, prev)) * 20, -1, 1);
    }

    let newsScore = 0;
    const reasoning = Array.isArray(state.reasoning) ? state.reasoning.join(' ').toLowerCase() : '';
    if (reasoning.includes('news')) newsScore = 0.15;
    if (reasoning.includes('crash') || reasoning.includes('selling')) newsScore = -0.25;
    if (reasoning.includes('rally') || reasoning.includes('breakthrough')) newsScore = 0.25;

    const exposure = clamp((state.holdings * state.price) / Math.max(1, state.portfolio_value), 0, 1);
    const riskPenalty = -exposure;

    const confidence = parseConfidenceFromReasoning(state.reasoning);
    const composite = (0.35 * trend) + (0.20 * rsiScore) + (0.20 * momentum) + (0.10 * newsScore) + (0.15 * riskPenalty);

    return {
        trend,
        rsi: rsiScore,
        momentum,
        news: newsScore,
        risk: riskPenalty,
        confidence,
        composite
    };
}

function drawDecisionFactorsCanvas(factors, state) {
    if (!scenDecisionCanvas || !factors) return;
    const ctx = scenDecisionCanvas.getContext('2d');
    if (!ctx) return;

    const width = Math.max(520, Math.floor(scenDecisionCanvas.getBoundingClientRect().width || 620));
    const height = 220;
    if (scenDecisionCanvas.width !== width || scenDecisionCanvas.height !== height) {
        scenDecisionCanvas.width = width;
        scenDecisionCanvas.height = height;
    }

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#101828';
    ctx.fillRect(0, 0, width, height);

    const entries = [
        ['Trend', factors.trend],
        ['RSI', factors.rsi],
        ['Momentum', factors.momentum],
        ['News', factors.news],
        ['Risk', factors.risk]
    ];

    const m = { l: 86, t: 16, r: 16, b: 24 };
    const plotW = width - m.l - m.r;
    const rowH = (height - m.t - m.b) / entries.length;
    const x0 = m.l + plotW / 2;

    ctx.strokeStyle = '#2a3e5f';
    ctx.beginPath();
    ctx.moveTo(x0, m.t);
    ctx.lineTo(x0, height - m.b);
    ctx.stroke();

    ctx.font = '11px Inter, Arial, sans-serif';
    entries.forEach((item, idx) => {
        const label = item[0];
        const value = clamp(item[1], -1, 1);
        const yMid = m.t + idx * rowH + rowH / 2;
        const barW = Math.abs(value) * (plotW / 2 - 8);
        const x = value >= 0 ? x0 : (x0 - barW);

        ctx.fillStyle = value >= 0 ? '#2ecc71' : '#ef5350';
        ctx.fillRect(x, yMid - 8, barW, 16);

        ctx.fillStyle = '#9ab0cc';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, m.l - 10, yMid);

        ctx.textAlign = value >= 0 ? 'left' : 'right';
        ctx.fillText(value.toFixed(2), value >= 0 ? (x + barW + 6) : (x - 6), yMid);
    });

    if (elDecisionBreakdown) {
        const action = (state.decision || 'hold').toUpperCase();
        const reasonLine = Array.isArray(state.reasoning)
            ? (state.reasoning.find(line => line.startsWith('Analyzed by:')) || '')
            : '';
        elDecisionBreakdown.textContent =
            `Action ${action} | Confidence ${(factors.confidence * 100).toFixed(0)}% | Composite ${(factors.composite).toFixed(2)}${reasonLine ? ` | ${reasonLine}` : ''}`;
    }
}

function updateScenarioAnalytics(state) {
    if (!state) return;

    const pv = Number(state.portfolio_value || 0);
    const prev = scenPortfolioHistory.length ? scenPortfolioHistory[scenPortfolioHistory.length - 1] : pv;
    scenPortfolioHistory.push(pv);
    if (prev > 0) scenReturnHistory.push((pv - prev) / prev);
    scenDecisionHistory.push(state.decision || 'hold');

    const backtest = computeBacktestMetrics(scenPortfolioHistory);
    const proj = runMonteCarloProjection(Math.max(1, pv), scenReturnHistory, 20, 300);
    drawMonteCarloCanvas(proj);

    if (elMcStats) {
        const terminalMid = proj.p50[proj.horizon];
        const terminalLo = proj.p05[proj.horizon];
        const terminalHi = proj.p95[proj.horizon];
        elMcStats.textContent =
            `WinProb ${(proj.winProb * 100).toFixed(1)}% | P05 ${terminalLo.toFixed(0)} | P50 ${terminalMid.toFixed(0)} | P95 ${terminalHi.toFixed(0)} | Backtest Ret ${(backtest.cumReturn * 100).toFixed(1)}% | MaxDD ${(backtest.maxDD * 100).toFixed(1)}% | Sharpe ${backtest.sharpe.toFixed(2)}`;
    }

    const factors = computeDecisionFactors(state);
    drawDecisionFactorsCanvas(factors, state);
}

// -------------------------------------------------------------
// Core Simulation Logic
// -------------------------------------------------------------


async function handleStartOrSwitch() {
    const ticker = tickerInput.value.toUpperCase() || "SPY";

    if (!currentSessionId) {
        // Start New Session
        await startScenario(ticker);
    } else {
        await switchTicker(ticker);
    }
}

async function startScenario(ticker) {
    startBtn.disabled = true;
    statusLabel.textContent = `Loading ${ticker}...`;

    // Clear logs
    elLog.innerHTML = `<div class="log-entry">--- SIMULATION STARTED ---\nInitial Capital: $10,000</div>`;
    elNewsLog.innerHTML = `<div class="log-entry" style="color:#aaa;">No news loaded.</div>`;
    scenData = [];
    resetScenarioAnalytics();
    if (scenCandleSeries) scenCandleSeries.setData([]);
    stopAutoPlay();

    try {
        const res = await fetch(`${CONFIG.serverUrl}/api/scenario/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ticker: ticker,
                start_date: '2020-01-01',
                initial_capital: 10000
            })
        });

        if (!res.ok) throw new Error("Failed to start");

        const data = await res.json();
        currentSessionId = data.session_id;
        currentTicker = data.ticker;
        initialCapital = 10000; // Reset

        // Init Chart if needed
        if (!scenChart) initScenChart();

        // Process Initial State
        processStep(data.initial_state);

        startBtn.textContent = "Switch Ticker"; // UPDATED
        startBtn.disabled = false;
        nextBtn.disabled = false;
        autoPlayBtn.disabled = false;
        if (restartBtn) restartBtn.disabled = false;
        statusLabel.textContent = "Active";

    } catch (e) {
        alert("Error starting scenario: " + e.message);
        statusLabel.textContent = "Connection Error";
        startBtn.textContent = "Start New Simulation";
        startBtn.disabled = false;
        if (restartBtn) restartBtn.disabled = true;
    }
}

async function switchTicker(ticker) {
    if (ticker === currentTicker) return;

    statusLabel.textContent = `Switching to ${ticker}...`;
    startBtn.disabled = true;

    try {
        const response = await fetch(`${CONFIG.serverUrl}/api/scenario/switch_ticker`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: currentSessionId,
                ticker: ticker
            })
        });

        if (response.ok) {
            currentTicker = ticker;
            statusLabel.textContent = "Active";
            // Clear chart for new ticker
            scenData = [];
            resetScenarioAnalytics();
            if (scenCandleSeries) scenCandleSeries.setData([]);
            // The backend should return the current state after switching,
            // but for now, we'll just clear and wait for nextStep to populate.
            // If the backend returns the current state, we'd call processStep(data.state) here.
        } else {
            const errorData = await response.json();
            statusLabel.textContent = `Switch Failed: ${errorData.error || response.statusText}`;
        }
    } catch (e) {
        console.error("Error switching ticker:", e);
        statusLabel.textContent = "Error";
    } finally {
        startBtn.disabled = false;
    }
}

async function nextStep() {
    if (!currentSessionId) return;

    try {
        const res = await fetch(`${CONFIG.serverUrl}/api/scenario/${currentSessionId}/next`, { method: 'POST' });
        const data = await res.json();

        if (data.status === 'finished') {
            stopAutoPlay();
            alert("Simulation Finished!");
            nextBtn.disabled = true;
            autoPlayBtn.disabled = true;
            statusLabel.textContent = "Completed";
            return;
        }

        processStep(data.state);

    } catch (e) {
        console.error(e);
        stopAutoPlay();
    }
}

let isPlaying = false;
function toggleAutoPlay() {
    if (isPlaying) {
        stopAutoPlay();
    } else {
        isPlaying = true;
        autoPlayBtn.textContent = "⏸ Pause";
        autoPlayBtn.classList.add("primary");
        autoPlayBtn.classList.remove("secondary");

        // Auto Play Loop (800ms per day)
        autoPlayInterval = setInterval(() => {
            if (!nextBtn.disabled) nextStep();
        }, 800);
    }
}

function stopAutoPlay() {
    isPlaying = false;
    autoPlayBtn.textContent = "▶ Auto Play";
    autoPlayBtn.classList.remove("primary");
    autoPlayBtn.classList.add("secondary");
    if (autoPlayInterval) clearInterval(autoPlayInterval);
}

function resetScenarioUI() {
    currentSessionId = null;
    currentTicker = tickerInput.value.toUpperCase() || "SPY";
    initialCapital = 10000;
    stopAutoPlay();
    scenData = [];
    resetScenarioAnalytics();
    if (scenCandleSeries) scenCandleSeries.setData([]);
    if (elDate) elDate.textContent = "-";
    if (elPrice) elPrice.textContent = "-";
    if (elPortfolio) elPortfolio.textContent = "-";
    const elHoldings = document.getElementById('scen-holdings');
    if (elHoldings) elHoldings.textContent = "-";
    if (elEvalBarFill) elEvalBarFill.style.width = "50%";
    if (elEvalScore) elEvalScore.textContent = "0.0 (Break Even)";
    if (elLog) elLog.innerHTML = `<div class="log-entry">Waiting to start...</div>`;
    if (elNewsLog) elNewsLog.innerHTML = `<div class="log-entry" style="color:#aaa;">No news loaded.</div>`;
    const tbody = document.getElementById('scen-positions-body');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="5" style="padding:10px; text-align:center; color:#555;">Cash Only</td></tr>';
    }
    startBtn.textContent = "Start Sim";
    startBtn.disabled = false;
    nextBtn.disabled = true;
    autoPlayBtn.disabled = true;
    if (restartBtn) restartBtn.disabled = true;
    statusLabel.textContent = "Ready";
}

function processStep(state) {
    if (!state) return;

    if (!scenChart || !scenCandleSeries) {
        initScenChart();
    }

    // 1. Update Stats
    elDate.textContent = state.date;
    elPrice.textContent = "$" + state.price.toFixed(2);
    elPortfolio.textContent = "$" + state.portfolio_value.toFixed(2);
    const elHoldings = document.getElementById('scen-holdings');
    if (elHoldings) {
        elHoldings.textContent = state.holdings ?? 0;
    }

    // Calc P&L
    const pnl = state.portfolio_value - initialCapital;
    const pnlPercent = (pnl / initialCapital) * 100;
    const sign = pnl >= 0 ? "+" : "";
    const color = pnl >= 0 ? "#4caf50" : "#ef5350";
    if (elPnL) {
        elPnL.textContent = `${sign}$${pnl.toFixed(2)} (${sign}${pnlPercent.toFixed(2)}%)`;
        elPnL.style.color = color;
    }

    // 2. Update Performance Bar (Chess Style)
    // 1.0 (Break Even) -> 50% width
    // Range: 0.5x (Loss) to 2.0x (Double)
    // Log scale usually better but linear for simplicity:
    // 50% + (percent / 2) -> e.g. +10% profit -> 55% width

    let barPercent = 50 + (pnlPercent / 2); // 100% gain = 100% width, -100% loss = 0% width
    barPercent = Math.max(0, Math.min(100, barPercent)); // Clamp

    if (elEvalBarFill) {
        elEvalBarFill.style.width = `${barPercent}%`;
        elEvalBarFill.style.backgroundColor = pnl >= 0 ? "#4caf50" : "#ef5350";
    }

    if (elEvalScore) {
        const ratio = state.portfolio_value / initialCapital;
        elEvalScore.textContent = `${ratio.toFixed(2)}x`;
    }

    // 2.5 Update Positions Table (NEW)
    const tbody = document.getElementById('scen-positions-body');
    if (tbody && state.positions) {
        tbody.innerHTML = '';
        Object.keys(state.positions).forEach(ticker => {
            const pos = state.positions[ticker];
            // Only show active
            if (pos.qty > 0) {
                const val = pos.qty * pos.last_price;
                const row = `
                        <tr style="border-bottom:1px solid #222;">
                            <td style="padding:5px;">${ticker}</td>
                            <td style="padding:5px;">${pos.qty}</td>
                            <td style="padding:5px;">$${pos.avg_price.toFixed(2)}</td>
                            <td style="padding:5px;">$${pos.last_price.toFixed(2)}</td>
                            <td style="padding:5px;">$${val.toFixed(2)}</td>
                        </tr>
                    `;
                tbody.innerHTML += row;
            }
        });

        if (tbody.innerHTML === '') {
            tbody.innerHTML = '<tr><td colspan="5" style="padding:10px; text-align:center; color:#555;">Cash Only</td></tr>';
        }
    }

    // 3. Update Logs (Reasoning)
    if (state.reasoning && state.reasoning.length > 0) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';
        const header = `[${state.date}] ${state.decision.toUpperCase()}`;
        // Colored status
        let color = '#ccc';
        if (state.decision === 'buy') color = '#00ff00';
        if (state.decision === 'sell') color = '#ff0000';

        entry.innerHTML = `<span style="color:${color}">${header}</span><br>${state.reasoning.join("<br>")}`;
        elLog.prepend(entry);

        // News Handling
        let newsFound = false;
        state.reasoning.forEach(line => {
            if (line.includes("NEWS:")) {
                newsFound = true;
                const newsEntry = document.createElement('div');
                newsEntry.className = 'log-entry';
                newsEntry.style.backgroundColor = '#222';
                newsEntry.style.borderLeft = '3px solid #fdd835';
                newsEntry.style.padding = '5px';
                newsEntry.style.marginBottom = '5px';
                newsEntry.innerHTML = `<strong style="color:#fdd835">[${state.date}] BREAKING NEWS</strong><br>${line.replace("📰 NEWS: ", "")}`;
                elNewsLog.prepend(newsEntry);
            }
        });

        if (!newsFound) {
            // Optional: Add "Quiet Day" log to show system is checking
            // const quiet = document.createElement('div');
            // quiet.textContent = `[${state.date}] No major news.`;
            // quiet.style.color = '#444';
            // quiet.style.fontSize = '10px';
            // elNewsLog.prepend(quiet);
        }
    }

    // 4. Update Chart
    const candle = {
        time: state.date,
        open: state.price,
        high: state.price,
        low: state.price,
        close: state.price
    };

    scenData.push(candle);
    if (scenCandleSeries) scenCandleSeries.setData(scenData);
    if (scenChart) scenChart.timeScale().scrollToPosition(0, true);
    updateScenarioAnalytics(state);
}

// Listeners
if (startBtn) {
    startBtn.addEventListener('click', handleStartOrSwitch); // UPDATED
    nextBtn.addEventListener('click', nextStep);
    if (autoPlayBtn) autoPlayBtn.addEventListener('click', toggleAutoPlay);
    if (restartBtn) restartBtn.addEventListener('click', resetScenarioUI);
}
