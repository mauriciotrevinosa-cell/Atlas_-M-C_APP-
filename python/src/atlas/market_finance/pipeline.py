from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from .analytics_layer import AnalyticsEngine, AnalyticsResult
from .data_layer import DataPayload, DataRouter, safe_symbol
from .risk_layer import RiskConfig, RiskEngine, RiskResult
from .simulation_layer import SimulationConfig, SimulationEngine, SimulationResult

logger = logging.getLogger("atlas.market_finance.pipeline")


@dataclass(slots=True)
class Phase1RunSummary:
    run_id: str
    run_dir: str
    manifest_path: str
    stage_outputs: Dict[str, Any]
    key_metrics: Dict[str, Any]


class Phase1Workflow:
    """Official Atlas Phase 1 workflow: data -> analytics -> simulation -> risk."""

    def __init__(
        self,
        output_root: str = "outputs/runs",
        provider_priority: Optional[Sequence[str]] = None,
    ) -> None:
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

        self.data_router = DataRouter(provider_priority=provider_priority)
        self.analytics_engine = AnalyticsEngine()
        self.simulation_engine = SimulationEngine()
        self.risk_engine = RiskEngine()

    def run(
        self,
        symbols: Sequence[str],
        start_date: str,
        end_date: str,
        interval: str = "1d",
        as_of: Optional[str] = None,
        run_id: Optional[str] = None,
        n_paths: int = 2000,
        horizon_days: int = 252,
        loss_threshold: float = 0.05,
        confidence: float = 0.95,
    ) -> Phase1RunSummary:
        run_id, run_dir = self._resolve_run(run_id)

        self._log_event(
            run_dir,
            "run_started",
            {
                "run_id": run_id,
                "symbols": list(symbols),
                "start_date": start_date,
                "end_date": end_date,
                "interval": interval,
            },
        )

        data_payloads = self.get_data_stage(
            run_id=run_id,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            as_of=as_of,
        )
        market_data = {symbol: payload.frame for symbol, payload in data_payloads.items()}

        analytics_result = self.analytics_stage(run_id=run_id, market_data=market_data)

        simulation_result = self.simulation_stage(
            run_id=run_id,
            market_data=market_data,
            config=SimulationConfig(n_paths=n_paths, horizon_days=horizon_days),
        )

        risk_result = self.risk_stage(
            run_id=run_id,
            market_data=market_data,
            simulation_result=simulation_result,
            config=RiskConfig(confidence=confidence, loss_threshold=loss_threshold),
        )

        stage_outputs = {
            "data": {
                symbol: {
                    "cache_hit": payload.cache_hit,
                    "source": payload.source,
                    "files": payload.files,
                    "metadata": payload.metadata,
                }
                for symbol, payload in data_payloads.items()
            },
            "analytics": {
                "summary": analytics_result.summary,
                "files": analytics_result.files,
            },
            "simulation": {
                "summary": simulation_result.summary,
                "files": simulation_result.files,
            },
            "risk": {
                "report": risk_result.report,
                "files": risk_result.files,
            },
        }

        key_metrics = {
            "portfolio_var": risk_result.report["portfolio"]["historical_var"],
            "portfolio_cvar": risk_result.report["portfolio"]["historical_cvar"],
            "probability_loss_gt_threshold": risk_result.report["portfolio"][
                "probability_loss_gt_threshold"
            ],
            "portfolio_quantiles": risk_result.report["portfolio"]["simulated_quantiles"],
        }

        manifest = {
            "run_id": run_id,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "parameters": {
                "symbols": list(symbols),
                "start_date": start_date,
                "end_date": end_date,
                "interval": interval,
                "n_paths": n_paths,
                "horizon_days": horizon_days,
                "confidence": confidence,
                "loss_threshold": loss_threshold,
            },
            "stage_outputs": stage_outputs,
            "key_metrics": key_metrics,
        }

        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(self._json_dumps(manifest), encoding="utf-8")

        self._log_event(
            run_dir,
            "run_completed",
            {
                "run_id": run_id,
                "manifest": str(manifest_path.resolve()),
                "key_metrics": key_metrics,
            },
        )

        return Phase1RunSummary(
            run_id=run_id,
            run_dir=str(run_dir.resolve()),
            manifest_path=str(manifest_path.resolve()),
            stage_outputs=stage_outputs,
            key_metrics=key_metrics,
        )

    def get_data_stage(
        self,
        run_id: str,
        symbols: Sequence[str],
        start_date: str,
        end_date: str,
        interval: str = "1d",
        as_of: Optional[str] = None,
    ) -> Dict[str, DataPayload]:
        _, run_dir = self._resolve_run(run_id)
        payloads = self.data_router.get_many(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            as_of=as_of,
            run_dir=run_dir,
            use_cache=True,
            allow_stale_cache=True,
        )

        summary = {
            symbol: {
                "cache_hit": payload.cache_hit,
                "source": payload.source,
                "files": payload.files,
                "metadata": payload.metadata,
            }
            for symbol, payload in payloads.items()
        }
        stage_path = run_dir / "data" / "data_stage_summary.json"
        stage_path.parent.mkdir(parents=True, exist_ok=True)
        stage_path.write_text(self._json_dumps(summary), encoding="utf-8")

        self._log_event(
            run_dir,
            "data_stage_completed",
            {"symbols": list(payloads.keys()), "summary_path": str(stage_path.resolve())},
        )

        return payloads

    def analytics_stage(
        self,
        run_id: str,
        market_data: Optional[Mapping[str, pd.DataFrame]] = None,
    ) -> AnalyticsResult:
        _, run_dir = self._resolve_run(run_id)
        data = dict(market_data) if market_data is not None else self._load_data_from_run(run_dir)

        result = self.analytics_engine.analyze(data, run_dir=run_dir)
        self._log_event(
            run_dir,
            "analytics_stage_completed",
            {"files": result.files},
        )
        return result

    def simulation_stage(
        self,
        run_id: str,
        market_data: Optional[Mapping[str, pd.DataFrame]] = None,
        config: Optional[SimulationConfig] = None,
    ) -> SimulationResult:
        _, run_dir = self._resolve_run(run_id)
        data = dict(market_data) if market_data is not None else self._load_data_from_run(run_dir)
        cfg = config or SimulationConfig()

        result = self.simulation_engine.simulate(data, run_dir=run_dir, config=cfg)
        self._log_event(
            run_dir,
            "simulation_stage_completed",
            {"files": result.files, "config": asdict(cfg)},
        )
        return result

    def risk_stage(
        self,
        run_id: str,
        market_data: Optional[Mapping[str, pd.DataFrame]] = None,
        simulation_result: Optional[SimulationResult] = None,
        config: Optional[RiskConfig] = None,
    ) -> RiskResult:
        _, run_dir = self._resolve_run(run_id)
        data = dict(market_data) if market_data is not None else self._load_data_from_run(run_dir)

        sim_result = simulation_result
        if sim_result is None:
            sim_result = self.simulation_stage(run_id=run_id, market_data=data)

        cfg = config or RiskConfig()
        result = self.risk_engine.evaluate(data, simulation_result=sim_result, run_dir=run_dir, config=cfg)

        self._log_event(
            run_dir,
            "risk_stage_completed",
            {"files": result.files, "config": asdict(cfg)},
        )
        return result

    def _resolve_run(self, run_id: Optional[str]) -> tuple[str, Path]:
        resolved = run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_root / resolved
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        return resolved, run_dir

    def _load_data_from_run(self, run_dir: Path) -> Dict[str, pd.DataFrame]:
        data_root = run_dir / "data"
        if not data_root.exists():
            raise FileNotFoundError(f"Run data directory not found: {data_root}")

        market_data: Dict[str, pd.DataFrame] = {}
        for symbol_dir in sorted(data_root.iterdir()):
            if not symbol_dir.is_dir():
                continue
            dataset_path = symbol_dir / "dataset.csv"
            if not dataset_path.exists():
                continue
            frame = pd.read_csv(dataset_path, index_col=0, parse_dates=True)
            frame.index.name = "timestamp_utc"
            market_data[safe_symbol(symbol_dir.name)] = frame

        if not market_data:
            raise ValueError(f"No dataset.csv files found under {data_root}")
        return market_data

    def _log_event(self, run_dir: Path, event: str, payload: Dict[str, Any]) -> None:
        line = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload,
        }
        log_path = run_dir / "logs" / "events.jsonl"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(self._json_dumps(line) + "\n")

    def _json_dumps(self, payload: Dict[str, Any]) -> str:
        def default(value: Any) -> Any:
            if isinstance(value, (np.floating, np.integer)):
                return value.item()
            if isinstance(value, np.ndarray):
                return value.tolist()
            if isinstance(value, pd.Timestamp):
                return value.isoformat()
            if isinstance(value, Path):
                return str(value)
            return str(value)

        return json.dumps(payload, default=default, indent=2)
