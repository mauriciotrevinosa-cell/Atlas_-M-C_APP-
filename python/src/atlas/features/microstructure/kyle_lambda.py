"""
Kyle's Lambda (Market Impact)

Measures price impact of order flow (liquidity).
Based on Kyle (1985).

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def estimate_kyle_lambda(
    data: pd.DataFrame, 
    window: int = 20
) -> pd.Series:
    """
    Estimate Kyle's Lambda (Price Impact)
    
    Model:
        ΔP = λ * Q + ε
        
    Where:
        ΔP: Price change
        Q: Signed volume (Order Flow)
        λ: Price impact coefficient
    
    Args:
        data: DataFrame with Close, Volume
        window: Rolling regression window
    
    Returns:
        pd.Series: Lambda values (rolling)
    """
    close = data['Close']
    volume = data['Volume']
    
    # Price changes
    price_change = close.diff()
    
    # Estimate trade direction (Tick Rule)
    direction = np.sign(price_change)
    direction = direction.replace(0, np.nan).ffill().fillna(1)
    
    # Signed Order Flow (Q)
    signed_flow = volume * direction
    
    # Rolling regression estimates
    # λ = Cov(ΔP, Q) / Var(Q)
    
    rolling_cov = price_change.rolling(window=window).cov(signed_flow)
    rolling_var = signed_flow.rolling(window=window).var()
    
    # Avoid division by zero
    kyle_lambda = rolling_cov / rolling_var.replace(0, np.nan)
    
    logger.debug(f"Calculated Kyle's Lambda (window={window})")
    
    return kyle_lambda
