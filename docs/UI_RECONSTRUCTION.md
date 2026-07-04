# Atlas UI Reconstruction Guide

This document turns the AI Studio frontend conversation into an implementation
path that fits the current repo.

## Current Reality

The active UI is `apps/desktop`: an Electron shell backed by vanilla HTML, CSS,
and JavaScript. It already has modules for finance, ARIA, indicators, MMO, real
estate, signals, RL, agents, visualizations, and dashboards.

`ui_web` is only a placeholder for a future TypeScript/React web application.
There is no production Next.js/Tailwind app wired into Atlas yet.

Because of that, the React/Tailwind/Three.js code from AI Studio should be
treated as an upgrade prototype, not as production code to import directly into
the desktop app today.

## Target Experience

Atlas V2 should feel like a modular operating surface:

- A dense but clean dashboard for daily operations.
- A launcher/library for Atlas modules.
- A wallet-style financial snapshot for personal and M&C capital views.
- A persistent ARIA assistant entrypoint that opens beside workflows.
- A 3D MMO preview that explains complex market states visually.
- Full-screen module transitions for deep work without terminal dependence.

## Visual Direction

Use a restrained light interface with selective glass effects. Avoid turning the
whole app into decorative cards. Atlas is an operational system, so the UI must
stay scannable, predictable, and useful under repeated use.

Recommended principles:

- Use glass only for primary panels, overlays, and high-value widgets.
- Keep dense operational screens flatter and more utilitarian.
- Use real module state and backend data before decorative animation.
- Keep 3D full-bleed or purposefully framed inside a real tool surface.
- Make ARIA a side drawer or command layer, not the only visible product.

## Proposed Stack

For the future web UI:

- React with TypeScript.
- Vite or Next.js, chosen after deciding whether Atlas needs SSR/routes or a
  desktop-style SPA.
- Tailwind CSS for utility styling.
- Framer Motion for module transitions.
- Lucide React for icons.
- Three.js through React Three Fiber for MMO and 3D lab scenes.
- FastAPI endpoints from the current Python server as the backend contract.

## Upgrade Package

The organized AI Studio prototype lives in `FR_upgrade/`:

- `IMPLEMENTATION_GUIDE.md`: install and integration notes.
- `Theme.css`: prototype visual theme.
- `Login.jsx`: reference login surface.
- `Dashboard.jsx`: reference OS dashboard.
- `MMORender.jsx`: reference 3D MMO geometry component.
- `AIgooglestudiocode.md`: raw copied conversation dump.

## Integration Path

1. Keep improving `apps/desktop` in place for short-term usability.
2. Use `FR_upgrade` as the visual reference, not as active production code.
3. When ready, scaffold the real `ui_web` app with TypeScript, React, Tailwind,
   routing, API client helpers, and test setup.
4. Move only stable concepts from `FR_upgrade` into `ui_web`.
5. Connect widgets to real Atlas endpoints before adding advanced animation.
6. Promote `ui_web` only after it can run the core Atlas workflows without
   depending on terminal-only entrypoints.

## First Implementation Milestones

- README and docs realignment: Atlas as M&C OS, not only quant trading.
- Desktop visual polish: make existing modules feel like one app.
- `ui_web` scaffold: real package, scripts, lint, test, and API contract.
- Dashboard shell: module launcher, wallet placeholder, ARIA drawer, MMO preview.
- Backend contracts: stable `/api/*` endpoints for dashboard data.
- Data-backed widgets: replace mock wallet and demo values.
- 3D verification: screenshot and canvas-pixel checks for MMO scenes.
