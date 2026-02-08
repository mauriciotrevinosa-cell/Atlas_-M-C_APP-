# UI & Feature Issues Report
**Date:** 2026-02-08
**Status:** Pending Fixes

## Reported Issues
1.  **Finance Module Unresponsive**: Clicking the "Finance" card in the Dashboard does not open the Finance view.
2.  **Bottom Navigation**: User indicated issues with the bottom navigation bar (likely not switching views or highlighting correctly).
3.  **Scenario Mode Portfolio Visibility**: The "Practice" (Scenario Mode) view does not display the detailed "Portfolio" (list of active assets/positions) during the simulation. It only shows the total value, which hides the multi-asset feature.

## Technical Analysis
1.  **Navigation Logic**:
    *   The `switchView` function in `index.html` handles class toggling.
    *   The CSS `pointer-events: none` on inactive views is correct, but we must ensure `app.js` or other scripts don't block the button events.
2.  **Scenario UI**:
    *   Currently, `index.html`'s `#view-practice` only has a `market-stats` row (Date, Price, Portfolio Value).
    *   It lacks a `<table>` or list to show the `positions` dictionary from the backend (`scenario.py`).
    *   The "Finance" view has this table, but the user wants to see it *while* simulating.

## Implementation Plan

### 1. Fix Dashboard & Navigation Interactions
*   **Action**: Verify `switchView` is globally accessible.
*   **Action**: Ensure `z-index` of `.module-card` is correct and not blocked by overlays.
*   **Action**: Add `cursor: pointer` to all interactive elements explicitly.

### 2. Enhance Scenario Mode (Multi-Asset View)
*   **Action**: Add a "Positions" panel to the `#view-practice` layout in `index.html`.
*   **Action**: Update `scenario.js` -> `processStep(state)` to parse `state.positions` (which needs to be added to the API response if not already there) and render it in the new panel.
    *   *Note*: The current `ScenarioState` in `scenario.py` might only return `holdings` (qty of current ticker). We need to ensure it returns the full `positions` dict.

### 3. Verify Finance View
*   **Action**: Ensure `finance.js` loads data correctly when the view is activated.

## Next Steps for "Claude" (System)
1.  Modify `index.html` to add the Positions table to Scenario Mode.
2.  Modify `scenario.py` to include `positions` in the `ScenarioState` returned to frontend.
3.  Modify `scenario.js` to render this positions table on every step.

## Resolution (2026-02-08)
### 1. Finance Module
- **Fixed**: Updated `index.html` `switchView` to trigger `updatePortfolio()` and correctly highlight navigation.
- **Fixed**: Removed aggressive `click` listener in `finance.js`.

### 2. Scenario Mode
- **Feature Added**: Added "Active Positions" table to the Practice view in `index.html`.
- **Backend**: Updated `ScenarioState` in `scenario.py` to include `positions`.
- **Frontend**: Updated `scenario.js` to render the positions table dynamically.

### 3. Git
- **Synced**: Changes pushed to remote repository.
