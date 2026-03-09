from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "python" / "src"))

from atlas.market_finance.pipeline import Phase1Workflow


def parse_args() -> argparse.Namespace:
    today = date.today()
    default_start = (today - timedelta(days=365)).isoformat()
    default_end = today.isoformat()

    parser = argparse.ArgumentParser(description="Run official ATLAS Phase 1 workflow demo")
    parser.add_argument("--symbols", nargs="+", default=["AAPL", "MSFT", "SPY"])
    parser.add_argument("--start", default=default_start, dest="start_date")
    parser.add_argument("--end", default=default_end, dest="end_date")
    parser.add_argument("--interval", default="1d")
    parser.add_argument("--n-paths", type=int, default=1500, dest="n_paths")
    parser.add_argument("--horizon-days", type=int, default=252, dest="horizon_days")
    parser.add_argument("--loss-threshold", type=float, default=0.05)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    workflow = Phase1Workflow(output_root=str(PROJECT_ROOT / "outputs" / "runs"))
    summary = workflow.run(
        symbols=args.symbols,
        start_date=args.start_date,
        end_date=args.end_date,
        interval=args.interval,
        n_paths=args.n_paths,
        horizon_days=args.horizon_days,
        loss_threshold=args.loss_threshold,
        confidence=args.confidence,
        run_id=args.run_id,
    )

    compact = {
        "run_id": summary.run_id,
        "run_dir": summary.run_dir,
        "manifest": summary.manifest_path,
        "portfolio_var": summary.key_metrics.get("portfolio_var"),
        "portfolio_cvar": summary.key_metrics.get("portfolio_cvar"),
        "probability_loss_gt_threshold": summary.key_metrics.get("probability_loss_gt_threshold"),
    }
    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
