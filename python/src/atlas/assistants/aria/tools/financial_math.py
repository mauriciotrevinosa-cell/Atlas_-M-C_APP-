"""
ARIA Mathematical Toolset — Financial Mathematics
====================================================
Production-ready financial calculations for ARIA's tool-calling system.
Covers: TVM, bonds, derivatives (Black-Scholes, Greeks), risk metrics,
portfolio math, and econometrics helpers.

Each function is designed to be called by ARIA as a tool.

Copyright (c) 2026 M&C. All rights reserved.
"""

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════
#  I. TIME VALUE OF MONEY
# ══════════════════════════════════════════════════════════════════

def present_value(fv: float, rate: float, periods: int) -> Dict[str, float]:
    """
    PV = FV / (1+r)^n

    Args:
        fv:      Future value
        rate:    Periodic interest rate (0.05 = 5%)
        periods: Number of periods
    """
    pv = fv / (1 + rate) ** periods
    return {"pv": round(pv, 4), "fv": fv, "rate": rate, "periods": periods}


def future_value(pv: float, rate: float, periods: int) -> Dict[str, float]:
    """FV = PV * (1+r)^n"""
    fv = pv * (1 + rate) ** periods
    return {"fv": round(fv, 4), "pv": pv, "rate": rate, "periods": periods}


def annuity_pv(payment: float, rate: float, periods: int) -> Dict[str, float]:
    """PV of ordinary annuity = PMT * [1 - (1+r)^-n] / r"""
    if rate == 0:
        pv = payment * periods
    else:
        pv = payment * (1 - (1 + rate) ** -periods) / rate
    return {"pv": round(pv, 4), "payment": payment, "rate": rate, "periods": periods}


def perpetuity_pv(payment: float, rate: float, growth: float = 0.0) -> Dict[str, float]:
    """
    PV = C / (r - g)
    If g=0: PV = C / r
    """
    if rate <= growth:
        return {"error": "rate must be > growth"}
    pv = payment / (rate - growth)
    return {"pv": round(pv, 4), "payment": payment, "rate": rate, "growth": growth}


def effective_rate(nominal: float, compounding_periods: int) -> Dict[str, float]:
    """(1 + r_eff) = (1 + r_nom/m)^m"""
    eff = (1 + nominal / compounding_periods) ** compounding_periods - 1
    return {"effective_rate": round(eff, 6), "nominal": nominal, "m": compounding_periods}


# ══════════════════════════════════════════════════════════════════
#  II. BOND MATHEMATICS
# ══════════════════════════════════════════════════════════════════

def bond_price(face: float, coupon_rate: float, ytm: float, periods: int) -> Dict[str, float]:
    """
    P = Σ C/(1+y)^t + F/(1+y)^T
    """
    coupon = face * coupon_rate
    price = sum(coupon / (1 + ytm) ** t for t in range(1, periods + 1))
    price += face / (1 + ytm) ** periods
    return {"price": round(price, 4), "coupon": coupon, "ytm": ytm}


def macaulay_duration(face: float, coupon_rate: float, ytm: float, periods: int) -> Dict[str, float]:
    """
    D_M = Σ [t * CF_t / (1+y)^t] / P
    """
    coupon = face * coupon_rate
    bp = bond_price(face, coupon_rate, ytm, periods)["price"]

    weighted_sum = 0
    for t in range(1, periods + 1):
        cf = coupon if t < periods else coupon + face
        weighted_sum += t * cf / (1 + ytm) ** t

    mac_dur = weighted_sum / bp
    mod_dur = mac_dur / (1 + ytm)

    return {
        "macaulay_duration": round(mac_dur, 4),
        "modified_duration": round(mod_dur, 4),
        "price": round(bp, 4),
    }


def bond_convexity(face: float, coupon_rate: float, ytm: float, periods: int) -> Dict[str, float]:
    """Convexity ≈ (1/P) * Σ CF_t * t(t+1) / (1+y)^(t+2)"""
    coupon = face * coupon_rate
    bp = bond_price(face, coupon_rate, ytm, periods)["price"]

    conv_sum = 0
    for t in range(1, periods + 1):
        cf = coupon if t < periods else coupon + face
        conv_sum += cf * t * (t + 1) / (1 + ytm) ** (t + 2)

    convexity = conv_sum / bp
    return {"convexity": round(convexity, 4), "price": round(bp, 4)}


# ══════════════════════════════════════════════════════════════════
#  III. CORPORATE FINANCE
# ══════════════════════════════════════════════════════════════════

def wacc(
    equity: float, debt: float, cost_equity: float,
    cost_debt: float, tax_rate: float,
) -> Dict[str, float]:
    """WACC = (E/V)*Re + (D/V)*Rd*(1-T)"""
    v = equity + debt
    w = (equity / v) * cost_equity + (debt / v) * cost_debt * (1 - tax_rate)
    return {
        "wacc": round(w, 6),
        "equity_weight": round(equity / v, 4),
        "debt_weight": round(debt / v, 4),
    }


def npv(cashflows: List[float], discount_rate: float) -> Dict[str, float]:
    """NPV = Σ CF_t / (1+r)^t"""
    n = sum(cf / (1 + discount_rate) ** t for t, cf in enumerate(cashflows))
    return {"npv": round(n, 4), "discount_rate": discount_rate, "n_periods": len(cashflows)}


def irr(cashflows: List[float], guess: float = 0.1, max_iter: int = 1000) -> Dict[str, float]:
    """Find IRR via Newton-Raphson."""
    r = guess
    for _ in range(max_iter):
        npv_val = sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows))
        dnpv = sum(-t * cf / (1 + r) ** (t + 1) for t, cf in enumerate(cashflows))
        if abs(dnpv) < 1e-12:
            break
        r -= npv_val / dnpv
        if abs(npv_val) < 1e-10:
            break
    return {"irr": round(r, 6)}


# ══════════════════════════════════════════════════════════════════
#  IV. BLACK-SCHOLES & GREEKS
# ══════════════════════════════════════════════════════════════════

def _norm_cdf(x: float) -> float:
    """Standard normal CDF (no scipy dependency)."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def black_scholes(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call",
) -> Dict[str, float]:
    """
    Black-Scholes option pricing.

    C = S*N(d1) - K*e^(-rT)*N(d2)
    P = K*e^(-rT)*N(-d2) - S*N(-d1)

    Args:
        S:     Current stock price
        K:     Strike price
        T:     Time to expiry (years)
        r:     Risk-free rate
        sigma: Volatility
        option_type: "call" or "put"
    """
    if T <= 0 or sigma <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return {"price": intrinsic, "d1": 0, "d2": 0}

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        price = S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        price = K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)

    return {
        "price": round(price, 4),
        "d1": round(d1, 6),
        "d2": round(d2, 6),
        "option_type": option_type,
    }


def greeks(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call",
) -> Dict[str, float]:
    """
    All Black-Scholes Greeks.

    Delta: dC/dS = N(d1) [call], N(d1)-1 [put]
    Gamma: d²C/dS² = φ(d1) / (S*σ*√T)
    Vega:  dC/dσ = S*φ(d1)*√T
    Theta: dC/dT (time decay)
    Rho:   dC/dr
    """
    if T <= 0 or sigma <= 0:
        return {"delta": 1.0 if option_type == "call" else -1.0,
                "gamma": 0, "vega": 0, "theta": 0, "rho": 0}

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    # Gamma (same for call/put)
    gamma = _norm_pdf(d1) / (S * sigma * math.sqrt(T))

    # Vega (same for call/put, per 1% move = divide by 100)
    vega = S * _norm_pdf(d1) * math.sqrt(T)

    if option_type == "call":
        delta = _norm_cdf(d1)
        theta = (-(S * _norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
                 - r * K * math.exp(-r * T) * _norm_cdf(d2))
        rho = K * T * math.exp(-r * T) * _norm_cdf(d2)
    else:
        delta = _norm_cdf(d1) - 1
        theta = (-(S * _norm_pdf(d1) * sigma) / (2 * math.sqrt(T))
                 + r * K * math.exp(-r * T) * _norm_cdf(-d2))
        rho = -K * T * math.exp(-r * T) * _norm_cdf(-d2)

    return {
        "delta": round(delta, 6),
        "gamma": round(gamma, 6),
        "vega": round(vega, 4),
        "theta": round(theta, 4),
        "rho": round(rho, 4),
        "option_type": option_type,
    }


def put_call_parity(
    S: float, K: float, T: float, r: float,
    call_price: Optional[float] = None, put_price: Optional[float] = None,
) -> Dict[str, float]:
    """
    C - P = S - K*e^(-rT)

    Given one, compute the other.
    """
    pv_k = K * math.exp(-r * T)
    if call_price is not None:
        put = call_price - S + pv_k
        return {"put_price": round(put, 4), "call_price": call_price, "pv_strike": round(pv_k, 4)}
    elif put_price is not None:
        call = put_price + S - pv_k
        return {"call_price": round(call, 4), "put_price": put_price, "pv_strike": round(pv_k, 4)}
    return {"error": "provide either call_price or put_price"}


def implied_volatility(
    market_price: float, S: float, K: float, T: float, r: float,
    option_type: str = "call", max_iter: int = 100,
) -> Dict[str, float]:
    """
    Find implied volatility via bisection method.
    """
    low, high = 0.001, 5.0
    for _ in range(max_iter):
        mid = (low + high) / 2
        bs_price = black_scholes(S, K, T, r, mid, option_type)["price"]
        if abs(bs_price - market_price) < 1e-6:
            break
        if bs_price > market_price:
            high = mid
        else:
            low = mid
    return {"implied_volatility": round(mid, 6), "market_price": market_price}


# ══════════════════════════════════════════════════════════════════
#  V. PORTFOLIO & RISK MATHEMATICS
# ══════════════════════════════════════════════════════════════════

def portfolio_stats(
    weights: List[float],
    expected_returns: List[float],
    cov_matrix: List[List[float]],
) -> Dict[str, float]:
    """
    Portfolio expected return and variance.

    E[Rp] = w' * μ
    σ²p   = w' * Σ * w
    """
    w = np.array(weights)
    mu = np.array(expected_returns)
    sigma = np.array(cov_matrix)

    port_return = float(w @ mu)
    port_var = float(w @ sigma @ w)
    port_vol = math.sqrt(port_var)

    return {
        "expected_return": round(port_return, 6),
        "variance": round(port_var, 6),
        "volatility": round(port_vol, 6),
        "sharpe": round(port_return / port_vol, 4) if port_vol > 0 else 0,
    }


def capm(
    risk_free: float, beta: float, market_return: float,
) -> Dict[str, float]:
    """E[Ri] = Rf + β(E[Rm] - Rf)"""
    expected = risk_free + beta * (market_return - risk_free)
    risk_premium = beta * (market_return - risk_free)
    return {
        "expected_return": round(expected, 6),
        "risk_premium": round(risk_premium, 6),
        "beta": beta,
    }


def beta_from_data(
    asset_returns: List[float], market_returns: List[float],
) -> Dict[str, float]:
    """β = Cov(Ri, Rm) / Var(Rm)"""
    a = np.array(asset_returns)
    m = np.array(market_returns)
    cov = np.cov(a, m)[0, 1]
    var_m = np.var(m, ddof=1)
    b = cov / var_m if var_m > 0 else 0
    corr = np.corrcoef(a, m)[0, 1]
    return {"beta": round(b, 4), "correlation": round(float(corr), 4)}


def value_at_risk(
    returns: List[float], confidence: float = 0.95, method: str = "historical",
) -> Dict[str, float]:
    """
    VaR and CVaR.

    Historical: sort returns, take quantile.
    Parametric: assume normal, use z-score.
    """
    r = np.array(returns)

    if method == "historical":
        var = float(-np.percentile(r, (1 - confidence) * 100))
        losses = r[r <= -var]
        cvar = float(-losses.mean()) if len(losses) > 0 else var
    else:  # parametric
        mu = float(r.mean())
        sigma = float(r.std())
        from math import erfinv
        z = math.sqrt(2) * erfinv(2 * confidence - 1)
        var = -(mu - z * sigma)
        cvar = -mu + sigma * _norm_pdf(z) / (1 - confidence)

    return {
        "var": round(var, 6),
        "cvar": round(cvar, 6),
        "confidence": confidence,
        "method": method,
    }


def sharpe_ratio(
    returns: List[float], risk_free_rate: float = 0.0,
) -> Dict[str, float]:
    """S = (E[R] - Rf) / σ"""
    r = np.array(returns)
    excess = r - risk_free_rate / 252  # Daily
    s = float(excess.mean() / excess.std() * math.sqrt(252)) if excess.std() > 0 else 0
    return {
        "sharpe": round(s, 4),
        "annualized_return": round(float(r.mean() * 252), 4),
        "annualized_vol": round(float(r.std() * math.sqrt(252)), 4),
    }


def sortino_ratio(
    returns: List[float], risk_free_rate: float = 0.0,
) -> Dict[str, float]:
    """Sortino = (E[R] - Rf) / downside_σ"""
    r = np.array(returns)
    excess = r - risk_free_rate / 252
    downside = r[r < 0]
    down_std = float(downside.std()) if len(downside) > 1 else 0.001
    s = float(excess.mean() / down_std * math.sqrt(252))
    return {"sortino": round(s, 4)}


# ══════════════════════════════════════════════════════════════════
#  VI. STATISTICS & ECONOMETRICS HELPERS
# ══════════════════════════════════════════════════════════════════

def descriptive_stats(data: List[float]) -> Dict[str, float]:
    """Complete descriptive statistics."""
    d = np.array(data)
    return {
        "mean": round(float(d.mean()), 6),
        "median": round(float(np.median(d)), 6),
        "std": round(float(d.std(ddof=1)), 6),
        "variance": round(float(d.var(ddof=1)), 6),
        "skewness": round(float(pd.Series(d).skew()), 4),
        "kurtosis": round(float(pd.Series(d).kurtosis()), 4),
        "min": round(float(d.min()), 6),
        "max": round(float(d.max()), 6),
        "count": len(d),
    }


def ols_regression(
    y: List[float], X: List[List[float]], add_intercept: bool = True,
) -> Dict[str, Any]:
    """
    OLS: β = (X'X)^-1 X'y

    Args:
        y: Dependent variable
        X: Independent variables (list of lists, each inner list = one variable)
        add_intercept: Add constant column
    """
    y_arr = np.array(y)
    X_arr = np.array(X).T  # Transpose so columns are variables

    if add_intercept:
        ones = np.ones((X_arr.shape[0], 1))
        X_arr = np.hstack([ones, X_arr])

    # β = (X'X)^-1 X'y
    XtX = X_arr.T @ X_arr
    Xty = X_arr.T @ y_arr
    beta = np.linalg.solve(XtX, Xty)

    # Fitted values and residuals
    y_hat = X_arr @ beta
    residuals = y_arr - y_hat

    # R-squared
    ss_res = float((residuals ** 2).sum())
    ss_tot = float(((y_arr - y_arr.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    # Standard errors
    n, k = X_arr.shape
    sigma2 = ss_res / (n - k) if n > k else 0
    var_beta = sigma2 * np.linalg.inv(XtX)
    se = np.sqrt(np.diag(var_beta))

    # t-statistics
    t_stats = beta / se

    labels = ["intercept"] + [f"x{i}" for i in range(1, len(beta) + (0 if add_intercept else 1))]
    if add_intercept:
        labels = ["intercept"] + [f"x{i}" for i in range(1, len(beta))]

    return {
        "coefficients": {labels[i]: round(float(beta[i]), 6) for i in range(len(beta))},
        "std_errors": {labels[i]: round(float(se[i]), 6) for i in range(len(se))},
        "t_statistics": {labels[i]: round(float(t_stats[i]), 4) for i in range(len(t_stats))},
        "r_squared": round(r2, 4),
        "adj_r_squared": round(1 - (1 - r2) * (n - 1) / (n - k), 4) if n > k else 0,
        "n_observations": n,
        "residual_std": round(math.sqrt(sigma2), 6),
    }


def correlation_matrix(data: Dict[str, List[float]]) -> Dict[str, Any]:
    """
    Compute Pearson correlation matrix from dict of series.

    Args:
        data: {"AAPL": [r1, r2, ...], "MSFT": [r1, r2, ...]}
    """
    df = pd.DataFrame(data)
    corr = df.corr()
    return {
        "matrix": {col: {row: round(corr.loc[row, col], 4) for row in corr.index} for col in corr.columns},
        "assets": list(corr.columns),
    }


# ══════════════════════════════════════════════════════════════════
#  VII. STOCHASTIC / SIMULATION
# ══════════════════════════════════════════════════════════════════

def gbm_simulate(
    S0: float, mu: float, sigma: float, T: float, n_steps: int, n_paths: int = 1000,
) -> Dict[str, Any]:
    """
    Geometric Brownian Motion simulation.

    dS = μS dt + σS dW
    S(t) = S0 * exp((μ - σ²/2)t + σW(t))

    Returns percentile summary (not full paths, to keep output small).
    """
    dt = T / n_steps
    np.random.seed(42)

    Z = np.random.standard_normal((n_paths, n_steps))
    log_returns = (mu - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * Z
    log_paths = np.cumsum(log_returns, axis=1)
    final_log = log_paths[:, -1]
    final_prices = S0 * np.exp(final_log)

    return {
        "S0": S0,
        "mu": mu,
        "sigma": sigma,
        "T": T,
        "n_paths": n_paths,
        "percentiles": {
            f"P{p}": round(float(np.percentile(final_prices, p)), 2)
            for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]
        },
        "mean": round(float(final_prices.mean()), 2),
        "std": round(float(final_prices.std()), 2),
        "prob_loss": round(float((final_prices < S0).mean()), 4),
    }


# ══════════════════════════════════════════════════════════════════
#  TOOL REGISTRY (for ARIA tool-calling system)
# ══════════════════════════════════════════════════════════════════

MATH_TOOLS = {
    # TVM
    "present_value": present_value,
    "future_value": future_value,
    "annuity_pv": annuity_pv,
    "perpetuity_pv": perpetuity_pv,
    "effective_rate": effective_rate,
    # Bonds
    "bond_price": bond_price,
    "macaulay_duration": macaulay_duration,
    "bond_convexity": bond_convexity,
    # Corporate
    "wacc": wacc,
    "npv": npv,
    "irr": irr,
    # Options
    "black_scholes": black_scholes,
    "greeks": greeks,
    "put_call_parity": put_call_parity,
    "implied_volatility": implied_volatility,
    # Portfolio & Risk
    "portfolio_stats": portfolio_stats,
    "capm": capm,
    "beta_from_data": beta_from_data,
    "value_at_risk": value_at_risk,
    "sharpe_ratio": sharpe_ratio,
    "sortino_ratio": sortino_ratio,
    # Stats & Econometrics
    "descriptive_stats": descriptive_stats,
    "ols_regression": ols_regression,
    "correlation_matrix": correlation_matrix,
    # Simulation
    "gbm_simulate": gbm_simulate,
}


def get_tool(name: str):
    """Get a math tool by name."""
    return MATH_TOOLS.get(name)


def list_tools() -> List[str]:
    """List all available math tools."""
    return list(MATH_TOOLS.keys())
