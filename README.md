# Atlas

Atlas is a local-first quantitative research platform with ARIA as assistant layer.

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
- `outputs/runs/`: per-run artifacts, manifests, and logs.
- `docs/REPO_MAP.md`: canonical repo map and governance policy.

## Dependencies

- Source of truth: `pyproject.toml`
- `requirements.txt` is compatibility-only (`-e .`).
