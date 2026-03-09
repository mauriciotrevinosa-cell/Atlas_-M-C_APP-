"""
DQNAgent — Pure-numpy Deep Q-Network.

Architecture (mirrors speed-racer-rl DQN.h adapted to Python):
  FC(state_dim, 128) → ReLU → FC(128, 64) → ReLU → FC(64, action_dim)

Training:
  - Experience replay (deque, capacity 10_000)
  - Double DQN target (policy selects action, target evaluates value)
  - Huber loss gradient
  - Adam optimizer (implemented in numpy)
  - Hard target-network copy every `target_update_freq` episodes
  - Epsilon-greedy exploration with exponential decay

No PyTorch / TensorFlow required.
"""

from __future__ import annotations

import json
import random
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np


# ── Replay Buffer ──────────────────────────────────────────────────────────────

class ReplayBuffer:
    """FIFO experience replay buffer (deque-backed)."""

    def __init__(self, capacity: int = 10_000):
        self._buf: deque = deque(maxlen=capacity)

    def push(
        self,
        state:      np.ndarray,
        action:     int,
        reward:     float,
        next_state: np.ndarray,
        done:       bool,
    ) -> None:
        self._buf.append((
            np.asarray(state,      dtype=np.float32),
            int(action),
            float(reward),
            np.asarray(next_state, dtype=np.float32),
            float(done),
        ))

    def sample(self, batch_size: int) -> Tuple[np.ndarray, ...]:
        batch           = random.sample(self._buf, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.stack(states),
            np.array(actions,      dtype=np.int32),
            np.array(rewards,      dtype=np.float32),
            np.stack(next_states),
            np.array(dones,        dtype=np.float32),
        )

    def __len__(self) -> int:
        return len(self._buf)

    @property
    def capacity(self) -> int:
        return self._buf.maxlen  # type: ignore[return-value]


# ── NumpyNet ───────────────────────────────────────────────────────────────────

class NumpyNet:
    """
    3-layer MLP (pure numpy).
    Forward pass  : matmul + ReLU + matmul + ReLU + matmul
    Backward pass : manual gradient + Adam update
    """

    def __init__(
        self,
        in_dim:  int,
        h1_dim:  int,
        h2_dim:  int,
        out_dim: int,
        lr:      float = 1e-3,
    ):
        # Xavier / He initialization
        self.W1 = np.random.randn(in_dim,  h1_dim)  * np.sqrt(2.0 / in_dim)
        self.b1 = np.zeros(h1_dim)
        self.W2 = np.random.randn(h1_dim,  h2_dim)  * np.sqrt(2.0 / h1_dim)
        self.b2 = np.zeros(h2_dim)
        self.W3 = np.random.randn(h2_dim,  out_dim) * np.sqrt(2.0 / h2_dim)
        self.b3 = np.zeros(out_dim)

        self.lr = lr

        # Adam state (β1=0.9, β2=0.999)
        self._t  = 0
        self._b1 = 0.9
        self._b2 = 0.999
        self._ep = 1e-8

        def _zeros_like(w): return np.zeros_like(w)
        self._m = {k: _zeros_like(v) for k, v in self._params.items()}
        self._v = {k: _zeros_like(v) for k, v in self._params.items()}

    # ── Param access ──────────────────────────────────────────────────────────

    @property
    def _params(self) -> Dict[str, np.ndarray]:
        return {
            'W1': self.W1, 'b1': self.b1,
            'W2': self.W2, 'b2': self.b2,
            'W3': self.W3, 'b3': self.b3,
        }

    # ── Forward ───────────────────────────────────────────────────────────────

    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Forward pass.

        Parameters
        ----------
        x : ndarray, shape (N, in_dim) or (in_dim,)

        Returns
        -------
        out   : ndarray, shape (N, out_dim)
        cache : dict    (stored for backward)
        """
        squeeze = x.ndim == 1
        if squeeze:
            x = x.reshape(1, -1)

        a1  = x  @ self.W1 + self.b1
        h1  = np.maximum(0.0, a1)
        a2  = h1 @ self.W2 + self.b2
        h2  = np.maximum(0.0, a2)
        out = h2 @ self.W3 + self.b3

        cache = {'x': x, 'a1': a1, 'h1': h1, 'a2': a2, 'h2': h2}

        if squeeze:
            out = out.squeeze(0)

        return out, cache

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Forward-only (no cache needed)."""
        out, _ = self.forward(x)
        return out

    # ── Backward + Adam ───────────────────────────────────────────────────────

    def backward(self, grad_out: np.ndarray, cache: Dict) -> None:
        """
        Backprop + Adam update.

        Parameters
        ----------
        grad_out : ndarray (N, out_dim) — dL/d(out)
        cache    : dict from forward()
        """
        x, a1, h1, a2, h2 = (
            cache['x'], cache['a1'], cache['h1'], cache['a2'], cache['h2']
        )
        N = x.shape[0]

        # Layer 3 grads
        dW3 = h2.T @ grad_out / N
        db3 = grad_out.mean(axis=0)

        # Layer 2 grads (through ReLU)
        dh2 = grad_out @ self.W3.T
        da2 = dh2 * (a2 > 0)
        dW2 = h1.T @ da2 / N
        db2 = da2.mean(axis=0)

        # Layer 1 grads (through ReLU)
        dh1 = da2 @ self.W2.T
        da1 = dh1 * (a1 > 0)
        dW1 = x.T @ da1 / N
        db1 = da1.mean(axis=0)

        grads = {'W1': dW1, 'b1': db1, 'W2': dW2, 'b2': db2, 'W3': dW3, 'b3': db3}

        # Adam
        self._t += 1
        for k, g in grads.items():
            self._m[k] = self._b1 * self._m[k] + (1.0 - self._b1) * g
            self._v[k] = self._b2 * self._v[k] + (1.0 - self._b2) * g ** 2
            m_hat = self._m[k] / (1.0 - self._b1 ** self._t)
            v_hat = self._v[k] / (1.0 - self._b2 ** self._t)
            self._params[k] -= self.lr * m_hat / (np.sqrt(v_hat) + self._ep)

    # ── Weight copy ───────────────────────────────────────────────────────────

    def copy_from(self, other: 'NumpyNet') -> None:
        """Hard-copy weights from `other` (target network sync)."""
        for k in self._params:
            self._params[k][:] = other._params[k]

    # ── Serialization ─────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        return {k: v.tolist() for k, v in self._params.items()}

    def from_dict(self, d: Dict) -> None:
        for k, v in d.items():
            if k in self._params:
                self._params[k][:] = np.array(v, dtype=np.float32)


# ── DQNAgent ───────────────────────────────────────────────────────────────────

class DQNAgent:
    """
    Double DQN Agent (pure numpy).

    Key design choices (inspired by speed-racer-rl DQN.h + Qlib RL policy):
      · Policy net    — action selection (ε-greedy)
      · Target net    — stable Q-value targets (hard copy every N episodes)
      · Double DQN    — policy net selects action, target net evaluates
      · Huber loss    — gradient clipping via Pseudo-Huber δ=1
      · Adam optimizer — per-parameter adaptive LR
    """

    def __init__(
        self,
        state_dim:          int   = 20,
        action_dim:         int   = 5,
        lr:                 float = 1e-3,
        gamma:              float = 0.99,
        epsilon_start:      float = 1.0,
        epsilon_end:        float = 0.05,
        epsilon_decay:      float = 0.995,
        buffer_capacity:    int   = 10_000,
        batch_size:         int   = 64,
        target_update_freq: int   = 10,
    ):
        self.state_dim          = state_dim
        self.action_dim         = action_dim
        self.gamma              = gamma
        self.epsilon            = epsilon_start
        self.epsilon_end        = epsilon_end
        self.epsilon_decay      = epsilon_decay
        self.batch_size         = batch_size
        self.target_update_freq = target_update_freq

        self.policy_net = NumpyNet(state_dim, 128, 64, action_dim, lr=lr)
        self.target_net = NumpyNet(state_dim, 128, 64, action_dim, lr=lr)
        self.target_net.copy_from(self.policy_net)

        self.buffer = ReplayBuffer(buffer_capacity)

        self.episode:      int        = 0
        self.train_steps:  int        = 0
        self._loss_hist:   List[float] = []
        self._q_val_hist:  List[float] = []
        self._action_counts: List[int] = [0] * action_dim

    # ── Action selection ──────────────────────────────────────────────────────

    def act(self, state: np.ndarray, explore: bool = True) -> int:
        """ε-greedy action selection."""
        if explore and np.random.random() < self.epsilon:
            a = int(np.random.randint(self.action_dim))
        else:
            q = self.policy_net.predict(state)
            a = int(np.argmax(q))
        self._action_counts[a] += 1
        return a

    def push(
        self,
        state:      np.ndarray,
        action:     int,
        reward:     float,
        next_state: np.ndarray,
        done:       bool,
    ) -> None:
        self.buffer.push(state, action, reward, next_state, done)

    # ── Training step ─────────────────────────────────────────────────────────

    def train_step(self) -> Optional[float]:
        """Sample one minibatch and update the policy network."""
        if len(self.buffer) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = self.buffer.sample(self.batch_size)

        # Current Q-values (need cache for backward)
        q_out, cache = self.policy_net.forward(states)
        q_vals       = q_out.copy()

        # Double DQN: policy selects action, target evaluates
        q_next_policy = self.policy_net.predict(next_states)
        best_next_a   = np.argmax(q_next_policy, axis=1)
        q_next_target = self.target_net.predict(next_states)
        q_next        = q_next_target[np.arange(self.batch_size), best_next_a]

        # Bellman targets
        targets = rewards + self.gamma * q_next * (1.0 - dones)

        # Huber-loss gradient (δ=1)
        q_target_mat = q_vals.copy()
        for i, a in enumerate(actions):
            diff = targets[i] - q_vals[i, a]
            # Pseudo-Huber: |diff|≤1 → -diff, else -sign(diff)
            q_target_mat[i, a] = q_vals[i, a] + (diff if abs(diff) <= 1.0 else np.sign(diff))

        grad_out = q_vals - q_target_mat  # dL/dQ

        self.policy_net.backward(grad_out, cache)

        # Metrics
        batch_loss = float(np.mean(
            (q_vals[np.arange(self.batch_size), actions] - targets) ** 2
        ))
        self._loss_hist.append(batch_loss)
        self._q_val_hist.append(float(q_vals.mean()))
        self.train_steps += 1

        return batch_loss

    # ── End-of-episode maintenance ────────────────────────────────────────────

    def end_episode(self) -> None:
        """Decay ε; optionally hard-copy target network."""
        self.episode += 1
        self.epsilon  = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

        if self.episode % self.target_update_freq == 0:
            self.target_net.copy_from(self.policy_net)

    # ── Serialization ─────────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Serialize agent state to JSON."""
        payload = {
            'episode':         self.episode,
            'epsilon':         self.epsilon,
            'train_steps':     self.train_steps,
            'policy_weights':  self.policy_net.to_dict(),
            'target_weights':  self.target_net.to_dict(),
            'loss_history':    self._loss_hist[-200:],
            'action_counts':   self._action_counts,
        }
        with open(path, 'w') as f:
            json.dump(payload, f)

    def load(self, path: str) -> None:
        """Load agent state from JSON."""
        with open(path, 'r') as f:
            d = json.load(f)
        self.episode         = d['episode']
        self.epsilon         = d['epsilon']
        self.train_steps     = d.get('train_steps', 0)
        self._loss_hist      = d.get('loss_history', [])
        self._action_counts  = d.get('action_counts', [0] * self.action_dim)
        self.policy_net.from_dict(d['policy_weights'])
        self.target_net.from_dict(d['target_weights'])

    # ── Metrics ───────────────────────────────────────────────────────────────

    @property
    def metrics(self) -> Dict:
        n = 20
        avg_loss  = float(np.mean(self._loss_hist[-n:]))  if self._loss_hist  else 0.0
        avg_qval  = float(np.mean(self._q_val_hist[-n:])) if self._q_val_hist else 0.0
        total_acts = max(sum(self._action_counts), 1)
        action_dist = {
            DQNAgent._ACTION_NAMES[i]: round(c / total_acts * 100, 1)
            for i, c in enumerate(self._action_counts)
        }
        return {
            'episode':     self.episode,
            'epsilon':     round(self.epsilon, 4),
            'train_steps': self.train_steps,
            'avg_loss':    round(avg_loss,  6),
            'avg_q':       round(avg_qval,  4),
            'buffer_size': len(self.buffer),
            'action_dist': action_dist,
        }

    _ACTION_NAMES = ['HOLD', 'BUY_SM', 'BUY_LG', 'SELL_SM', 'SELL_LG']

    def __repr__(self) -> str:
        return (
            f'DQNAgent(ep={self.episode}, ε={self.epsilon:.3f}, '
            f'buf={len(self.buffer)}, steps={self.train_steps})'
        )
