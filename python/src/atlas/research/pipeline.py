"""
Quant research pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Mapping, Optional

import pandas as pd

from atlas.market_finance.data_layer import DataRouter

from .idea import HypothesisType, ResearchIdea
from .report import ResearchReport, ResearchStage
from .validator import StatisticalValidator


@dataclass(slots=True)
class PipelineConfig:
    output_root: str = "outputs/runs"
    interval: str = "1d"
    use_cache: bool = True
    allow_stale_cache: bool = True
    n_bootstrap: int = 2000


class QuantResearchPipeline:
    """End-to-end local-first research loop: idea -> data -> backtest -> validation."""

    def __init__(
        self,
        config: PipelineConfig | None = None,
        data_router: DataRouter | None = None,
        validator: StatisticalValidator | None = None,
    ) -> None:
        self.config = config or PipelineConfig()
        self.data_router = data_router or DataRouter()
        self.validator = validator or StatisticalValidator()

    def run(
        self,
        idea: ResearchIdea,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        data_override: Optional[Mapping[str, pd.DataFrame]] = None,
    ) -> ResearchReport:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_dir = Path(self.config.output_root) / run_id / "research"
        run_dir.mkdir(parents=True, exist_ok=True)

        start, end = self._resolve_dates(
            start_date=start_date,
            end_date=end_date,
            lookback_days=idea.lookback_days,
        )
        symbols = [s.strip().upper() for s in idea.symbols if s.strip()]
        if not symbols:
            raise ValueError("ResearchIdea requires at least one symbol")

        if data_override is None:
            payloads = self.data_router.get_many(
                symbols=symbols,
                start_date=start,
                end_date=end,
                interval=self.config.interval,
                run_dir=run_dir,
                use_cache=self.config.use_cache,
                allow_stale_cache=self.config.allow_stale_cache,
            )
            market_data = {symbol: payloads[symbol].frame for symbol in payloads}
        else:
            market_data = {k.strip().upper(): v.copy() for k, v in data_override.items()}

        strategy_returns = self._build_strategy_returns(market_data, idea)
        validation = self.validator.validate(strategy_returns, n_bootstrap=self.config.n_bootstrap)

        metrics = {
            "start_date": start,
            "end_date": end,
            "hypothesis": idea.hypothesis,
            "hypothesis_type": idea.hypothesis_type.value,
            "n_symbols": len(market_data),
            "n_observations": int(strategy_returns.dropna().shape[0]),
            "mean_return": float(strategy_returns.mean()),
            "std_return": float(strategy_returns.std(ddof=1)) if len(strategy_returns) > 1 else 0.0,
            "validation": {
                "p_value": validation.p_value,
                "effect_size": validation.effect_size,
                "ci_low": validation.ci_low,
                "ci_high": validation.ci_high,
                "significant": validation.significant,
            },
        }

        returns_path = run_dir / "strategy_returns.csv"
        strategy_returns.to_frame("strategy_return").to_csv(returns_path, index=True)

        report = ResearchReport(
            run_id=run_id,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            stage=ResearchStage.VALIDATION,
            idea_name=idea.name,
            symbols=sorted(market_data.keys()),
            metrics=metrics,
            artifacts={"strategy_returns_csv": str(returns_path.resolve())},
        )

        report_path = run_dir / "research_report.json"
        report_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        report.artifacts["research_report_json"] = str(report_path.resolve())
        return report

    def _build_strategy_returns(
        self,
        market_data: Mapping[str, pd.DataFrame],
        idea: ResearchIdea,
    ) -> pd.Series:
        rets: list[pd.Series] = []
        for symbol, frame in market_data.items():
            close = _series(frame, "close")
            base_ret = close.pct_change().fillna(0.0)

            if idea.hypothesis_type == HypothesisType.MOMENTUM:
                signal = close.pct_change(5).shift(1).apply(lambda x: 1.0 if x > 0 else -1.0)
            elif idea.hypothesis_type == HypothesisType.MEAN_REVERSION:
                signal = close.pct_change(5).shift(1).apply(lambda x: -1.0 if x > 0 else 1.0)
            elif idea.hypothesis_type == HypothesisType.VOLATILITY:
                vol = base_ret.rolling(20, min_periods=20).std()
                signal = (vol > vol.rolling(60, min_periods=20).mean()).astype(float)
                signal = signal.replace({0.0: -1.0})
            else:  # FLOW
                vol = _series(frame, "volume").fillna(0.0)
                signal = (vol > vol.rolling(20, min_periods=20).mean() * 1.2).astype(float)
                signal = signal.replace({0.0: -1.0})

            strat = (signal * base_ret).fillna(0.0)
            strat.name = symbol
            rets.append(strat)

        if not rets:
            return pd.Series(dtype=float)
        panel = pd.concat(rets, axis=1).dropna(how="all")
        return panel.mean(axis=1)

    def _resolve_dates(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        lookback_days: int,
    ) -> tuple[str, str]:
        end = date.fromisoformat(end_date) if end_date else date.today()
        start = date.fromisoformat(start_date) if start_date else end - timedelta(days=int(lookback_days))
        return start.isoformat(), end.isoformat()


def _col(frame: pd.DataFrame, name: str) -> str:
    lower_map = {c.lower(): c for c in frame.columns}
    key = name.lower()
    if key not in lower_map:
        raise KeyError(f"Required column '{name}' not found")
    return lower_map[key]


def _series(frame: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(frame[_col(frame, name)], errors="coerce")

