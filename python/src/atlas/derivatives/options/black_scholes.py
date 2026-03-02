"""
Black-Scholes options analytics helpers.

Pure numpy implementation used by Atlas server routes for:
- Greeks calculator
- Synthetic options chain
- IV surface
- Synthetic position templates
"""

from __future__ import annotations

import math
from typing import Dict, List

import numpy as np

SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_pdf(x: np.ndarray | float) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return np.exp(-0.5 * x * x) / SQRT_2PI


def _norm_cdf(x: np.ndarray | float) -> np.ndarray:
    """
    Abramowitz-Stegun approximation (max error ~7.5e-8).
    """
    x = np.asarray(x, dtype=float)
    ax = np.abs(x)
    k = 1.0 / (1.0 + 0.2316419 * ax)
    poly = (
        k
        * (
            0.319381530
            + k
            * (
                -0.356563782
                + k * (1.781477937 + k * (-1.821255978 + k * 1.330274429))
            )
        )
    )
    cdf_pos = 1.0 - _norm_pdf(ax) * poly
    return np.where(x >= 0.0, cdf_pos, 1.0 - cdf_pos)


def _safe_inputs(S: float, K: float, T: float, sigma: float) -> tuple[float, float, float, float]:
    S = max(float(S), 1e-8)
    K = max(float(K), 1e-8)
    T = max(float(T), 1e-8)
    sigma = max(float(sigma), 1e-8)
    return S, K, T, sigma


def _d1_d2(S: float, K: float, T: float, r: float, sigma: float) -> tuple[float, float]:
    S, K, T, sigma = _safe_inputs(S, K, T, sigma)
    sqrt_t = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt_t)
    d2 = d1 - sigma * sqrt_t
    return d1, d2


def bs_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    option_type: str = "call",
) -> Dict[str, float]:
    """
    Return Black-Scholes price + greeks.

    Theta is returned per day, Vega/Rho per 1%.
    """
    opt = (option_type or "call").lower().strip()
    if opt not in {"call", "put"}:
        raise ValueError("option_type must be 'call' or 'put'")

    S, K, T, sigma = _safe_inputs(S, K, T, sigma)
    d1, d2 = _d1_d2(S, K, T, r, sigma)
    nd1 = float(_norm_pdf(d1))
    Nd1 = float(_norm_cdf(d1))
    Nd2 = float(_norm_cdf(d2))
    disc = math.exp(-r * T)
    sqrt_t = math.sqrt(T)

    if opt == "call":
        price = S * Nd1 - K * disc * Nd2
        delta = Nd1
        theta = (-S * nd1 * sigma / (2.0 * sqrt_t) - r * K * disc * Nd2) / 365.0
        rho = (K * T * disc * Nd2) / 100.0
    else:
        Nmd1 = float(_norm_cdf(-d1))
        Nmd2 = float(_norm_cdf(-d2))
        price = K * disc * Nmd2 - S * Nmd1
        delta = Nd1 - 1.0
        theta = (-S * nd1 * sigma / (2.0 * sqrt_t) + r * K * disc * Nmd2) / 365.0
        rho = (-K * T * disc * Nmd2) / 100.0

    gamma = nd1 / (S * sigma * sqrt_t)
    vega = (S * nd1 * sqrt_t) / 100.0

    return {
        "price": float(price),
        "delta": float(delta),
        "gamma": float(gamma),
        "theta": float(theta),
        "vega": float(vega),
        "rho": float(rho),
    }


def _smile_iv(base_sigma: float, strike: float, spot: float, expiry_years: float) -> float:
    # Light skew + smile + gentle term effect for synthetic but realistic surfaces.
    m = strike / max(spot, 1e-8) - 1.0
    smile = 0.55 * (m * m)
    skew = -0.22 * m
    term = 1.0 + 0.12 * math.log1p(max(expiry_years, 1e-8) * 12.0)
    iv = base_sigma * term * (1.0 + smile + skew)
    return float(max(0.05, iv))


def options_chain(
    S: float,
    T: float,
    r: float,
    sigma: float,
    n_strikes: int = 11,
) -> Dict[str, object]:
    """
    Build a synthetic options chain around ATM.
    """
    n = int(max(3, n_strikes))
    if n % 2 == 0:
        n += 1

    span = 0.22
    strikes = np.linspace(S * (1.0 - span), S * (1.0 + span), n)
    rows: List[Dict[str, object]] = []

    for k in strikes:
        kf = float(k)
        local_iv = _smile_iv(float(sigma), kf, float(S), float(T))
        call = bs_greeks(S, kf, T, r, local_iv, "call")
        put = bs_greeks(S, kf, T, r, local_iv, "put")
        rows.append(
            {
                "strike": round(kf, 2),
                "iv": round(local_iv, 4),
                "call": call,
                "put": put,
            }
        )

    atm_idx = int(np.argmin(np.abs(strikes - S)))
    atm_iv = rows[atm_idx]["iv"]

    return {
        "spot": float(S),
        "expiry": float(T),
        "r": float(r),
        "base_iv": float(sigma),
        "atm_iv": float(atm_iv),
        "strikes": rows,
    }


def iv_surface(
    S: float,
    r: float = 0.05,
    sigma: float = 0.20,
    expiries: List[float] | None = None,
    n_strikes: int = 7,
) -> Dict[str, object]:
    """
    Return 7x7 (default) synthetic IV surface grid.
    """
    if expiries is None:
        expiries = [7 / 365, 14 / 365, 30 / 365, 60 / 365, 90 / 365, 180 / 365, 365 / 365]

    n_k = int(max(3, n_strikes))
    strikes = np.linspace(S * 0.78, S * 1.22, n_k)

    grid: List[List[float]] = []
    for t in expiries:
        row = []
        for k in strikes:
            row.append(round(_smile_iv(float(sigma), float(k), float(S), float(t)), 4))
        grid.append(row)

    return {
        "spot": float(S),
        "r": float(r),
        "base_iv": float(sigma),
        "expiries": [float(x) for x in expiries],
        "strikes": [float(x) for x in strikes],
        "iv_grid": grid,
    }


def synthetic_positions(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
) -> Dict[str, Dict[str, float]]:
    """
    Return simple synthetic strategy metrics for dashboard display.
    """
    call_atm = bs_greeks(S, K, T, r, sigma, "call")
    put_atm = bs_greeks(S, K, T, r, sigma, "put")

    K_up = K * 1.05
    K_dn = K * 0.95
    call_up = bs_greeks(S, K_up, T, r, _smile_iv(sigma, K_up, S, T), "call")
    put_dn = bs_greeks(S, K_dn, T, r, _smile_iv(sigma, K_dn, S, T), "put")

    K_bull_low = K * 0.98
    K_bull_high = K * 1.02
    bull_low = bs_greeks(S, K_bull_low, T, r, _smile_iv(sigma, K_bull_low, S, T), "call")
    bull_high = bs_greeks(S, K_bull_high, T, r, _smile_iv(sigma, K_bull_high, S, T), "call")

    K_bear_low = K * 0.98
    K_bear_high = K * 1.02
    bear_low = bs_greeks(S, K_bear_low, T, r, _smile_iv(sigma, K_bear_low, S, T), "put")
    bear_high = bs_greeks(S, K_bear_high, T, r, _smile_iv(sigma, K_bear_high, S, T), "put")

    straddle_cost = call_atm["price"] + put_atm["price"]
    strangle_cost = call_up["price"] + put_dn["price"]
    bull_cost = max(0.0, bull_low["price"] - bull_high["price"])
    bear_cost = max(0.0, bear_high["price"] - bear_low["price"])

    return {
        "straddle": {
            "cost": float(straddle_cost),
            "breakeven_up": float(K + straddle_cost),
            "breakeven_down": float(K - straddle_cost),
            "delta": float(call_atm["delta"] + put_atm["delta"]),
            "gamma": float(call_atm["gamma"] + put_atm["gamma"]),
        },
        "strangle": {
            "put_strike": float(K_dn),
            "call_strike": float(K_up),
            "cost": float(strangle_cost),
            "breakeven_up": float(K_up + strangle_cost),
            "breakeven_down": float(K_dn - strangle_cost),
        },
        "bull_spread": {
            "buy_call": float(K_bull_low),
            "sell_call": float(K_bull_high),
            "net_debit": float(bull_cost),
            "max_profit": float((K_bull_high - K_bull_low) - bull_cost),
            "max_loss": float(bull_cost),
        },
        "bear_spread": {
            "buy_put": float(K_bear_high),
            "sell_put": float(K_bear_low),
            "net_debit": float(bear_cost),
            "max_profit": float((K_bear_high - K_bear_low) - bear_cost),
            "max_loss": float(bear_cost),
        },
    }


__all__ = [
    "bs_greeks",
    "iv_surface",
    "options_chain",
    "synthetic_positions",
]
