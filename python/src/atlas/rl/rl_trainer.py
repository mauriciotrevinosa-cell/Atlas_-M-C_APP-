"""
RLTrainer — DQN training loop for Atlas RL environment.

Features:
  · Episode management (run_episode / train)
  · Sharpe / drawdown / win-rate metric tracking
  · Best-model checkpoint (JSON weights)
  · Callback support for real-time frontend updates
  · Stop flag for graceful interruption
  · Summary statistics
"""

from __future__ import annotations

import logging
import os
import time
from typing import Callable, Dict, List, Optional

import numpy as np

from .trading_env import TradingEnvironment
from .dqn_agent import DQNAgent

logger = logging.getLogger(__name__)


class RLTrainer:
    """
    High-level training orchestrator.

    Usage
    -----
    trainer = RLTrainer(ticker='SPY', max_episodes=300)
    history = trainer.train(on_episode=lambda m: print(m))
    print(trainer.get_summary())
    """

    DEFAULT_SAVE_DIR = os.path.join(
        os.path.dirname(__file__), 'checkpoints'
    )

    def __init__(
        self,
        ticker:          str   = 'SPY',
        initial_capital: float = 100_000.0,
        episode_length:  int   = 252,
        max_episodes:    int   = 500,
        save_dir:        Optional[str] = None,
        # DQN hyper-params (passed to DQNAgent)
        lr:                  float = 1e-3,
        gamma:               float = 0.99,
        epsilon_start:       float = 1.0,
        epsilon_end:         float = 0.05,
        epsilon_decay:       float = 0.995,
        batch_size:          int   = 64,
        buffer_capacity:     int   = 10_000,
        target_update_freq:  int   = 10,
        # Env params
        regime_switch: bool = True,
    ):
        self.ticker         = ticker
        self.max_episodes   = max_episodes
        self.save_dir       = save_dir or self.DEFAULT_SAVE_DIR
        os.makedirs(self.save_dir, exist_ok=True)

        self.env = TradingEnvironment(
            initial_capital = initial_capital,
            episode_length  = episode_length,
            ticker          = ticker,
            regime_switch   = regime_switch,
        )

        self.agent = DQNAgent(
            state_dim          = self.env.state_dim,
            action_dim         = self.env.action_dim,
            lr                 = lr,
            gamma              = gamma,
            epsilon_start      = epsilon_start,
            epsilon_end        = epsilon_end,
            epsilon_decay      = epsilon_decay,
            batch_size         = batch_size,
            buffer_capacity    = buffer_capacity,
            target_update_freq = target_update_freq,
        )

        # Episode history
        self._returns:    List[float] = []
        self._sharpes:    List[float] = []
        self._drawdowns:  List[float] = []
        self._losses:     List[float] = []
        self._n_trades:   List[int]   = []
        self._best_return: float = -np.inf
        self._running:     bool  = False

    # ── Episode runner ─────────────────────────────────────────────────────────

    def run_episode(self) -> Dict:
        """Execute one full training episode and return metrics."""
        state      = self.env.reset()
        ep_loss    = []
        n_trades   = 0

        while True:
            action = self.agent.act(state, explore=True)
            next_state, reward, done, info = self.env.step(action)

            self.agent.push(state, action, reward, next_state, done)
            loss = self.agent.train_step()

            if loss is not None:
                ep_loss.append(loss)
            if action != 0:
                n_trades += 1

            state = next_state
            if done:
                break

        self.agent.end_episode()

        # ── Per-episode metrics ─────────────────────────────────────────────
        total_ret = info['total_return']

        # Sharpe from step-level returns
        rets = np.array([r for _, r, _, _ in [
            # re-derive step returns from trade log if available
        ]])
        # simpler: use agent loss list as proxy; compute Sharpe from PnL slope
        # We approximate Sharpe via total_ret / realized vol estimate
        vol_est   = self.env.sigma / np.sqrt(252) * np.sqrt(self.env.episode_length)
        sharpe    = total_ret / (vol_est + 1e-9)

        # Max drawdown
        pv_curve = np.array([t['portfolio_value'] for t in self.env.trade_log]) \
                   if self.env.trade_log else np.array([self.env.portfolio_value])
        if len(pv_curve) > 1:
            peak     = np.maximum.accumulate(pv_curve)
            dd_curve = (pv_curve - peak) / (peak + 1e-9)
            max_dd   = float(dd_curve.min())
        else:
            max_dd = 0.0

        avg_loss = float(np.mean(ep_loss)) if ep_loss else 0.0

        metrics = {
            'episode':           self.agent.episode,
            'total_return_pct':  round(total_ret * 100, 2),
            'sharpe':            round(sharpe, 3),
            'max_drawdown_pct':  round(max_dd * 100, 2),
            'avg_loss':          round(avg_loss, 6),
            'n_trades':          n_trades,
            'epsilon':           round(self.agent.epsilon, 4),
            'portfolio_value':   round(self.env.portfolio_value, 2),
            'ticker':            self.ticker,
        }

        # Store
        self._returns.append(total_ret * 100)
        self._sharpes.append(sharpe)
        self._drawdowns.append(max_dd * 100)
        self._losses.append(avg_loss)
        self._n_trades.append(n_trades)

        # Checkpoint best
        if total_ret > self._best_return:
            self._best_return = total_ret
            ckpt = os.path.join(self.save_dir, f'{self.ticker}_best.json')
            try:
                self.agent.save(ckpt)
            except Exception as exc:
                logger.warning(f'Checkpoint save failed: {exc}')

        return metrics

    # ── Main training loop ─────────────────────────────────────────────────────

    def train(
        self,
        n_episodes:  Optional[int]                  = None,
        on_episode:  Optional[Callable[[Dict], None]] = None,
        stop_flag:   Optional[List[bool]]            = None,
        verbose_every: int = 10,
    ) -> List[Dict]:
        """
        Run the training loop.

        Parameters
        ----------
        n_episodes    : override max_episodes
        on_episode    : callback(metrics) called after each episode
        stop_flag     : list[bool]; set stop_flag[0]=True to halt early
        verbose_every : log progress every N episodes

        Returns
        -------
        history : list of per-episode metric dicts
        """
        n       = n_episodes or self.max_episodes
        history: List[Dict] = []
        self._running = True

        logger.info(
            f'[RLTrainer] Start — ticker={self.ticker}, '
            f'episodes={n}, ε_start={self.agent.epsilon:.2f}'
        )

        for ep in range(n):
            if stop_flag and stop_flag[0]:
                logger.info(f'[RLTrainer] Halted at episode {ep} (stop_flag).')
                break

            t0      = time.perf_counter()
            metrics = self.run_episode()
            metrics['elapsed_ms'] = round((time.perf_counter() - t0) * 1000, 1)
            history.append(metrics)

            if ep % verbose_every == 0:
                avg10 = (
                    np.mean(self._returns[-10:])
                    if len(self._returns) >= 10 else 0.0
                )
                logger.info(
                    f'[RLTrainer] Ep {ep:4d}/{n} | '
                    f'ret={metrics["total_return_pct"]:+6.2f}% | '
                    f'avg10={avg10:+5.1f}% | '
                    f'sharpe={metrics["sharpe"]:.3f} | '
                    f'ε={metrics["epsilon"]:.3f} | '
                    f'loss={metrics["avg_loss"]:.5f} | '
                    f'trades={metrics["n_trades"]}'
                )

            if on_episode:
                try:
                    on_episode(metrics)
                except Exception as exc:
                    logger.warning(f'on_episode callback raised: {exc}')

        self._running = False
        logger.info(
            f'[RLTrainer] Complete — best_return={self._best_return*100:.2f}%'
        )
        return history

    # ── Summary ───────────────────────────────────────────────────────────────

    def get_summary(self) -> Dict:
        """Return training summary statistics."""
        if not self._returns:
            return {'error': 'No episodes run yet.'}

        arr = np.array(self._returns)
        return {
            'ticker':           self.ticker,
            'n_episodes':       int(len(arr)),
            'avg_return_pct':   round(float(arr.mean()), 2),
            'best_return_pct':  round(float(arr.max()),  2),
            'worst_return_pct': round(float(arr.min()),  2),
            'win_rate_pct':     round(float((arr > 0).mean() * 100), 1),
            'avg_sharpe':       round(float(np.mean(self._sharpes)), 3),
            'avg_drawdown_pct': round(float(np.mean(self._drawdowns)), 2),
            'total_trades':     int(sum(self._n_trades)),
            'avg_trades_ep':    round(float(np.mean(self._n_trades)), 1),
            'epsilon_final':    round(self.agent.epsilon, 4),
            'train_steps':      self.agent.train_steps,
            'best_return_seen': round(self._best_return * 100, 2),
            'agent_metrics':    self.agent.metrics,
        }

    # ── Convenience ───────────────────────────────────────────────────────────

    def load_best(self) -> bool:
        """Load best checkpoint. Returns True if found."""
        ckpt = os.path.join(self.save_dir, f'{self.ticker}_best.json')
        if os.path.exists(ckpt):
            self.agent.load(ckpt)
            logger.info(f'[RLTrainer] Loaded checkpoint: {ckpt}')
            return True
        return False

    def evaluate(self, n_episodes: int = 20) -> Dict:
        """
        Run evaluation episodes (no exploration, no training).
        Returns averaged metrics.
        """
        results = []
        for _ in range(n_episodes):
            state = self.env.reset()
            while True:
                action = self.agent.act(state, explore=False)
                state, _, done, info = self.env.step(action)
                if done:
                    break
            results.append(info['total_return'])

        arr = np.array(results) * 100
        return {
            'eval_episodes':     n_episodes,
            'avg_return_pct':    round(float(arr.mean()), 2),
            'best_return_pct':   round(float(arr.max()),  2),
            'worst_return_pct':  round(float(arr.min()),  2),
            'win_rate_pct':      round(float((arr > 0).mean() * 100), 1),
            'std_return_pct':    round(float(arr.std()), 2),
        }

    def __repr__(self) -> str:
        return (
            f'RLTrainer(ticker={self.ticker}, '
            f'episodes={self.agent.episode}/{self.max_episodes}, '
            f'running={self._running})'
        )
