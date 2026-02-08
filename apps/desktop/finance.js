/**
 * Finance Module (Portfolio + 3D Lab)
 */

async function updatePortfolio() {
    try {
        const response = await fetch('/api/portfolio');
        const data = await response.json();

        // Update Equity
        document.getElementById('total-equity').textContent = formatCurrency(data.total_equity);

        // Update Table
        const tbody = document.getElementById('portfolio-table-body');
        tbody.innerHTML = '';

        if (data.positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="padding:20px; text-align:center; color:#555;">No active positions</td></tr>';
            return;
        }

        data.positions.forEach(pos => {
            const pnlColor = pos.pnl >= 0 ? '#4caf50' : '#e74c3c';
            const row = `
                <tr style="border-bottom:1px solid #222;">
                    <td style="padding:12px; font-weight:bold;">${pos.symbol}</td>
                    <td style="padding:12px;">${pos.qty}</td>
                    <td style="padding:12px;">$${pos.avg_price.toFixed(2)}</td>
                    <td style="padding:12px;">$${pos.current_price.toFixed(2)}</td>
                    <td style="padding:12px; color:${pnlColor}; font-weight:bold;">
                        ${pos.pnl >= 0 ? '+' : ''}$${pos.pnl.toFixed(2)} (${pos.pnl_pct.toFixed(1)}%)
                    </td>
                </tr>
            `;
            tbody.innerHTML += row;
        });

    } catch (e) {
        console.error("Portfolio update failed", e);
    }
}

async function generate3D(type) {
    const status = document.getElementById('3d-render-status');
    const container = document.getElementById('3d-output-container');
    const img = document.getElementById('3d-image-result');

    status.textContent = `Generating ${type}... (This performs heavy computation)`;
    status.style.color = '#fff';

    try {
        const response = await fetch(`/api/viz/3d/${type}`);
        const data = await response.json();

        if (data.path) {
            // Because path is local file system, we need to serve it via static content or blob
            // For now, assuming server returns a relative URL or base64 
            // In a real desktop app we can load local file
            // Let's assume the server moved it to a public folder
            status.textContent = "Render complete!";
            status.style.color = '#4caf50';

            img.src = data.url; // Server should return /static/renders/filename.png
            container.style.display = 'block';
        } else {
            status.textContent = "Render failed.";
            status.style.color = 'red';
        }
    } catch (e) {
        status.textContent = "Error: " + e.message;
        status.style.color = 'red';
    }
}

function formatCurrency(num) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(num);
}

// Initial load
document.addEventListener('DOMContentLoaded', () => {
    updatePortfolio();
});

