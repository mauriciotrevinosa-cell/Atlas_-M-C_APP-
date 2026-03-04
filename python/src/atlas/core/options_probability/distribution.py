"""
Risk-neutral style distribution approximation from options data.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, sqrt

import numpy as np

from .fetcher import OptionsChain


@dataclass(slots=True)
class PriceDistribution:
    strikes: list[float]
    probabilities: list[float]
    mean: float
    std: float
    quantiles: dict[str, float]
    horizon_days: float


class RiskNeutralDistribution:
    """
    Approximates terminal price distribution with a lognormal model anchored to ATM IV.
    """

    def estimate(self, chain: OptionsChain, n_bins: int = 31) -> PriceDistribution:
        if n_bins < 7:
            raise ValueError("n_bins must be >= 7")

        frame = _chain_frame(chain)
        if frame.empty:
            raise ValueError("No options rows available to estimate distribution")

        now = np.datetime64("now")
        dte_days = (
            (frame["expiration"].to_numpy(dtype="datetime64[ns]") - now)
            / np.timedelta64(1, "D")
        ).astype(float)
        dte_days = dte_days[dte_days > 0]
        if dte_days.size == 0:
            horizon = 30.0
        else:
            horizon = float(np.median(dte_days))

        moneyness = frame["strike"].to_numpy(dtype=float) / max(chain.underlying_price, 1e-9)
        iv = frame["impliedVolatility"].to_numpy(dtype=float)
        atm_mask = np.abs(moneyness - 1.0) <= 0.03
        sigma_annual = float(np.median(iv[atm_mask])) if atm_mask.any() else float(np.median(iv))
        sigma_annual = max(sigma_annual, 1e-6)

        t = max(horizon / 365.0, 1e-6)
        mu_ln = log(max(chain.underlying_price, 1e-9)) - 0.5 * (sigma_annual ** 2) * t
        sigma_ln = sigma_annual * sqrt(t)

        low = chain.underlying_price * 0.70
        high = chain.underlying_price * 1.30
        strikes = np.linspace(low, high, n_bins)
        edges = np.concatenate(([strikes[0] - (strikes[1] - strikes[0]) / 2], (strikes[:-1] + strikes[1:]) / 2, [strikes[-1] + (strikes[-1] - strikes[-2]) / 2]))

        probs = []
        for i in range(len(strikes)):
            left = max(edges[i], 1e-9)
            right = max(edges[i + 1], left + 1e-9)
            probs.append(max(0.0, _lognormal_cdf(right, mu_ln, sigma_ln) - _lognormal_cdf(left, mu_ln, sigma_ln)))

        probs_arr = np.array(probs, dtype=float)
        total = float(probs_arr.sum())
        if total > 0:
            probs_arr /= total

        mean = float(np.sum(strikes * probs_arr))
        var = float(np.sum(((strikes - mean) ** 2) * probs_arr))
        std = sqrt(max(var, 0.0))
        quantiles = _quantiles_from_discrete(strikes, probs_arr, [0.05, 0.25, 0.5, 0.75, 0.95])

        return PriceDistribution(
            strikes=[float(v) for v in strikes],
            probabilities=[float(v) for v in probs_arr],
            mean=mean,
            std=std,
            quantiles={
                "q05": quantiles[0.05],
                "q25": quantiles[0.25],
                "q50": quantiles[0.5],
                "q75": quantiles[0.75],
                "q95": quantiles[0.95],
            },
            horizon_days=horizon,
        )


def _chain_frame(chain: OptionsChain):
    import pandas as pd

    calls = chain.calls.copy() if chain.calls is not None else pd.DataFrame()
    puts = chain.puts.copy() if chain.puts is not None else pd.DataFrame()
    frame = pd.concat([calls, puts], ignore_index=True)
    if frame.empty:
        return frame
    frame["expiration"] = pd.to_datetime(frame["expiration"], utc=True, errors="coerce")
    for col in ["strike", "impliedVolatility"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame.dropna(subset=["strike", "impliedVolatility", "expiration"])


def _lognormal_cdf(x: float, mu_ln: float, sigma_ln: float) -> float:
    if x <= 0 or sigma_ln <= 0:
        return 0.0
    z = (log(x) - mu_ln) / (sigma_ln * sqrt(2.0))
    return 0.5 * (1.0 + erf(z))


def _quantiles_from_discrete(values: np.ndarray, probabilities: np.ndarray, levels: list[float]) -> dict[float, float]:
    cdf = np.cumsum(probabilities)
    out: dict[float, float] = {}
    for level in levels:
        idx = int(np.searchsorted(cdf, level, side="left"))
        idx = min(max(idx, 0), len(values) - 1)
        out[level] = float(values[idx])
    return out

