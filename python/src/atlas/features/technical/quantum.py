"""
Quantum Finance Features

Wave Function Collapse and Probability Density calculation for 
price action behavior modeling.

Copyright (c) 2026 M&C. All Rights Reserved.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

def wave_function_collapse(
    data: pd.Series,
    momentum_lookback: int = 30,
    volatility_lookback: int = 60,
    resolution: int = 2048,
    evolution_time: float = 0.5
) -> Dict[str, Any]:
    """
    Models the asset price as a quantum wave function.
    
    Args:
        data: Price series up to the measurement date.
        momentum_lookback: Days to calculate drift/momentum.
        volatility_lookback: Days to calculate uncertainty (width of wave).
        resolution: Number of points in the price space grid.
        evolution_time: Time steps for the split-step Fourier evolution.
        
    Returns:
        Dict: Contains 'price_space', 'probability_density', 'center_price',
              'uncertainty', 'drift'
    """
    if len(data) < volatility_lookback:
        raise ValueError("Not enough historical data for the requested lookbacks.")
        
    recent_prices = data.tail(momentum_lookback)
    vol_prices = data.tail(volatility_lookback)
    
    # 1. Quantum State Preparation
    center_price = recent_prices.iloc[-1]
    price_std = vol_prices.std() * 1.5 
    
    trend = (recent_prices.iloc[-1] - recent_prices.iloc[0]) / len(recent_prices)
    momentum = trend * 0.1 
    
    logger.debug(f"Quantum Init - Center: {center_price:.2f}, Sigma: {price_std:.2f}, Drift: {trend:.2f}")

    # 2. Build the Grid (Price Space)
    x_min = center_price - price_std * 5
    x_max = center_price + price_std * 5
    
    x = np.linspace(x_min, x_max, resolution)
    dx = x[1] - x[0]
    
    # 3. Initial Wave Function (Gaussian Wave Packet)
    psi = np.exp(-0.5 * ((x - center_price) / price_std)**2) * np.exp(1j * momentum * x)
    psi /= np.sqrt(np.sum(np.abs(psi)**2) * dx) # Normalize
    
    # 4. Time Evolution (Free-Particle Schrodinger via Fourier)
    k = 2 * np.pi * np.fft.fftfreq(len(x), d=dx)
    psi_k = np.fft.fft(psi)
    psi_k *= np.exp(-0.5j * (k**2) * evolution_time)
    psi_evolved = np.fft.ifft(psi_k)
    
    prob_density = np.abs(psi_evolved)**2
    
    return {
        'price_space': x,
        'probability_density': prob_density,
        'center_price': center_price,
        'uncertainty': price_std,
        'drift': trend
    }
