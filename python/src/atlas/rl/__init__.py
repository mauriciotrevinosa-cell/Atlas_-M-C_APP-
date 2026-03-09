"""
Atlas RL — Reinforcement Learning Trading Environment
======================================================
Inspired by:
  - speed-racer-rl DQN architecture (policy net + target net)
  - Qlib SAOE order execution RL (state, reward, simulator design)
  - Classic DQN paper (Mnih et al. 2013) + Double DQN + Huber loss

Modules:
  trading_env  — Gym-style single-asset trading environment (GBM synthetic prices)
  dqn_agent    — Pure-numpy DQNAgent (3-layer MLP + Adam, no PyTorch needed)
  rl_trainer   — Episode training loop, metrics, checkpointing
"""

from .trading_env import TradingEnvironment
from .dqn_agent import DQNAgent, NumpyNet, ReplayBuffer
from .rl_trainer import RLTrainer

__all__ = [
    'TradingEnvironment',
    'DQNAgent',
    'NumpyNet',
    'ReplayBuffer',
    'RLTrainer',
]
