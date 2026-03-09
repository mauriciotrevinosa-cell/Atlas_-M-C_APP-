"""
DQNTradingEngine — Phase 4 ML Engines (Reinforcement Learning)

Double DQN (DDQN) trading agent for Atlas.

Architecture inspired by speed-racer-rl (MIT License):
  - Two networks: policy_net (online) + target_net (frozen copy)
  - Soft target update: τ = 0.005 (polyak averaging)
  - Experience replay buffer (deque, capacity 50 000)
  - Epsilon-greedy exploration with linear decay

Adapted for trading:
  - State:  15-dimensional market feature vector (see TradingState)
  - Action: HOLD=0, BUY=1, SELL=2
  - Reward: realized PnL + unrealized PnL change (step reward)

Plugs into Atlas via BaseStrategy (implements generate_signals()).
For training, use RLTradingTrainer.

Dependencies:
  torch        — neural network and training
  numpy        — replay buffer and state construction
  pandas       — data interface

Install:
  pip install torch numpy pandas
"""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    # Graceful degradation: engine loads but training/inference fail
    torch = None  # type: ignore
    nn = None     # type: ignore
    optim = None  # type: ignore

from atlas.strategies.base import BaseStrategy


# ── Action space ──────────────────────────────────────────────────────────────

class TradingAction(IntEnum):
    HOLD = 0
    BUY  = 1
    SELL = 2


# ── State ─────────────────────────────────────────────────────────────────────

@dataclass
class TradingState:
    """
    15-dimensional state vector for the DQN agent.

    Features are designed to be stationary (returns, ratios, normalized values)
    so the network can generalize across different price levels.
    """
    # Price dynamics (5)
    ret_1: float   # 1-bar log return
    ret_5: float   # 5-bar log return
    ret_10: float  # 10-bar log return
    ret_20: float  # 20-bar log return
    hl_range: float  # (high - low) / close

    # Volume (2)
    volume_z: float    # 20-bar z-score of volume
    volume_ratio: float  # current volume / 5-bar avg volume

    # Momentum indicators (4)
    rsi_14: float       # RSI(14) normalized to [0,1]
    macd_hist: float    # MACD histogram, z-scored
    bb_position: float  # (close - lower_bb) / (upper_bb - lower_bb) → [0,1]
    atr_ratio: float    # ATR(14) / close

    # Portfolio state (4)
    position: float       # current position: -1/0/1
    unrealized_pnl: float # unrealized PnL as fraction of entry price
    capital_ratio: float  # current capital / initial capital (log scale)
    market_regime: float  # trend regime: -1=bear, 0=neutral, +1=bull (SMA cross)

    STATE_DIM: int = 15

    def to_tensor(self) -> "torch.Tensor":
        if not _TORCH_AVAILABLE:
            raise ImportError("torch is required for DQN inference.")
        values = [
            self.ret_1, self.ret_5, self.ret_10, self.ret_20, self.hl_range,
            self.volume_z, self.volume_ratio,
            self.rsi_14, self.macd_hist, self.bb_position, self.atr_ratio,
            self.position, self.unrealized_pnl, self.capital_ratio,
            self.market_regime,
        ]
        return torch.tensor(values, dtype=torch.float32)


# ── Neural network ────────────────────────────────────────────────────────────

def _build_dqn_net(state_dim: int, action_dim: int, hidden: int = 64) -> "nn.Module":
    """Three-layer MLP: state → hidden → hidden → Q-values."""
    if not _TORCH_AVAILABLE:
        raise ImportError("torch is required.")
    return nn.Sequential(
        nn.Linear(state_dim, hidden),
        nn.ReLU(),
        nn.Linear(hidden, hidden),
        nn.ReLU(),
        nn.Linear(hidden, action_dim),
    )


# ── Replay buffer ─────────────────────────────────────────────────────────────

class ReplayBuffer:
    """
    Circular experience replay buffer.

    Stores (state, action, reward, next_state, done) tuples.
    Samples a random mini-batch for training.
    """

    def __init__(self, capacity: int = 50_000):
        self.buffer: deque = deque(maxlen=capacity)

    def push(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int) -> Tuple:
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states,      dtype=np.float32),
            np.array(actions,     dtype=np.int64),
            np.array(rewards,     dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones,       dtype=np.float32),
        )

    def __len__(self) -> int:
        return len(self.buffer)


# ── Double DQN agent ──────────────────────────────────────────────────────────

class DoubleDQN:
    """
    Double DQN (DDQN) agent for trading.

    Key hyperparameters:
      gamma         = 0.99   discount factor
      tau           = 0.005  soft target network update rate
      lr            = 1e-4   Adam learning rate
      batch_size    = 64
      epsilon_start = 1.0    initial exploration rate
      epsilon_end   = 0.05   minimum exploration rate
      epsilon_decay = 5000   linear decay over N steps
    """

    GAMMA         = 0.99
    TAU           = 0.005
    LR            = 1e-4
    BATCH_SIZE    = 64
    EPS_START     = 1.0
    EPS_END       = 0.05
    EPS_DECAY     = 5_000
    GRAD_CLIP     = 1.0
    UPDATE_EVERY  = 4      # Train every N environment steps

    ACTION_DIM = len(TradingAction)  # 3

    def __init__(self, state_dim: int = TradingState.STATE_DIM, hidden: int = 64):
        if not _TORCH_AVAILABLE:
            raise ImportError(
                "PyTorch is required for DoubleDQN. "
                "Install with: pip install torch"
            )

        self.state_dim = state_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Policy net (updated every step) + Target net (soft-updated)
        self.policy_net = _build_dqn_net(state_dim, self.ACTION_DIM, hidden).to(self.device)
        self.target_net = _build_dqn_net(state_dim, self.ACTION_DIM, hidden).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.LR)
        self.loss_fn   = nn.SmoothL1Loss()  # Huber loss

        self.replay = ReplayBuffer()
        self.steps_done = 0

    # ── Action selection ──────────────────────────────────────────────────────

    def select_action(self, state: np.ndarray) -> int:
        """
        Epsilon-greedy action selection.

        Epsilon decays linearly from EPS_START → EPS_END over EPS_DECAY steps.
        """
        epsilon = max(
            self.EPS_END,
            self.EPS_START - (self.EPS_START - self.EPS_END) * self.steps_done / self.EPS_DECAY,
        )
        self.steps_done += 1

        if random.random() < epsilon:
            return random.randrange(self.ACTION_DIM)

        with torch.no_grad():
            t = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            q_values = self.policy_net(t)
            return int(q_values.argmax(dim=1).item())

    def greedy_action(self, state: np.ndarray) -> int:
        """Pure greedy action (no exploration) for inference."""
        with torch.no_grad():
            t = torch.tensor(state, dtype=torch.float32, device=self.device).unsqueeze(0)
            return int(self.policy_net(t).argmax(dim=1).item())

    # ── Training ──────────────────────────────────────────────────────────────

    def push(self, state, action, reward, next_state, done):
        self.replay.push(state, action, reward, next_state, done)

    def train_step(self) -> Optional[float]:
        """
        Sample a mini-batch and perform one gradient update.

        Returns the loss value, or None if buffer not yet large enough.
        """
        if len(self.replay) < self.BATCH_SIZE:
            return None

        states, actions, rewards, next_states, dones = self.replay.sample(self.BATCH_SIZE)

        states_t      = torch.tensor(states,      device=self.device)
        actions_t     = torch.tensor(actions,     device=self.device).unsqueeze(1)
        rewards_t     = torch.tensor(rewards,     device=self.device)
        next_states_t = torch.tensor(next_states, device=self.device)
        dones_t       = torch.tensor(dones,       device=self.device)

        # Current Q values
        current_q = self.policy_net(states_t).gather(1, actions_t).squeeze(1)

        # Double DQN target: use policy_net to SELECT action, target_net to EVALUATE it
        with torch.no_grad():
            next_actions = self.policy_net(next_states_t).argmax(dim=1, keepdim=True)
            next_q       = self.target_net(next_states_t).gather(1, next_actions).squeeze(1)
            target_q     = rewards_t + self.GAMMA * next_q * (1.0 - dones_t)

        loss = self.loss_fn(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), self.GRAD_CLIP)
        self.optimizer.step()

        # Soft update target network
        self._soft_update()

        return float(loss.item())

    def _soft_update(self) -> None:
        """Polyak averaging: target ← τ * policy + (1-τ) * target."""
        for target_p, policy_p in zip(
            self.target_net.parameters(), self.policy_net.parameters()
        ):
            target_p.data.copy_(
                self.TAU * policy_p.data + (1.0 - self.TAU) * target_p.data
            )

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        if not _TORCH_AVAILABLE:
            raise ImportError("torch required.")
        torch.save({
            "policy_state_dict": self.policy_net.state_dict(),
            "target_state_dict": self.target_net.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "steps_done": self.steps_done,
        }, path)

    def load(self, path: str) -> None:
        if not _TORCH_AVAILABLE:
            raise ImportError("torch required.")
        checkpoint = torch.load(path, map_location=self.device)
        self.policy_net.load_state_dict(checkpoint["policy_state_dict"])
        self.target_net.load_state_dict(checkpoint["target_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.steps_done = checkpoint.get("steps_done", 0)
        self.target_net.eval()


# ── Atlas strategy adapter ────────────────────────────────────────────────────

class DQNTradingEngine(BaseStrategy):
    """
    Wraps DoubleDQN as an Atlas BaseStrategy for use in the
    backtesting pipeline and orchestration layer.

    After training (fit()), generate_signals() runs the policy
    in greedy mode across the full data window.

    Usage::

        engine = DQNTradingEngine()
        engine.fit(train_data)
        signals = engine.generate_signals(test_data)
    """

    def __init__(self, state_dim: int = TradingState.STATE_DIM, hidden: int = 64):
        super().__init__(
            name="dqn_trading",
            description="Double DQN reinforcement learning trading engine.",
        )
        self.agent = DoubleDQN(state_dim=state_dim, hidden=hidden)

    def fit(self, data: pd.DataFrame, episodes: int = 100, **kwargs) -> "DQNTradingEngine":
        """
        Train the DQN agent on historical data.

        Each episode steps through the full data window.
        Use DQNTradingTrainer for a more controlled training loop
        with evaluation and early stopping.
        """
        trainer = DQNTradingTrainer(self.agent)
        trainer.train(data, episodes=episodes)
        self._fitted = True
        return self

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Run the trained policy in greedy mode.

        Returns a DataFrame with a 'signal' column (-1 / 0 / 1).
        Requires fit() to have been called first.
        """
        if not _TORCH_AVAILABLE:
            raise ImportError("torch required for DQN inference.")

        features = _extract_features(data)
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 0

        for i, idx in enumerate(data.index):
            if i >= len(features):
                break
            state = features[i]
            action = self.agent.greedy_action(state)
            if action == TradingAction.BUY:
                signals.loc[idx, "signal"] = 1
            elif action == TradingAction.SELL:
                signals.loc[idx, "signal"] = -1

        return signals


# ── Feature extraction ────────────────────────────────────────────────────────

def _extract_features(data: pd.DataFrame) -> np.ndarray:
    """
    Build the 15-feature state matrix from OHLCV data.

    Returns an (N, 15) float32 array. Rows with NaN (warm-up period)
    are forward-filled so all indices align with `data`.
    """
    df = data.copy()
    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    n = len(df)
    features = np.zeros((n, TradingState.STATE_DIM), dtype=np.float32)

    # ── Returns ───────────────────────────────────────────────────────────────
    log_ret = np.log(close / close.shift(1))
    features[:, 0] = log_ret.values
    features[:, 1] = np.log(close / close.shift(5)).values
    features[:, 2] = np.log(close / close.shift(10)).values
    features[:, 3] = np.log(close / close.shift(20)).values

    # ── HL range ──────────────────────────────────────────────────────────────
    features[:, 4] = ((high - low) / close).values

    # ── Volume ────────────────────────────────────────────────────────────────
    vol_mean20 = vol.rolling(20).mean()
    vol_std20  = vol.rolling(20).std().replace(0, 1)
    features[:, 5] = ((vol - vol_mean20) / vol_std20).values

    vol_mean5 = vol.rolling(5).mean().replace(0, 1)
    features[:, 6] = (vol / vol_mean5).values

    # ── RSI(14) ───────────────────────────────────────────────────────────────
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean().replace(0, 1e-9)
    rs    = gain / loss
    features[:, 7] = (100 - 100 / (1 + rs)).values / 100.0  # Normalized [0,1]

    # ── MACD histogram (z-scored) ─────────────────────────────────────────────
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist  = macd - signal
    hist_z = (hist - hist.rolling(50).mean()) / hist.rolling(50).std().replace(0, 1)
    features[:, 8] = hist_z.values

    # ── Bollinger Band position ───────────────────────────────────────────────
    sma20   = close.rolling(20).mean()
    std20   = close.rolling(20).std()
    upper   = sma20 + 2 * std20
    lower   = sma20 - 2 * std20
    bb_pos  = (close - lower) / (upper - lower).replace(0, 1)
    features[:, 9] = bb_pos.clip(0, 1).values

    # ── ATR(14) / close ───────────────────────────────────────────────────────
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr  = tr.rolling(14).mean()
    features[:, 10] = (atr / close.replace(0, 1)).values

    # ── Portfolio state (defaults — overridden during live/sim trading) ────────
    # positions 11-14 stay 0 when generating signals in batch mode
    # (unrealized PnL, capital ratio, etc. are updated during step-by-step sim)

    # ── Market regime: SMA(50) vs SMA(200) ────────────────────────────────────
    sma50  = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    regime = np.sign((sma50 - sma200).fillna(0)).values.astype(np.float32)
    features[:, 14] = regime

    # Fill leading NaNs from rolling calculations
    df_feat = pd.DataFrame(features)
    df_feat = df_feat.ffill().fillna(0)

    return df_feat.values.astype(np.float32)


# ── Trainer ───────────────────────────────────────────────────────────────────

class DQNTradingTrainer:
    """
    Training loop for DoubleDQN on historical OHLCV data.

    Each episode steps through the full price history, computing rewards
    based on realized + unrealized PnL.
    """

    INITIAL_CAPITAL = 10_000.0
    TRADE_COST      = 0.001     # 0.1% per trade (taker fee)
    MAX_POSITION    = 1         # 1 = fully invested

    def __init__(self, agent: DoubleDQN):
        self.agent = agent

    def train(
        self,
        data: pd.DataFrame,
        episodes: int = 100,
        verbose: bool = True,
    ) -> List[float]:
        """
        Train for `episodes` passes over `data`.

        Returns list of episode total rewards.
        """
        features = _extract_features(data)
        close    = data["close"].values
        n        = len(close)
        episode_rewards = []

        for ep in range(episodes):
            capital  = self.INITIAL_CAPITAL
            position = 0       # -1 / 0 / 1
            entry_price = 0.0
            total_reward = 0.0

            for i in range(n - 1):
                state = features[i].copy()
                # Inject portfolio state into features 11-14
                state[11] = float(position)
                state[12] = float(
                    (close[i] - entry_price) / entry_price
                    if entry_price > 0 and position != 0 else 0.0
                )
                state[13] = float(np.log(capital / self.INITIAL_CAPITAL + 1e-9))

                action = self.agent.select_action(state)
                reward = 0.0

                # ── Execute action ────────────────────────────────────────────
                if action == TradingAction.BUY and position <= 0:
                    if position == -1:  # Close short
                        pnl = (entry_price - close[i]) * (1 - self.TRADE_COST)
                        capital += pnl
                        reward  += pnl / self.INITIAL_CAPITAL
                    position = 1
                    entry_price = close[i]
                    capital -= capital * self.TRADE_COST  # Buy fee

                elif action == TradingAction.SELL and position >= 0:
                    if position == 1:  # Close long
                        pnl = (close[i] - entry_price) * (1 - self.TRADE_COST)
                        capital += pnl
                        reward  += pnl / self.INITIAL_CAPITAL
                    position = -1
                    entry_price = close[i]
                    capital -= capital * self.TRADE_COST  # Sell fee

                # ── Unrealized PnL as step reward ─────────────────────────────
                if position == 1:
                    reward += (close[i + 1] - close[i]) / close[i] * 0.1
                elif position == -1:
                    reward += (close[i] - close[i + 1]) / close[i] * 0.1

                next_state = features[i + 1].copy()
                next_state[11] = float(position)
                next_state[12] = float(
                    (close[i + 1] - entry_price) / entry_price
                    if entry_price > 0 and position != 0 else 0.0
                )
                next_state[13] = float(np.log(capital / self.INITIAL_CAPITAL + 1e-9))

                done = i == n - 2
                self.agent.push(state, action, reward, next_state, done)

                if i % self.agent.UPDATE_EVERY == 0:
                    self.agent.train_step()

                total_reward += reward

            episode_rewards.append(total_reward)

            if verbose and (ep + 1) % 10 == 0:
                avg = np.mean(episode_rewards[-10:])
                print(f"Episode {ep+1:4d}/{episodes} | "
                      f"Reward: {total_reward:8.4f} | "
                      f"Avg(10): {avg:8.4f} | "
                      f"Epsilon: {max(DoubleDQN.EPS_END, DoubleDQN.EPS_START - (DoubleDQN.EPS_START - DoubleDQN.EPS_END) * self.agent.steps_done / DoubleDQN.EPS_DECAY):.3f}")

        return episode_rewards
