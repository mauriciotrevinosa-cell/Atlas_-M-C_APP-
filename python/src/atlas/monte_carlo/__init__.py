"""
Monte Carlo Simulation Module

Advanced Monte Carlo with:
- Multiple stochastic processes (GBM, Heston, Jump-Diffusion)
- Variance reduction (Antithetic, Control, Quasi-random)
- Path analysis and convergence diagnostics

Copyright © 2026 M&C. All Rights Reserved.
"""

from .simulator import (
    MonteCarloSimulator,
    SimulationConfig,
    SimulationResults,
    ProcessType,
    VarianceReduction
)

__all__ = [
    'MonteCarloSimulator',
    'SimulationConfig',
    'SimulationResults',
    'ProcessType',
    'VarianceReduction'
]
