# Atlas

Atlas is a local-first operating system for M&C workflows: a modular platform
for quantitative research, simulation, risk modeling, automation,
visualization, real estate analysis, and future engineering/design systems.
Market finance is the current Phase 1 implementation; it is not the whole
identity of Atlas.

## Quick Start

```powershell
# 1) Install dependencies from pyproject source of truth
pip install -e .

# 2) Run official Phase 1 demo (data -> analytics -> simulation -> risk)
python run_atlas.py --demo

# 3) Run ARIA terminal with Atlas workflow tools
python run_aria.py
```

## Main Entrypoints

- `python run_atlas.py`: launches browser mode.
- `python run_atlas.py --demo`: runs official Phase 1 workflow and writes artifacts to `outputs/runs/<run_id>/`.
- `python scripts/run_phase1_demo.py`: direct CLI for Phase 1 run params.
- `python run_aria.py`: ARIA terminal with Phase 1 tool registry.

## Project Layout

- `python/src/atlas/market_finance/`: official Phase 1 implementation.
- `python/src/atlas/assistants/aria/`: ARIA core and tools.
- `apps/desktop/`: current Electron desktop app and visual modules.
- `ui_web/`: planned modern React/TypeScript web UI.
- `FR_upgrade/`: organized AI Studio frontend upgrade prototype and raw dump.
- `docs/ATLAS_MASTER_VISION.md`: canonical M&C OS product vision.
- `docs/UI_RECONSTRUCTION.md`: frontend reconstruction guide.
- `docs/SAFE_DELETE_POLICY.md`: required policy for moving removed files to `trash/`.
- `outputs/runs/`: per-run artifacts, manifests, and logs.
- `docs/REPO_MAP.md`: canonical repo map and governance policy.

## Dependencies

- Source of truth: `pyproject.toml`
- `requirements.txt` is compatibility-only (`-e .`).

## About Atlas

Atlas is a comprehensive, local-first intelligence and simulation ecosystem
designed to expand M&C's analytical, operational, and creative capabilities.
Its first implemented domain is market finance: data ingestion, advanced market
analysis, simulation, backtesting, and risk modeling. The broader roadmap
extends the same deterministic architecture into real estate, automation,
knowledge systems, visualization, and engineering/design workflows.

Crucially, while the platform incorporates **ARIA** (Atlas Reasoning &
Intelligence Assistant) to augment workflows, accelerate data synthesis, and
provide analytical context, **AI operates strictly as a supplementary tool, not
as the system architect**. The core infrastructure, business logic, and
portfolio execution rules are deterministic and mathematically grounded. Atlas
keeps human researchers in control, using artificial intelligence to enhance
productivity without relinquishing architectural integrity or strategic
authority.

## License

**PROPRIETARY & CONFIDENTIAL** - This an internal project solely for demonstration purposes. Nobody may use, copy, modify, merge, publish, distribute, sublicense, or sell this software without explicit written permission. See the [LICENSE](LICENSE) file for details.
Copyright (c) 2026 Mauricio Gerardo Trevino Saldana (mauriciotrevinosa@gmail.com)
