# Qlib Patterns for Atlas — Data Layer, Backtest & ML Models

**Source:** Microsoft Qlib (MIT License) — `qlib-main/`
**License:** MIT — code can be copied/adapted directly with attribution.
**Created:** 2026-02-25
**Purpose:** Concrete implementation patterns from production quant framework to guide Atlas phases 1, 4, 7, 11.

---

## 1. Data Layer Architecture (Phase 1)

### 1.1 The Three-Layer Data Pipeline

Qlib separates data into **three distinct representations** (critical pattern):

```python
# qlib/data/dataset/handler.py — DataHandlerLP
class DataHandlerLP(DataHandler):
    # DK_R: raw data loaded directly from source
    # DK_I: processed for INFERENCE (shared + infer_processors)
    # DK_L: processed for LEARNING (shared + infer + learn_processors)
    DK_R: DATA_KEY_TYPE = "raw"
    DK_I: DATA_KEY_TYPE = "infer"
    DK_L: DATA_KEY_TYPE = "learn"
```

**Why this matters for Atlas:** Inference-time data must NOT include future leakage (e.g., normalization fitted on test data). Learning data can apply extra processors (e.g., drop samples that hit limit-up/down). Separation makes this explicit.

**Atlas adaptation:** `AtlasDataHandler` in `data_layer/data_handler.py`:

```python
class AtlasDataHandler:
    """
    Three-key data handler adapted from Qlib's DataHandlerLP.

    DK_R = raw OHLCV from provider
    DK_I = normalized, NaN-cleaned, ready for inference
    DK_L = DK_I + label columns, ready for model training
    """

    def __init__(
        self,
        instruments: list[str],
        start_time: str,
        end_time: str,
        data_loader,                          # AtlasDataLoader ABC
        infer_processors: list = [],          # applied to inference data
        learn_processors: list = [],          # additional for learning
        shared_processors: list = [],         # applied to both
    ):
        ...

    def fetch(
        self,
        selector: slice | str,               # time range
        col_set: str = "all",                # "feature", "label", "all"
        data_key: str = "infer",             # "raw" | "infer" | "learn"
    ) -> pd.DataFrame:
        ...
```

### 1.2 Data Processor Pipeline (Composable Transforms)

```python
# qlib/data/dataset/processor.py — Processor ABC
class Processor(Serializable):
    def fit(self, df: pd.DataFrame = None):
        """Learn parameters from training data (e.g., mean/std for normalization)."""
        ...

    def __call__(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply transform to data."""
        ...

    def is_for_infer(self) -> bool:
        """If True, applied during inference. If False, training only."""
        return True
```

**Available processors in Qlib (MIT — can copy):**
| Processor | What it does |
|-----------|-------------|
| `DropnaLabel` | Drop rows where label is NaN (training only) |
| `DropnaProcessor` | Drop rows with any NaN |
| `DropCol` | Remove specific columns |
| `FilterCol` | Keep only specified columns |
| `Fillna` | Fill NaN with value (default 0) |
| `MinMaxNorm` | Min-max normalization (fit on train) |
| `ZScoreNorm` | Z-score normalization (fit on train) |
| `RobustZScoreNorm` | Median-based Z-score (resistant to outliers) |
| `CSZScoreNorm` | Cross-sectional Z-score per date |
| `ProcessInf` | Replace ±inf with clip value |
| `TanhProcess` | Tanh-based denoising |

**Atlas adaptation:** Create `data_layer/processors.py` and copy these directly.

### 1.3 DatasetH — Time-Segmented Dataset

```python
# qlib/data/dataset/__init__.py — DatasetH
class DatasetH(Dataset):
    def __init__(
        self,
        handler: DataHandler,
        segments: dict[str, tuple[str, str]],  # train/valid/test splits
    ):
        # Example:
        # segments = {
        #     'train': ("2020-01-01", "2023-12-31"),
        #     'valid': ("2024-01-01", "2024-06-30"),
        #     'test':  ("2024-07-01", "2025-01-01"),
        # }
        ...

    def prepare(
        self,
        segments: list[str],           # ["train", "valid"]
        col_set: list[str],            # ["feature", "label"]
        data_key: str = "infer",
    ) -> list[pd.DataFrame]:
        """Returns list of DataFrames, one per segment."""
        ...
```

**Atlas adaptation:** `AtlasDataset` in `data_layer/dataset.py` — wraps `AtlasDataHandler` with configurable time splits.

### 1.4 Multi-Level Cache Strategy

Qlib uses two levels of cache:
1. **Feature-level cache** — per-instrument, per-field expressions (disk)
2. **Handler-level cache** — processed DataFrame after processors (disk)

**Atlas cache implementation pattern:**

```python
# data_layer/cache_store.py — expand this
class AtlasCacheStore:
    """
    Level 1: Memory cache (dict, LRU)     — hot data for current session
    Level 2: Disk cache (Parquet/HDF5)   — persisted processed DataFrames
    """

    def get(self, key: str, data_key: str = "infer") -> pd.DataFrame | None: ...
    def set(self, key: str, df: pd.DataFrame, data_key: str = "infer"): ...
    def invalidate(self, key: str): ...
    def clear_memory(self): ...
```

---

## 2. Model Interface (Phase 4)

### 2.1 Base Model ABC

```python
# qlib/model/base.py — BaseModel / Model / ModelFT (MIT — copy directly)
class BaseModel(Serializable):
    @abc.abstractmethod
    def predict(self, *args, **kwargs) -> object:
        """Make predictions."""
        ...

class Model(BaseModel):
    def fit(self, dataset: Dataset, reweighter=None):
        """
        Typical usage:
            df_train, df_valid = dataset.prepare(
                ["train", "valid"],
                col_set=["feature", "label"],
                data_key=DataHandlerLP.DK_L
            )
            x_train = df_train["feature"]
            y_train = df_train["label"]
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def predict(self, dataset: Dataset, segment: str = "test") -> pd.Series:
        """Returns predicted alpha scores per instrument per date."""
        raise NotImplementedError()

class ModelFT(Model):
    """Fine-tunable model (e.g., incremental online learning)."""
    @abc.abstractmethod
    def finetune(self, dataset: Dataset): ...
```

**Atlas adaptation:** All ML engines in `python/src/atlas/strategies/` should implement this interface. Current `BaseEngine` ABC should align with this.

### 2.2 Available ML Models to Adopt from Qlib (MIT)

Direct copy candidates from `qlib/contrib/model/`:

| File | Model | Notes |
|------|-------|-------|
| `pytorch_lstm.py` | LSTM | Standard LSTM for time-series signals |
| `pytorch_gru.py` | GRU | Faster than LSTM, often comparable quality |
| `pytorch_transformer.py` | Transformer | Self-attention over time windows |
| `xgboost.py` | XGBoost | Strong baseline, fast to train |
| `catboost_model.py` | CatBoost | Handles categoricals, robust |
| `gbdt.py` | LightGBM | Fastest tree model, best for features |
| `linear.py` | LinearModel | Ridge/Lasso baseline |
| `pytorch_alstm.py` | Attention-LSTM | LSTM + attention mechanism |

**Recommended order for Atlas Phase 4:**
1. `xgboost.py` + `gbdt.py` — fast iteration, no GPU needed
2. `pytorch_lstm.py` — time-series baseline
3. `pytorch_transformer.py` — state of the art

---

## 3. Strategy Interface (Phase 4/5)

### 3.1 BaseStrategy ABC

```python
# qlib/strategy/base.py — BaseStrategy (MIT — copy directly)
class BaseStrategy:
    @abstractmethod
    def generate_trade_decision(
        self,
        execute_result: list = None,
    ) -> BaseTradeDecision:
        """
        Called at each trading bar. Returns orders to execute.
        execute_result: results from previous bar's execution.
        """
        raise NotImplementedError()

    # Properties available inside strategy:
    @property
    def trade_calendar(self) -> TradeCalendarManager: ...

    @property
    def trade_position(self) -> BasePosition: ...

    @property
    def trade_exchange(self) -> Exchange: ...
```

### 3.2 Signal-Based Strategy

```python
# qlib/contrib/strategy/signal_strategy.py — TopkDropoutStrategy
class BaseSignalStrategy(BaseStrategy, ABC):
    """Strategy that consumes ML model predictions (alpha scores)."""

    def __init__(self, signal, risk_degree=0.95, ...):
        # signal: model predictions (pd.Series or DataFrame)
        ...

    def get_risk_degree(self, trade_step=None) -> float:
        """What fraction of capital to deploy. Default 0.95."""
        return self.risk_degree

class TopkDropoutStrategy(BaseSignalStrategy):
    """
    Canonical quant strategy:
    - Hold top-K stocks by predicted alpha score
    - Replace lowest performers with higher-scoring candidates
    - Prevents excessive turnover via 'dropout' mechanism
    """
    def generate_trade_decision(self, execute_result=None):
        # 1. Get current signal scores for today
        # 2. Rank stocks by score
        # 3. Hold top-K, sell bottom, buy new entries
        ...
```

**Atlas adaptation:** `AtlasSignalStrategy` in `strategies/signal_strategy.py` wrapping Atlas signal engine output.

### 3.3 RL Strategy Interface

```python
# qlib/strategy/base.py — RLIntStrategy
class RLIntStrategy(RLStrategy):
    """RL strategy with state/action interpreters."""

    def __init__(self, policy, state_interpreter, action_interpreter, ...):
        self.state_interpreter = state_interpreter  # market features → RL obs
        self.action_interpreter = action_interpreter # RL action → orders

    def generate_trade_decision(self, execute_result=None):
        state = self.state_interpreter.interpret(execute_result)
        action = self.policy.step(state)
        return self.action_interpreter.interpret(action)

# Interpreters to implement for Atlas:
class AtlasStateInterpreter(StateInterpreter):
    """Convert Atlas market features (OHLCV + indicators) → RL obs vector."""
    def interpret(self, execute_result) -> np.ndarray:
        # Return: [price_change, volume_ratio, rsi, macd, bb_position, ...]
        ...

class AtlasActionInterpreter(ActionInterpreter):
    """Convert RL action {0=HOLD, 1=BUY, 2=SELL} → Atlas Order."""
    def interpret(self, state, action) -> Order:
        ...
```

---

## 4. Backtest Engine (Phase 11)

### 4.1 Exchange — Realistic Market Simulation

```python
# qlib/backtest/exchange.py — Exchange (MIT — copy directly)
class Exchange:
    """
    Simulates market with realistic costs and constraints.

    Key parameters:
    - freq: "day" | "1min" | "5min"
    - deal_price: "$close" | "$open" | "$vwap" | ("$open", "$close") for buy/sell
    - open_cost: 0.0015 (0.15% commission on buy)
    - close_cost: 0.0025 (0.25% commission on sell)
    - min_cost: 5.0 (minimum $5 commission per trade)
    - limit_threshold: ±0.1 for circuit breaker (stock halted if >10% move)
    - volume_threshold: max pct of daily volume per order
    """

    def get_deal_price(self, stock_id, start_time, end_time, direction): ...
    def check_stock_suspended(self, stock_id, trade_start_time): ...
    def deal(self, order: Order, trade_account: Account) -> bool: ...
```

**Atlas adaptation:** `execution/exchange_simulator.py` — extends `paper_broker.py` with realistic cost modeling.

### 4.2 Order and Position

```python
# qlib/backtest/decision.py — Order dataclass (MIT — copy directly)
@dataclass
class Order:
    stock_id: str
    amount: float        # shares, non-negative
    direction: OrderDir  # OrderDir.BUY or OrderDir.SELL
    start_time: pd.Timestamp
    end_time: pd.Timestamp
    deal_amount: float = 0.0   # filled by exchange after execution
    factor: float = None       # price factor

class OrderDir(IntEnum):
    SELL = 0
    BUY = 1
```

### 4.3 Backtest Runner Pattern

```python
# Qlib backtest usage pattern (from examples):
from qlib.backtest import backtest, executor as exec

executor_config = {
    "class": "SimulatorExecutor",
    "module_path": "qlib.backtest.executor",
    "kwargs": {
        "time_per_step": "day",
        "generate_portfolio_metrics": True,
    },
}

backtest_config = {
    "start_time": "2020-01-01",
    "end_time": "2023-12-31",
    "account": 1_000_000,    # starting capital
    "benchmark": "SH000300", # benchmark index
    "exchange_kwargs": {
        "open_cost": 0.0015,
        "close_cost": 0.0025,
        "min_cost": 5,
        "deal_price": "close",
    },
}

# Atlas adaptation for runner.py:
class AtlasBacktestRunner:
    def run(
        self,
        strategy,           # AtlasStrategy instance
        dataset,            # AtlasDataset
        exchange_config: dict,
        start_time: str,
        end_time: str,
        initial_capital: float = 100_000,
    ) -> BacktestReport:
        ...

    def generate_report(self, portfolio_metrics) -> BacktestReport:
        """Compute Sharpe, MaxDrawdown, Annualized Return, Win Rate, etc."""
        ...
```

---

## 5. Feature Expressions (Phase 3)

Qlib uses a **symbolic expression language** for features. Atlas should adopt this:

```python
# Qlib feature expression examples (from DataHandlerLP configs)
# These become column names in the feature DataFrame:

OHLCV_FEATURES = [
    "$close",           # raw close price
    "$open", "$high", "$low",
    "$volume",
    "Ref($close, 1)",  # previous day close
    "Ref($close, 5)",  # 5 days ago close
    "Mean($close, 5)", # 5-day moving average
    "Std($close, 10)", # 10-day volatility
    "($close-$open)/$open",  # intraday return
    "($high-$low)/$close",   # intraday range
    "Log($volume/$volume)",  # volume ratio
    "Rsquare($close, 5)",    # R² of linear fit
    "Resi($close, 5)",       # residual of linear fit
    "Slope($close, 5)",      # slope of linear fit
    "Max($high, 5)",         # 5-day high
    "Min($low, 5)",          # 5-day low
    "Rank($volume)",         # cross-sectional rank
    "IdxMax($high, 20)",     # days since 20-day high
    "Corr($close, $volume, 10)",  # rolling correlation
]

# In Atlas: define these in core_intelligence/features/technical/indicators.py
# as a FEATURE_REGISTRY dictionary mapping name → computation function
```

---

## 6. Processors to Implement in Atlas (copy from Qlib)

File: `python/src/atlas/data_layer/processors.py`

```python
# MIT — direct copy with attribution header:
# Adapted from Microsoft Qlib (MIT License)
# https://github.com/microsoft/qlib

class Processor(ABC):
    def fit(self, df: pd.DataFrame = None): pass
    @abstractmethod
    def __call__(self, df: pd.DataFrame) -> pd.DataFrame: ...
    def is_for_infer(self) -> bool: return True
    def readonly(self) -> bool: return False

class DropnaLabel(Processor):
    """Drop rows where label column is NaN. Training-only."""
    def is_for_infer(self): return False

class Fillna(Processor):
    """Fill NaN values with a constant (default 0)."""

class ProcessInf(Processor):
    """Replace ±inf with clipped value."""

class ZScoreNorm(Processor):
    """Z-score normalization per feature column. Fit on training data."""
    def fit(self, df):
        self.mean = df.mean()
        self.std = df.std()
    def __call__(self, df):
        return (df - self.mean) / (self.std + 1e-8)

class RobustZScoreNorm(Processor):
    """Median-based Z-score. Resistant to outliers."""
    def fit(self, df):
        self.median = df.median()
        self.mad = (df - self.median).abs().median()
    def __call__(self, df):
        return (df - self.median) / (self.mad * 1.4826 + 1e-8)

class CSZScoreNorm(Processor):
    """Cross-sectional normalization: normalize each date row across instruments."""
    def __call__(self, df):
        return df.groupby(level="datetime").transform(
            lambda x: (x - x.mean()) / (x.std() + 1e-8)
        )
```

---

## 7. Implementation Priority for Atlas

### Immediate (Phase 1 upgrade):
1. ✅ Implement `AtlasDataHandler` with `DK_R/DK_I/DK_L` keys
2. ✅ Implement `Processor` ABC + `ZScoreNorm`, `RobustZScoreNorm`, `Fillna`, `ProcessInf`, `DropnaLabel`
3. ✅ Implement `AtlasDataset` with `segments` (train/valid/test)
4. ✅ Expand `cache_store.py` with Level 1 (memory) + Level 2 (Parquet)

### Phase 4 (ML Engines):
5. ✅ Copy `pytorch_lstm.py` from Qlib → `strategies/ml/lstm_engine.py`
6. ✅ Copy `xgboost.py` from Qlib → `strategies/ml/xgboost_engine.py`
7. ✅ Implement `AtlasStateInterpreter` + `AtlasActionInterpreter` for RL

### Phase 11 (Backtest):
8. ✅ Implement `Exchange` simulator with cost model (from Qlib Exchange)
9. ✅ Expand `runner.py` into full `AtlasBacktestRunner`
10. ✅ Implement `BacktestReport` with Sharpe, MaxDD, Annualized Return

---

## 8. Reference Files to Copy

From `C:/Users/mauri/AppData/Local/Temp/atlas_repos/qlib-main/qlib-main/qlib/`:

| Source | Copy to Atlas |
|--------|--------------|
| `data/dataset/processor.py` | `data_layer/processors.py` |
| `model/base.py` | `strategies/base_model.py` |
| `strategy/base.py` | `strategies/base_strategy.py` |
| `backtest/decision.py` (Order class) | `execution/order.py` |
| `backtest/exchange.py` | `execution/exchange_simulator.py` |
| `contrib/model/pytorch_lstm.py` | `strategies/ml/lstm_engine.py` |
| `contrib/model/xgboost.py` | `strategies/ml/xgboost_engine.py` |
| `contrib/strategy/signal_strategy.py` | `strategies/signal_strategy.py` |

**Attribution header to add to all copied files:**
```python
# Adapted from Microsoft Qlib (MIT License)
# Original: https://github.com/microsoft/qlib
# Copyright (c) Microsoft Corporation
```
