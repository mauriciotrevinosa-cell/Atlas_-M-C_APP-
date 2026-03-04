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

from .data_layer import safe_symbol

logger = logging.getLogger("atlas.market_finance.simulation")


@dataclass(slots=True)
class SimulationConfig:
    n_paths: int = 2000
    horizon_days: int = 252
    seed: int = 42
    sample_paths: int = 30


@dataclass(slots=True)
class SimulationResult:
    summary: Dict[str, Any]
    files: Dict[str, str]
    symbols: list[str]
    paths_by_symbol: Dict[str, np.ndarray]
    portfolio_paths: np.ndarray
    final_returns_by_symbol: Dict[str, np.ndarray]
    portfolio_final_returns: np.ndarray


class SimulationEngine:
    """Multi-asset Monte Carlo simulation (GBM based on historical log-return moments)."""

    def simulate(
        self,
        market_data: Mapping[str, pd.DataFrame],
        run_dir: Path,
        config: SimulationConfig,
    ) -> SimulationResult:
        simulation_dir = run_dir / "simulation"
        simulation_dir.mkdir(parents=True, exist_ok=True)

        symbols = sorted([safe_symbol(symbol) for symbol in market_data.keys() if not market_data[symbol].empty])
        if not symbols:
            raise ValueError("Simulation requires at least one symbol with data")

        returns_panel = self._returns_panel(market_data, symbols)
        if returns_panel.empty:
            raise ValueError("Simulation requires non-empty returns data")

        start_prices = np.array([float(market_data[symbol]["close"].iloc[-1]) for symbol in symbols], dtype=float)
        n_assets = len(symbols)

        rng = np.random.default_rng(config.seed)

        mu = returns_panel.mean().to_numpy(dtype=float)
        cov = returns_panel.cov().to_numpy(dtype=float)
        cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)

        if n_assets == 1:
            sigma = float(np.sqrt(max(cov[0, 0], 1e-12)))
            draws = rng.normal(
                loc=float(mu[0]),
                scale=sigma,
                size=(config.n_paths, config.horizon_days, 1),
            )
        else:
            cov += np.eye(n_assets) * 1e-10
            draws = rng.multivariate_normal(
                mean=mu,
                cov=cov,
                size=(config.n_paths, config.horizon_days),
                method="svd",
            )

        cumulative = np.cumsum(draws, axis=1)
        paths = start_prices[np.newaxis, np.newaxis, :] * np.exp(cumulative)

        paths_by_symbol: Dict[str, np.ndarray] = {
            symbol: paths[:, :, idx] for idx, symbol in enumerate(symbols)
        }

        portfolio_paths = np.mean(paths, axis=2)
        portfolio_start = float(np.mean(start_prices))

        final_returns_by_symbol: Dict[str, np.ndarray] = {}
        for idx, symbol in enumerate(symbols):
            final_returns_by_symbol[symbol] = (paths[:, -1, idx] / start_prices[idx]) - 1.0

        portfolio_final_returns = (portfolio_paths[:, -1] / portfolio_start) - 1.0

        summary = {
            "config": {
                "n_paths": config.n_paths,
                "horizon_days": config.horizon_days,
                "seed": config.seed,
            },
            "symbols": symbols,
            "symbol_quantiles": {
                symbol: {
                    "p5": float(np.percentile(final_returns_by_symbol[symbol], 5)),
                    "p50": float(np.percentile(final_returns_by_symbol[symbol], 50)),
                    "p95": float(np.percentile(final_returns_by_symbol[symbol], 95)),
                }
                for symbol in symbols
            },
            "portfolio_quantiles": {
                "p5": float(np.percentile(portfolio_final_returns, 5)),
                "p50": float(np.percentile(portfolio_final_returns, 50)),
                "p95": float(np.percentile(portfolio_final_returns, 95)),
            },
        }

        files: Dict[str, str] = {}

        summary_path = simulation_dir / "simulation_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        files["simulation_summary_json"] = str(summary_path.resolve())

        final_returns_df = pd.DataFrame({symbol: final_returns_by_symbol[symbol] for symbol in symbols})
        final_returns_df["portfolio"] = portfolio_final_returns
        final_returns_path = simulation_dir / "final_returns.csv"
        final_returns_df.to_csv(final_returns_path, index=False)
        files["final_returns_csv"] = str(final_returns_path.resolve())

        sample_count = min(config.sample_paths, config.n_paths)
        sample_rows = []
        for path_id in range(sample_count):
            for day in range(config.horizon_days):
                row: Dict[str, Any] = {"path_id": path_id, "step": day + 1}
                for symbol in symbols:
                    row[symbol] = float(paths_by_symbol[symbol][path_id, day])
                row["portfolio"] = float(portfolio_paths[path_id, day])
                sample_rows.append(row)
        sample_df = pd.DataFrame(sample_rows)
        sample_path = simulation_dir / "sample_paths.csv"
        sample_df.to_csv(sample_path, index=False)
        files["sample_paths_csv"] = str(sample_path.resolve())

        npz_path = simulation_dir / "simulation_paths.npz"
        np.savez_compressed(
            npz_path,
            symbols=np.array(symbols, dtype="U32"),
            paths=paths,
            portfolio_paths=portfolio_paths,
        )
        files["simulation_paths_npz"] = str(npz_path.resolve())

        histogram_path = simulation_dir / "portfolio_histogram.png"
        self._render_histogram(portfolio_final_returns, histogram_path)
        files["portfolio_histogram_png"] = str(histogram_path.resolve())

        fan_chart_path = simulation_dir / "portfolio_fan_chart.png"
        self._render_fan_chart(portfolio_paths, fan_chart_path)
        files["portfolio_fan_chart_png"] = str(fan_chart_path.resolve())

        return SimulationResult(
            summary=summary,
            files=files,
            symbols=symbols,
            paths_by_symbol=paths_by_symbol,
            portfolio_paths=portfolio_paths,
            final_returns_by_symbol=final_returns_by_symbol,
            portfolio_final_returns=portfolio_final_returns,
        )

    def _returns_panel(
        self,
        market_data: Mapping[str, pd.DataFrame],
        symbols: list[str],
    ) -> pd.DataFrame:
        returns = {}
        for symbol in symbols:
            frame = market_data[symbol]
            returns[symbol] = np.log(frame["close"] / frame["close"].shift(1))
        panel = pd.DataFrame(returns).dropna(how="all")
        panel = panel.fillna(0.0)
        return panel

    def _render_histogram(self, portfolio_final_returns: np.ndarray, output_path: Path) -> None:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.hist(portfolio_final_returns, bins=40, alpha=0.85, color="#1f77b4")
        ax.set_title("Portfolio Final Return Distribution")
        ax.set_xlabel("Return")
        ax.set_ylabel("Frequency")
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)

    def _render_fan_chart(self, portfolio_paths: np.ndarray, output_path: Path) -> None:
        quantiles = {
            "p5": np.percentile(portfolio_paths, 5, axis=0),
            "p25": np.percentile(portfolio_paths, 25, axis=0),
            "p50": np.percentile(portfolio_paths, 50, axis=0),
            "p75": np.percentile(portfolio_paths, 75, axis=0),
            "p95": np.percentile(portfolio_paths, 95, axis=0),
        }
        x = np.arange(1, portfolio_paths.shape[1] + 1)

        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.fill_between(x, quantiles["p5"], quantiles["p95"], alpha=0.25, color="#1f77b4", label="p5-p95")
        ax.fill_between(x, quantiles["p25"], quantiles["p75"], alpha=0.35, color="#2ca02c", label="p25-p75")
        ax.plot(x, quantiles["p50"], color="#111111", linewidth=2.0, label="median")
        ax.set_title("Portfolio Monte Carlo Fan Chart")
        ax.set_xlabel("Day")
        ax.set_ylabel("Portfolio Value")
        ax.legend(loc="best")
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
