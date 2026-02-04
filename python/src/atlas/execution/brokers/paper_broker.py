"""
Paper Execution Broker
Simulates order execution without real-money risk.
"""
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

class PaperBroker:
    """
    Paper Broker for simulated execution.
    Features:
    - Order validation
    - Instant fills (or simulated latency)
    - Slippage modeling hooks
    """
    def __init__(self, initial_capital: float = 100000.0):
        self.capital = initial_capital
        self.positions = {}
        self.orders = {}
        
    def submit_order(self, symbol: str, quantity: float, side: str, order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
        """
        Submit simulated order.
        """
        order_id = str(uuid.uuid4())
        
        # Basic validation
        if quantity <= 0:
            return {"error": "Invalid quantity"}
            
        order = {
            "id": order_id,
            "symbol": symbol,
            "quantity": quantity,
            "side": side,
            "type": order_type,
            "status": "filled", # Instant fill for now
            "timestamp": datetime.now().isoformat(),
            "avg_fill_price": price if price else 100.0 # Mock price
        }
        
        self.orders[order_id] = order
        self._update_position(symbol, quantity, side)
        
        return order

    def _update_position(self, symbol: str, quantity: float, side: str):
        current_qty = self.positions.get(symbol, 0)
        if side.lower() == "buy":
            self.positions[symbol] = current_qty + quantity
        elif side.lower() == "sell":
            self.positions[symbol] = current_qty - quantity

    def get_portfolio(self) -> Dict[str, Any]:
        return {
            "cash": self.capital,
            "positions": self.positions,
            "equity": self.capital # Simplified
        }
