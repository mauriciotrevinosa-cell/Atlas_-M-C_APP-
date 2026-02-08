
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
const statusLabel = document.getElementById('scenario-status');
const tickerInput = document.getElementById('sim-ticker'); // NEW

const elDate = document.getElementById('scen-date');
const elPrice = document.getElementById('scen-price');
const elPortfolio = document.getElementById('scen-portfolio');
const elPnL = document.getElementById('scen-pnl'); // NEW
const elLog = document.getElementById('scen-log');
const elNewsLog = document.getElementById('scen-news-log');

// Eval Bar Elements
const elEvalBarFill = document.getElementById('eval-bar-fill');
const elEvalScore = document.getElementById('eval-score');

// Chart Elements
const scenChartContainer = document.getElementById('scen-chart-container');
let scenChart = null;
let scenCandleSeries = null;
let scenData = []; // Store accumulated OHLC data for the chart

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
        rightPriceScale: {
            borderColor: '#cccccc',
        },
        timeScale: {
            borderColor: '#cccccc',
        },
    });
    // Resizer
    new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== scenChartContainer) { return; }
        if (scenChart) {
            const newRect = entries[0].contentRect;
            scenChart.applyOptions({ width: newRect.width, height: newRect.height });
        }
    }).observe(scenChartContainer);


    async function handleStartOrSwitch() {
        const ticker = tickerInput.value.toUpperCase() || "SPY";

        if (!sessionId) {
            // Start New Session
            startScenario(ticker);
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
            statusLabel.textContent = "Active";

        } catch (e) {
            alert("Error starting scenario: " + e.message);
            statusSpan.textContent = "Connection Error";
            startBtn.textContent = "Start New Simulation";
            startBtn.disabled = false;
        }
    }

    async function switchTicker(ticker) {
        if (ticker === currentTicker) return;

        statusSpan.textContent = `Switching to ${ticker}...`;
        startBtn.disabled = true;

        try {
            const response = await fetch(`${CONFIG.serverUrl}/api/scenario/switch_ticker`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    ticker: ticker
                })
            });

            if (response.ok) {
                currentTicker = ticker;
                statusSpan.textContent = "Active";
                // Clear chart for new ticker
                scenData = [];
                candleSeries.setData([]);
                // The backend should return the current state after switching,
                // but for now, we'll just clear and wait for nextStep to populate.
                // If the backend returns the current state, we'd call processStep(data.state) here.
            } else {
                const errorData = await response.json();
                statusSpan.textContent = `Switch Failed: ${errorData.error || response.statusText}`;
            }
        } catch (e) {
            console.error("Error switching ticker:", e);
            statusSpan.textContent = "Error";
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

    function processStep(state) {
        // 1. Update Stats
        elDate.textContent = state.date;
        elPrice.textContent = "$" + state.price.toFixed(2);
        elPortfolio.textContent = "$" + state.portfolio_value.toFixed(2);

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
        scenCandleSeries.setData(scenData);
        scenChart.timeScale().scrollToPosition(0, true);
    }

    // Listeners
    if (startBtn) {
        startBtn.addEventListener('click', handleStartOrSwitch); // UPDATED
        nextBtn.addEventListener('click', nextStep);
        if (autoPlayBtn) autoPlayBtn.addEventListener('click', toggleAutoPlay);
    }
