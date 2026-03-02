# RL Trading Engine — DQN Implementation Guide

**Source:** speed-racer-rl by Anthony Atanasov (MIT License)
**License:** MIT — C++ code can be ported/adapted directly.
**Created:** 2026-02-25
**Purpose:** Adapt Double DQN from a C++ racing simulator to a Python trading RL agent for Atlas Phase 4 ML Engines.

---

## 1. Original Architecture (speed-racer-rl)

The C++ implementation uses:
- **Double DQN** (DDQN) — action selection with policy net, evaluation with target net
- **MLP policy network**: `state_size → 64 → 64 → action_size`
- **Soft target update**: `θ' ← τθ + (1-τ)θ'` (τ=0.005 per step)
- **Adam optimizer** with gradient clipping (norm=1.0)
- **Experience replay buffer**: random sampling from circular buffer

### Original C++ DQN class summary:
```cpp
// dqn.h — DQNNet: MLP with 3 FC layers
struct DQNNetImpl : torch::nn::Module {
    Linear fc1(state_size, 64), fc2(64, 64), fc3(64, action_size);
    Tensor forward(Tensor x) { relu(fc1) → relu(fc2) → fc3 }
};

// DQN class methods:
// - predict(state) → Q-values vector
// - train(batch) → loss  [Double DQN + soft update]
// - soft_update_target(tau=0.005)
// - save_model / load_model
```

### Original Experience struct:
```cpp
// replay_buffer.h
struct Experience { state, action, reward, next_state, done }
class ReplayBuffer {
    add(state, action, reward, next_state, done)
    sample(batch_size) → {states, actions, rewards, next_states, dones}
    can_sample(batch_size) → bool
}
```

---

## 2. Python Trading Adaptation

### 2.1 State Space (Market Features)

**File:** `strategies/ml/rl/state_builder.py`

```python
# MIT — adapted from speed-racer-rl concepts
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass
class TradingState:
    """
    State vector for the trading RL agent.
    Dimensions: ~20 features (normalize to [-1, 1] or [0, 1])
    """
    # Price features
    price_change_1d: float       # (close - close_1) / close_1
    price_change_5d: float       # (close - close_5) / close_5
    price_change_20d: float      # (close - close_20) / close_20
    high_low_ratio: float        # (high - low) / close

    # Volume features
    volume_ratio_5d: float       # volume / volume_ma_5
    volume_ratio_20d: float      # volume / volume_ma_20

    # Technical indicators (pre-normalized)
    rsi_14: float                # RSI / 100
    macd_signal: float           # MACD histogram normalized
    bb_position: float           # (close - bb_lower) / (bb_upper - bb_lower)
    atr_ratio: float             # ATR / close (volatility)

    # Position features
    position: float              # -1=short, 0=flat, 1=long
    unrealized_pnl: float        # normalized unrealized PnL
    time_in_trade: float         # steps held / max_steps

    # Market regime
    trend_strength: float        # ADX / 100
    volatility_regime: float     # current_vol / historical_vol

    def to_array(self) -> np.ndarray:
        return np.array([
            self.price_change_1d, self.price_change_5d, self.price_change_20d,
            self.high_low_ratio, self.volume_ratio_5d, self.volume_ratio_20d,
            self.rsi_14, self.macd_signal, self.bb_position, self.atr_ratio,
            self.position, self.unrealized_pnl, self.time_in_trade,
            self.trend_strength, self.volatility_regime,
        ], dtype=np.float32)

STATE_DIM = 15   # len(TradingState.to_array())
```

### 2.2 Action Space

```python
# strategies/ml/rl/actions.py
from enum import IntEnum

class TradingAction(IntEnum):
    HOLD = 0
    BUY = 1     # enter long (or close short)
    SELL = 2    # enter short (or close long)

ACTION_DIM = 3  # len(TradingAction)

# Reward function options:
class RewardFunction:
    @staticmethod
    def pnl_reward(prev_portfolio_value: float, curr_portfolio_value: float) -> float:
        """Simple PnL reward."""
        return (curr_portfolio_value - prev_portfolio_value) / prev_portfolio_value

    @staticmethod
    def sharpe_reward(returns: list[float], window: int = 20) -> float:
        """Rolling Sharpe ratio as reward. More stable training."""
        if len(returns) < 2:
            return 0.0
        recent = returns[-window:]
        mean = np.mean(recent)
        std = np.std(recent) + 1e-8
        return mean / std * np.sqrt(252)

    @staticmethod
    def risk_adjusted_reward(pnl: float, drawdown: float, trade_cost: float = 0.001) -> float:
        """PnL minus transaction cost and drawdown penalty."""
        return pnl - trade_cost - 0.1 * max(drawdown, 0)
```

### 2.3 DQN Network (Python/PyTorch port from C++)

**File:** `strategies/ml/rl/dqn.py`

```python
# Adapted from speed-racer-rl dqn.h (MIT License)
# Original C++/LibTorch → Python/PyTorch port
# Copyright 2026 Anthony Atanasov (original), Atlas adaptation

import torch
import torch.nn as nn
import numpy as np
from copy import deepcopy

class DQNNet(nn.Module):
    """
    MLP policy network.
    Mirrors the C++ DQNNetImpl: state_size → 64 → 64 → action_size
    """
    def __init__(self, state_size: int, action_size: int):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(state_size, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, action_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class DoubleDQN:
    """
    Double DQN agent for trading decisions.

    Port of speed-racer-rl DQN class (MIT) with trading-specific adjustments:
    - action space: {HOLD, BUY, SELL} instead of {LEFT, ACCEL, BRAKE, ...}
    - state space: market features instead of racing simulation state
    - reward: PnL-based instead of lap time
    """

    def __init__(
        self,
        state_size: int = STATE_DIM,
        action_size: int = ACTION_DIM,
        learning_rate: float = 1e-3,
        gamma: float = 0.99,
        tau: float = 0.005,          # soft update factor (from original)
        epsilon_start: float = 1.0,  # exploration
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.995,
        device: str = "auto",
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.tau = tau
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay

        # Device setup
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        # Policy net + target net (Double DQN)
        self.policy_net = DQNNet(state_size, action_size).to(self.device)
        self.target_net = deepcopy(self.policy_net).to(self.device)
        self.target_net.eval()

        self.optimizer = torch.optim.Adam(
            self.policy_net.parameters(),
            lr=learning_rate
        )

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        Epsilon-greedy action selection.
        During inference (training=False), always greedy.
        """
        if training and np.random.random() < self.epsilon:
            return np.random.randint(self.action_size)  # explore

        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax(dim=1).item()  # exploit

    def train_step(self, batch: dict) -> float:
        """
        Double DQN update on a single batch.
        Mirrors DQN::train() from speed-racer-rl.

        batch keys: states, actions, rewards, next_states, dones
        """
        states = torch.FloatTensor(batch["states"]).to(self.device)
        actions = torch.LongTensor(batch["actions"]).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor(batch["rewards"]).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(batch["next_states"]).to(self.device)
        dones = torch.FloatTensor(batch["dones"]).unsqueeze(1).to(self.device)

        # Current Q(s, a)
        current_q = self.policy_net(states).gather(1, actions)

        # Double DQN target:
        # action selected by policy net, evaluated by target net
        with torch.no_grad():
            next_actions = self.policy_net(next_states).argmax(1, keepdim=True)
            next_q = self.target_net(next_states).gather(1, next_actions)
            target_q = rewards + self.gamma * next_q * (1.0 - dones)

        # Huber loss (more stable than MSE for RL)
        loss = nn.functional.huber_loss(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)  # from original
        self.optimizer.step()

        # Soft update target network (from original: tau=0.005)
        self._soft_update_target()

        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        return loss.item()

    def _soft_update_target(self):
        """θ' ← τθ + (1-τ)θ' — from speed-racer-rl soft_update_target()"""
        with torch.no_grad():
            for target_param, policy_param in zip(
                self.target_net.parameters(),
                self.policy_net.parameters()
            ):
                target_param.data.copy_(
                    self.tau * policy_param.data + (1.0 - self.tau) * target_param.data
                )

    def save(self, path: str):
        torch.save({
            "policy_net": self.policy_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "epsilon": self.epsilon,
        }, path)

    def load(self, path: str):
        checkpoint = torch.load(path, map_location=self.device)
        self.policy_net.load_state_dict(checkpoint["policy_net"])
        self.target_net.load_state_dict(checkpoint["target_net"])
        self.optimizer.load_state_dict(checkpoint["optimizer"])
        self.epsilon = checkpoint["epsilon"]
```

### 2.4 Replay Buffer (Python port from C++)

**File:** `strategies/ml/rl/replay_buffer.py`

```python
# Adapted from speed-racer-rl replay_buffer.h (MIT License)
# Original C++ → Python port

import numpy as np
import random
from dataclasses import dataclass
from collections import deque

@dataclass
class Experience:
    """Mirrors speed-racer-rl Experience struct."""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool

class ReplayBuffer:
    """
    Experience replay buffer.
    Circular buffer using deque (faster than list.pop(0) in original C++).
    """

    def __init__(self, capacity: int = 10_000):
        self.buffer: deque[Experience] = deque(maxlen=capacity)

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ):
        """Add experience. Automatically evicts oldest when full."""
        self.buffer.append(Experience(state, action, reward, next_state, done))

    def sample(self, batch_size: int) -> dict:
        """Random batch sampling (uniform, without replacement)."""
        batch = random.sample(self.buffer, batch_size)
        return {
            "states": np.stack([e.state for e in batch]),
            "actions": np.array([e.action for e in batch]),
            "rewards": np.array([e.reward for e in batch]),
            "next_states": np.stack([e.next_state for e in batch]),
            "dones": np.array([e.done for e in batch], dtype=np.float32),
        }

    def __len__(self) -> int:
        return len(self.buffer)

    def can_sample(self, batch_size: int) -> bool:
        return len(self) >= batch_size
```

### 2.5 Training Loop

**File:** `strategies/ml/rl/trainer.py`

```python
# Atlas RL Trainer — adapted from speed-racer-rl racing_trainer.cpp concepts

class RLTradingTrainer:
    """
    Training loop for the DQN trading agent.

    Environment: TradingEnv (wraps Atlas backtest engine)
    Agent: DoubleDQN
    Buffer: ReplayBuffer
    """

    def __init__(
        self,
        env,                          # TradingEnv instance
        agent: DoubleDQN,
        buffer: ReplayBuffer,
        batch_size: int = 64,
        min_buffer_size: int = 1000,  # warmup before training starts
        train_frequency: int = 4,     # train every N steps
        eval_frequency: int = 100,    # evaluate every N episodes
    ):
        self.env = env
        self.agent = agent
        self.buffer = buffer
        self.batch_size = batch_size
        self.min_buffer_size = min_buffer_size
        self.train_frequency = train_frequency
        self.eval_frequency = eval_frequency

    def train(self, num_episodes: int) -> dict:
        """Run full training loop."""
        stats = {"episode_rewards": [], "losses": [], "epsilon_history": []}
        step = 0

        for episode in range(num_episodes):
            state = self.env.reset()
            episode_reward = 0
            done = False

            while not done:
                # Select action
                action = self.agent.select_action(state, training=True)

                # Execute action in environment
                next_state, reward, done, info = self.env.step(action)

                # Store experience
                self.buffer.add(state, action, reward, next_state, done)
                state = next_state
                episode_reward += reward
                step += 1

                # Train when buffer has enough experiences
                if (
                    self.buffer.can_sample(self.batch_size)
                    and len(self.buffer) >= self.min_buffer_size
                    and step % self.train_frequency == 0
                ):
                    batch = self.buffer.sample(self.batch_size)
                    loss = self.agent.train_step(batch)
                    stats["losses"].append(loss)

            stats["episode_rewards"].append(episode_reward)
            stats["epsilon_history"].append(self.agent.epsilon)

            if episode % self.eval_frequency == 0:
                eval_reward = self._evaluate()
                print(
                    f"Episode {episode:4d} | "
                    f"Train Reward: {episode_reward:7.2f} | "
                    f"Eval Reward: {eval_reward:7.2f} | "
                    f"Epsilon: {self.agent.epsilon:.3f}"
                )

        return stats

    def _evaluate(self, num_episodes: int = 5) -> float:
        """Run evaluation episodes (no exploration)."""
        total_reward = 0
        for _ in range(num_episodes):
            state = self.env.reset()
            done = False
            while not done:
                action = self.agent.select_action(state, training=False)
                state, reward, done, _ = self.env.step(action)
                total_reward += reward
        return total_reward / num_episodes
```

### 2.6 Trading Environment

**File:** `strategies/ml/rl/trading_env.py`

```python
# TradingEnv — wraps Atlas backtest as a Gym-compatible environment

class TradingEnv:
    """
    OpenAI Gym-compatible environment for RL training.
    Wraps Atlas data layer + execution engine.
    """

    def __init__(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 10_000,
        transaction_cost: float = 0.001,   # 0.1% per trade
        max_steps: int = 252,              # 1 trading year
    ):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.max_steps = max_steps
        self._load_data(symbol, start_date, end_date)

    def reset(self) -> np.ndarray:
        """Reset environment for new episode."""
        self.current_step = 0
        self.portfolio_value = self.initial_capital
        self.position = 0  # 0=flat, 1=long, -1=short
        self.entry_price = 0.0
        self.trade_history = []
        return self._get_state()

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict]:
        """
        Execute action.
        Returns: (next_state, reward, done, info)
        """
        prev_portfolio = self.portfolio_value
        self._execute_action(action)
        self.current_step += 1

        reward = RewardFunction.risk_adjusted_reward(
            pnl=(self.portfolio_value - prev_portfolio) / prev_portfolio,
            drawdown=self._current_drawdown(),
        )

        done = (self.current_step >= self.max_steps)
        return self._get_state(), reward, done, {"portfolio": self.portfolio_value}

    def _get_state(self) -> np.ndarray:
        """Build TradingState from current market data."""
        row = self.data.iloc[self.current_step]
        state = TradingState(
            price_change_1d=row["price_change_1d"],
            price_change_5d=row["price_change_5d"],
            # ... compute all features
            position=float(self.position),
            unrealized_pnl=self._unrealized_pnl(),
            time_in_trade=min(self.current_step / self.max_steps, 1.0),
        )
        return state.to_array()
```

---

## 3. Integration with Atlas Qlib-style Strategy

The DQN agent integrates as a `BaseEngine` via Qlib's `RLIntStrategy` pattern:

```python
# strategies/ml/rl/rl_engine.py
from ...strategies.base import BaseEngine
from .dqn import DoubleDQN
from .replay_buffer import ReplayBuffer
from .trading_env import TradingEnv

class DQNTradingEngine(BaseEngine):
    """
    RL-based trading engine using Double DQN.
    Implements the BaseEngine interface for integration with Atlas orchestration.
    """

    name = "dqn_trading"

    def __init__(self, model_path: str | None = None, **kwargs):
        self.agent = DoubleDQN(**kwargs)
        self.buffer = ReplayBuffer(capacity=50_000)
        if model_path:
            self.agent.load(model_path)

    def generate_signal(self, state: np.ndarray) -> dict:
        """Generate trading signal from current market state."""
        action = self.agent.select_action(state, training=False)
        q_values = self._get_q_values(state)

        return {
            "action": TradingAction(action).name,
            "confidence": float(q_values.max() - q_values.min()),  # rough confidence
            "q_values": {
                "HOLD": float(q_values[0]),
                "BUY": float(q_values[1]),
                "SELL": float(q_values[2]),
            }
        }

    def train(self, symbol: str, start_date: str, end_date: str, episodes: int = 200):
        """Train the DQN agent on historical data."""
        env = TradingEnv(symbol, start_date, end_date)
        trainer = RLTradingTrainer(env, self.agent, self.buffer)
        return trainer.train(num_episodes=episodes)
```

---

## 4. File Structure to Create

```
python/src/atlas/strategies/ml/rl/
├── __init__.py
├── dqn.py           # DoubleDQN class (ported from C++)
├── replay_buffer.py # ReplayBuffer (ported from C++)
├── actions.py       # TradingAction enum + RewardFunction
├── state_builder.py # TradingState dataclass
├── trading_env.py   # TradingEnv (Gym-compatible)
├── trainer.py       # RLTradingTrainer
└── rl_engine.py     # DQNTradingEngine (BaseEngine adapter)
```

---

## 5. Hyperparameter Reference

From speed-racer-rl defaults + trading adaptations:

| Parameter | Racing (original) | Trading (adapted) | Notes |
|-----------|------------------|-------------------|-------|
| Hidden size | 64, 64 | 64, 64 | Same MLP |
| Learning rate | 0.001 | 0.0001–0.001 | Lower for noisy rewards |
| Gamma | 0.99 | 0.99 | Standard |
| Tau | 0.005 | 0.005 | Same soft update |
| Epsilon start | 1.0 | 1.0 | Full exploration |
| Epsilon end | - | 0.05 | 5% random action floor |
| Epsilon decay | - | 0.995/step | ~1000 steps to reach 0.05 |
| Batch size | - | 64 | Standard |
| Buffer size | - | 50,000 | ~200 trading days |
| Min buffer | - | 1,000 | Warmup period |
| Train freq | - | 4 steps | Every 4 decisions |
| Grad clip | 1.0 | 1.0 | Same as original |
