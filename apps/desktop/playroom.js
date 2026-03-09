/**
 * Play Room - Experimental Sandbox Environment
 */

const PlayRoom = (function () {
    let initialized = false;

    const sandboxExperiments = [
        {
            id: 'git-city',
            title: 'Git City (Codebase Metadata)',
            description: 'A 3D generative city where buildings represent code files, heights represent lines of code, and roads are folder structures (Procedural Simulation).',
            icon: '🏙️',
            status: 'Online',
            color: '#3498db'
        },
        {
            id: 'racing-rl',
            title: 'Speed Racer (RL Agents)',
            description: 'Neuroevolution Agents. 100 neural networks learning to drive around a 2D track simultaneously using genetic mutation.',
            icon: '🏎️',
            status: 'Online',
            color: '#e74c3c'
        },
        {
            id: 'swarm-sim',
            title: 'Agent Swarm Simulator',
            description: 'Multi-agent system simulation demonstrating flocking behaviors and consensus algorithms.',
            icon: '🐝',
            status: 'Offline',
            color: '#f1c40f'
        }
    ];

    function renderGrid() {
        const grid = document.getElementById('playroom-grid');
        if (!grid) return;

        grid.innerHTML = '';

        sandboxExperiments.forEach(exp => {
            const card = document.createElement('div');
            card.className = 'scenario-card main';
            card.style.cssText = `border-top: 2px solid ${exp.color}; display:flex; flex-direction:column; gap:10px; cursor:pointer; transition: transform 0.2s ease;`;
            card.onmouseover = () => card.style.transform = 'translateY(-2px)';
            card.onmouseout = () => card.style.transform = 'translateY(0)';

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; display:flex; align-items:center; gap:8px;">
                        <span style="font-size:20px;">${exp.icon}</span>
                        ${exp.title}
                    </h3>
                    <span style="font-size:10px; padding:4px 8px; border-radius:12px; border:1px solid ${exp.color}40; color:${exp.status === 'Online' ? exp.color : '#888'}; font-family:monospace;">
                        ${exp.status}
                    </span>
                </div>
                <p style="font-size:13px; color:#888; margin:0; line-height:1.4; flex-grow:1;">
                    ${exp.description}
                </p>
                <div style="padding-top:12px; border-top:1px solid #333; margin-top:5px;">
                    <button class="btn ${exp.status === 'Online' ? 'primary' : 'secondary'}" onclick="PlayRoom.launch('${exp.id}')" style="width:100%; ${exp.status === 'Online' ? `background:${exp.color}15; border-color:${exp.color}40; color:${exp.color};` : ''}" ${exp.status !== 'Online' ? 'disabled' : ''}>
                        Initialize Engine
                    </button>
                </div>
            `;
            grid.appendChild(card);
        });
    }

    function init() {
        if (initialized) return;
        renderGrid();
        initialized = true;
    }

    function launch(expId) {
        const grid = document.getElementById('playroom-grid');
        grid.style.display = 'none';

        let container = document.getElementById('playroom-active-exp');
        if (!container) {
            container = document.createElement('div');
            container.id = 'playroom-active-exp';
            container.className = 'scenario-card';
            container.style.width = '100%';
            container.style.height = '650px';
            container.style.position = 'relative';
            document.getElementById('view-playroom').appendChild(container);
        }

        container.style.display = 'block';
        container.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; padding-bottom:10px; border-bottom:1px solid #333;">
                <h3 style="margin:0;">Active Simulation: <span style="color:#7c3fe4;">${expId}</span></h3>
                <button class="btn secondary" onclick="PlayRoom.closeExp()">Back to Sandbox</button>
            </div>
            <div id="playroom-mount" style="width:100%; height:calc(100% - 50px); position:relative; overflow:hidden; border-radius:8px; background:#0b0f1a;"></div>
        `;

        if (expId === 'git-city' && window.PlayRoomGitCity) {
            window.PlayRoomGitCity.launch('playroom-mount');
        } else if (expId === 'racing-rl' && window.PlayRoomRacing) {
            window.PlayRoomRacing.launch('playroom-mount');
        } else {
            document.getElementById('playroom-mount').innerHTML = `
                <div style="color:#e74c3c; padding:20px; font-family:monospace;">
                    <h3>[ERROR] Engine core offline.</h3>
                    <p>The neural interface or graphics context for <strong>${expId}</strong> could not be located in the current build.</p>
                </div>
            `;
        }
    }

    function closeExp() {
        const grid = document.getElementById('playroom-grid');
        const container = document.getElementById('playroom-active-exp');
        
        if (window.PlayRoomGitCity) window.PlayRoomGitCity.cleanup();
        if (window.PlayRoomRacing) window.PlayRoomRacing.cleanup();
        
        if (container) container.style.display = 'none';
        if (grid) {
            grid.style.display = 'grid'; // assuming .scenario-grid uses grid
        }
    }

    return { init, launch, closeExp };
})();

// Expose globally for inline handlers and cross-module wiring.
window.PlayRoom = PlayRoom;
