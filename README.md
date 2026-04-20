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

## About Atlas

Atlas is a comprehensive, local-first quantitative research and algorithmic trading platform designed for advanced market analysis, simulation, and risk modeling. Built upon a rigorous, event-driven architecture, Atlas provides researchers with a robust environment to ingest market data, backtest analytical strategies, and seamlessly transition quantitative models from research to execution.

Crucially, while the platform incorporates **ARIA** (Atlas Reasoning & Intelligence Assistant) to augment workflows, accelerate data synthesis, and provide analytical context, **AI operates strictly as a supplementary tool, not as the system architect**. The core infrastructure, business logic, and portfolio execution rules are purely deterministic and mathematically grounded. Atlas is designed to keep human researchers firmly in control, using artificial intelligence to enhance productivity without relinquishing architectural integrity or strategic authority.

## License

**PROPRIETARY & CONFIDENTIAL** - This an internal project solely for demonstration purposes. Nobody may use, copy, modify, merge, publish, distribute, sublicense, or sell this software without explicit written permission. See the [LICENSE](LICENSE) file for details.
Copyright (c) 2026 Mauricio Gerardo Trevino Saldana (mauriciotrevinosa@gmail.com)
