"""
Order Book Imbalance

Measures the imbalance between buy and sell orders in the limit order book.

Copyright © 2026 M&C. All Rights Reserved.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def calculate_obi(
    bid_vol: pd.Series, 
    ask_vol: pd.Series
) -> pd.Series:
    """
    Calculate Order Book Imbalance (OBI)
    
    OBI = (BidVol - AskVol) / (BidVol + AskVol)
    
    Range: [-1, 1]
    -1: Full sell pressure
    1: Full buy pressure
    
    Args:
        bid_vol: Volume at best bid
        ask_vol: Volume at best ask
    
    Returns:
        pd.Series: OBI values
    """
    total_vol = bid_vol + ask_vol
    imbalance = (bid_vol - ask_vol) / total_vol.replace(0, np.nan)
    
    return imbalance.fillna(0)
