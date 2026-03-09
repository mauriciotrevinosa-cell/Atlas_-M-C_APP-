"""
Execution Algorithms — Full Mathematical Implementations
=========================================================
Reference: ALGORITHMS_LIBRARY.md — Algorithms #8, #9, #10

Algorithms:
  TWAPAlgo         — Time-Weighted Average Price (equal-slice execution)
  VWAPAlgo         — Volume-Weighted Average Price (volume-proportional execution)
  AlmgrenChrissOptimizer — Optimal execution (market impact vs. price risk)

Mathematical foundations:
  TWAP:  Divide Q_total into N equal slices; execute every Δt = T/N
  VWAP:  q(t) = Q_total × V(t)/V_total  (track intraday volume distribution)
  AC:    Q(t) = Q₀ × sinh(κ(T−t)) / sinh(κT)  where κ = √(λσ²/η)

References:
  Kissell & Glantz (2003). "Optimal Trading Strategies"
  Almgren, R., Chriss, N. (2001). "Optimal Execution of Portfolio Transactions"
  Almgren, R. (2003). "Optimal Execution with Nonlinear Impact Functions"
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Shared Types ───────────────────────────────────────────────────────────────

@dataclass
class ExecutionSlice:
    """Single execution slice from any algorithm."""
    index:    int
    time:     float          # seconds from start
    quantity: float          # shares to execute
    participation: float     # fraction of total order
    expected_price: float    # estimated fill price
    impact_cost:    float    # estimated market impact

@dataclass
class ExecutionSchedule:
    """Complete execution schedule output."""
    algorithm:    str
    total_qty:    float
    duration:     float       # total seconds
    slices:       List[ExecutionSlice] = field(default_factory=list)
    # Cost estimates
    expected_impact: float = 0.0    # bps
    expected_spread: float = 0.0    # bps
    timing_risk:     float = 0.0    # σ in $ (price risk from holding)
    # Summary
    shortfall_estimate: float = 0.0  # Implementation shortfall estimate

    def to_dict(self) -> Dict:
        return {
            'algorithm':         self.algorithm,
            'total_qty':         self.total_qty,
            'duration_sec':      self.duration,
            'n_slices':          len(self.slices),
            'expected_impact_bps': round(self.expected_impact, 2),
            'expected_spread_bps': round(self.expected_spread, 2),
            'timing_risk_usd':   round(self.timing_risk, 2),
            'shortfall_est_bps': round(self.shortfall_estimate, 2),
            'slices':            [
                {
                    'idx':        s.index,
                    'time_s':     round(s.time, 1),
                    'qty':        round(s.quantity, 4),
                    'pct':        round(s.participation * 100, 2),
                    'est_price':  round(s.expected_price, 4),
                    'impact_bps': round(s.impact_cost * 1e4, 2),
                }
                for s in self.slices
            ],
        }


# ── TWAP ──────────────────────────────────────────────────────────────────────

class TWAPAlgo:
    """
    Time-Weighted Average Price Execution.

    Divides order Q_total into N equal slices, one every Δt = T/N seconds.
    Simplest strategy — predictable but ignores volume/liquidity patterns.

    Parameters
    ----------
    n_slices     : number of equal time slices (default 12 = one per 5min in 1hr)
    spread_bps   : assumed bid-ask spread in bps (default 5)
    impact_factor: temporary impact factor η (price moves η × qty/ADV)
    """

    def __init__(
        self,
        n_slices:     int   = 12,
        spread_bps:   float = 5.0,
        impact_factor: float = 0.1,
    ):
        self.n_slices     = max(1, n_slices)
        self.spread_bps   = spread_bps
        self.impact_factor = impact_factor

    def schedule(
        self,
        total_qty:   float,
        duration_s:  float,
        price:       float,
        adv:         float = 1_000_000,
        sigma:       float = 0.015,
    ) -> ExecutionSchedule:
        """
        Generate TWAP execution schedule.

        Parameters
        ----------
        total_qty  : total shares to execute
        duration_s : execution window in seconds
        price      : current mid price
        adv        : average daily volume (shares)
        sigma      : daily price volatility (fractional, e.g. 0.015 = 1.5%)
        """
        dt         = duration_s / self.n_slices
        slice_qty  = total_qty  / self.n_slices
        adv_per_s  = adv / 23_400  # trading seconds per day

        slices = []
        cumulative_impact = 0.0

        for i in range(self.n_slices):
            t = i * dt

            # Temporary market impact (linear model)
            participation = slice_qty / max(adv_per_s * dt, 1.0)
            temp_impact   = self.impact_factor * participation * price   # $/share
            cumulative_impact += temp_impact

            slices.append(ExecutionSlice(
                index        = i,
                time         = t,
                quantity     = slice_qty,
                participation = slice_qty / total_qty,
                expected_price = price + temp_impact,
                impact_cost   = temp_impact / price,  # fractional
            ))

        # Cost estimates
        spread_cost  = self.spread_bps / 2   # half-spread per trade
        impact_bps   = (cumulative_impact / price) * 1e4 / self.n_slices

        # Timing risk: σ_daily × √(T_days) × price × Q
        T_days       = duration_s / 23_400
        timing_risk  = sigma * math.sqrt(T_days) * price * total_qty / 2

        return ExecutionSchedule(
            algorithm        = 'TWAP',
            total_qty        = total_qty,
            duration         = duration_s,
            slices           = slices,
            expected_impact  = impact_bps,
            expected_spread  = spread_cost,
            timing_risk      = timing_risk,
            shortfall_estimate = impact_bps + spread_cost,
        )

    def __repr__(self) -> str:
        return f'TWAPAlgo(n_slices={self.n_slices}, spread={self.spread_bps}bps)'


# ── VWAP ──────────────────────────────────────────────────────────────────────

class VWAPAlgo:
    """
    Volume-Weighted Average Price Execution.

    Executes proportionally to predicted intraday volume distribution.
    Lower market impact than TWAP — follows liquidity pools.

    Intraday Volume Pattern: U-shaped (heavy at open/close, lighter midday).

    Parameters
    ----------
    n_buckets    : number of time buckets
    spread_bps   : bid-ask spread assumption
    impact_factor: temporary impact factor η
    """

    # Default U-shaped intraday volume distribution (normalized)
    _DEFAULT_VOLUME_CURVE = np.array([
        0.12, 0.09, 0.07, 0.06, 0.05, 0.05,   # 9:30-12:00
        0.04, 0.04, 0.05, 0.06, 0.07, 0.09,   # 12:00-15:00
        0.10, 0.11,                             # 15:00-16:00 (close surge)
    ])

    def __init__(
        self,
        n_buckets:     int   = 14,
        spread_bps:    float = 5.0,
        impact_factor: float = 0.08,
        volume_curve:  Optional[np.ndarray] = None,
    ):
        self.n_buckets    = n_buckets
        self.spread_bps   = spread_bps
        self.impact_factor = impact_factor

        if volume_curve is not None:
            vc = np.asarray(volume_curve, dtype=np.float64)
            self._volume_curve = vc / vc.sum()
        else:
            vc = self._DEFAULT_VOLUME_CURVE
            self._volume_curve = vc / vc.sum()
            # Resample to requested n_buckets
            if n_buckets != len(vc):
                xs = np.linspace(0, 1, len(vc))
                xn = np.linspace(0, 1, n_buckets)
                self._volume_curve = np.interp(xn, xs, vc)
                self._volume_curve /= self._volume_curve.sum()

    def schedule(
        self,
        total_qty:  float,
        duration_s: float,
        price:      float,
        adv:        float = 1_000_000,
        sigma:      float = 0.015,
        volume_forecast: Optional[np.ndarray] = None,
    ) -> ExecutionSchedule:
        """
        Generate VWAP execution schedule.

        Parameters
        ----------
        total_qty       : total shares to execute
        duration_s      : execution window in seconds
        price           : current mid price
        adv             : average daily volume
        sigma           : daily volatility
        volume_forecast : optional override (normalized) volume distribution
        """
        if volume_forecast is not None:
            vf = np.asarray(volume_forecast, dtype=np.float64)
            weights = vf / vf.sum()
        else:
            weights = self._volume_curve.copy()

        # Resize weights to match n_buckets if needed
        if len(weights) != self.n_buckets:
            xs = np.linspace(0, 1, len(weights))
            xn = np.linspace(0, 1, self.n_buckets)
            weights = np.interp(xn, xs, weights)
            weights /= weights.sum()

        dt          = duration_s / self.n_buckets
        adv_per_bkt = adv / 23_400 * dt

        slices = []
        total_impact = 0.0

        for i in range(self.n_buckets):
            qty_i = total_qty * weights[i]
            t     = i * dt

            # Participation rate for this bucket
            part  = qty_i / max(adv_per_bkt, 1.0)
            # VWAP tracks liquidity → lower impact than TWAP
            impact = self.impact_factor * part * price * 0.8  # 20% discount vs TWAP
            total_impact += impact

            slices.append(ExecutionSlice(
                index        = i,
                time         = t,
                quantity     = qty_i,
                participation = qty_i / total_qty,
                expected_price = price + impact,
                impact_cost   = impact / price,
            ))

        avg_impact_bps = (total_impact / price) * 1e4 / self.n_buckets
        T_days         = duration_s / 23_400
        timing_risk    = sigma * math.sqrt(T_days) * price * total_qty / 2

        return ExecutionSchedule(
            algorithm        = 'VWAP',
            total_qty        = total_qty,
            duration         = duration_s,
            slices           = slices,
            expected_impact  = avg_impact_bps,
            expected_spread  = self.spread_bps / 2,
            timing_risk      = timing_risk,
            shortfall_estimate = avg_impact_bps + self.spread_bps / 2,
        )

    def __repr__(self) -> str:
        return f'VWAPAlgo(n_buckets={self.n_buckets}, spread={self.spread_bps}bps)'


# ── Almgren-Chriss ────────────────────────────────────────────────────────────

class AlmgrenChrissOptimizer:
    """
    Almgren-Chriss Optimal Execution.

    Trade-off: minimize  E[Cost] + λ · Var[Cost]

    Linear price impact model:
      Temporary: f(v) = η·v   (price recovers immediately)
      Permanent:  g(x) = γ·x  (price impact persists)

    Optimal trajectory:
      Q(t) = Q₀ · sinh(κ(T−t)) / sinh(κT)
      κ = √(λσ²/η)

    Extremes:
      λ→0 (risk-neutral): linear depletion — minimize impact only
      λ→∞ (risk-averse):  very fast execution — minimize timing risk

    Parameters
    ----------
    eta   : η, temporary impact coefficient (higher = more liquid)
    gamma : γ, permanent impact coefficient
    sigma : daily price volatility (fractional)
    lam   : λ, risk aversion (0=risk-neutral → fast; large=risk-averse → slow)
    """

    def __init__(
        self,
        eta:   float = 2.5e-7,    # $/share per share/day
        gamma: float = 2.5e-7,    # permanent impact
        sigma: float = 0.015,     # daily vol
        lam:   float = 1e-6,      # risk aversion
        spread_bps: float = 5.0,
    ):
        self.eta        = eta
        self.gamma      = gamma
        self.sigma      = sigma
        self.lam        = lam
        self.spread_bps = spread_bps

    def schedule(
        self,
        total_qty:    float,
        duration_s:   float,
        price:        float,
        n_slices:     int   = 20,
        adv:          float = 1_000_000,
    ) -> ExecutionSchedule:
        """
        Generate Almgren-Chriss optimal execution schedule.

        Parameters
        ----------
        total_qty  : total shares to execute (positive = sell, negative = buy)
        duration_s : total execution window (seconds)
        price      : current mid price ($)
        n_slices   : number of time steps
        adv        : average daily volume (for impact estimation)
        """
        T      = duration_s / 23_400   # convert to trading days
        Q0     = abs(total_qty)
        sign   = 1.0 if total_qty >= 0 else -1.0
        dt     = T / n_slices

        # κ = √(λσ²/η)
        kappa = math.sqrt(max(self.lam * self.sigma ** 2 / (self.eta + 1e-15), 1e-12))

        # Optimal trajectory Q(t) = Q₀ · sinh(κ(T-t)) / sinh(κT)
        sinh_kT = math.sinh(kappa * T) + 1e-15
        t_grid  = np.linspace(0, T, n_slices + 1)
        Q_traj  = Q0 * np.sinh(kappa * (T - t_grid)) / sinh_kT

        # Execution quantities (negative difference = what to execute per step)
        dQ = np.diff(Q_traj)   # dQ[i] = Q[i+1] - Q[i] < 0 for selling

        slices = []
        total_temp_impact  = 0.0
        total_perm_impact  = 0.0
        Q_remaining        = Q0

        for i, delta_q in enumerate(dQ):
            q_exec = abs(delta_q)
            t_s    = t_grid[i] * 23_400   # back to seconds

            # Execution rate (shares/day)
            rate        = q_exec / (dt + 1e-9)
            temp_impact = self.eta  * rate          # $/share
            perm_impact = self.gamma * q_exec        # $/share (permanent)

            total_temp_impact += temp_impact * q_exec
            total_perm_impact += perm_impact * q_exec

            Q_remaining -= q_exec

            slices.append(ExecutionSlice(
                index        = i,
                time         = t_s,
                quantity     = sign * q_exec,
                participation = q_exec / Q0,
                expected_price = price - sign * (temp_impact + perm_impact),
                impact_cost   = (temp_impact + perm_impact) / price,
            ))

        # Total cost estimates
        total_impact_dollar = total_temp_impact + 0.5 * total_perm_impact
        impact_bps  = (total_impact_dollar / (price * Q0 + 1e-9)) * 1e4

        # Timing risk: σ × price × √(T) × E[Q²]
        q_traj_mid  = 0.5 * (Q_traj[:-1] + Q_traj[1:])
        timing_risk = self.sigma * price * math.sqrt(dt) * float(np.sqrt((q_traj_mid ** 2).sum() * dt))

        return ExecutionSchedule(
            algorithm        = 'Almgren-Chriss',
            total_qty        = total_qty,
            duration         = duration_s,
            slices           = slices,
            expected_impact  = impact_bps,
            expected_spread  = self.spread_bps / 2,
            timing_risk      = timing_risk,
            shortfall_estimate = impact_bps + self.spread_bps / 2,
        )

    def efficient_frontier(
        self,
        total_qty:  float,
        duration_s: float,
        price:      float,
        n_points:   int = 20,
    ) -> List[Dict]:
        """
        Compute the mean-variance efficient frontier for execution.

        Sweeps λ from risk-neutral to risk-averse, producing the classic
        Almgren-Chriss cost/risk trade-off curve.

        Returns list of dicts: {lambda, impact_bps, timing_risk, shortfall}
        """
        lambdas = np.logspace(-8, -3, n_points)
        frontier = []

        for lam in lambdas:
            orig_lam  = self.lam
            self.lam  = float(lam)
            sched     = self.schedule(total_qty, duration_s, price, n_slices=15)
            self.lam  = orig_lam

            frontier.append({
                'lambda':         float(lam),
                'impact_bps':     sched.expected_impact,
                'timing_risk':    sched.timing_risk,
                'shortfall_bps':  sched.shortfall_estimate,
                'first_slice_pct': round(sched.slices[0].participation * 100, 2),
            })

        return frontier

    def calibrate_from_kyle(
        self,
        kyle_lambda: float,
        adv:         float,
        price:       float,
    ) -> None:
        """
        Calibrate η (temporary impact) from Kyle's Lambda estimate.

        η ≈ kyle_lambda × price / ADV
        """
        self.eta   = kyle_lambda * price / (adv + 1e-9)
        self.gamma = self.eta * 0.5  # permanent ≈ half of temporary (rule of thumb)
        logger.info(f'AlmgrenChriss: calibrated η={self.eta:.2e}, γ={self.gamma:.2e}')

    def __repr__(self) -> str:
        return (
            f'AlmgrenChrissOptimizer(η={self.eta:.1e}, γ={self.gamma:.1e}, '
            f'σ={self.sigma:.3f}, λ={self.lam:.1e})'
        )
