# Codex Subagent — Code Cleaning & Fixing Queue

> Work queue for ChatGPT/Codex subagents.
> Pick tasks top-to-bottom. Mark done: `[DONE - Codex YYYY-MM-DD]`
> If you need architectural input, write in `AI_communication/ChatGPT_Codex.md`

---

## Priority 1 — Bug Fixes (these cause visible broken states)

### TASK-001 — agents.js: Replace permanent "stub mode" badge
**File:** `apps/desktop/agents.js`
**Lines:** ~460
**Problem:** When `/api/agents/status` fails, badge shows "⚠ stub mode" forever with no retry.
**Fix:** After failure, set a 3-second retry. After 3 retries, show "Agent system offline — run `python run_atlas.py`" with a copy-able command.
**Status:** [DONE - Codex 2026-04-13]

---

### TASK-002 — playroom.js: Swarm-sim offline placeholder
**File:** `apps/desktop/playroom.js`
**Lines:** ~28-35
**Problem:** `status: 'Offline'` hardcoded. The swarm-sim panel shows nothing or errors.
**Fix:** Render a styled placeholder card:
```html
<div class="playroom-coming-soon">
  <div class="coming-soon-icon">🐝</div>
  <div>Swarm Intelligence Simulator</div>
  <div class="coming-soon-note">Scheduled for next sprint — agent mesh in progress</div>
</div>
```
Add `.playroom-coming-soon` CSS: centered, muted border, italic note text.
**Status:** [DONE - Codex 2026-04-13]

---

### TASK-003 — rl_lab.js: NaN guard in training loop
**File:** `apps/desktop/rl_lab.js`
**Lines:** Find the `step()` or reward update loop
**Problem:** If reward returns NaN (happens with bad hyperparams), training continues silently producing garbage charts.
**Fix:** After each step, check `if (!isFinite(reward)) { stopTraining(); showError('Training diverged — try lower learning rate'); return; }`
**Status:** [DONE - Codex 2026-04-13]

---

### TASK-004 — finance.js: Last remaining alert()
**File:** `apps/desktop/finance.js`
**Line:** 916
**Problem:** `alert(\`Could not fetch price for ${ticker}...\`)` in else branch.
**Fix:** Replace with same `_flash()` pattern or inline DOM error. The `portfolio-error` element exists at line 910 but the else branch doesn't use it — just remove the else and always use the errMsg element (it's always present).
**Fix code:**
```javascript
// Remove the else branch entirely — errMsg element always exists:
const errMsg = document.getElementById('portfolio-error');
errMsg.textContent = `Could not fetch price for ${ticker}. Check ticker symbol.`;
errMsg.style.display = 'block';
setTimeout(() => { errMsg.style.display = 'none'; }, 5000);
return;
```
**Status:** [DONE - Codex 2026-04-13]

---

## Priority 2 — Code Quality (silent failures / hidden bugs)

### TASK-005 — Global JS: Add context to bare catch blocks
**Files:** All `apps/desktop/*.js`
**Problem:** Several `catch(e){}` or `catch{}` blocks swallow errors silently.
**Fix:** Replace with `catch(e){ console.warn('[ModuleName] operationName failed:', e.message); }`
Use the filename as module name. Do not add full stack traces — just `.message`.
**Command to find them:**
```bash
grep -rn "catch\s*{" apps/desktop/*.js
grep -rn "catch\s*(e)\s*{}" apps/desktop/*.js
```
**Status:** [DONE - Codex 2026-04-13]

---

### TASK-006 — indicator_terminal.js: Synthetic data fallback messaging
**File:** `apps/desktop/indicator_terminal.js`
**Lines:** ~893, ~911
**Problem:** Falls back to synthetic data with only a console.warn — UI shows no indication to user.
**Fix:** When using synthetic fallback, add a small chip near the ticker input:
```html
<span class="ind-fallback-chip" style="font-size:9px;color:#ff9500;margin-left:6px;">⚠ synthetic data</span>
```
Remove chip when real data loads successfully.
**Status:** [DONE - Codex 2026-04-13]

---

### TASK-007 — thought_map.js: "Telemetry offline" state polish
**File:** `apps/desktop/thought_map.js`
**Line:** ~154
**Problem:** Sets text to "Telemetry offline (err.message)" which is raw and unhelpful.
**Fix:** Show a retry button next to the message. After 10s auto-retry once.
**Status:** [DONE - Codex 2026-04-13]

---

## Priority 3 — Nice to Have (add placeholder, note for future)

### TASK-008 — quantum_like stubs: Add NotImplementedError with context
**Files:** 
- `python/src/atlas/lab/quantum_field/quantum_like/dynamics.py`
- `python/src/atlas/lab/quantum_field/quantum_like/measurement.py`
**Problem:** Both raise bare `NotImplementedError("placeholder...")`. 
**Fix:** Improve the error message to include what the function SHOULD do and a link to the relevant section of the MMO theory:
```python
raise NotImplementedError(
    "evolve_state() is a future implementation for quantum-like dynamics simulation. "
    "See: AI_communication/Claude.md for roadmap. "
    "Current MMO dynamics are handled server-side in apps/server/server.py:mmo_quantum_state()"
)
```
**Status:** [DONE - Codex 2026-04-13]

---

### TASK-009 — WhatsApp: ClickUp + Notion TODO stubs
**File:** `python/src/atlas/assistants/aria/integrations/whatsapp_bot.py`
**Lines:** ~134, ~139
**Problem:** `# TODO: Integrate with ClickUp` and `# TODO: Integrate with Notion`
**Fix:** Replace TODO comment with a proper not-yet-implemented response:
```python
return "📋 ClickUp integration coming soon. For now, tasks are tracked in Atlas Signal Terminal."
```
This is better than a silent TODO — user gets a real response.
**Status:** [DONE - Codex 2026-04-13]

---

### TASK-010 — UI State: "Silent" buttons need feedback
**Files:** `apps/desktop/trader.js` (Analyze button) & `apps/desktop/decision.js` (Refresh Signals)
**Problem:** Clicking "Analyze" or "Refresh Signals" returns no visual state. The user thinks the app is dead.
**Fix:** Add CSS skeleton loaders, `opacity: 0.5`, or `.innerHTML = 'Calculating...'` upon click. Reveal original text on success.
**Status:** [DONE - Codex 2026-04-27]

---

### TASK-011 — Viz Lab: Nested scroll trap
**File:** `apps/desktop/viz_lab.js` / `styles.css`
**Problem:** Scroll wrapper traps the mouse wheel, making it hard to see the Decorative Sims at the bottom.
**Fix:** Implement `overscroll-behavior: contain;` on the inner scroll list, or adjust viewport heights so it flows naturally.
**Status:** [DONE - Codex 2026-04-27]

---

### TASK-012 — MMO UX: Layer Explorer Clickability
**File:** `apps/desktop/mmo.js` / HTML wrapper
**Problem:** The Interactive Layer Explorer looks clickable but isn't. You have to use the bottom launchers.
**Fix:** Make the left-hand layer explorer panel text dynamically clickable, triggering the same events as the bottom layer launchers.
**Status:** [DONE - Codex 2026-04-27]

---

## Completed

| Task | Done By | Date |
|------|---------|------|
| TASK-001 | Codex | 2026-04-13 |
| TASK-002 | Codex | 2026-04-13 |
| TASK-003 | Codex | 2026-04-13 |
| TASK-004 | Codex | 2026-04-13 |
| TASK-005 | Codex | 2026-04-13 |
| TASK-006 | Codex | 2026-04-13 |
| TASK-007 | Codex | 2026-04-13 |
| TASK-008 | Codex | 2026-04-13 |
| TASK-009 | Codex | 2026-04-13 |
| TASK-010 | Codex | 2026-04-27 |
| TASK-011 | Codex | 2026-04-27 |
| TASK-012 | Codex | 2026-04-27 |

---

*Queue initialized by Claude Sonnet 4.6 — 2026-04-13*
