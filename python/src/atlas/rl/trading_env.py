"""
TradingEnvironment — Gym-style single-asset RL environment.

State space  (20 features):
  [0-2]  returns: ret_1d, ret_5d, ret_20d
  [3]    realized vol (20d)
  [4-5]  price vs SMA20, SMA50
  [6]    high-low ratio (daily range / price)
  [7]    volume ratio (today / 20d avg)
  [8]    RSI-14 (normalized 0-1)
  [9]    MACD histogram (normalized)
  [10]   Bollinger %B (0-1)
  [11]   ATR / price (normalized)
  [12]   ADX-lite (trend strength 0-1)
  [13]   position ratio  (position value / initial_capital)
  [14]   cash ratio       (cash / initial_capital)
  [15]   unrealized PnL   (normalized)
  [16]   step ratio       (step / episode_length)
  [17]   drawdown magnitude (0 = no DD, 1 = large DD)
  [18]   signed trend     (ADX × direction)
  [19]   volatility regime (0=low, 1=high)

Action space (5 discrete):
  0 HOLD
  1 BUY_SMALL   (10% of initial capital)
  2 BUY_LARGE   (25% of initial capital)
  3 SELL_SMALL  (10% of initial capital)
  4 SELL_LARGE  (25% of initial capital)

Reward: Sharpe-shaped PnL change with drawdown penalty.

Prices are generated via GBM with optional regime-switching.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Optional, Tuple


class TradingEnvironment:
    """
    Single-asset trading environment (no external dependencies).
    Designed to be used with DQNAgent from dqn_agent.py.
    """

    ACTIONS = {
        0: 'HOLD',
        1: 'BUY_SMALL',
        2: 'BUY_LARGE',
        3: 'SELL_SMALL',
        4: 'SELL_LARGE',
    }
    STATE_DIM  = 20
    ACTION_DIM = 5
    TRADE_COST = 0.001   # 0.1% one-way transaction cost

    # Ticker profiles: (annual_mu, annual_sigma, label)
    TICKER_PROFILES = {
        'SPY':  (0.10, 0.16, 'S&P 500 ETF'),
        'QQQ':  (0.14, 0.22, 'Nasdaq 100 ETF'),
        'TSLA': (0.18, 0.55, 'Tesla (High Vol)'),
        'BTC':  (0.30, 0.80, 'Bitcoin (Crypto)'),
        'GLD':  (0.04, 0.12, 'Gold ETF (Defensive)'),
        'IWM':  (0.08, 0.20, 'Russell 2000 ETF'),
        'VXX':  (-0.40, 0.70, 'VIX ETN (mean-revert)'),
        'TLT':  (0.03, 0.14, '20yr Treasury ETF'),
    }

    def __init__(
        self,
        initial_capital: float  = 100_000.0,
        episode_length: int     = 252,
        ticker: str             = 'SPY',
        mu: Optional[float]     = None,
        sigma: Optional[float]  = None,
        seed: Optional[int]     = None,
        regime_switch: bool     = True,
    ):
        profile = self.TICKER_PROFILES.get(ticker, (0.08, 0.18, ticker))
        self.initial_capital = initial_capital
        self.episode_length  = episode_length
        self.ticker          = ticker
        self.mu              = mu if mu is not None else profile[0]
        self.sigma           = sigma if sigma is not None else profile[1]
        self.regime_switch   = regime_switch
        self._rng = np.random.RandomState(seed)

        # Episode state (initialized on reset)
        self._prices:  Optional[np.ndarray] = None
        self._highs:   Optional[np.ndarray] = None
        self._lows:    Optional[np.ndarray] = None
        self._volumes: Optional[np.ndarray] = None
        self._lrets:   Optional[np.ndarray] = None

        self._warm    = 60       # bars reserved for indicator warm-up
        self._step    = 0
        self._done    = False
        self._cash    = initial_capital
        self._shares  = 0.0
        self._peak    = initial_capital
        self._step_returns: List[float] = []
        self.trade_log: List[Dict]      = []

    # ── Price Generator ────────────────────────────────────────────────────────

    def _generate_episode(self) -> None:
        """Generate GBM price series with optional 2-state regime switching."""
        n   = self.episode_length + self._warm + 1
        dt  = 1.0 / 252.0

        if self.regime_switch:
            # Regime: BULL (80% of time) / BEAR (20%)
            regimes    = self._rng.choice([0, 1], size=n, p=[0.80, 0.20])
            mus        = np.where(regimes == 0, self.mu, -abs(self.mu))
            sigmas     = np.where(regimes == 0, self.sigma, self.sigma * 1.4)
        else:
            mus   = np.full(n, self.mu)
            sigmas = np.full(n, self.sigma)

        drift  = (mus    - 0.5 * sigmas**2) * dt
        noise  = sigmas  * np.sqrt(dt) * self._rng.randn(n)
        lrets  = drift + noise

        prices  = np.exp(np.cumsum(lrets)) * 100.0
        spread  = np.abs(self._rng.randn(n)) * 0.005
        highs   = prices * (1.0 + spread)
        lows    = prices * (1.0 - spread)
        vol_avg = 1_000_000.0
        volumes = self._rng.exponential(vol_avg, n) * (1 + 2 * np.abs(lrets / (sigmas * np.sqrt(dt) + 1e-9)))

        self._prices  = prices
        self._highs   = highs
        self._lows    = lows
        self._volumes = volumes
        self._lrets   = lrets

    # ── Indicator Computation ──────────────────────────────────────────────────

    def _indicators(self, idx: int) -> Dict[str, float]:
        """Compute TA features at absolute index `idx` (uses prior history)."""
        p = self._prices
        h = self._highs
        lo = self._lows
        v  = self._volumes
        c  = p[:idx + 1]

        if len(c) < 55:
            return {k: 0.0 for k in ('rsi', 'macd', 'bb_pos', 'atr', 'adx', 'sma20', 'sma50', 'vr', 'vol20')}

        # RSI-14
        diff = np.diff(c[-15:])
        up   = np.maximum(diff, 0.0).mean()
        dn   = np.maximum(-diff, 0.0).mean() + 1e-9
        rsi  = up / (up + dn)

        # MACD histogram (12,26,9)  — using simple EMA approximation
        def ema(x, p):
            k = 2.0 / (p + 1)
            e = float(x[0])
            for v in x[1:]:
                e = float(v) * k + e * (1 - k)
            return e

        e12  = ema(c[-27:], 12)
        e26  = ema(c[-27:], 26)
        macd = (e12 - e26) / (c[-1] + 1e-9)
        # normalize to roughly [-1, 1]
        macd_n = float(np.clip(macd / 0.05, -1.0, 1.0)) * 0.5 + 0.5

        # Bollinger %B
        sma20  = c[-20:].mean()
        std20  = c[-20:].std() + 1e-9
        bb_pos = float(np.clip((c[-1] - (sma20 - 2 * std20)) / (4 * std20), 0.0, 1.0))

        # SMA50
        sma50 = c[-50:].mean()

        # ATR-14
        if len(h) > 15:
            tr = np.maximum(
                h[idx-13:idx+1] - lo[idx-13:idx+1],
                np.maximum(
                    np.abs(h[idx-13:idx+1] - p[idx-14:idx]),
                    np.abs(lo[idx-13:idx+1] - p[idx-14:idx])
                )
            )
            atr = tr.mean() / (c[-1] + 1e-9)
        else:
            atr = 0.0

        # ADX-lite
        if len(h) > 16:
            up_move = h[idx-14:idx] - h[idx-15:idx-1]
            dn_move = lo[idx-15:idx-1] - lo[idx-14:idx]
            plus_dm  = np.where(up_move > dn_move, np.maximum(up_move, 0), 0).sum()
            minus_dm = np.where(dn_move > up_move, np.maximum(dn_move, 0), 0).sum()
            adx = abs(plus_dm - minus_dm) / (plus_dm + minus_dm + 1e-9)
        else:
            adx = 0.0

        # Volume ratio
        vr    = v[idx] / (v[idx-19:idx+1].mean() + 1e-9)
        # 20d realized vol
        vol20 = c[-20:].std() / (c[-1] + 1e-9)

        return {
            'rsi':   float(rsi),
            'macd':  float(macd_n),
            'bb_pos': float(bb_pos),
            'atr':   float(np.clip(atr, 0, 0.1) / 0.1),
            'adx':   float(adx),
            'sma20': float(np.clip((c[-1] / (sma20 + 1e-9)) - 1.0, -0.1, 0.1) / 0.1),
            'sma50': float(np.clip((c[-1] / (sma50 + 1e-9)) - 1.0, -0.15, 0.15) / 0.15),
            'vr':    float(np.clip(vr, 0, 3) / 3),
            'vol20': float(np.clip(vol20, 0, 0.05) / 0.05),
        }

    # ── State Construction ─────────────────────────────────────────────────────

    def _get_state(self) -> np.ndarray:
        """Build 20-dim state vector from current environment state."""
        idx = self._warm + self._step
        c   = self._prices
        lr  = self._lrets
        hi  = self._highs

        price = c[idx]
        ind   = self._indicators(idx)

        # Price returns
        ret1  = lr[idx]
        ret5  = lr[max(0, idx-4):idx+1].sum()
        ret20 = lr[max(0, idx-19):idx+1].sum()

        # Range
        hl = (hi[idx] - self._lows[idx]) / (price + 1e-9)

        # Portfolio metrics
        pv     = self._cash + self._shares * price
        pos_r  = (self._shares * price) / (self.initial_capital + 1e-9)
        cash_r = self._cash / (self.initial_capital + 1e-9)
        upnl   = (pv - self.initial_capital) / self.initial_capital
        dd     = (pv - self._peak) / (self._peak + 1e-9)
        step_r = self._step / self.episode_length

        # Regime features
        trend_signed = float(np.sign(ret20) * ind['adx'])
        vol_regime   = ind['vol20']

        state = np.array([
            # [0-2] Returns
            float(np.clip(ret1,  -0.10, 0.10) / 0.10),
            float(np.clip(ret5,  -0.20, 0.20) / 0.20),
            float(np.clip(ret20, -0.30, 0.30) / 0.30),
            # [3-7] Price features
            ind['vol20'],
            ind['sma20'],
            ind['sma50'],
            float(np.clip(hl, 0, 0.05) / 0.05),
            ind['vr'],
            # [8-12] Indicators
            ind['rsi'],
            ind['macd'],
            ind['bb_pos'],
            ind['atr'],
            ind['adx'],
            # [13-17] Portfolio
            float(np.clip(pos_r,  -1.0, 1.0)),
            float(np.clip(cash_r,  0.0, 1.0)),
            float(np.clip(upnl, -0.50, 0.50) / 0.50),
            float(step_r),
            float(np.clip(dd, -0.50, 0.0) / 0.50 * -1.0),
            # [18-19] Regime
            float(np.clip(trend_signed, -1.0, 1.0)),
            float(vol_regime),
        ], dtype=np.float32)

        return state

    # ── Gym Interface ──────────────────────────────────────────────────────────

    def reset(self) -> np.ndarray:
        """Reset episode: generate new prices, clear state."""
        self._generate_episode()
        self._step        = 0
        self._done        = False
        self._cash        = self.initial_capital
        self._shares      = 0.0
        self._peak        = self.initial_capital
        self._step_returns = []
        self.trade_log     = []
        return self._get_state()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one trading step.

        Returns
        -------
        next_state, reward, done, info
        """
        assert not self._done, 'Episode finished. Call reset().'
        assert 0 <= action < self.ACTION_DIM, f'Invalid action {action}'

        idx   = self._warm + self._step
        price = self._prices[idx]
        pv_before = self._cash + self._shares * price

        # ── Execute action ────────────────────────────────
        action_str = 'HOLD'
        cost       = 0.0

        if action == 1:   # BUY_SMALL
            spend = min(self._cash, 0.10 * self.initial_capital)
            if spend >= price:
                bought        = spend / price * (1 - self.TRADE_COST)
                self._shares += bought
                self._cash   -= spend
                cost          = spend * self.TRADE_COST
                action_str    = f'BUY_SM @{price:.2f}'

        elif action == 2: # BUY_LARGE
            spend = min(self._cash, 0.25 * self.initial_capital)
            if spend >= price:
                bought        = spend / price * (1 - self.TRADE_COST)
                self._shares += bought
                self._cash   -= spend
                cost          = spend * self.TRADE_COST
                action_str    = f'BUY_LG @{price:.2f}'

        elif action == 3: # SELL_SMALL
            sv = min(self._shares * price, 0.10 * self.initial_capital)
            if sv > 0:
                self._shares -= sv / price
                self._cash   += sv * (1 - self.TRADE_COST)
                cost          = sv * self.TRADE_COST
                action_str    = f'SELL_SM @{price:.2f}'

        elif action == 4: # SELL_LARGE
            sv = min(self._shares * price, 0.25 * self.initial_capital)
            if sv > 0:
                self._shares -= sv / price
                self._cash   += sv * (1 - self.TRADE_COST)
                cost          = sv * self.TRADE_COST
                action_str    = f'SELL_LG @{price:.2f}'

        # ── Advance step ──────────────────────────────────
        self._step += 1
        next_idx    = self._warm + self._step
        next_price  = self._prices[next_idx] if self._step < self.episode_length else price

        pv_after    = self._cash + self._shares * next_price
        self._peak  = max(self._peak, pv_after)

        # ── Reward ────────────────────────────────────────
        step_ret = (pv_after - pv_before) / self.initial_capital
        self._step_returns.append(step_ret)

        # Sharpe shaping (running estimate over last 20 steps)
        reward = step_ret
        if len(self._step_returns) > 10:
            arr    = np.array(self._step_returns[-20:])
            sharpe = arr.mean() / (arr.std() + 1e-9) * np.sqrt(252)
            reward += 0.001 * sharpe

        # Drawdown penalty
        dd = (pv_after - self._peak) / (self._peak + 1e-9)
        if dd < -0.05:
            reward += 0.5 * dd

        # ── Termination ───────────────────────────────────
        self._done = (self._step >= self.episode_length)

        info = {
            'action':          action_str,
            'price':           float(price),
            'portfolio_value': float(pv_after),
            'cash':            float(self._cash),
            'shares':          float(self._shares),
            'step':            self._step,
            'total_return':    float((pv_after - self.initial_capital) / self.initial_capital),
            'drawdown':        float(dd),
        }

        if action != 0:
            self.trade_log.append({'step': self._step, **info})

        next_state = (
            self._get_state() if not self._done
            else np.zeros(self.STATE_DIM, dtype=np.float32)
        )

        return next_state, float(reward), self._done, info

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def state_dim(self) -> int:
        return self.STATE_DIM

    @property
    def action_dim(self) -> int:
        return self.ACTION_DIM

    @property
    def current_price(self) -> float:
        if self._prices is None:
            return 100.0
        idx = min(self._warm + self._step, len(self._prices) - 1)
        return float(self._prices[idx])

    @property
    def portfolio_value(self) -> float:
        return float(self._cash + self._shares * self.current_price)

    def __repr__(self) -> str:
        return (
            f'TradingEnvironment(ticker={self.ticker}, '
            f'step={self._step}/{self.episode_length}, '
            f'pv={self.portfolio_value:,.0f})'
        )
