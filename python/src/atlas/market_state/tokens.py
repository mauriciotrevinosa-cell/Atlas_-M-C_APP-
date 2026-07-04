"""
Market-state tokenization for Atlas simulations and agents.

The tokenizer turns current market conditions into compact, deterministic
tokens. It is inspired by world-model token pipelines, but it does not train or
run a generative model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import pandas as pd

from .regime import RegimeDetector, RegimeState
from .volatility import VolatilityRegime


@dataclass(frozen=True)
class MarketStateToken:
    """One compact market-state token."""

    category: str
    value: str
    score: float = 0.0
    evidence: str = ""

    @property
    def token(self) -> str:
        return f"{self.category.upper()}:{self.value.upper()}"

    def to_dict(self) -> Dict[str, object]:
        return {
            "token": self.token,
            "category": self.category,
            "value": self.value,
            "score": float(self.score),
            "evidence": self.evidence,
        }


class MarketStateTokenizer:
    """Create deterministic state tokens from market data."""

    def __init__(
        self,
        regime_detector: Optional[RegimeDetector] = None,
        volatility_detector: Optional[VolatilityRegime] = None,
    ):
        self.regime_detector = regime_detector or RegimeDetector()
        self.volatility_detector = volatility_detector or VolatilityRegime()

    def from_ohlcv(self, data: pd.DataFrame, ticker: str = "UNKNOWN") -> List[MarketStateToken]:
        if data.empty:
            raise ValueError("from_ohlcv requires non-empty data")
        if "Close" not in data.columns:
            raise ValueError("from_ohlcv requires a Close column")

        tokens: List[MarketStateToken] = [
            MarketStateToken("asset", str(ticker).upper(), evidence="input"),
        ]

        regime = self._safe_regime(data)
        if regime:
            tokens.append(
                MarketStateToken(
                    "regime",
                    regime.regime,
                    score=regime.confidence,
                    evidence="RegimeDetector",
                )
            )
            tokens.append(
                MarketStateToken(
                    "confidence",
                    self._bucket(regime.confidence, low=0.4, high=0.75),
                    score=regime.confidence,
                    evidence="regime_confidence",
                )
            )
        else:
            tokens.append(MarketStateToken("regime", "unknown", evidence="insufficient_data"))

        vol = self._safe_volatility(data)
        tokens.append(MarketStateToken("volatility", vol, evidence="VolatilityRegime"))

        close = data["Close"].astype(float)
        tokens.append(self._momentum_token(close, 5))
        tokens.append(self._momentum_token(close, 20))

        if "Volume" in data.columns:
            tokens.append(self._volume_token(data["Volume"].astype(float)))

        return tokens

    @staticmethod
    def to_prompt_context(tokens: Iterable[MarketStateToken]) -> str:
        """Render tokens as a compact agent/MMO context line."""
        return " ".join(token.token for token in tokens)

    def _safe_regime(self, data: pd.DataFrame) -> Optional[RegimeState]:
        try:
            if len(data) < self.regime_detector.lookback:
                return None
            return self.regime_detector.detect(data)
        except Exception:
            return None

    def _safe_volatility(self, data: pd.DataFrame) -> str:
        try:
            if len(data) < self.volatility_detector.lookback:
                return "unknown"
            return self.volatility_detector.classify(data)
        except Exception:
            return "unknown"

    @staticmethod
    def _momentum_token(close: pd.Series, periods: int) -> MarketStateToken:
        if len(close) <= periods:
            return MarketStateToken(f"momentum_{periods}", "unknown", evidence="insufficient_data")
        ret = float(close.iloc[-1] / close.iloc[-periods - 1] - 1.0)
        threshold = 0.01 if periods <= 5 else 0.03
        if ret > threshold:
            value = "up"
        elif ret < -threshold:
            value = "down"
        else:
            value = "flat"
        return MarketStateToken(
            f"momentum_{periods}",
            value,
            score=ret,
            evidence=f"{periods}_period_return",
        )

    @staticmethod
    def _volume_token(volume: pd.Series) -> MarketStateToken:
        if len(volume) < 20:
            return MarketStateToken("volume", "unknown", evidence="insufficient_data")
        recent = float(volume.iloc[-5:].mean())
        baseline = float(volume.iloc[-20:].mean())
        ratio = recent / baseline if baseline else 0.0
        if ratio > 1.35:
            value = "expanding"
        elif ratio < 0.75:
            value = "contracting"
        else:
            value = "normal"
        return MarketStateToken("volume", value, score=ratio, evidence="5_vs_20_volume_ratio")

    @staticmethod
    def _bucket(value: float, low: float, high: float) -> str:
        if value < low:
            return "low"
        if value >= high:
            return "high"
        return "medium"
