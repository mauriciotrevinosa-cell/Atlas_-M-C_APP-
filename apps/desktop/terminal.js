// terminal.js
// Handles the interactive terminal logic for the ARIA Chat View.

class Terminal {
    constructor(containerId, inputId, statusId) {
        this.container = document.getElementById(containerId);
        this.input = document.getElementById(inputId);
        this.statusText = document.getElementById(statusId);
        this.statusDot = document.getElementById('status-dot');

        if (!this.container || !this.input) {
            console.warn("Terminal elements not found. Skipping init.");
            return;
        }

        this.initEventListeners();
        this.updateConnectionStatus(true);
        this.appendMessage("assistant", "System initialized. ARIA Routing Engine online.");
    }

    initEventListeners() {
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && this.input.value.trim() !== '') {
                this.handleUserInput(this.input.value.trim());
            }
        });
    }

    updateConnectionStatus(isConnected) {
        if (!this.statusText || !this.statusDot) return;

        if (isConnected) {
            this.statusText.textContent = "Connected to Local Agent Layer";
            this.statusDot.style.background = "#2ecc71"; // Green
        } else {
            this.statusText.textContent = "Offline";
            this.statusDot.style.background = "#e74c3c"; // Red
        }
    }

    appendMessage(role, text) {
        const div = document.createElement('div');
        div.className = `message ${role}`;

        // Simple formatting for markdown-like code blocks
        let formattedText = text.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        formattedText = formattedText.replace(/`([^`]+)`/g, '<code>$1</code>');

        div.innerHTML = formattedText;
        this.container.appendChild(div);

        // Auto-scroll to bottom
        this.container.scrollTop = this.container.scrollHeight;
    }

    async handleUserInput(query) {
        // UI updates
        this.appendMessage("user", query);
        this.input.value = '';

        // Notify ARIA Core visualizer (if it exists)
        if (window._ariaSetCoreState) {
            window._ariaSetCoreState("THINKING");
        }

        // Show thinking indicator
        const thinkingId = "msg-" + Date.now();
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = "message assistant thinking";
        thinkingDiv.id = thinkingId;
        thinkingDiv.innerHTML = "<span class='loader'></span> Processing via ARIA Query Router...";
        this.container.appendChild(thinkingDiv);
        this.container.scrollTop = this.container.scrollHeight;

        try {
            // In Phase 1, we simulate the fetch to the backend or hit the local Python server
            // For now, we mock the routing response to prove functionality in the UI

            // Artificial delay to simulate LLM thinking
            await new Promise(r => setTimeout(r, 1500));

            // Remove thinking indicator
            const tDiv = document.getElementById(thinkingId);
            if (tDiv) tDiv.remove();

            // Mock router classification
            let targetAgent = "planner_agent";
            let responseText = "";

            if (query.toLowerCase().includes("review") || query.toLowerCase().includes("pr")) {
                targetAgent = "reviewer_agent";
                responseText = `[Routed to **${targetAgent}**]\n\nI have reviewed the code. Everything looks functionally sound, but ensure tests cover edge cases.`;
            } else if (query.toLowerCase().includes("test")) {
                targetAgent = "test_agent";
                responseText = `[Routed to **${targetAgent}**]\n\nGenerating test fixtures and nominal cases for your implementation.`;
            } else if (query.startsWith("/")) {
                responseText = `Executing system command: ${query}`;
            } else {
                responseText = `[Routed to **${targetAgent}**]\n\nBased on your query, here is an initial implementation plan:\n1. Update UI components.\n2. Bind data layer.\n\n*Execute \`/run\` to proceed.*`;
            }

            if (window._ariaSetCoreState) {
                window._ariaSetCoreState("SPEAKING");
            }

            this.appendMessage("assistant", responseText);

        } catch (error) {
            const tDiv = document.getElementById(thinkingId);
            if (tDiv) tDiv.remove();

            this.appendMessage("assistant", `<span style="color:#e74c3c;">Error communicating with ARIA Core: ${error.message}</span>`);
            if (window._ariaSetCoreState) {
                window._ariaSetCoreState("ALERT");
            }
        }

        // Reset state after a short delay
        setTimeout(() => {
            if (window._ariaSetCoreState) {
                window._ariaSetCoreState("IDLE");
            }
        }, 2000);
    }
}

// Initialize when DOM is ready and we switch to the chat view
document.addEventListener("DOMContentLoaded", () => {
    // We attach it to the window so it can be accessed globally
    window.AriaTerminal = new Terminal('chat', 'input', 'status-text');

    // Make the slash hints interactive
    window._selectSlash = function (cmd) {
        const input = document.getElementById('input');
        if (input) {
            input.value = cmd;
            input.focus();
        }
    };
});
