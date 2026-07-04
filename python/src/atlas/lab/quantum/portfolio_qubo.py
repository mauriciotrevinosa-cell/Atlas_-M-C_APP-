"""
MMO quantum-inspired portfolio state optimizer.

This is Atlas-owned code rebuilt from the Folder 3 quantum-finance intake idea:
Markowitz allocation expressed as a small binary/QUBO-style search problem. It
does not require Qiskit/myQLM and feeds Mau's Market Ontology as a deterministic
portfolio-state layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Dict, List, Sequence

import numpy as np


@dataclass(frozen=True)
class QuantumPortfolioResult:
    selected_assets: List[str]
    bitstring: str
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    objective: float
    risk_aversion: float
    cardinality: int
    search_space: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_assets": self.selected_assets,
            "bitstring": self.bitstring,
            "weights": self.weights,
            "expected_return": round(self.expected_return, 8),
            "volatility": round(self.volatility, 8),
            "objective": round(self.objective, 8),
            "risk_aversion": self.risk_aversion,
            "cardinality": self.cardinality,
            "search_space": self.search_space,
            "mode": "quantum_inspired_exhaustive_qubo",
            "atlas_layer": "mmo",
            "ontology": "mau_market_ontology",
            "lab_only": True,
        }


class QuantumPortfolioQUBO:
    """
    Small-cardinality binary optimizer for portfolio selection.

    Objective:
        maximize mu'w - risk_aversion * w'Σw

    The binary variable decides whether an asset is included. Selected assets
    receive equal weights. This is intentionally deterministic and auditable.
    """

    def optimize(
        self,
        assets: Sequence[str],
        expected_returns: Sequence[float],
        covariance: Sequence[Sequence[float]],
        cardinality: int,
        risk_aversion: float = 1.0,
    ) -> QuantumPortfolioResult:
        asset_list = [str(asset).upper() for asset in assets]
        mu = np.asarray(expected_returns, dtype=float)
        cov = np.asarray(covariance, dtype=float)

        self._validate(asset_list, mu, cov, cardinality)

        best: QuantumPortfolioResult | None = None
        search_space = 0
        for combo in combinations(range(len(asset_list)), cardinality):
            search_space += 1
            weights_array = np.zeros(len(asset_list), dtype=float)
            weights_array[list(combo)] = 1.0 / cardinality
            expected_return = float(weights_array @ mu)
            variance = float(weights_array @ cov @ weights_array)
            objective = expected_return - risk_aversion * variance
            volatility = float(np.sqrt(max(variance, 0.0)))
            selected = [asset_list[idx] for idx in combo]
            bitstring = "".join("1" if idx in combo else "0" for idx in range(len(asset_list)))
            weights = {
                asset: float(weights_array[idx])
                for idx, asset in enumerate(asset_list)
                if weights_array[idx] > 0
            }
            candidate = QuantumPortfolioResult(
                selected_assets=selected,
                bitstring=bitstring,
                weights=weights,
                expected_return=expected_return,
                volatility=volatility,
                objective=objective,
                risk_aversion=risk_aversion,
                cardinality=cardinality,
                search_space=0,
            )
            if best is None or candidate.objective > best.objective:
                best = candidate

        assert best is not None
        return QuantumPortfolioResult(
            selected_assets=best.selected_assets,
            bitstring=best.bitstring,
            weights=best.weights,
            expected_return=best.expected_return,
            volatility=best.volatility,
            objective=best.objective,
            risk_aversion=risk_aversion,
            cardinality=cardinality,
            search_space=search_space,
        )

    @staticmethod
    def _validate(
        assets: Sequence[str],
        expected_returns: np.ndarray,
        covariance: np.ndarray,
        cardinality: int,
    ) -> None:
        n_assets = len(assets)
        if n_assets == 0:
            raise ValueError("At least one asset is required")
        if expected_returns.shape != (n_assets,):
            raise ValueError("expected_returns length must match assets")
        if covariance.shape != (n_assets, n_assets):
            raise ValueError("covariance must be a square matrix matching assets")
        if cardinality < 1 or cardinality > n_assets:
            raise ValueError("cardinality must be between 1 and number of assets")
        if not np.allclose(covariance, covariance.T, atol=1e-10):
            raise ValueError("covariance must be symmetric")
