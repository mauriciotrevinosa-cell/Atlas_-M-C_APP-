/**
 * terminal.js — ARIA Chat Utilities
 * -----------------------------------
 * Provides connection-status helpers and the slash-command picker.
 * Input handling is done entirely by app.js — do NOT add duplicate
 * keypress listeners here (that would cause double responses).
 */

'use strict';

class Terminal {
  constructor(containerId, inputId, statusId) {
    this.container  = document.getElementById(containerId);
    this.input      = document.getElementById(inputId);
    this.statusText = document.getElementById(statusId);
    this.statusDot  = document.getElementById('status-dot');

    if (!this.container || !this.input) {
      console.warn('[Terminal] elements not found — skipping init');
      return;
    }

    // ⚠️  Do NOT add a keypress/keydown listener here.
    // app.js owns input handling and calls the real /query endpoint.
    // Adding a second listener here would cause duplicate messages.

    this.updateConnectionStatus(true);
  }

  updateConnectionStatus(isConnected) {
    if (this.statusText) {
      this.statusText.textContent = isConnected
        ? 'Connected to ARIA'
        : 'Offline';
    }
    if (this.statusDot) {
      this.statusDot.style.background = isConnected ? '#2ecc71' : '#e74c3c';
    }
  }

  /** Append a message bubble — used externally by other modules if needed. */
  appendMessage(role, text) {
    if (!this.container) return;
    const div = document.createElement('div');
    div.className = `message ${role}`;
    let html = text
      .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>');
    div.innerHTML = html;
    this.container.appendChild(div);
    this.container.scrollTop = this.container.scrollHeight;
  }
}


// ── Slash-command picker ────────────────────────────────────────────────────

window._selectSlash = function (cmd) {
  const input = document.getElementById('input');
  if (input) {
    input.value = cmd + ' ';
    input.focus();
    // Trigger the input-change handler so the slash hints update
    input.dispatchEvent(new Event('input'));
  }
};


// ── Init ────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  window.AriaTerminal = new Terminal('chat', 'input', 'status-text');
});
