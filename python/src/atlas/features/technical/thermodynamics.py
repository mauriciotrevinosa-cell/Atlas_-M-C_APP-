"""
Thermodynamic Finance Features

Ising Model of Ferromagnetism mapping market microstructure (volatility/sentiment) 
to Spin Dynamics and Phase Transitions.

Copyright (c) 2026 M&C. All Rights Reserved.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class IsingSystem:
    """Core Physics Engine for Market Sentiment."""
    def __init__(self, n: int, target_sentiment: float, gain: float):
        self.n = n
        self.target = target_sentiment
        self.gain = gain
        np.random.seed(42)  # For deterministic behavior if desired
        self.lattice = np.random.choice([-1, 1], size=(n, n, n))
        
    def _get_neighbor_sum(self, x: int, y: int, z: int) -> int:
        n = self.n
        lat = self.lattice
        return (
            lat[(x+1)%n, y, z] + lat[(x-1)%n, y, z] +
            lat[x, (y+1)%n, z] + lat[x, (y-1)%n, z] +
            lat[x, y, (z+1)%n] + lat[x, y, (z-1)%n]
        )

    def metropolis_step(self, temp: float) -> int:
        n = self.n
        lat = self.lattice
        
        current_up_ratio = np.mean(lat == 1)
        bias = self.gain * (self.target - current_up_ratio)
        change_count = 0
        
        for _ in range(n**3):
            x, y, z = np.random.randint(0, n, 3)
            spin = lat[x, y, z]
            neighbor_sum = self._get_neighbor_sum(x, y, z)
            
            # dE for flip s -> -s
            dE = 2 * spin * (neighbor_sum + bias)
            
            if dE <= 0 or np.random.rand() < np.exp(-dE / temp):
                lat[x, y, z] *= -1
                change_count += 1
                
        return change_count

    def get_observables(self) -> float:
        return np.mean(self.lattice)

def analyze_phase_transition(
    grid_size: int = 12,
    target_sentiment: float = 0.5,
    control_gain: float = 5.0,
    temp_range: tuple = (10.0, 0.1),
    temp_steps: int = 50,
    steps_per_temp: int = 100
) -> pd.DataFrame:
    """
    Simulates the market cooling down from Chaos to Order.
    Tracks Susceptibility (Variance of Magnetization) to find Critical Temp.
    
    Returns:
        pd.DataFrame: DataFrame containing Temperature, Magnetization, Susceptibility
    """
    sim = IsingSystem(n=grid_size, target_sentiment=target_sentiment, gain=control_gain)
    temps = np.linspace(temp_range[0], temp_range[1], temp_steps)
    results = []
    
    logger.debug("Starting Ising Model Analysis...")
    for T in temps:
        changes = 0
        magnetizations = []
        
        for step in range(steps_per_temp):
            c = sim.metropolis_step(T)
            changes += c
            if step > steps_per_temp * 0.8:
                m = sim.get_observables()
                magnetizations.append(m)
                
        avg_m = np.mean(magnetizations) if magnetizations else 0
        var_m = np.var(magnetizations) if magnetizations else 0
        # Susceptibility
        chi = var_m / T if T > 0 else 0
        
        results.append({
            "Temperature": T,
            "Magnetization": avg_m,
            "Susceptibility": chi,
            "Activity": changes
        })
        
    df = pd.DataFrame(results)
    
    # Identify Critical Phase Transition (Peak susceptibility)
    try:
        critical_idx_scalar = df['Susceptibility'].idxmax()
        tc = df.loc[critical_idx_scalar, 'Temperature']
        logger.debug(f"Found Critical Temp (Tc) at: {tc:.2f}")
    except (ValueError, KeyError, AssertionError):
        pass
        
    return df
