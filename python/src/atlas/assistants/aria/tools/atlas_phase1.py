from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence

from atlas.market_finance.pipeline import Phase1Workflow
from atlas.market_finance.risk_layer import RiskConfig
from atlas.market_finance.simulation_layer import SimulationConfig

PROJECT_ROOT = Path(__file__).resolve().parents[6]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "runs"


def _default_dates(start_date: Optional[str], end_date: Optional[str]) -> tuple[str, str]:
    today = date.today()
    start = start_date or (today - timedelta(days=365)).isoformat()
    end = end_date or today.isoformat()
    return start, end


def _parse_symbols(symbols: Sequence[str] | str) -> list[str]:
    if isinstance(symbols, str):
        items = [part.strip() for part in symbols.replace(";", ",").split(",")]
        return [item.upper() for item in items if item]
    return [str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()]


def _new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _run_dir(run_id: str) -> Path:
    return DEFAULT_OUTPUT_ROOT / run_id


class _BasePhase1Tool:
    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description
        self.workflow = Phase1Workflow(output_root=str(DEFAULT_OUTPUT_ROOT))

    def get_parameters_schema(self) -> Dict[str, Any]:
        raise NotImplementedError


class AtlasGetDataTool(_BasePhase1Tool):
    def __init__(self) -> None:
        super().__init__(
            name="atlas_get_data",
            description="Fetch data with provider priority + cache and persist per-run artifacts.",
        )

    def execute(
        self,
        symbols: Sequence[str] | str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_symbols = _parse_symbols(symbols)
        if not resolved_symbols:
            return {"success": False, "error": "No symbols provided"}

        resolved_run = run_id or _new_run_id()
        start, end = _default_dates(start_date, end_date)

        payloads = self.workflow.get_data_stage(
            run_id=resolved_run,
            symbols=resolved_symbols,
            start_date=start,
            end_date=end,
            interval=interval,
        )

        return {
            "success": True,
            "run_id": resolved_run,
            "run_dir": str(_run_dir(resolved_run).resolve()),
            "stage": "data",
            "symbols": list(payloads.keys()),
            "outputs": {
                symbol: {
                    "source": payload.source,
                    "cache_hit": payload.cache_hit,
                    "files": payload.files,
                }
                for symbol, payload in payloads.items()
            },
        }

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Symbols, e.g. ['AAPL','MSFT','SPY']",
                },
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "interval": {"type": "string", "default": "1d"},
                "run_id": {"type": "string", "description": "Optional run id"},
            },
            "required": ["symbols"],
        }


class AtlasAnalyticsTool(_BasePhase1Tool):
    def __init__(self) -> None:
        super().__init__(
            name="atlas_analytics",
            description="Run analytics layer (returns, rolling vol, rolling corr, heatmap, candlestick patterns).",
        )

    def execute(
        self,
        run_id: str,
        symbols: Optional[Sequence[str] | str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
    ) -> Dict[str, Any]:
        run_dir = _run_dir(run_id)
        if not (run_dir / "data").exists():
            if symbols is None:
                return {
                    "success": False,
                    "error": "Data stage not found for run_id. Provide symbols/start_date/end_date to fetch data first.",
                }
            start, end = _default_dates(start_date, end_date)
            self.workflow.get_data_stage(
                run_id=run_id,
                symbols=_parse_symbols(symbols),
                start_date=start,
                end_date=end,
                interval=interval,
            )

        result = self.workflow.analytics_stage(run_id=run_id)
        return {
            "success": True,
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "stage": "analytics",
            "summary": result.summary,
            "files": result.files,
        }

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "Existing run id"},
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional: fetch data first if run has no data",
                },
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "interval": {"type": "string", "default": "1d"},
            },
            "required": ["run_id"],
        }


class AtlasSimulateTool(_BasePhase1Tool):
    def __init__(self) -> None:
        super().__init__(
            name="atlas_simulate",
            description="Run multi-asset Monte Carlo simulation and generate distributions + fan chart.",
        )

    def execute(
        self,
        run_id: str,
        n_paths: int = 1500,
        horizon_days: int = 252,
        symbols: Optional[Sequence[str] | str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
    ) -> Dict[str, Any]:
        run_dir = _run_dir(run_id)
        if not (run_dir / "data").exists():
            if symbols is None:
                return {
                    "success": False,
                    "error": "Data stage not found for run_id. Provide symbols/start_date/end_date to fetch data first.",
                }
            start, end = _default_dates(start_date, end_date)
            self.workflow.get_data_stage(
                run_id=run_id,
                symbols=_parse_symbols(symbols),
                start_date=start,
                end_date=end,
                interval=interval,
            )

        result = self.workflow.simulation_stage(
            run_id=run_id,
            config=SimulationConfig(n_paths=n_paths, horizon_days=horizon_days),
        )

        return {
            "success": True,
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "stage": "simulation",
            "summary": result.summary,
            "files": result.files,
        }

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "n_paths": {"type": "integer", "default": 1500},
                "horizon_days": {"type": "integer", "default": 252},
                "symbols": {"type": "array", "items": {"type": "string"}},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "interval": {"type": "string", "default": "1d"},
            },
            "required": ["run_id"],
        }


class AtlasRiskTool(_BasePhase1Tool):
    def __init__(self) -> None:
        super().__init__(
            name="atlas_risk",
            description="Run risk layer (historical VaR/CVaR, max drawdown, loss probability, quantile table).",
        )

    def execute(
        self,
        run_id: str,
        confidence: float = 0.95,
        loss_threshold: float = 0.05,
        n_paths: int = 1500,
        horizon_days: int = 252,
    ) -> Dict[str, Any]:
        run_dir = _run_dir(run_id)
        if not (run_dir / "data").exists():
            return {
                "success": False,
                "error": "Data stage not found for run_id. Run atlas_get_data or atlas_phase1_run first.",
            }

        sim = self.workflow.simulation_stage(
            run_id=run_id,
            config=SimulationConfig(n_paths=n_paths, horizon_days=horizon_days),
        )
        risk = self.workflow.risk_stage(
            run_id=run_id,
            simulation_result=sim,
            config=RiskConfig(confidence=confidence, loss_threshold=loss_threshold),
        )

        return {
            "success": True,
            "run_id": run_id,
            "run_dir": str(run_dir.resolve()),
            "stage": "risk",
            "report": risk.report,
            "files": risk.files,
        }

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "confidence": {"type": "number", "default": 0.95},
                "loss_threshold": {"type": "number", "default": 0.05},
                "n_paths": {"type": "integer", "default": 1500},
                "horizon_days": {"type": "integer", "default": 252},
            },
            "required": ["run_id"],
        }


class AtlasPhase1RunTool(_BasePhase1Tool):
    def __init__(self) -> None:
        super().__init__(
            name="atlas_phase1_run",
            description="Run full official Phase 1 workflow (data->analytics->simulation->risk).",
        )

    def execute(
        self,
        symbols: Sequence[str] | str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
        n_paths: int = 1500,
        horizon_days: int = 252,
        confidence: float = 0.95,
        loss_threshold: float = 0.05,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_symbols = _parse_symbols(symbols)
        if not resolved_symbols:
            return {"success": False, "error": "No symbols provided"}

        start, end = _default_dates(start_date, end_date)
        summary = self.workflow.run(
            symbols=resolved_symbols,
            start_date=start,
            end_date=end,
            interval=interval,
            n_paths=n_paths,
            horizon_days=horizon_days,
            confidence=confidence,
            loss_threshold=loss_threshold,
            run_id=run_id,
        )

        return {
            "success": True,
            "run_id": summary.run_id,
            "run_dir": summary.run_dir,
            "manifest": summary.manifest_path,
            "key_metrics": summary.key_metrics,
        }

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbols": {"type": "array", "items": {"type": "string"}},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                "interval": {"type": "string", "default": "1d"},
                "n_paths": {"type": "integer", "default": 1500},
                "horizon_days": {"type": "integer", "default": 252},
                "confidence": {"type": "number", "default": 0.95},
                "loss_threshold": {"type": "number", "default": 0.05},
                "run_id": {"type": "string"},
            },
            "required": ["symbols"],
        }


class AtlasRunScriptTool(_BasePhase1Tool):
    def __init__(self) -> None:
        super().__init__(
            name="atlas_run_script",
            description="Run approved Atlas scripts from the scripts/ directory (safe code-interpreter pattern).",
        )

    def execute(
        self,
        script_name: str,
        args: Optional[Sequence[str]] = None,
        timeout: int = 240,
    ) -> Dict[str, Any]:
        scripts_dir = PROJECT_ROOT / "scripts"
        target = (scripts_dir / script_name).resolve()

        if not str(target).startswith(str(scripts_dir.resolve())):
            return {"success": False, "error": "Script path outside scripts/ is not allowed"}
        if target.suffix.lower() != ".py":
            return {"success": False, "error": "Only .py scripts are allowed"}
        if not target.exists():
            return {"success": False, "error": f"Script not found: {target}"}

        cli_args = [sys.executable, str(target)]
        for arg in args or []:
            cli_args.append(str(arg))

        proc = subprocess.run(
            cli_args,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "script": str(target),
            "stdout": proc.stdout[-12000:],
            "stderr": proc.stderr[-12000:],
        }

    def get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "script_name": {"type": "string", "description": "Script file under scripts/, e.g. run_phase1_demo.py"},
                "args": {"type": "array", "items": {"type": "string"}},
                "timeout": {"type": "integer", "default": 240},
            },
            "required": ["script_name"],
        }


class AtlasToolRegistry:
    """Formal registry for official Atlas workflow tools exposed to ARIA."""

    def build_tools(self) -> list[Any]:
        return [
            AtlasGetDataTool(),
            AtlasAnalyticsTool(),
            AtlasSimulateTool(),
            AtlasRiskTool(),
            AtlasPhase1RunTool(),
            AtlasRunScriptTool(),
        ]


def register_phase1_tools(aria: Any) -> list[str]:
    registered: list[str] = []
    registry = AtlasToolRegistry()
    for tool in registry.build_tools():
        aria.register_tool(tool)
        registered.append(tool.name)
    return registered
