"""Built-in Operations handlers with explicit data provenance.

These handlers never fetch, seed, or infer missing market values.  They only
normalise user/API supplied observations or derive metrics from prior workflow
steps, so an empty input cannot accidentally become convincing demo data.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Dict

import pandas as pd

from atlas.analytics.risk_metrics import (
    calmar_ratio,
    drawdown_summary,
    historical_var,
    sharpe_ratio,
    sortino_ratio,
)

from .engine import StepRegistry


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite number") from exc
    if not isfinite(result):
        raise ValueError(f"{field} must be a finite number")
    return result


def portfolio_snapshot(inputs: Dict[str, Any], _context: Dict[str, Any]) -> Dict[str, Any]:
    """Value an observed portfolio without supplying fictional prices."""
    raw_positions = inputs.get("positions")
    if not isinstance(raw_positions, list):
        raise ValueError("positions must be a list")
    cash = _number(inputs.get("cash", 0), "cash")
    if cash < 0:
        raise ValueError("cash cannot be negative")

    positions = []
    invested = 0.0
    for index, raw in enumerate(raw_positions):
        if not isinstance(raw, dict):
            raise ValueError(f"positions[{index}] must be an object")
        symbol = str(raw.get("symbol") or "").strip().upper()
        if not symbol:
            raise ValueError(f"positions[{index}].symbol is required")
        quantity = _number(raw.get("quantity"), f"positions[{index}].quantity")
        price = _number(raw.get("price"), f"positions[{index}].price")
        if quantity < 0 or price < 0:
            raise ValueError(f"positions[{index}] quantity and price cannot be negative")
        market_value = quantity * price
        invested += market_value
        positions.append({
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "market_value": round(market_value, 6),
        })

    total = cash + invested
    for item in positions:
        item["weight"] = round(item["market_value"] / total, 8) if total else 0.0
    return {
        "positions": positions,
        "position_count": len(positions),
        "cash": round(cash, 6),
        "invested": round(invested, 6),
        "total_value": round(total, 6),
        "provenance": {"kind": "INPUT", "price_field": "positions[].price"},
    }


def portfolio_risk(inputs: Dict[str, Any], _context: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate established Atlas risk metrics from observed period returns."""
    raw_returns = inputs.get("returns")
    if not isinstance(raw_returns, list) or len(raw_returns) < 2:
        raise ValueError("returns must contain at least two observed period returns")
    values = [_number(value, f"returns[{index}]") for index, value in enumerate(raw_returns)]
    returns = pd.Series(values, dtype=float)
    confidence = _number(inputs.get("confidence", 0.95), "confidence")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    risk_free_rate = _number(inputs.get("risk_free_rate", 0), "risk_free_rate")
    sortino = sortino_ratio(returns, risk_free_rate=risk_free_rate)
    return {
        "observations": len(values),
        "drawdown": drawdown_summary(returns),
        "historical_var": historical_var(returns, confidence=confidence),
        "sharpe_ratio": round(sharpe_ratio(returns, risk_free_rate=risk_free_rate), 6),
        "sortino_ratio": round(sortino, 6) if isfinite(sortino) else None,
        "calmar_ratio": calmar_ratio(returns),
        "provenance": {"kind": "COMPUTED", "input": "observed returns"},
    }


def signal_snapshot(inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Expose a signal produced by a selected prior step, without synthesising one."""
    requested = str(inputs.get("source_step_id") or "").strip()
    steps = context.get("steps", {})
    candidates = [(requested, steps.get(requested))] if requested else list(steps.items())[::-1]
    for step_id, step in candidates:
        data = step.get("data") if isinstance(step, dict) else None
        if not isinstance(data, dict) or "signal" not in data:
            continue
        return {
            "signal": data["signal"],
            "confidence": data.get("confidence"),
            "symbol": data.get("symbol") or inputs.get("symbol"),
            "source_step_id": step_id,
            "source_handler": step.get("handler"),
            "provenance": {"kind": "DERIVED", "source_step_id": step_id},
        }
    if requested and requested not in steps:
        raise ValueError(f"source step not found: {requested}")
    raise ValueError("no prior workflow step contains a signal")


def register_builtin_handlers(registry: StepRegistry) -> None:
    registry.register("atlas.portfolio.snapshot", portfolio_snapshot)
    registry.register("atlas.portfolio.risk", portfolio_risk)
    registry.register("atlas.signals.snapshot", signal_snapshot)

