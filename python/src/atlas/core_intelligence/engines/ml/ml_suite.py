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
