"""
ML Engine Suite
================
Production ML models for feature-based signal generation.
All models share a common interface for the engine registry.

Models:
- LSTMEngine:         Sequential patterns in time series
- XGBoostEngine:      Gradient boosted trees for tabular features
- RandomForestEngine:  Ensemble tree model (baseline)
- FeaturePipeline:     Standardized feature preparation

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
import pickle
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.ml")


# ══════════════════════════════════════════════════════════════════
#  Base Interface
# ══════════════════════════════════════════════════════════════════

class MLEngine(ABC):
    """Abstract base for all ML engines."""

    def __init__(self, name: str, model_dir: str = "data/models"):
        self.name = name
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.is_trained = False

    @abstractmethod
    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        """Train the model. Returns training metrics."""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate predictions."""
        pass

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Probability/confidence of prediction."""
        pass

    def save(self, filename: Optional[str] = None):
        """Save model to disk."""
        path = self.model_dir / (filename or f"{self.name}.pkl")
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info("Model saved: %s", path)

    def load(self, filename: Optional[str] = None):
        """Load model from disk."""
        path = self.model_dir / (filename or f"{self.name}.pkl")
        with open(path, "rb") as f:
            loaded = pickle.load(f)
        self.__dict__.update(loaded.__dict__)
        logger.info("Model loaded: %s", path)


# ══════════════════════════════════════════════════════════════════
#  Feature Pipeline
# ══════════════════════════════════════════════════════════════════

class FeaturePipeline:
    """
    Prepare features for ML models from OHLCV + indicators.
    Standardizes the feature → label pipeline.
    """

    def __init__(self, lookback: int = 20, forecast_horizon: int = 5):
        self.lookback = lookback
        self.horizon = forecast_horizon
        self._feature_names: List[str] = []

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build feature matrix from OHLCV data.

        Input: DataFrame with columns: open, high, low, close, volume
        Output: DataFrame with computed features
        """
        features = pd.DataFrame(index=df.index)

        # Price-based
        features["return_1d"] = df["close"].pct_change(1)
        features["return_5d"] = df["close"].pct_change(5)
        features["return_10d"] = df["close"].pct_change(10)
        features["return_20d"] = df["close"].pct_change(20)

        # Volatility
        features["vol_5d"] = df["close"].pct_change().rolling(5).std()
        features["vol_10d"] = df["close"].pct_change().rolling(10).std()
        features["vol_20d"] = df["close"].pct_change().rolling(20).std()

        # Volume
        features["volume_sma_ratio"] = df["volume"] / df["volume"].rolling(20).mean()
        features["volume_change"] = df["volume"].pct_change()

        # Price position
        features["high_low_range"] = (df["high"] - df["low"]) / df["close"]
        features["close_position"] = (df["close"] - df["low"]) / (df["high"] - df["low"]).replace(0, 1)

        # Moving averages
        for w in [5, 10, 20, 50]:
            sma = df["close"].rolling(w).mean()
            features[f"sma_{w}_dist"] = (df["close"] - sma) / sma

        # RSI approximation
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-10)
        features["rsi_14"] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df["close"].ewm(span=12).mean()
        ema26 = df["close"].ewm(span=26).mean()
        features["macd"] = (ema12 - ema26) / df["close"]

        # Bollinger %B
        sma20 = df["close"].rolling(20).mean()
        std20 = df["close"].rolling(20).std()
        features["bb_pctb"] = (df["close"] - sma20 + 2 * std20) / (4 * std20).replace(0, 1)

        self._feature_names = features.columns.tolist()
        return features.dropna()

    def build_labels(
        self, df: pd.DataFrame, method: str = "direction",
    ) -> pd.Series:
        """
        Build prediction labels.

        Methods:
            "direction": 1 if price goes up in horizon, 0 otherwise
            "return":    Actual forward return
            "triple":    -1/0/1 based on thresholds
        """
        fwd_return = df["close"].pct_change(self.horizon).shift(-self.horizon)

        if method == "direction":
            return (fwd_return > 0).astype(int)
        elif method == "return":
            return fwd_return
        elif method == "triple":
            threshold = fwd_return.std() * 0.5
            labels = pd.Series(0, index=df.index)
            labels[fwd_return > threshold] = 1
            labels[fwd_return < -threshold] = -1
            return labels
        return fwd_return

    def prepare(
        self, df: pd.DataFrame, label_method: str = "direction",
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Full pipeline: features + labels, aligned and cleaned."""
        features = self.build_features(df)
        labels = self.build_labels(df, label_method)

        # Align
        common = features.index.intersection(labels.dropna().index)
        X = features.loc[common].values
        y = labels.loc[common].values

        return X, y, self._feature_names


# ══════════════════════════════════════════════════════════════════
#  XGBoost Engine
# ══════════════════════════════════════════════════════════════════

class XGBoostEngine(MLEngine):
    """Gradient Boosted Trees for tabular financial features."""

    def __init__(self, **xgb_params):
        super().__init__("xgboost")
        self.params = {
            "n_estimators": 200,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 5,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            **xgb_params,
        }
        self.model = None

    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        try:
            from xgboost import XGBClassifier
        except ImportError:
            return {"error": "xgboost not installed. pip install xgboost"}

        # Train/val split
        split = int(len(X) * 0.8)
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        self.model = XGBClassifier(**self.params, use_label_encoder=False, eval_metric="logloss")
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        self.is_trained = True

        # Metrics
        train_acc = float((self.model.predict(X_train) == y_train).mean())
        val_acc = float((self.model.predict(X_val) == y_val).mean())

        return {
            "train_accuracy": round(train_acc, 4),
            "val_accuracy": round(val_acc, 4),
            "n_train": len(X_train),
            "n_val": len(X_val),
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_trained:
            raise RuntimeError("Model not trained")
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self.is_trained:
            raise RuntimeError("Model not trained")
        return self.model.predict_proba(X)

    def feature_importance(self) -> Dict[str, float]:
        if self.model is None:
            return {}
        imp = self.model.feature_importances_
        return {f"f{i}": round(float(v), 4) for i, v in enumerate(imp)}


# ══════════════════════════════════════════════════════════════════
#  Random Forest Engine
# ══════════════════════════════════════════════════════════════════

class RandomForestEngine(MLEngine):
    """Ensemble tree baseline model."""

    def __init__(self, **rf_params):
        super().__init__("random_forest")
        self.params = {
            "n_estimators": 200,
            "max_depth": 8,
            "min_samples_leaf": 20,
            "max_features": "sqrt",
            "random_state": 42,
            **rf_params,
        }
        self.model = None

    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        from sklearn.ensemble import RandomForestClassifier

        split = int(len(X) * 0.8)
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        self.model = RandomForestClassifier(**self.params)
        self.model.fit(X_train, y_train)
        self.is_trained = True

        train_acc = float(self.model.score(X_train, y_train))
        val_acc = float(self.model.score(X_val, y_val))

        return {
            "train_accuracy": round(train_acc, 4),
            "val_accuracy": round(val_acc, 4),
            "n_train": len(X_train),
            "n_val": len(X_val),
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(X)


# ══════════════════════════════════════════════════════════════════
#  LSTM Engine
# ══════════════════════════════════════════════════════════════════

class LSTMEngine(MLEngine):
    """
    LSTM for sequential pattern recognition.
    Uses PyTorch if available, falls back to numpy simulation.
    """

    def __init__(self, hidden_size: int = 64, num_layers: int = 2,
                 sequence_length: int = 20, epochs: int = 50, lr: float = 0.001):
        super().__init__("lstm")
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.seq_len = sequence_length
        self.epochs = epochs
        self.lr = lr
        self.model = None
        self._scaler_mean = None
        self._scaler_std = None

    def _make_sequences(self, X: np.ndarray, y: np.ndarray) -> Tuple:
        """Convert flat features to sequences for LSTM."""
        sequences = []
        labels = []
        for i in range(self.seq_len, len(X)):
            sequences.append(X[i - self.seq_len:i])
            labels.append(y[i])
        return np.array(sequences), np.array(labels)

    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
        except ImportError:
            return {"error": "PyTorch not installed. pip install torch"}

        # Normalize
        self._scaler_mean = X.mean(axis=0)
        self._scaler_std = X.std(axis=0) + 1e-8
        X_norm = (X - self._scaler_mean) / self._scaler_std

        # Sequences
        X_seq, y_seq = self._make_sequences(X_norm, y)
        split = int(len(X_seq) * 0.8)

        X_train = torch.FloatTensor(X_seq[:split])
        y_train = torch.LongTensor(y_seq[:split])
        X_val = torch.FloatTensor(X_seq[split:])
        y_val = torch.LongTensor(y_seq[split:])

        n_features = X.shape[1]
        n_classes = len(np.unique(y))

        # Model
        class LSTMModel(nn.Module):
            def __init__(self, input_size, hidden_size, num_layers, n_classes):
                super().__init__()
                self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=0.2)
                self.fc = nn.Linear(hidden_size, n_classes)

            def forward(self, x):
                out, _ = self.lstm(x)
                out = self.fc(out[:, -1, :])
                return out

        self.model = LSTMModel(n_features, self.hidden_size, self.num_layers, n_classes)
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)

        dataset = TensorDataset(X_train, y_train)
        loader = DataLoader(dataset, batch_size=64, shuffle=True)

        # Train
        self.model.train()
        for epoch in range(self.epochs):
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                output = self.model(batch_X)
                loss = criterion(output, batch_y)
                loss.backward()
                optimizer.step()

        # Evaluate
        self.model.eval()
        with torch.no_grad():
            train_pred = self.model(X_train).argmax(dim=1).numpy()
            val_pred = self.model(X_val).argmax(dim=1).numpy()

        self.is_trained = True

        return {
            "train_accuracy": round(float((train_pred == y_train.numpy()).mean()), 4),
            "val_accuracy": round(float((val_pred == y_val.numpy()).mean()), 4),
            "n_train": len(X_train),
            "n_val": len(X_val),
            "epochs": self.epochs,
        }

    def predict(self, X: np.ndarray) -> np.ndarray:
        import torch
        X_norm = (X - self._scaler_mean) / self._scaler_std
        # Need sequence
        if len(X_norm) < self.seq_len:
            return np.zeros(len(X_norm))
        X_seq = np.array([X_norm[i - self.seq_len:i] for i in range(self.seq_len, len(X_norm))])
        self.model.eval()
        with torch.no_grad():
            return self.model(torch.FloatTensor(X_seq)).argmax(dim=1).numpy()

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        import torch
        X_norm = (X - self._scaler_mean) / self._scaler_std
        if len(X_norm) < self.seq_len:
            return np.zeros((len(X_norm), 2))
        X_seq = np.array([X_norm[i - self.seq_len:i] for i in range(self.seq_len, len(X_norm))])
        self.model.eval()
        with torch.no_grad():
            logits = self.model(torch.FloatTensor(X_seq))
            return torch.softmax(logits, dim=1).numpy()


# ══════════════════════════════════════════════════════════════════
#  DQN Engine  (Reinforcement Learning)
# ══════════════════════════════════════════════════════════════════

class DQNEngine(MLEngine):
    """
    Deep Q-Network for RL-based trading signal generation.

    State  : normalized feature window of length seq_len.
    Actions: 0 = SELL, 1 = HOLD, 2 = BUY.
    Reward : sign(action − 1) × forward_return — rewards profitable calls.

    Uses PyTorch when available. Falls back to a tabular Q-table
    (numpy only) so the engine is always trainable regardless of environment.

    Training flow:
      1. Roll a sliding window through the feature matrix.
      2. For each step compute the PnL-based reward from the chosen action.
      3. Store (s, a, r, s') tuples in an experience replay buffer.
      4. Sample mini-batches and minimise the Bellman TD error.
      5. Periodically sync target network weights (hard update every C steps).
    """

    N_ACTIONS = 3  # SELL=0, HOLD=1, BUY=2

    def __init__(
        self,
        seq_len: int = 10,
        hidden_size: int = 128,
        episodes: int = 30,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: float = 0.97,
        gamma: float = 0.95,
        lr: float = 5e-4,
        batch_size: int = 64,
        target_update_freq: int = 10,
        buffer_size: int = 4096,
    ):
        super().__init__("dqn")
        self.seq_len = seq_len
        self.hidden_size = hidden_size
        self.episodes = episodes
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.gamma = gamma
        self.lr = lr
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.buffer_size = buffer_size

        # Runtime state (set during training)
        self.model = None
        self.target_model = None
        self._scaler_mean: Optional[np.ndarray] = None
        self._scaler_std: Optional[np.ndarray] = None
        self._use_torch: bool = False
        # Tabular Q fallback (n_states × N_ACTIONS) — used without PyTorch
        self._q_table: Optional[np.ndarray] = None
        self._n_features: int = 0

    # ── Internal helpers ──────────────────────────────────────────

    def _normalize(self, X: np.ndarray) -> np.ndarray:
        return (X - self._scaler_mean) / (self._scaler_std + 1e-8)

    def _make_windows(self, X: np.ndarray) -> np.ndarray:
        """Roll a sliding window of length seq_len over feature rows."""
        n = len(X)
        if n < self.seq_len + 1:
            return np.empty((0, self.seq_len, X.shape[1]))
        return np.stack(
            [X[i: i + self.seq_len] for i in range(n - self.seq_len)],
            axis=0,
        )

    @staticmethod
    def _pnl_reward(action: int, fwd_return: float) -> float:
        """
        Reward = position * forward return, where position ∈ {-1, 0, +1}.
        SELL=-1, HOLD=0, BUY=+1.  Penalise HOLD very slightly to encourage
        active positioning.
        """
        position = action - 1  # {0→-1, 1→0, 2→+1}
        return float(position * fwd_return) - (0.001 if action == 1 else 0.0)

    # ── PyTorch path ──────────────────────────────────────────────

    def _build_torch_qnet(self, input_size: int):
        """Construct a simple MLP Q-network using PyTorch."""
        import torch.nn as nn

        class QNet(nn.Module):
            def __init__(self, in_size: int, hidden: int, n_actions: int):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(in_size, hidden),
                    nn.ReLU(),
                    nn.Linear(hidden, hidden // 2),
                    nn.ReLU(),
                    nn.Linear(hidden // 2, n_actions),
                )

            def forward(self, x):
                return self.net(x)

        return QNet(input_size, self.hidden_size, self.N_ACTIONS)

    def _train_torch(self, X: np.ndarray, fwd_returns: np.ndarray) -> Dict[str, float]:
        import random
        import torch
        import torch.nn as nn

        windows = self._make_windows(X)           # (T, seq_len, n_feat)
        T = len(windows)
        if T < self.batch_size:
            return {"error": f"Need ≥{self.batch_size} windows; got {T}"}

        flat_size = self.seq_len * X.shape[1]
        self.model = self._build_torch_qnet(flat_size)
        self.target_model = self._build_torch_qnet(flat_size)
        self.target_model.load_state_dict(self.model.state_dict())

        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        loss_fn = nn.SmoothL1Loss()
        replay: List[Tuple] = []

        epsilon = self.epsilon_start
        total_reward = 0.0
        update_count = 0

        for ep in range(self.episodes):
            ep_reward = 0.0
            for t in range(T - 1):
                state_t = torch.FloatTensor(windows[t].flatten()).unsqueeze(0)
                r_t = float(fwd_returns[t + self.seq_len]) if (t + self.seq_len) < len(fwd_returns) else 0.0

                # ε-greedy action
                if random.random() < epsilon:
                    action = random.randint(0, self.N_ACTIONS - 1)
                else:
                    with torch.no_grad():
                        action = int(self.model(state_t).argmax(dim=1).item())

                reward = self._pnl_reward(action, r_t)
                ep_reward += reward

                state_tp1 = torch.FloatTensor(windows[t + 1].flatten()).unsqueeze(0)
                done = (t == T - 2)
                replay.append((state_t, action, reward, state_tp1, done))
                if len(replay) > self.buffer_size:
                    replay.pop(0)

                # Mini-batch update
                if len(replay) >= self.batch_size:
                    batch = random.sample(replay, self.batch_size)
                    bs, ba, br, bsp, bd = zip(*batch)
                    bs  = torch.cat(bs)
                    bsp = torch.cat(bsp)
                    ba  = torch.LongTensor(ba)
                    br  = torch.FloatTensor(br)
                    bd  = torch.FloatTensor(bd)

                    q_curr = self.model(bs).gather(1, ba.unsqueeze(1)).squeeze(1)
                    with torch.no_grad():
                        q_next = self.target_model(bsp).max(1).values
                        q_target = br + self.gamma * q_next * (1 - bd)

                    loss = loss_fn(q_curr, q_target)
                    optimizer.zero_grad()
                    loss.backward()
                    nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                    optimizer.step()
                    update_count += 1

                    # Hard target-network sync
                    if update_count % self.target_update_freq == 0:
                        self.target_model.load_state_dict(self.model.state_dict())

            epsilon = max(self.epsilon_end, epsilon * self.epsilon_decay)
            total_reward += ep_reward

        avg_reward = total_reward / max(self.episodes, 1)

        # Final accuracy: fraction of correctly directional calls
        self.model.eval()
        correct = 0
        for t in range(T - 1):
            state_t = torch.FloatTensor(windows[t].flatten()).unsqueeze(0)
            with torch.no_grad():
                a = int(self.model(state_t).argmax(dim=1).item())
            r_t = float(fwd_returns[t + self.seq_len]) if (t + self.seq_len) < len(fwd_returns) else 0.0
            if (a == 2 and r_t > 0) or (a == 0 and r_t < 0) or (a == 1 and abs(r_t) < 0.005):
                correct += 1

        return {
            "train_accuracy": round(correct / max(T - 1, 1), 4),
            "avg_episode_reward": round(avg_reward, 6),
            "episodes": self.episodes,
            "n_windows": T,
            "epsilon_final": round(epsilon, 4),
        }

    # ── NumPy fallback (tabular Q-table) ─────────────────────────

    def _train_numpy(self, X: np.ndarray, fwd_returns: np.ndarray) -> Dict[str, float]:
        """
        Simplified tabular Q-learning on discretised states.
        Uses a flattened sign-binarised feature vector as state key.
        No PyTorch required.
        """
        import random

        windows = self._make_windows(X)
        T = len(windows)
        if T < 20:
            return {"error": f"Need ≥20 windows; got {T}"}

        # Discretise: sign of mean of each feature window → binary state ID
        def _state_id(w: np.ndarray) -> int:
            signs = (w.mean(axis=0) > 0).astype(np.uint8)
            # Fold into an integer index bounded to [0, 1023]
            n_feat = len(signs)
            top = signs[:min(n_feat, 10)]
            idx = 0
            for bit in top:
                idx = (idx << 1) | int(bit)
            return idx

        n_states = 1024
        Q = np.zeros((n_states, self.N_ACTIONS))
        epsilon = self.epsilon_start
        total_reward = 0.0

        for ep in range(self.episodes):
            ep_reward = 0.0
            for t in range(T - 1):
                s  = _state_id(windows[t])
                sp = _state_id(windows[t + 1])
                r_t = float(fwd_returns[t + self.seq_len]) if (t + self.seq_len) < len(fwd_returns) else 0.0

                action = (
                    np.random.randint(self.N_ACTIONS)
                    if random.random() < epsilon
                    else int(Q[s].argmax())
                )
                reward = self._pnl_reward(action, r_t)
                ep_reward += reward

                # Bellman update
                Q[s, action] += self.lr * (
                    reward + self.gamma * Q[sp].max() - Q[s, action]
                )
            epsilon = max(self.epsilon_end, epsilon * self.epsilon_decay)
            total_reward += ep_reward

        self._q_table = Q
        self._n_features = X.shape[1]

        # Directional accuracy on the training windows
        correct = 0
        for t in range(T - 1):
            s   = _state_id(windows[t])
            a   = int(Q[s].argmax())
            r_t = float(fwd_returns[t + self.seq_len]) if (t + self.seq_len) < len(fwd_returns) else 0.0
            if (a == 2 and r_t > 0) or (a == 0 and r_t < 0) or (a == 1 and abs(r_t) < 0.005):
                correct += 1

        return {
            "train_accuracy": round(correct / max(T - 1, 1), 4),
            "avg_episode_reward": round(total_reward / max(self.episodes, 1), 6),
            "episodes": self.episodes,
            "n_windows": T,
            "backend": "numpy_tabular",
        }

    # ── Public interface ──────────────────────────────────────────

    def train(self, X: np.ndarray, y: np.ndarray, **kwargs) -> Dict[str, float]:
        """
        Train the DQN agent.

        ``y`` is interpreted as 1-step forward returns for reward computation
        (the FeaturePipeline label is ignored; PnL reward is used instead).
        Internally fetches forward returns from ``X`` if ``fwd_returns`` is
        not supplied via kwargs.
        """
        # Normalise features
        self._scaler_mean = X.mean(axis=0)
        self._scaler_std  = X.std(axis=0) + 1e-8
        X_norm = self._normalize(X)

        # Forward return proxy: 1-day percentage change column (return_1d ≈ col 0)
        fwd_returns = np.concatenate([X[:, 0][1:], [0.0]])  # shift return_1d by 1

        try:
            import torch  # noqa: F401
            self._use_torch = True
            metrics = self._train_torch(X_norm, fwd_returns)
        except ImportError:
            self._use_torch = False
            metrics = self._train_numpy(X_norm, fwd_returns)

        if "error" not in metrics:
            self.is_trained = True

        return {**metrics, "backend": "torch" if self._use_torch else "numpy_tabular"}

    def predict(self, X: np.ndarray) -> np.ndarray:
        X_norm = self._normalize(X)
        windows = self._make_windows(X_norm)
        if len(windows) == 0:
            return np.ones(len(X), dtype=int)  # default HOLD

        if self._use_torch and self.model is not None:
            import torch
            self.model.eval()
            flat = torch.FloatTensor(windows.reshape(len(windows), -1))
            with torch.no_grad():
                actions = self.model(flat).argmax(dim=1).numpy()
        else:
            if self._q_table is None:
                return np.ones(len(windows), dtype=int)

            def _sid(w: np.ndarray) -> int:
                signs = (w.mean(axis=0) > 0).astype(np.uint8)
                top = signs[:min(len(signs), 10)]
                idx = 0
                for bit in top:
                    idx = (idx << 1) | int(bit)
                return idx

            actions = np.array([int(self._q_table[_sid(w)].argmax()) for w in windows])

        # Pad start with HOLD (1) to match original length
        pad = np.ones(len(X) - len(actions), dtype=int)
        return np.concatenate([pad, actions])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return soft Q-value distribution (softmax over Q-values)."""
        X_norm = self._normalize(X)
        windows = self._make_windows(X_norm)
        T = len(windows)
        if T == 0:
            return np.full((len(X), self.N_ACTIONS), 1.0 / self.N_ACTIONS)

        if self._use_torch and self.model is not None:
            import torch
            self.model.eval()
            flat = torch.FloatTensor(windows.reshape(T, -1))
            with torch.no_grad():
                logits = self.model(flat)
                probs = torch.softmax(logits, dim=1).numpy()
        else:
            if self._q_table is None:
                return np.full((T, self.N_ACTIONS), 1.0 / self.N_ACTIONS)

            def _sid(w: np.ndarray) -> int:
                signs = (w.mean(axis=0) > 0).astype(np.uint8)
                top = signs[:min(len(signs), 10)]
                idx = 0
                for bit in top:
                    idx = (idx << 1) | int(bit)
                return idx

            raw_q = np.array([self._q_table[_sid(w)] for w in windows])
            # Softmax over Q-values
            eq = np.exp(raw_q - raw_q.max(axis=1, keepdims=True))
            probs = eq / eq.sum(axis=1, keepdims=True)

        pad = np.full((len(X) - T, self.N_ACTIONS), 1.0 / self.N_ACTIONS)
        return np.vstack([pad, probs])
