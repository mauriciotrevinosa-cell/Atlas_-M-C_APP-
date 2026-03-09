"""
Orchestration Router — Phase 9

Routes analysis requests through the Atlas pipeline:
Data → Market State → Features → Signal Engine → Risk → Output

The router coordinates the "brain" modules and returns a structured
decision object that ARIA or a UI can present to the user.

Copyright © 2026 M&C. All Rights Reserved.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class AnalysisRequest:
    """Input parameters for a full pipeline run."""
    symbol: str
    timeframe: str = "1y"
    interval: str = "1d"
    portfolio_value: float = 10_000.0
    risk_per_trade: float = 0.01       # 1% of capital per trade
    target_volatility: float = 0.15    # 15% annualised vol target
    modules: List[str] = field(default_factory=lambda: [
        "market_state", "indicators", "risk"
    ])


@dataclass
class AnalysisResult:
    """Structured output from a pipeline run."""
    symbol: str
    timestamp: pd.Timestamp
    market_state: Dict[str, Any] = field(default_factory=dict)
    indicators: Dict[str, Any] = field(default_factory=dict)
    risk: Dict[str, Any] = field(default_factory=dict)
    signal: str = "neutral"            # "bullish" | "bearish" | "neutral"
    confidence: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "timestamp": str(self.timestamp),
            "market_state": self.market_state,
            "indicators": self.indicators,
            "risk": self.risk,
            "signal": self.signal,
            "confidence": self.confidence,
            "errors": self.errors,
        }


class PipelineRouter:
    """
    Multi-Brain Orchestration Router.

    Coordinates Atlas modules into a single analysis pipeline.
    Modules are called in dependency order; failures in one module
    are logged and the pipeline continues with reduced output.

    Example:
        >>> router = PipelineRouter()
        >>> req = AnalysisRequest(symbol="BTC-USD", timeframe="6mo")
        >>> result = router.run(req)
        >>> print(result.signal, result.confidence)
    """

    def __init__(self):
        self._data_manager = None
        self._regime_detector = None
        self._vol_analyzer = None
        logger.info("Initialized PipelineRouter")

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def run(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Run the full analysis pipeline for a given request.

        Args:
            request: AnalysisRequest with symbol, timeframe, etc.

        Returns:
            AnalysisResult with populated fields
        """
        logger.info("Pipeline run: %s [%s/%s]", request.symbol, request.timeframe, request.interval)

        result = AnalysisResult(
            symbol=request.symbol,
            timestamp=pd.Timestamp.now(),
        )

        # Step 1: Fetch data
        data = self._fetch_data(request, result)
        if data is None or data.empty:
            return result

        # Step 2: Market State
        if "market_state" in request.modules:
            self._run_market_state(data, request, result)

        # Step 3: Technical Indicators
        if "indicators" in request.modules:
            self._run_indicators(data, request, result)

        # Step 4: Risk
        if "risk" in request.modules:
            self._run_risk(data, request, result)

        # Step 5: Compose signal
        result.signal, result.confidence = self._compose_signal(result)

        logger.info(
            "Pipeline complete: %s → %s (%.0f%% confidence)",
            request.symbol, result.signal, result.confidence * 100,
        )
        return result

    def quick_analysis(self, symbol: str, timeframe: str = "3mo") -> Dict[str, Any]:
        """
        Quick one-call analysis with sensible defaults.

        Returns:
            Plain dict (JSON-serialisable)
        """
        req = AnalysisRequest(symbol=symbol, timeframe=timeframe)
        return self.run(req).to_dict()

    # ------------------------------------------------------------------ #
    # Pipeline steps                                                       #
    # ------------------------------------------------------------------ #

    def _fetch_data(
        self, request: AnalysisRequest, result: AnalysisResult
    ) -> Optional[pd.DataFrame]:
        try:
            if self._data_manager is None:
                from atlas.data_layer import DataManager
                self._data_manager = DataManager()

            data = self._data_manager.get(
                request.symbol,
                timeframe=request.timeframe,
                interval=request.interval,
            )
            logger.debug("Fetched %d rows for %s", len(data), request.symbol)
            return data
        except Exception as exc:
            msg = f"Data fetch failed: {exc}"
            logger.error(msg)
            result.errors.append(msg)
            return None

    def _run_market_state(
        self,
        data: pd.DataFrame,
        request: AnalysisRequest,
        result: AnalysisResult,
    ) -> None:
        try:
            if self._regime_detector is None:
                from atlas.core_intelligence.market_state import RegimeDetector, VolatilityAnalyzer
                self._regime_detector = RegimeDetector()
                self._vol_analyzer = VolatilityAnalyzer()

            regime = self._regime_detector.detect(data)
            vol = self._vol_analyzer.analyze(data)

            result.market_state = {
                "regime": regime.get("regime", "unknown"),
                "adx": regime.get("adx", 0),
                "trend_strength": regime.get("trend_strength", ""),
                "vol_regime": vol.get("regime", "unknown"),
                "hv_20": vol.get("hv_20", 0),
                "atr_pct": vol.get("atr_pct", 0),
            }
        except Exception as exc:
            msg = f"Market state failed: {exc}"
            logger.error(msg)
            result.errors.append(msg)

    def _run_indicators(
        self,
        data: pd.DataFrame,
        request: AnalysisRequest,
        result: AnalysisResult,
    ) -> None:
        try:
            close = data["Close"]
            # RSI
            delta = close.diff()
            gains = delta.where(delta > 0, 0.0)
            losses = -delta.where(delta < 0, 0.0)
            avg_gain = gains.ewm(alpha=1/14, adjust=False).mean()
            avg_loss = losses.ewm(alpha=1/14, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, 1e-9)
            rsi = float((100 - 100 / (1 + rs)).iloc[-1])

            # SMA cross
            sma_20 = float(close.rolling(20).mean().iloc[-1])
            sma_50 = float(close.rolling(50).mean().iloc[-1])
            current = float(close.iloc[-1])

            result.indicators = {
                "rsi_14": round(rsi, 2),
                "sma_20": round(sma_20, 4),
                "sma_50": round(sma_50, 4),
                "current_price": round(current, 4),
                "above_sma20": current > sma_20,
                "above_sma50": current > sma_50,
                "sma_cross_bullish": sma_20 > sma_50,
            }
        except Exception as exc:
            msg = f"Indicators failed: {exc}"
            logger.error(msg)
            result.errors.append(msg)

    def _run_risk(
        self,
        data: pd.DataFrame,
        request: AnalysisRequest,
        result: AnalysisResult,
    ) -> None:
        try:
            from atlas.risk.engine import VaRCVaR, PositionSizer

            returns = data["Close"].pct_change().dropna()
            realized_vol = float(returns.std() * (252 ** 0.5))

            calc = VaRCVaR(confidence=0.95)
            var_res = calc.calculate(returns)

            sizer = PositionSizer(max_position=0.25)
            kelly_f = sizer.kelly_from_returns(returns, fraction=0.5)
            vol_f = sizer.volatility_target(request.target_volatility, realized_vol)

            result.risk = {
                "var_95": round(var_res["var"], 4),
                "cvar_95": round(var_res["cvar"], 4),
                "realized_vol_ann": round(realized_vol, 4),
                "kelly_half": round(kelly_f, 4),
                "vol_target_size": round(vol_f, 4),
                "suggested_position_pct": round(min(kelly_f, vol_f) * 100, 1),
            }
        except Exception as exc:
            msg = f"Risk engine failed: {exc}"
            logger.error(msg)
            result.errors.append(msg)

    # ------------------------------------------------------------------ #
    # Signal composition                                                   #
    # ------------------------------------------------------------------ #

    def _compose_signal(
        self, result: AnalysisResult
    ) -> tuple[str, float]:
        """Simple rule-based signal from market state + indicators."""
        votes = []

        ms = result.market_state
        ind = result.indicators

        if ms:
            regime = ms.get("regime", "")
            if "up" in regime:
                votes.append(1)
            elif "down" in regime:
                votes.append(-1)
            else:
                votes.append(0)

        if ind:
            rsi = ind.get("rsi_14", 50)
            if rsi < 35:
                votes.append(1)   # oversold
            elif rsi > 65:
                votes.append(-1)  # overbought
            else:
                votes.append(0)

            if ind.get("sma_cross_bullish"):
                votes.append(1)
            else:
                votes.append(-1)

        if not votes:
            return "neutral", 0.0

        score = sum(votes) / len(votes)
        if score > 0.3:
            return "bullish", round(score, 2)
        elif score < -0.3:
            return "bearish", round(abs(score), 2)
        else:
            return "neutral", round(abs(score), 2)
