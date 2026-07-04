# Atlas V2 Frontend Upgrade Guide

This folder contains the AI Studio frontend upgrade cleaned into separate files.
It is a prototype package, not production code currently wired into Atlas.

## Intended Stack

- React with TypeScript or JSX.
- Tailwind CSS for utility styles.
- Framer Motion for transitions.
- Lucide React for icons.
- Three.js through React Three Fiber for 3D MMO visuals.
- Atlas FastAPI server as the backend.

## Install Notes

Run dependency installation only inside the future React app folder, not at the
repo root unless that app has been scaffolded.

```bash
npm install framer-motion lucide-react three @react-three/fiber @react-three/drei
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Tailwind content should include the actual React source folder. If this package
is used directly during prototyping, include:

```js
content: ["./FR_upgrade/**/*.{js,jsx,ts,tsx}"]
```

## Files

- `Theme.css`: prototype glass and background classes.
- `Login.jsx`: reference login screen.
- `Dashboard.jsx`: reference dashboard with wallet, library, ARIA button, and
  MMO preview.
- `MMORender.jsx`: reference React Three Fiber MMO geometry.

## Important Integration Rule

Do not paste these files directly into `apps/desktop`. The current desktop app
is vanilla Electron and browser scripts. These files belong in the future
`ui_web` React app or in a new React-powered desktop surface.

## Backend Mapping

- Wallet widget: future finance/personal capital endpoints.
- Library widget: current desktop module registry and future route catalog.
- ARIA floating button: ARIA chat/tool endpoint and streaming events.
- MMO render: market state, simulation, and MMO endpoints.

## Next Steps

1. Decide whether `ui_web` should be Vite SPA or Next.js.
2. Scaffold the actual React app under `ui_web`.
3. Port the visual ideas from this folder into typed components.
4. Replace mock values with API-backed data.
5. Add visual regression checks before promoting the UI.
