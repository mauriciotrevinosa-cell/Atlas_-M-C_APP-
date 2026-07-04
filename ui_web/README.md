# Atlas Web UI (TypeScript/React)

This module is the modern Atlas web UI served by `run_atlas.py` when
`ui_web/dist` is present.

Status: active. `START_ATLAS.bat` now triggers `run_atlas.py`, which rebuilds
this UI when source files are newer than the current `dist` output.

Current frontend reality:

- `ui_web` is the active browser UI served at `/`.
- `apps/desktop` remains available at `/desktop/index.html`.
- `FR_upgrade` contains the cleaned AI Studio visual prototype.
- `docs/UI_RECONSTRUCTION.md` defines the migration path.
- `docs/OPERATIONS_WORKSPACE.md` defines the shared manual/ARIA workflow engine.
- Rebuilt `info_instructions` capabilities should be merged into existing Atlas
  surfaces first: Provider Registry, Research Workspace, La Biblioteca, ARIA,
  Signals, MMO, RL Lab, and Scenario Lab. Create a new UI section only when
  Atlas has no equivalent module yet.

Suggested stack: React + TypeScript, Tailwind CSS, Framer Motion, Lucide React,
and React Three Fiber for 3D MMO scenes.

## Commands

```powershell
npm install
npm run build
```

After `npm run build`, `python run_atlas.py` serves this UI from `ui_web/dist`.
The previous desktop UI remains available at `/desktop/index.html`.
