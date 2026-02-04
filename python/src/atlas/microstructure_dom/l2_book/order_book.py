"""
L2 Order Book Data Structure
Handles depth of market data.
"""
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PriceLevel:
    price: float
    volume: float
    orders: int = 0

class OrderBook:
    """
    L2 Order Book representation.
    """
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids: List[PriceLevel] = []
        self.asks: List[PriceLevel] = []
        self.timestamp = datetime.now()
        
    def update(self, bids: List[Dict], asks: List[Dict]):
        """
        Update book from snapshot or delta.
        """
        self.bids = [PriceLevel(p['price'], p['volume']) for p in bids]
        self.asks = [PriceLevel(p['price'], p['volume']) for p in asks]
        self.timestamp = datetime.now()
        
    def get_mid_price(self) -> float:
        if not self.bids or not self.asks:
            return 0.0
        return (self.bids[0].price + self.asks[0].price) / 2.0
        
    def get_imbalance(self, depth: int = 5) -> float:
        """Calculate volume imbalance at top N levels."""
        bid_vol = sum(b.volume for b in self.bids[:depth])
        ask_vol = sum(a.volume for a in self.asks[:depth])
        
        if bid_vol + ask_vol == 0:
            return 0.0
            
        return (bid_vol - ask_vol) / (bid_vol + ask_vol)
