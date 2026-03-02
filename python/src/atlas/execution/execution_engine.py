"""
Execution Engine
=================
Order execution algorithms (TWAP, VWAP) and broker abstractions.

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("atlas.execution")


# ---------------------------------------------------------------------------
# Order Types
# ---------------------------------------------------------------------------

class Order:
    """Represents a trading order."""

    def __init__(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ):
        self.symbol = symbol
        self.side = side  # "buy" or "sell"
        self.quantity = quantity
        self.order_type = order_type  # "market", "limit", "stop"
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.id = f"ORD-{int(time.time()*1000)}"
        self.status = "pending"  # pending, filled, cancelled, rejected
        self.fill_price = None
        self.fill_time = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "symbol": self.symbol, "side": self.side,
            "quantity": self.quantity, "type": self.order_type,
            "status": self.status, "fill_price": self.fill_price,
        }


# ---------------------------------------------------------------------------
# Broker Abstraction
# ---------------------------------------------------------------------------

class BaseBroker(ABC):
    """Abstract base for broker implementations."""

    @abstractmethod
    def submit_order(self, order: Order) -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_balance(self) -> Dict[str, float]:
        pass


class PaperBroker(BaseBroker):
    """Simulated broker for paper trading."""

    def __init__(self, initial_balance: float = 100_000):
        self.balance = initial_balance
        self.positions: Dict[str, Dict] = {}
        self.orders: List[Order] = []
        self.trade_history: List[Dict] = []

    def submit_order(self, order: Order) -> Dict[str, Any]:
        """Instantly fill at market (simulated)."""
        # Simulate fill price with small slippage
        fill_price = order.limit_price or 0  # In paper mode, caller must set
        slippage = fill_price * 0.0005 * (1 if order.side == "buy" else -1)
        order.fill_price = fill_price + slippage
        order.fill_time = time.time()
        order.status = "filled"

        # Update position
        cost = order.fill_price * order.quantity
        if order.side == "buy":
            self.balance -= cost
            self.positions[order.symbol] = {
                "quantity": self.positions.get(order.symbol, {}).get("quantity", 0) + order.quantity,
                "avg_price": order.fill_price,
                "side": "long",
            }
        else:
            self.balance += cost
            current_qty = self.positions.get(order.symbol, {}).get("quantity", 0)
            new_qty = current_qty - order.quantity
            if new_qty <= 0:
                self.positions.pop(order.symbol, None)
            else:
                self.positions[order.symbol]["quantity"] = new_qty

        self.orders.append(order)
        self.trade_history.append(order.to_dict())
        logger.info("Paper fill: %s %s %.4f @ %.2f", order.side, order.symbol, order.quantity, order.fill_price)
        return order.to_dict()

    def cancel_order(self, order_id: str) -> bool:
        for o in self.orders:
            if o.id == order_id and o.status == "pending":
                o.status = "cancelled"
                return True
        return False

    def get_position(self, symbol: str) -> Dict[str, Any]:
        return self.positions.get(symbol, {"quantity": 0, "side": "flat"})

    def get_balance(self) -> Dict[str, float]:
        return {"cash": round(self.balance, 2), "positions": len(self.positions)}


# ---------------------------------------------------------------------------
# Execution Algorithms
# ---------------------------------------------------------------------------

class TWAPExecutor:
    """Time-Weighted Average Price — split order into equal time slices."""

    def __init__(self, broker: BaseBroker, n_slices: int = 10, interval_seconds: float = 60):
        self.broker = broker
        self.n_slices = n_slices
        self.interval = interval_seconds

    def execute(self, symbol: str, side: str, total_qty: float, current_price: float) -> List[Dict]:
        """Execute TWAP order (simulated — instant in paper mode)."""
        slice_qty = total_qty / self.n_slices
        fills = []
        for i in range(self.n_slices):
            # Simulate small price movement per slice
            noise = current_price * np.random.normal(0, 0.0002)
            order = Order(symbol, side, slice_qty, "market", limit_price=current_price + noise)
            fill = self.broker.submit_order(order)
            fills.append(fill)
        avg_fill = np.mean([f["fill_price"] for f in fills if f.get("fill_price")])
        logger.info("TWAP complete: %d slices, avg fill %.4f", self.n_slices, avg_fill)
        return fills


class VWAPExecutor:
    """Volume-Weighted Average Price — weight slices by historical volume profile."""

    def __init__(self, broker: BaseBroker, n_slices: int = 10):
        self.broker = broker
        self.n_slices = n_slices

    def execute(
        self, symbol: str, side: str, total_qty: float,
        current_price: float, volume_profile: Optional[List[float]] = None,
    ) -> List[Dict]:
        """Execute VWAP order."""
        # Default: uniform if no volume profile provided
        if volume_profile is None or len(volume_profile) != self.n_slices:
            volume_profile = [1.0 / self.n_slices] * self.n_slices
        else:
            total = sum(volume_profile)
            volume_profile = [v / total for v in volume_profile]

        fills = []
        for i, weight in enumerate(volume_profile):
            slice_qty = total_qty * weight
            if slice_qty <= 0:
                continue
            noise = current_price * np.random.normal(0, 0.0003)
            order = Order(symbol, side, slice_qty, "market", limit_price=current_price + noise)
            fill = self.broker.submit_order(order)
            fills.append(fill)

        avg_fill = np.mean([f["fill_price"] for f in fills if f.get("fill_price")])
        logger.info("VWAP complete: %d slices, avg fill %.4f", len(fills), avg_fill)
        return fills
