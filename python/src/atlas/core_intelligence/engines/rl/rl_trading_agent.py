"""
Reinforcement Learning Trading Agent
=======================================
Complete RL stack: Environment + Agent + Training Loop.

Environment: OpenAI Gym-style trading environment
Agent:       DQN (Deep Q-Network) with experience replay
Reward:      Risk-adjusted PnL (Sharpe-aware)

The agent observes market state + features → decides action → receives reward.

Actions: 0=HOLD, 1=BUY, 2=SELL, 3=CLOSE
State:   [features + position_info + pnl_info]

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import random
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.rl")


# ══════════════════════════════════════════════════════════════════
#  TRADING ENVIRONMENT
# ══════════════════════════════════════════════════════════════════

class TradingEnvironment:
    """
    Gym-style trading environment.

    Observation space: feature vector + position state
    Action space:      {0: HOLD, 1: BUY, 2: SELL, 3: CLOSE}
    Reward:            Risk-adjusted PnL
    """

    HOLD = 0
    BUY = 1
    SELL = 2
    CLOSE = 3

    def __init__(
        self,
        features: np.ndarray,
        prices: np.ndarray,
        initial_capital: float = 100_000,
        commission_pct: float = 0.001,
        max_position: float = 1.0,
        reward_type: str = "sharpe",  # "pnl", "sharpe", "sortino"
    ):
        """
        Args:
            features:        Feature matrix (T × N_features)
            prices:          Close prices array (T,)
            initial_capital: Starting capital
            commission_pct:  Commission as fraction
            max_position:    Max position as fraction of capital
            reward_type:     Reward shaping method
        """
        self.features = features
        self.prices = prices
        self.initial_capital = initial_capital
        self.commission = commission_pct
        self.max_position = max_position
        self.reward_type = reward_type

        self.n_features = features.shape[1]
        self.n_steps = len(prices)

        # State
        self.current_step = 0
        self.capital = initial_capital
        self.position = 0.0  # +1 = long, -1 = short, 0 = flat
        self.entry_price = 0.0
        self.total_pnl = 0.0
        self.trade_count = 0
        self.returns_history: List[float] = []

        # Observation: features + [position, unrealized_pnl, capital_pct, step_pct]
        self.observation_size = self.n_features + 4

    def reset(self) -> np.ndarray:
        """Reset environment to initial state."""
        self.current_step = 0
        self.capital = self.initial_capital
        self.position = 0.0
        self.entry_price = 0.0
        self.total_pnl = 0.0
        self.trade_count = 0
        self.returns_history = []
        return self._get_observation()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Execute one step.

        Returns:
            observation, reward, done, info
        """
        price = self.prices[self.current_step]
        prev_capital = self.capital

        # Execute action
        trade_pnl = 0.0

        if action == self.BUY and self.position <= 0:
            # Close short if exists
            if self.position < 0:
                trade_pnl = (self.entry_price - price) * abs(self.position) * self.capital
                self.capital += trade_pnl - abs(trade_pnl * self.commission)
            # Open long
            self.position = self.max_position
            self.entry_price = price
            self.capital -= self.capital * self.commission
            self.trade_count += 1

        elif action == self.SELL and self.position >= 0:
            # Close long if exists
            if self.position > 0:
                trade_pnl = (price - self.entry_price) / self.entry_price * self.position * prev_capital
                self.capital += trade_pnl - abs(trade_pnl * self.commission)
            # Open short
            self.position = -self.max_position
            self.entry_price = price
            self.capital -= self.capital * self.commission
            self.trade_count += 1

        elif action == self.CLOSE and self.position != 0:
            if self.position > 0:
                trade_pnl = (price - self.entry_price) / self.entry_price * self.position * prev_capital
            else:
                trade_pnl = (self.entry_price - price) / self.entry_price * abs(self.position) * prev_capital
            self.capital += trade_pnl - abs(trade_pnl * self.commission)
            self.position = 0.0
            self.entry_price = 0.0
            self.trade_count += 1

        # Track
        step_return = (self.capital - prev_capital) / prev_capital
        self.returns_history.append(step_return)
        self.total_pnl = self.capital - self.initial_capital

        # Reward
        reward = self._compute_reward(step_return, trade_pnl)

        # Advance
        self.current_step += 1
        done = self.current_step >= self.n_steps - 1

        # Force close at end
        if done and self.position != 0:
            if self.position > 0:
                final_pnl = (price - self.entry_price) / self.entry_price * self.position * self.capital
            else:
                final_pnl = (self.entry_price - price) / self.entry_price * abs(self.position) * self.capital
            self.capital += final_pnl
            self.position = 0

        info = {
            "capital": round(self.capital, 2),
            "position": self.position,
            "total_pnl": round(self.total_pnl, 2),
            "trade_count": self.trade_count,
            "step": self.current_step,
        }

        obs = self._get_observation() if not done else np.zeros(self.observation_size)
        return obs, reward, done, info

    def _get_observation(self) -> np.ndarray:
        """Build observation vector."""
        if self.current_step >= len(self.features):
            return np.zeros(self.observation_size)

        features = self.features[self.current_step]

        # Augment with position info
        unrealized = 0.0
        if self.position != 0 and self.entry_price > 0:
            price = self.prices[self.current_step]
            if self.position > 0:
                unrealized = (price - self.entry_price) / self.entry_price
            else:
                unrealized = (self.entry_price - price) / self.entry_price

        augmented = np.array([
            self.position,
            unrealized,
            self.capital / self.initial_capital - 1.0,
            self.current_step / self.n_steps,
        ])

        return np.concatenate([features, augmented])

    def _compute_reward(self, step_return: float, trade_pnl: float) -> float:
        """Compute shaped reward."""
        if self.reward_type == "pnl":
            return step_return * 100  # Scale up

        elif self.reward_type == "sharpe":
            # Rolling Sharpe-like reward
            if len(self.returns_history) < 10:
                return step_return * 100
            recent = np.array(self.returns_history[-20:])
            mean_r = recent.mean()
            std_r = recent.std()
            sharpe = mean_r / (std_r + 1e-8)
            return float(sharpe)

        elif self.reward_type == "sortino":
            if len(self.returns_history) < 10:
                return step_return * 100
            recent = np.array(self.returns_history[-20:])
            downside = recent[recent < 0]
            down_std = downside.std() if len(downside) > 1 else 1e-8
            return float(recent.mean() / (down_std + 1e-8))

        return step_return * 100


# ══════════════════════════════════════════════════════════════════
#  DQN AGENT
# ══════════════════════════════════════════════════════════════════

class ReplayBuffer:
    """Experience replay buffer."""

    def __init__(self, capacity: int = 50000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int) -> List:
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    """
    Deep Q-Network trading agent.

    Architecture: State → FC layers → Q-values per action
    Training:     Experience replay + target network + epsilon-greedy
    """

    def __init__(
        self,
        state_size: int,
        action_size: int = 4,
        hidden_size: int = 128,
        lr: float = 0.001,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        batch_size: int = 64,
        target_update: int = 10,
        buffer_size: int = 50000,
    ):
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update
        self.train_step = 0

        self.memory = ReplayBuffer(buffer_size)

        # Networks (lazy init — requires torch)
        self._q_network = None
        self._target_network = None
        self._optimizer = None
        self._hidden_size = hidden_size
        self._lr = lr

    def _init_networks(self):
        """Initialize PyTorch networks on first use."""
        if self._q_network is not None:
            return

        import torch
        import torch.nn as nn

        class QNetwork(nn.Module):
            def __init__(self, state_size, action_size, hidden):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(state_size, hidden),
                    nn.ReLU(),
                    nn.Linear(hidden, hidden),
                    nn.ReLU(),
                    nn.Linear(hidden, hidden // 2),
                    nn.ReLU(),
                    nn.Linear(hidden // 2, action_size),
                )

            def forward(self, x):
                return self.net(x)

        self._q_network = QNetwork(self.state_size, self.action_size, self._hidden_size)
        self._target_network = QNetwork(self.state_size, self.action_size, self._hidden_size)
        self._target_network.load_state_dict(self._q_network.state_dict())
        self._optimizer = torch.optim.Adam(self._q_network.parameters(), lr=self._lr)

    def select_action(self, state: np.ndarray) -> int:
        """Epsilon-greedy action selection."""
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size - 1)

        self._init_networks()
        import torch
        with torch.no_grad():
            q_values = self._q_network(torch.FloatTensor(state).unsqueeze(0))
            return int(q_values.argmax().item())

    def store(self, state, action, reward, next_state, done):
        """Store transition in replay buffer."""
        self.memory.push(state, action, reward, next_state, done)

    def learn(self) -> Optional[float]:
        """One training step from replay buffer."""
        if len(self.memory) < self.batch_size:
            return None

        self._init_networks()
        import torch
        import torch.nn.functional as F

        batch = self.memory.sample(self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states = torch.FloatTensor(np.array(states))
        actions = torch.LongTensor(actions).unsqueeze(1)
        rewards = torch.FloatTensor(rewards).unsqueeze(1)
        next_states = torch.FloatTensor(np.array(next_states))
        dones = torch.FloatTensor(dones).unsqueeze(1)

        # Current Q values
        current_q = self._q_network(states).gather(1, actions)

        # Target Q values
        with torch.no_grad():
            next_q = self._target_network(next_states).max(1)[0].unsqueeze(1)
            target_q = rewards + self.gamma * next_q * (1 - dones)

        # Loss
        loss = F.mse_loss(current_q, target_q)

        self._optimizer.zero_grad()
        loss.backward()
        self._optimizer.step()

        # Update target network
        self.train_step += 1
        if self.train_step % self.target_update_freq == 0:
            self._target_network.load_state_dict(self._q_network.state_dict())

        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        return float(loss.item())


# ══════════════════════════════════════════════════════════════════
#  TRAINING LOOP
# ══════════════════════════════════════════════════════════════════

class RLTrainer:
    """
    Train DQN agent on historical data.
    """

    def __init__(self, env: TradingEnvironment, agent: DQNAgent):
        self.env = env
        self.agent = agent
        self.episode_rewards: List[float] = []
        self.episode_pnls: List[float] = []

    def train(self, n_episodes: int = 100, verbose: bool = True) -> Dict[str, Any]:
        """
        Run training loop.

        Returns:
            Training statistics
        """
        for episode in range(n_episodes):
            state = self.env.reset()
            total_reward = 0.0
            done = False

            while not done:
                action = self.agent.select_action(state)
                next_state, reward, done, info = self.env.step(action)

                self.agent.store(state, action, reward, next_state, float(done))
                loss = self.agent.learn()

                state = next_state
                total_reward += reward

            self.episode_rewards.append(total_reward)
            self.episode_pnls.append(info["total_pnl"])

            if verbose and (episode + 1) % 10 == 0:
                avg_reward = np.mean(self.episode_rewards[-10:])
                avg_pnl = np.mean(self.episode_pnls[-10:])
                logger.info(
                    "Episode %d/%d | Reward: %.2f | PnL: $%.0f | ε: %.3f | Trades: %d",
                    episode + 1, n_episodes, avg_reward, avg_pnl,
                    self.agent.epsilon, info["trade_count"],
                )

        return {
            "episodes": n_episodes,
            "final_epsilon": round(self.agent.epsilon, 4),
            "avg_reward_last10": round(float(np.mean(self.episode_rewards[-10:])), 4),
            "avg_pnl_last10": round(float(np.mean(self.episode_pnls[-10:])), 2),
            "best_pnl": round(float(max(self.episode_pnls)), 2),
            "worst_pnl": round(float(min(self.episode_pnls)), 2),
            "total_trades_last": info["trade_count"],
        }

    def evaluate(self, n_episodes: int = 10) -> Dict[str, Any]:
        """Evaluate agent with no exploration (epsilon=0)."""
        old_eps = self.agent.epsilon
        self.agent.epsilon = 0.0  # Pure exploitation

        pnls = []
        for _ in range(n_episodes):
            state = self.env.reset()
            done = False
            while not done:
                action = self.agent.select_action(state)
                state, _, done, info = self.env.step(action)
            pnls.append(info["total_pnl"])

        self.agent.epsilon = old_eps

        return {
            "eval_episodes": n_episodes,
            "mean_pnl": round(float(np.mean(pnls)), 2),
            "std_pnl": round(float(np.std(pnls)), 2),
            "win_rate": round(float((np.array(pnls) > 0).mean()), 3),
            "max_pnl": round(float(max(pnls)), 2),
            "min_pnl": round(float(min(pnls)), 2),
        }
