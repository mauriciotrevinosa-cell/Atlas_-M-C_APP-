from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, Dict, Mapping

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .simulation_layer import SimulationResult

logger = logging.getLogger("atlas.market_finance.risk")


@dataclass(slots=True)
class RiskConfig:
    confidence: float = 0.95
    loss_threshold: float = 0.05


@dataclass(slots=True)
class RiskResult:
    report: Dict[str, Any]
    files: Dict[str, str]


class RiskEngine:
    """Risk metrics over historical returns and Monte Carlo outcomes."""

    def evaluate(
        self,
        market_data: Mapping[str, pd.DataFrame],
        simulation_result: SimulationResult,
        run_dir: Path,
        config: RiskConfig,
    ) -> RiskResult:
        risk_dir = run_dir / "risk"
        risk_dir.mkdir(parents=True, exist_ok=True)

        historical_returns = self._historical_returns(market_data)
        portfolio_historical = pd.DataFrame(historical_returns).dropna(how="all").mean(axis=1)

        report: Dict[str, Any] = {
            "confidence": config.confidence,
            "loss_threshold": config.loss_threshold,
            "symbols": {},
            "portfolio": {},
        }

        quantile_rows = []

        for symbol in simulation_result.symbols:
            hist = historical_returns.get(symbol, pd.Series(dtype=float)).dropna()
            sim_returns = simulation_result.final_returns_by_symbol[symbol]
            path_matrix = simulation_result.paths_by_symbol[symbol]

            var, cvar = self._historical_var_cvar(hist, confidence=config.confidence)
            mdd_distribution = self._max_drawdown_distribution(path_matrix)

            quantiles = self._quantiles(sim_returns)
            quantile_rows.append({"asset": symbol, **quantiles})

            report["symbols"][symbol] = {
                "historical_var": var,
                "historical_cvar": cvar,
                "max_drawdown": {
                    "mean": float(np.mean(mdd_distribution)),
                    "p95": float(np.percentile(mdd_distribution, 95)),
                    "worst": float(np.max(mdd_distribution)),
                },
                "probability_loss_gt_threshold": float(np.mean(sim_returns < -config.loss_threshold)),
                "simulated_quantiles": quantiles,
            }

        portfolio_var, portfolio_cvar = self._historical_var_cvar(
            portfolio_historical.dropna(), confidence=config.confidence
        )
        portfolio_mdd = self._max_drawdown_distribution(simulation_result.portfolio_paths)
        portfolio_quantiles = self._quantiles(simulation_result.portfolio_final_returns)
        quantile_rows.append({"asset": "portfolio", **portfolio_quantiles})

        report["portfolio"] = {
            "historical_var": portfolio_var,
            "historical_cvar": portfolio_cvar,
            "max_drawdown": {
                "mean": float(np.mean(portfolio_mdd)),
                "p95": float(np.percentile(portfolio_mdd, 95)),
                "worst": float(np.max(portfolio_mdd)),
            },
            "probability_loss_gt_threshold": float(
                np.mean(simulation_result.portfolio_final_returns < -config.loss_threshold)
            ),
            "simulated_quantiles": portfolio_quantiles,
        }

        files: Dict[str, str] = {}

        report_path = risk_dir / "risk_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        files["risk_report_json"] = str(report_path.resolve())

        quantiles_path = risk_dir / "quantiles_table.csv"
        pd.DataFrame(quantile_rows).to_csv(quantiles_path, index=False)
        files["quantiles_table_csv"] = str(quantiles_path.resolve())

        distribution_path = risk_dir / "portfolio_distribution.png"
        self._render_distribution(
            simulation_result.portfolio_final_returns,
            report["portfolio"]["historical_var"],
            distribution_path,
        )
        files["portfolio_distribution_png"] = str(distribution_path.resolve())

        return RiskResult(report=report, files=files)

    def _historical_returns(self, market_data: Mapping[str, pd.DataFrame]) -> Dict[str, pd.Series]:
        out: Dict[str, pd.Series] = {}
        for symbol, frame in market_data.items():
            out[symbol] = np.log(frame["close"] / frame["close"].shift(1))
        return out

    def _historical_var_cvar(self, returns: pd.Series, confidence: float) -> tuple[float, float]:
        if returns.empty:
            return 0.0, 0.0
        alpha = 1.0 - confidence
        cutoff = float(np.quantile(returns, alpha))
        tail = returns[returns <= cutoff]
        var = float(-cutoff)
        cvar = float(-tail.mean()) if not tail.empty else var
        return var, cvar

    def _max_drawdown_distribution(self, paths: np.ndarray) -> np.ndarray:
        running_max = np.maximum.accumulate(paths, axis=1)
        drawdowns = (running_max - paths) / np.maximum(running_max, 1e-12)
        return np.max(drawdowns, axis=1)

    def _quantiles(self, values: np.ndarray) -> Dict[str, float]:
        return {
            "q01": float(np.percentile(values, 1)),
            "q05": float(np.percentile(values, 5)),
            "q25": float(np.percentile(values, 25)),
            "q50": float(np.percentile(values, 50)),
            "q75": float(np.percentile(values, 75)),
            "q95": float(np.percentile(values, 95)),
            "q99": float(np.percentile(values, 99)),
        }

    def _render_distribution(self, values: np.ndarray, var_value: float, output_path: Path) -> None:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.hist(values, bins=40, alpha=0.85, color="#9467bd")
        ax.axvline(-var_value, color="#d62728", linestyle="--", linewidth=2, label=f"-VaR ({var_value:.2%})")
        ax.set_title("Portfolio Final Return Distribution")
        ax.set_xlabel("Return")
        ax.set_ylabel("Frequency")
        ax.legend(loc="best")
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
