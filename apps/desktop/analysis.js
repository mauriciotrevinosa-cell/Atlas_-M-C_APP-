
/**
 * Analysis Tab Logic
 * Handles real-time charts and market data.
 */

const analysisTickerInput = document.getElementById('analysis-ticker');
const analysisLoadBtn = document.getElementById('analysis-load-btn');
const analysisPriceDisplay = document.getElementById('analysis-price');
const analysisNewsList = document.getElementById('analysis-news-list');
const analysisChartContainer = document.getElementById('analysis-chart-container');

let analysisChart = null;
let analysisCandleSeries = null;

// Initialize Chart
function initAnalysisChart() {
    if (!analysisChartContainer) return;

    // Create Chart
    analysisChart = LightweightCharts.createChart(analysisChartContainer, {
        width: analysisChartContainer.clientWidth,
        height: analysisChartContainer.clientHeight,
        layout: {
            background: { type: 'solid', color: 'white' },
            textColor: 'black',
        },
        grid: {
            vertLines: { color: '#eee' },
            horzLines: { color: '#eee' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#cccccc',
        },
        timeScale: {
            borderColor: '#cccccc',
        },
    });

    analysisCandleSeries = analysisChart.addCandlestickSeries({
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
    });

    // Resize observer
    new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== analysisChartContainer) { return; }
        const newRect = entries[0].contentRect;
        analysisChart.applyOptions({ width: newRect.width, height: newRect.height });
    }).observe(analysisChartContainer);
}

async function loadAnalysisData() {
    const ticker = analysisTickerInput.value.toUpperCase();
    analysisLoadBtn.textContent = "Loading...";
    analysisPriceDisplay.textContent = "...";

    try {
        const res = await fetch(`${CONFIG.serverUrl}/api/market_data/${ticker}`);

        if (!res.ok) throw new Error("Failed to fetch data");

        const data = await res.json();

        // Update Price
        analysisPriceDisplay.textContent = `$${data.price.toFixed(2)}`;

        // Update Chart
        if (!analysisChart) initAnalysisChart();
        analysisCandleSeries.setData(data.ohlc);

        // Update News
        analysisNewsList.innerHTML = "";
        if (data.news && data.news.length > 0) {
            data.news.forEach(n => {
                const el = document.createElement('div');
                el.className = 'log-entry';
                el.style.borderBottom = '1px solid #eee';
                el.style.color = '#333';
                const time = new Date(n.timestamp * 1000).toLocaleDateString();
                el.innerHTML = `<small style="color:#888;">${time} • ${n.publisher}</small><br><strong><a href="${n.link}" target="_blank" style="text-decoration:none; color:inherit;">${n.title}</a></strong>`;
                analysisNewsList.appendChild(el);
            });
        } else {
            analysisNewsList.innerHTML = "<div class='log-entry' style='color:#666;'>No recent news found.</div>";
        }

    } catch (e) {
        alert("Error: " + e.message);
    } finally {
        analysisLoadBtn.textContent = "Load Data";
    }
}

// Event Listeners
if (analysisLoadBtn) {
    analysisLoadBtn.addEventListener('click', loadAnalysisData);

    // Load initial data on view switch if empty
    document.addEventListener('click', (e) => {
        if (e.target.closest('.module-card[onclick*="analysis"]')) {
            setTimeout(() => {
                if (analysisChartContainer && !analysisChart) {
                    initAnalysisChart();
                    loadAnalysisData();
                }
            }, 100);
        }
    });
}
