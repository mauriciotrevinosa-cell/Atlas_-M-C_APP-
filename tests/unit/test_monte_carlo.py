"""
Tests for Monte Carlo Module

Copyright © 2026 M&C. All Rights Reserved.
"""

import pytest
import numpy as np
import pandas as pd
from atlas.monte_carlo import (
    MonteCarloSimulator,
    SimulationConfig,
    ProcessType,
    VarianceReduction
)

class TestMonteCarlo:
    """Test suite for Monte Carlo Simulator"""
    
    def test_initialization(self):
        config = SimulationConfig(n_paths=100, n_steps=10)
        sim = MonteCarloSimulator(config)
        assert sim.config.n_paths == 100
        assert sim.config.n_steps == 10

    def test_gbm_simulation(self):
        config = SimulationConfig(n_paths=100, n_steps=50, seed=42)
        sim = MonteCarloSimulator(config)
        
        results = sim.simulate_gbm(S0=100, mu=0.05, sigma=0.2)
        
        assert results.paths.shape == (100, 51)
        assert results.paths[0, 0] == 100
        assert len(results.percentiles) > 0
        
        # Check basic stats
        stats = results.summary_statistics()
        assert isinstance(stats, pd.DataFrame)
        assert 'Mean Final Value' in stats['Metric'].values

    def test_antithetic_variates(self):
        config = SimulationConfig(
            n_paths=100, 
            variance_reduction=VarianceReduction.ANTITHETIC,
            seed=42
        )
        sim = MonteCarloSimulator(config)
        results = sim.simulate_gbm(S0=100, mu=0.05, sigma=0.2)
        
        # Antithetic means paths come in pairs
        # but the public interface just returns all paths
        assert results.paths.shape == (100, 253)

    def test_heston_simulation(self):
        config = SimulationConfig(n_paths=50, n_steps=20, seed=42)
        sim = MonteCarloSimulator(config)
        
        results = sim.simulate_heston(
            S0=100, V0=0.04, mu=0.05, 
            kappa=2.0, theta=0.04, sigma_v=0.3, rho=-0.7
        )
        
        assert results.paths.shape == (50, 21)
        assert (results.paths >= 0).all()

    def test_jump_diffusion(self):
        config = SimulationConfig(n_paths=50, n_steps=20, seed=42)
        sim = MonteCarloSimulator(config)
        
        results = sim.simulate_jump_diffusion(
            S0=100, mu=0.05, sigma=0.2,
            lambda_jump=0.1, mu_jump=-0.1, sigma_jump=0.1
        )
        
        assert results.paths.shape == (50, 21)
