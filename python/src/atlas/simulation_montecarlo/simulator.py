"""
Monte Carlo Simulator — Phase 8

Advanced Monte Carlo with multiple stochastic processes and variance reduction.

References:
    Glasserman, P. (2004). Monte Carlo Methods in Financial Engineering.
    Jäckel, P. (2002). Monte Carlo Methods in Finance.

Copyright © 2026 M&C. All Rights Reserved.
"""

from typing import Optional, Tuple, Dict
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
import pandas as pd
from scipy import stats
import logging

logger = logging.getLogger(__name__)


class ProcessType(Enum):
    """Stochastic process types"""
    GBM = "geometric_brownian_motion"
    HESTON = "heston_stochastic_volatility"
    JUMP_DIFFUSION = "merton_jump_diffusion"


class VarianceReduction(Enum):
    """Variance reduction techniques"""
    NONE = "none"
    ANTITHETIC = "antithetic_variates"
    CONTROL = "control_variates"
    QUASI = "quasi_random_sobol"


@dataclass
class SimulationConfig:
    """Configuration for Monte Carlo simulation"""
    n_paths: int = 10_000
    n_steps: int = 252
    dt: float = 1 / 252
    process: ProcessType = ProcessType.GBM
    variance_reduction: VarianceReduction = VarianceReduction.ANTITHETIC
    seed: Optional[int] = None

    def __post_init__(self):
        if self.n_paths < 1:
            raise ValueError("n_paths must be positive")
        if self.n_steps < 1:
            raise ValueError("n_steps must be positive")
        if self.dt <= 0:
            raise ValueError("dt must be positive")


@dataclass
class SimulationResults:
    """Results from a Monte Carlo simulation"""
    paths: np.ndarray           # Shape: (n_paths, n_steps+1)
    mean_path: np.ndarray
    std_path: np.ndarray
    percentiles: Dict[float, np.ndarray]
    variance_reduction_factor: Optional[float] = None

    def summary_statistics(self) -> pd.DataFrame:
        """Generate summary statistics for final prices"""
        final = self.paths[:, -1]
        return pd.DataFrame({
            "Metric": [
                "Mean", "Std", "Min", "Max",
                "5th Pct", "25th Pct", "Median", "75th Pct", "95th Pct",
                "Skewness", "Kurtosis"
            ],
            "Value": [
                np.mean(final), np.std(final), np.min(final), np.max(final),
                np.percentile(final, 5), np.percentile(final, 25),
                np.percentile(final, 50), np.percentile(final, 75),
                np.percentile(final, 95),
                float(stats.skew(final)), float(stats.kurtosis(final))
            ]
        })


class MonteCarloSimulator:
    """
    Advanced Monte Carlo Simulator.

    Supports GBM, Heston stochastic volatility, and Merton jump-diffusion
    processes, with antithetic, control-variate, and quasi-random (Sobol)
    variance reduction.

    Example:
        >>> cfg = SimulationConfig(n_paths=10000, variance_reduction=VarianceReduction.ANTITHETIC, seed=42)
        >>> sim = MonteCarloSimulator(cfg)
        >>> results = sim.simulate_gbm(S0=100, mu=0.10, sigma=0.20)
        >>> print(results.summary_statistics())
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        if config.seed is not None:
            np.random.seed(config.seed)
        logger.info(
            "Initialized MonteCarloSimulator — "
            f"n_paths={config.n_paths}, vr={config.variance_reduction.value}"
        )

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def simulate_gbm(
        self,
        S0: float,
        mu: float,
        sigma: float,
        T: Optional[float] = None,
    ) -> SimulationResults:
        """
        Simulate Geometric Brownian Motion.

        dS = μ S dt + σ S dW
        S(t) = S0 exp((μ − σ²/2)t + σ W(t))

        Args:
            S0: Initial price
            mu: Drift (annualised)
            sigma: Volatility (annualised)
            T: Time horizon in years (default: n_steps * dt)

        Returns:
            SimulationResults
        """
        logger.info(f"simulate_gbm: S0={S0}, μ={mu}, σ={sigma}")
        if T is None:
            T = self.config.n_steps * self.config.dt

        vr = self.config.variance_reduction
        if vr == VarianceReduction.ANTITHETIC:
            paths = self._gbm_antithetic(S0, mu, sigma, T)
        elif vr == VarianceReduction.CONTROL:
            paths = self._gbm_control_variates(S0, mu, sigma, T)
        elif vr == VarianceReduction.QUASI:
            paths = self._gbm_quasi_random(S0, mu, sigma, T)
        else:
            paths = self._gbm_standard(S0, mu, sigma, T)

        return self._make_results(paths)

    def simulate_heston(
        self,
        S0: float,
        V0: float,
        mu: float,
        kappa: float,
        theta: float,
        sigma_v: float,
        rho: float,
        T: Optional[float] = None,
    ) -> SimulationResults:
        """
        Simulate Heston Stochastic Volatility Model.

        dS = μ S dt + √V S dW₁
        dV = κ(θ − V) dt + σᵥ √V dW₂
        Corr(dW₁, dW₂) = ρ

        Args:
            S0: Initial price
            V0: Initial variance
            mu: Drift
            kappa: Mean-reversion speed
            theta: Long-run variance
            sigma_v: Vol-of-vol
            rho: Correlation between price and variance shocks
            T: Time horizon

        Returns:
            SimulationResults

        Reference:
            Heston (1993). "A Closed-Form Solution for Options with Stochastic Volatility"
        """
        logger.info(f"simulate_heston: S0={S0}, V0={V0}, κ={kappa}")
        if T is None:
            T = self.config.n_steps * self.config.dt

        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths

        S = np.zeros((n_paths, n_steps + 1))
        V = np.zeros((n_paths, n_steps + 1))
        S[:, 0] = S0
        V[:, 0] = V0

        for t in range(n_steps):
            Z1 = np.random.normal(0, 1, n_paths)
            Z2 = np.random.normal(0, 1, n_paths)
            W1 = Z1
            W2 = rho * Z1 + np.sqrt(1 - rho ** 2) * Z2

            V_sqrt = np.maximum(V[:, t], 0)
            V[:, t + 1] = (
                V[:, t]
                + kappa * (theta - V[:, t]) * dt
                + sigma_v * np.sqrt(V_sqrt * dt) * W2
            )
            V[:, t + 1] = np.maximum(V[:, t + 1], 0)

            S[:, t + 1] = S[:, t] * np.exp(
                (mu - 0.5 * V_sqrt) * dt
                + np.sqrt(V_sqrt * dt) * W1
            )

        return self._make_results(S)

    def simulate_jump_diffusion(
        self,
        S0: float,
        mu: float,
        sigma: float,
        lambda_jump: float,
        mu_jump: float,
        sigma_jump: float,
        T: Optional[float] = None,
    ) -> SimulationResults:
        """
        Simulate Merton Jump-Diffusion Model.

        dS = μ S dt + σ S dW + S (J−1) dN
        J ~ LogNormal(μ_J, σ_J²);  dN ~ Poisson(λ dt)

        Args:
            S0: Initial price
            mu: Continuous drift
            sigma: Diffusion volatility
            lambda_jump: Jump intensity (jumps/year)
            mu_jump: Mean log-jump size
            sigma_jump: Std of log-jump size
            T: Time horizon

        Returns:
            SimulationResults

        Reference:
            Merton (1976). "Option Pricing when Underlying Stock Returns are Discontinuous"
        """
        logger.info(f"simulate_jump_diffusion: λ={lambda_jump}, μ_J={mu_jump}")
        if T is None:
            T = self.config.n_steps * self.config.dt

        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths

        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0

        for t in range(n_steps):
            dW = np.random.normal(0, np.sqrt(dt), n_paths)
            diffusion = (mu - 0.5 * sigma ** 2) * dt + sigma * dW

            n_jumps = np.random.poisson(lambda_jump * dt, n_paths)
            jump_component = np.zeros(n_paths)
            for i in range(n_paths):
                if n_jumps[i] > 0:
                    jumps = np.random.lognormal(mu_jump, sigma_jump, n_jumps[i])
                    jump_component[i] = np.log(np.prod(jumps))

            paths[:, t + 1] = paths[:, t] * np.exp(diffusion + jump_component)

        return self._make_results(paths)

    # ------------------------------------------------------------------ #
    # GBM internals                                                        #
    # ------------------------------------------------------------------ #

    def _gbm_standard(self, S0: float, mu: float, sigma: float, T: float) -> np.ndarray:
        """Standard GBM without variance reduction."""
        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths

        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0
        dW = np.random.normal(0, np.sqrt(dt), (n_paths, n_steps))
        drift = (mu - 0.5 * sigma ** 2) * dt

        for t in range(n_steps):
            paths[:, t + 1] = paths[:, t] * np.exp(drift + sigma * dW[:, t])
        return paths

    def _gbm_antithetic(self, S0: float, mu: float, sigma: float, T: float) -> np.ndarray:
        """
        GBM with Antithetic Variates.

        For each path drawn with Z, generate a paired path with −Z.
        Induces negative correlation → reduces variance.

        Reference: Glasserman (2004), Section 4.1
        """
        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths
        half = n_paths // 2

        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0
        dW = np.random.normal(0, np.sqrt(dt), (half, n_steps))
        drift = (mu - 0.5 * sigma ** 2) * dt

        for t in range(n_steps):
            paths[:half, t + 1] = paths[:half, t] * np.exp(drift + sigma * dW[:, t])
            paths[half:2*half, t + 1] = paths[half:2*half, t] * np.exp(drift + sigma * (-dW[:, t]))

        logger.debug("GBM antithetic — %d paths generated", n_paths)
        return paths

    def _gbm_control_variates(self, S0: float, mu: float, sigma: float, T: float) -> np.ndarray:
        """
        GBM with Control Variates using geometric average.

        Ŷ_cv = Ŷ + c(E[C] − Ĉ),  c = −Cov(Ŷ, Ĉ)/Var(Ĉ)

        Reference: Glasserman (2004), Section 4.2
        """
        paths = self._gbm_standard(S0, mu, sigma, T)

        # Geometric mean as control variate
        geometric_mean_analytic = S0 * np.exp(mu * T / 2)
        geometric_means = stats.gmean(paths, axis=1)

        final = paths[:, -1]
        cov = np.cov(final, geometric_means)[0, 1]
        var_ctrl = np.var(geometric_means)
        c = -cov / var_ctrl if var_ctrl > 0 else 0.0

        paths_adj = paths.copy()
        paths_adj[:, -1] = final + c * (geometric_mean_analytic - geometric_means)

        logger.debug("GBM control variates — c=%.4f", c)
        return paths_adj

    def _gbm_quasi_random(self, S0: float, mu: float, sigma: float, T: float) -> np.ndarray:
        """
        GBM with Quasi-Random Sobol Sequences.

        Achieves O(1/n) convergence vs O(1/√n) for pseudo-random.

        Reference: Glasserman (2004), Section 5.1–5.2
        """
        try:
            from scipy.stats import qmc
        except ImportError:
            logger.warning("scipy.stats.qmc unavailable — falling back to standard MC")
            return self._gbm_standard(S0, mu, sigma, T)

        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths

        sampler = qmc.Sobol(d=n_steps, scramble=True)
        sobol_u = sampler.random(n=n_paths)
        dW = stats.norm.ppf(np.clip(sobol_u, 1e-10, 1 - 1e-10)) * np.sqrt(dt)

        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0
        drift = (mu - 0.5 * sigma ** 2) * dt

        for t in range(n_steps):
            paths[:, t + 1] = paths[:, t] * np.exp(drift + sigma * dW[:, t])

        logger.debug("GBM quasi-random Sobol — %d paths", n_paths)
        return paths

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _make_results(self, paths: np.ndarray) -> SimulationResults:
        mean_path = np.mean(paths, axis=0)
        std_path = np.std(paths, axis=0)
        percentiles = {
            0.05: np.percentile(paths, 5, axis=0),
            0.25: np.percentile(paths, 25, axis=0),
            0.50: np.percentile(paths, 50, axis=0),
            0.75: np.percentile(paths, 75, axis=0),
            0.95: np.percentile(paths, 95, axis=0),
        }
        return SimulationResults(
            paths=paths,
            mean_path=mean_path,
            std_path=std_path,
            percentiles=percentiles,
        )


# ------------------------------------------------------------------ #
# Convergence Diagnostics                                              #
# ------------------------------------------------------------------ #

class ConvergenceDiagnostics:
    """Utility tools for diagnosing Monte Carlo convergence."""

    @staticmethod
    def standard_error(estimates: np.ndarray) -> float:
        """SE = σ / √n"""
        return float(np.std(estimates, ddof=1) / np.sqrt(len(estimates)))

    @staticmethod
    def confidence_interval(
        estimates: np.ndarray,
        level: float = 0.95,
    ) -> Tuple[float, float]:
        """Normal CI around the sample mean."""
        mean = np.mean(estimates)
        se = ConvergenceDiagnostics.standard_error(estimates)
        z = stats.norm.ppf((1 + level) / 2)
        margin = z * se
        return (float(mean - margin), float(mean + margin))

    @staticmethod
    def variance_reduction_factor(var_standard: float, var_reduced: float) -> float:
        """VRF = Var(standard) / Var(reduced).  VRF > 1 → improvement."""
        if var_reduced == 0:
            return float("inf")
        return float(var_standard / var_reduced)
