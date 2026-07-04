# Atlas Web UI (TypeScript/React)

This module is reserved for the future modern Atlas web UI.

Status: pending implementation.

Current frontend reality:

- `apps/desktop` is the active Electron/vanilla JS app.
- `FR_upgrade` contains the cleaned AI Studio visual prototype.
- `docs/UI_RECONSTRUCTION.md` defines the migration path.

Suggested stack: React + TypeScript, Tailwind CSS, Framer Motion, Lucide React,
and React Three Fiber for 3D MMO scenes.

## Commands

```powershell
npm install
npm run build
```

After `npm run build`, `python run_atlas.py` serves this UI from `ui_web/dist`.
The previous desktop UI remains available at `/desktop/index.html`.
