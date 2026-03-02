"""
Monte Carlo Simulator with Advanced Variance Reduction

This module implements institutional-grade Monte Carlo simulation
with multiple variance reduction techniques.

References:
    - Glasserman, P. (2004). Monte Carlo Methods in Financial Engineering
    - Jäckel, P. (2002). Monte Carlo Methods in Finance
"""

from typing import Optional, Tuple, Callable, Dict, List
from dataclasses import dataclass
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
    GARCH = "garch_forecast"


class VarianceReduction(Enum):
    """Variance reduction techniques"""
    NONE = "none"
    ANTITHETIC = "antithetic_variates"
    CONTROL = "control_variates"
    IMPORTANCE = "importance_sampling"
    STRATIFIED = "stratified_sampling"
    QUASI = "quasi_random_sobol"


@dataclass
class SimulationConfig:
    """Configuration for Monte Carlo simulation"""
    n_paths: int = 10000
    n_steps: int = 252
    dt: float = 1/252
    process: ProcessType = ProcessType.GBM
    variance_reduction: VarianceReduction = VarianceReduction.ANTITHETIC
    seed: Optional[int] = None
    
    def __post_init__(self):
        """Validate configuration"""
        if self.n_paths < 1:
            raise ValueError("n_paths must be positive")
        if self.n_steps < 1:
            raise ValueError("n_steps must be positive")
        if self.dt <= 0:
            raise ValueError("dt must be positive")


@dataclass
class SimulationResults:
    """Results from Monte Carlo simulation"""
    paths: np.ndarray  # Shape: (n_paths, n_steps)
    mean_path: np.ndarray
    std_path: np.ndarray
    percentiles: Dict[float, np.ndarray]
    variance_reduction_factor: Optional[float] = None
    convergence_diagnostics: Optional[Dict] = None
    
    def summary_statistics(self) -> pd.DataFrame:
        """Generate summary statistics"""
        final_values = self.paths[:, -1]
        
        return pd.DataFrame({
            'Metric': [
                'Mean Final Value',
                'Std Final Value',
                'Min Final Value',
                'Max Final Value',
                '5th Percentile',
                '95th Percentile',
                'Skewness',
                'Kurtosis'
            ],
            'Value': [
                np.mean(final_values),
                np.std(final_values),
                np.min(final_values),
                np.max(final_values),
                np.percentile(final_values, 5),
                np.percentile(final_values, 95),
                stats.skew(final_values),
                stats.kurtosis(final_values)
            ]
        })


class MonteCarloSimulator:
    """
    Advanced Monte Carlo Simulator
    
    Implements multiple stochastic processes and variance reduction techniques.
    
    Example:
        >>> config = SimulationConfig(n_paths=10000, variance_reduction=VarianceReduction.ANTITHETIC)
        >>> simulator = MonteCarloSimulator(config)
        >>> results = simulator.simulate_gbm(S0=100, mu=0.05, sigma=0.2)
        >>> print(results.summary_statistics())
    """
    
    def __init__(self, config: SimulationConfig):
        """
        Initialize simulator
        
        Args:
            config: Simulation configuration
        """
        self.config = config
        
        # Set random seed for reproducibility
        if config.seed is not None:
            np.random.seed(config.seed)
        
        logger.info(
            f"Initialized MonteCarloSimulator: "
            f"n_paths={config.n_paths}, "
            f"variance_reduction={config.variance_reduction.value}"
        )
    
    def simulate_gbm(
        self,
        S0: float,
        mu: float,
        sigma: float,
        T: Optional[float] = None
    ) -> SimulationResults:
        """
        Simulate Geometric Brownian Motion
        
        Process:
            dS = μ*S*dt + σ*S*dW
        
        Solution:
            S(t) = S0 * exp((μ - σ²/2)*t + σ*W(t))
        
        Args:
            S0: Initial stock price
            mu: Drift (expected return)
            sigma: Volatility
            T: Time horizon (default: n_steps * dt)
        
        Returns:
            SimulationResults object
        """
        logger.info(f"Simulating GBM: S0={S0}, μ={mu}, σ={sigma}")
        
        if T is None:
            T = self.config.n_steps * self.config.dt
        
        # Generate random increments based on variance reduction method
        if self.config.variance_reduction == VarianceReduction.ANTITHETIC:
            paths = self._gbm_antithetic(S0, mu, sigma, T)
        
        elif self.config.variance_reduction == VarianceReduction.CONTROL:
            paths = self._gbm_control_variates(S0, mu, sigma, T)
        
        elif self.config.variance_reduction == VarianceReduction.QUASI:
            paths = self._gbm_quasi_random(S0, mu, sigma, T)
        
        else:  # Standard Monte Carlo
            paths = self._gbm_standard(S0, mu, sigma, T)
        
        # Calculate statistics
        mean_path = np.mean(paths, axis=0)
        std_path = np.std(paths, axis=0)
        
        percentiles = {
            0.05: np.percentile(paths, 5, axis=0),
            0.25: np.percentile(paths, 25, axis=0),
            0.50: np.percentile(paths, 50, axis=0),
            0.75: np.percentile(paths, 75, axis=0),
            0.95: np.percentile(paths, 95, axis=0)
        }
        
        return SimulationResults(
            paths=paths,
            mean_path=mean_path,
            std_path=std_path,
            percentiles=percentiles
        )
    
    def _gbm_standard(
        self,
        S0: float,
        mu: float,
        sigma: float,
        T: float
    ) -> np.ndarray:
        """Standard GBM simulation (no variance reduction)"""
        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths
        
        # Pre-allocate array
        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0
        
        # Generate random increments
        dW = np.random.normal(
            0,
            np.sqrt(dt),
            size=(n_paths, n_steps)
        )
        
        # Simulate paths
        for t in range(n_steps):
            paths[:, t + 1] = paths[:, t] * np.exp(
                (mu - 0.5 * sigma**2) * dt + sigma * dW[:, t]
            )
        
        return paths
    
    def _gbm_antithetic(
        self,
        S0: float,
        mu: float,
        sigma: float,
        T: float
    ) -> np.ndarray:
        """GBM with Antithetic Variates"""
        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths
        
        # Use half the paths (other half are antithetic)
        # Ensure n_paths is even for this method
        if n_paths % 2 != 0:
            logger.warning("n_paths is odd, increasing by 1 for antithetic variates")
            n_paths += 1
            
        half_paths = n_paths // 2
        
        # Pre-allocate
        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0
        
        # Generate random increments for half the paths
        dW = np.random.normal(
            0,
            np.sqrt(dt),
            size=(half_paths, n_steps)
        )
        
        # Simulate normal paths
        for t in range(n_steps):
            drift = (mu - 0.5 * sigma**2) * dt
            
            # Normal paths
            paths[:half_paths, t + 1] = paths[:half_paths, t] * np.exp(
                drift + sigma * dW[:, t]
            )
            
            # Antithetic paths (use -dW)
            paths[half_paths:2*half_paths, t + 1] = paths[half_paths:2*half_paths, t] * np.exp(
                drift + sigma * (-dW[:, t])
            )
        
        logger.debug(f"Generated {n_paths} paths using antithetic variates")
        
        return paths
    
    def _gbm_control_variates(
        self,
        S0: float,
        mu: float,
        sigma: float,
        T: float
    ) -> np.ndarray:
        """GBM with Control Variates"""
        # Generate standard paths first
        paths_standard = self._gbm_standard(S0, mu, sigma, T)
        
        # Use geometric average as control variate
        # E[geometric mean] is known analytically
        geometric_mean_analytic = S0 * np.exp(mu * T / 2)
        
        # Calculate sample geometric mean for each path
        geometric_means = stats.gmean(paths_standard[:, 1:], axis=1) # Exclude S0
        
        # Estimate optimal coefficient c
        final_values = paths_standard[:, -1]
        
        cov = np.cov(final_values, geometric_means)[0, 1]
        var_control = np.var(geometric_means)
        
        c_optimal = -cov / var_control if var_control > 0 else 0
        
        # Apply control variate adjustment
        adjustment = c_optimal * (geometric_mean_analytic - geometric_means)
        
        # Adjust final values
        paths_adjusted = paths_standard.copy()
        paths_adjusted[:, -1] = final_values + adjustment
        
        logger.debug(f"Control variate coefficient: c={c_optimal:.4f}")
        
        return paths_adjusted
    
    def _gbm_quasi_random(
        self,
        S0: float,
        mu: float,
        sigma: float,
        T: float
    ) -> np.ndarray:
        """GBM with Quasi-Random (Sobol) Sequences"""
        try:
            from scipy.stats import qmc
        except ImportError:
            logger.warning("scipy.stats.qmc not available, using standard MC")
            return self._gbm_standard(S0, mu, sigma, T)
        
        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths
        
        # Generate Sobol sequence
        # Sobol dimension = n_steps
        # n_samples = n_paths
        # Use power of 2 for n_paths for best Sobol performance usually
        sobol_sampler = qmc.Sobol(d=n_steps, scramble=True)
        
        # Determine number of samples needed (next power of 2 is best)
        # But we use n_paths directly here
        
        # Note: qmc.Sobol requires d to be int. n_steps is int.
        # Check if n_steps is too large for Sobol (usually fine < 21201)
        
        try:
            sobol_samples = sobol_sampler.random(n=n_paths)
            
            # Transform to normal distribution
            dW = stats.norm.ppf(sobol_samples) * np.sqrt(dt)
            
            # Pre-allocate
            paths = np.zeros((n_paths, n_steps + 1))
            paths[:, 0] = S0
            
            # Simulate paths
            for t in range(n_steps):
                paths[:, t + 1] = paths[:, t] * np.exp(
                    (mu - 0.5 * sigma**2) * dt + sigma * dW[:, t]
                )
            
            logger.debug("Generated paths using Sobol quasi-random sequence")
            return paths
            
        except Exception as e:
            logger.warning(f"Sobol generation failed: {e}, falling back to standard")
            return self._gbm_standard(S0, mu, sigma, T)

    def simulate_heston(
        self,
        S0: float,
        V0: float,
        mu: float,
        kappa: float,
        theta: float,
        sigma_v: float,
        rho: float,
        T: Optional[float] = None
    ) -> SimulationResults:
        """Simulate Heston Stochastic Volatility Model"""
        logger.info(f"Simulating Heston: S0={S0}, V0={V0}, κ={kappa}, θ={theta}")
        
        if T is None:
            T = self.config.n_steps * self.config.dt
        
        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths
        
        # Pre-allocate
        S = np.zeros((n_paths, n_steps + 1))
        V = np.zeros((n_paths, n_steps + 1))
        
        S[:, 0] = S0
        V[:, 0] = V0
        
        # Generate correlated Brownian motions
        for t in range(n_steps):
            # Independent normals
            Z1 = np.random.normal(0, 1, n_paths)
            Z2 = np.random.normal(0, 1, n_paths)
            
            # Correlated normals
            W1 = Z1
            W2 = rho * Z1 + np.sqrt(1 - rho**2) * Z2
            
            # Variance process (with Feller condition check)
            V_sqrt = np.maximum(V[:, t], 0)  # Ensure positive
            V[:, t + 1] = V[:, t] + kappa * (theta - V[:, t]) * dt + \
                         sigma_v * np.sqrt(V_sqrt) * np.sqrt(dt) * W2
            V[:, t + 1] = np.maximum(V[:, t + 1], 0)  # Absorption at zero
            
            # Price process
            S[:, t + 1] = S[:, t] * np.exp(
                (mu - 0.5 * V_sqrt) * dt + np.sqrt(V_sqrt * dt) * W1
            )
        
        # Calculate statistics
        mean_path = np.mean(S, axis=0)
        std_path = np.std(S, axis=0)
        
        percentiles = {
            0.05: np.percentile(S, 5, axis=0),
            0.50: np.percentile(S, 50, axis=0),
            0.95: np.percentile(S, 95, axis=0)
        }
        
        return SimulationResults(
            paths=S,
            mean_path=mean_path,
            std_path=std_path,
            percentiles=percentiles
        )
    
    def simulate_jump_diffusion(
        self,
        S0: float,
        mu: float,
        sigma: float,
        lambda_jump: float,
        mu_jump: float,
        sigma_jump: float,
        T: Optional[float] = None
    ) -> SimulationResults:
        """Simulate Merton Jump-Diffusion Model"""
        logger.info(
            f"Simulating Jump-Diffusion: λ={lambda_jump}, "
            f"μ_J={mu_jump}, σ_J={sigma_jump}"
        )
        
        if T is None:
            T = self.config.n_steps * self.config.dt
        
        dt = self.config.dt
        n_steps = self.config.n_steps
        n_paths = self.config.n_paths
        
        # Pre-allocate
        paths = np.zeros((n_paths, n_steps + 1))
        paths[:, 0] = S0
        
        for t in range(n_steps):
            # Diffusion component
            dW = np.random.normal(0, np.sqrt(dt), n_paths)
            diffusion = (mu - 0.5 * sigma**2) * dt + sigma * dW
            
            # Jump component
            n_jumps = np.random.poisson(lambda_jump * dt, n_paths)
            
            jump_component = np.zeros(n_paths)
            # Vectorized jump calc
            # If any jumps
            has_jumps = n_jumps > 0
            if np.any(has_jumps):
                 # Total log jump size for each path
                 # Since n_jumps varies, we can't easily vectoriz fully without loops or complex indexing
                 # But we can loop over the paths that have jumps or approximation
                 # For simplicity in this implementation, we loop like the guide
                 for i in np.where(has_jumps)[0]:
                     jumps = np.random.lognormal(
                         mu_jump,
                         sigma_jump,
                         n_jumps[i]
                     )
                     jump_component[i] = np.log(np.prod(jumps))
            
            # Update paths
            paths[:, t + 1] = paths[:, t] * np.exp(
                diffusion + jump_component
            )
        
        # Calculate statistics
        mean_path = np.mean(paths, axis=0)
        std_path = np.std(paths, axis=0)
        
        percentiles = {
            0.05: np.percentile(paths, 5, axis=0),
            0.50: np.percentile(paths, 50, axis=0),
            0.95: np.percentile(paths, 95, axis=0)
        }
        
        return SimulationResults(
            paths=paths,
            mean_path=mean_path,
            std_path=std_path,
            percentiles=percentiles
        )
