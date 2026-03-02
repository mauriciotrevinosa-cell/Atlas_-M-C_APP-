"""
ARIA Trader — Composite Scorer
Elite quantitative engine that fuses all Atlas signal layers into one unified score.

Score Architecture:
  Technical  (35%) — MultiStrategyEngine 5-engine consensus
  Factor     (25%) — qlib Alpha158 factor groups (MOMENTUM/VOLUME/VOL/QUALITY/TECH/MICRO)
  Fundamental(20%) — DCF intrinsic value + quality metrics
  Momentum   (10%) — Multi-horizon price momentum + volume confirmation
  Regime     (10%) — Market structure + correlation regime
  ──────────────────────────────────────────────────────
  Composite:  -100 to +100
  Verdict:    STRONG BUY / BUY / HOLD / AVOID / STRONG SELL
  Confidence: 0.0 – 1.0
  Prediction: Entry / Stop / Target / R:R / Horizon (bars)
"""

from __future__ import annotations
import sys
import os
import math
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd

logger = logging.getLogger("aria_trader")


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class ComponentScore:
    name: str
    weight: float
    raw_score: float          # -1..+1
    weighted_contribution: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PricePrediction:
    entry: float
    stop_loss: float
    target_1: float
    target_2: float
    rr_ratio: float
    horizon_days: int
    expected_return_pct: float
    atr: float


@dataclass
class TraderResult:
    ticker: str
    composite_score: float          # -100..+100
    verdict: str                    # STRONG BUY / BUY / HOLD / AVOID / STRONG SELL
    confidence: float               # 0..1
    components: List[ComponentScore]
    prediction: Optional[PricePrediction]
    last_close: float
    insights: List[str]             # Human-readable key insights
    risk_flags: List[str]           # Risk warnings
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "ticker":          self.ticker,
            "composite_score": round(self.composite_score, 2),
            "verdict":         self.verdict,
            "confidence":      round(self.confidence, 3),
            "last_close":      self.last_close,
            "components": [
                {
                    "name":     c.name,
                    "weight":   c.weight,
                    "score":    round(c.raw_score * 100, 1),
                    "contrib":  round(c.weighted_contribution * 100, 1),
                    "details":  c.details,
                }
                for c in self.components
            ],
            "prediction": {
                "entry":              self.prediction.entry,
                "stop_loss":          self.prediction.stop_loss,
                "target_1":           self.prediction.target_1,
                "target_2":           self.prediction.target_2,
                "rr_ratio":           round(self.prediction.rr_ratio, 2),
                "horizon_days":       self.prediction.horizon_days,
                "expected_return_pct":round(self.prediction.expected_return_pct, 2),
                "atr":                round(self.prediction.atr, 4),
            } if self.prediction else None,
            "insights":    self.insights,
            "risk_flags":  self.risk_flags,
            "timestamp":   self.timestamp,
        }


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

def _zscore_norm(series: pd.Series) -> float:
    """Normalise the last value of a series using z-score → tanh → [-1,1]."""
    if len(series) < 5:
        return 0.0
    mu, sigma = series.mean(), series.std()
    if sigma == 0:
        return 0.0
    z = (series.iloc[-1] - mu) / sigma
    return float(math.tanh(z))          # smooth bounded [-1,1]

def _safe_div(a, b, default=0.0):
    try:
        return float(a) / float(b) if float(b) != 0 else default
    except Exception:
        return default


# ─────────────────────────────────────────────
# Composite Scorer
# ─────────────────────────────────────────────

class CompositeScorer:
    """
    Elite fusion engine.  Call `.score(ticker, df)`.
    All sub-scorers are called with try/except so a failing module
    never kills the whole pipeline.
    """

    # Component weights — must sum to 1.0
    WEIGHTS = {
        "technical":   0.35,
        "factor":      0.25,
        "fundamental": 0.20,
        "momentum":    0.10,
        "regime":      0.10,
    }

    # Verdict thresholds (composite_score)
    VERDICTS = [
        ( 60,  100, "STRONG BUY"),
        ( 25,   60, "BUY"),
        (-15,   25, "HOLD"),
        (-60,  -15, "AVOID"),
        (-100, -60, "STRONG SELL"),
    ]

    def score(self, ticker: str, df: pd.DataFrame,
              info: Optional[dict] = None) -> TraderResult:
        """
        Parameters
        ----------
        ticker : str
        df     : OHLCV DataFrame with Capitalized columns (Open/High/Low/Close/Volume)
        info   : Optional dict of yfinance `.info` fundamentals (pre-fetched to avoid duplicate calls)
        """
        from datetime import datetime

        components: List[ComponentScore] = []
        insights:   List[str] = []
        risk_flags: List[str] = []

        last_close = float(df["Close"].iloc[-1]) if len(df) > 0 else 0.0

        # ── 1. Technical ──────────────────────────────────────────────
        tech_score, tech_details = self._score_technical(ticker, df)
        components.append(ComponentScore(
            name="technical", weight=self.WEIGHTS["technical"],
            raw_score=tech_score,
            weighted_contribution=tech_score * self.WEIGHTS["technical"],
            details=tech_details,
        ))

        # ── 2. Factor ─────────────────────────────────────────────────
        factor_score, factor_details = self._score_factor(df)
        components.append(ComponentScore(
            name="factor", weight=self.WEIGHTS["factor"],
            raw_score=factor_score,
            weighted_contribution=factor_score * self.WEIGHTS["factor"],
            details=factor_details,
        ))

        # ── 3. Fundamental ────────────────────────────────────────────
        fund_score, fund_details = self._score_fundamental(ticker, last_close, info)
        components.append(ComponentScore(
            name="fundamental", weight=self.WEIGHTS["fundamental"],
            raw_score=fund_score,
            weighted_contribution=fund_score * self.WEIGHTS["fundamental"],
            details=fund_details,
        ))

        # ── 4. Momentum ───────────────────────────────────────────────
        mom_score, mom_details = self._score_momentum(df)
        components.append(ComponentScore(
            name="momentum", weight=self.WEIGHTS["momentum"],
            raw_score=mom_score,
            weighted_contribution=mom_score * self.WEIGHTS["momentum"],
            details=mom_details,
        ))

        # ── 5. Regime ─────────────────────────────────────────────────
        regime_score, regime_details = self._score_regime(df)
        components.append(ComponentScore(
            name="regime", weight=self.WEIGHTS["regime"],
            raw_score=regime_score,
            weighted_contribution=regime_score * self.WEIGHTS["regime"],
            details=regime_details,
        ))

        # ── Composite ─────────────────────────────────────────────────
        composite = sum(c.weighted_contribution for c in components)
        composite_scaled = _clamp(composite * 100, -100, 100)

        # Confidence: inverse of dispersion among components
        scores_arr = np.array([c.raw_score for c in components])
        dispersion = float(np.std(scores_arr))          # 0=all agree, 1=chaos
        confidence = _clamp(1.0 - dispersion, 0.0, 1.0)

        verdict = self._verdict(composite_scaled)

        # ── Price Prediction ──────────────────────────────────────────
        prediction = self._make_prediction(df, composite_scaled, verdict)

        # ── Insights & Flags ──────────────────────────────────────────
        insights  = self._generate_insights(components, verdict, prediction, tech_details, fund_details, mom_details)
        risk_flags = self._generate_risk_flags(df, fund_details, dispersion, components)

        return TraderResult(
            ticker=ticker,
            composite_score=round(composite_scaled, 2),
            verdict=verdict,
            confidence=round(confidence, 3),
            components=components,
            prediction=prediction,
            last_close=last_close,
            insights=insights,
            risk_flags=risk_flags,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    # ─────────────────────────────────────────
    # Component Scorers
    # ─────────────────────────────────────────

    def _score_technical(self, ticker: str, df: pd.DataFrame):
        """35% — MultiStrategyEngine consensus + per-engine breakdown."""
        details: Dict[str, Any] = {}
        try:
            _add_path()
            from atlas.core_intelligence.engines.rule_based.multi_strategy import MultiStrategyEngine
            engine = MultiStrategyEngine()
            context = {"ticker": ticker, "period": "1y"}
            signals = engine.analyze(df, context)
            if not signals:
                return 0.0, {"error": "no signals"}
            # net_score is already -1..+1 based on buy_weight - sell_weight
            sig = signals[0]
            raw = float(getattr(sig, "strength", 0.0))
            action = getattr(sig, "action", "HOLD")
            if action == "SELL":
                raw = -abs(raw)
            elif action == "BUY":
                raw = abs(raw)
            else:
                raw = raw * 0.2  # HOLD dampened

            details = {
                "action":     action,
                "confidence": round(abs(raw), 3),
                "reason":     getattr(sig, "reason", ""),
            }
            return _clamp(raw), details
        except Exception as e:
            logger.warning("technical scorer error: %s", e)
            # Fallback: compute manually
            return self._score_technical_fallback(df)

    def _score_technical_fallback(self, df: pd.DataFrame):
        """Manual 5-indicator consensus when MultiStrategyEngine unavailable."""
        try:
            c = df["Close"]
            signals = []

            # SMA cross
            if len(c) >= 50:
                sma20 = c.rolling(20).mean().iloc[-1]
                sma50 = c.rolling(50).mean().iloc[-1]
                signals.append(1.0 if sma20 > sma50 else -1.0)

            # RSI
            if len(c) >= 15:
                delta = c.diff()
                gain = delta.clip(lower=0).rolling(14).mean()
                loss = (-delta.clip(upper=0)).rolling(14).mean()
                rs = gain / (loss + 1e-9)
                rsi = 100 - 100 / (1 + rs.iloc[-1])
                if rsi < 30:
                    signals.append(1.0)
                elif rsi > 70:
                    signals.append(-1.0)
                else:
                    signals.append((_clamp((50 - rsi) / 20)))

            # MACD
            if len(c) >= 26:
                ema12 = c.ewm(span=12).mean()
                ema26 = c.ewm(span=26).mean()
                macd = ema12 - ema26
                signal_line = macd.ewm(span=9).mean()
                hist = macd.iloc[-1] - signal_line.iloc[-1]
                signals.append(_clamp(hist / (c.mean() * 0.01 + 1e-9)))

            # BB position
            if len(c) >= 20:
                ma20 = c.rolling(20).mean()
                std20 = c.rolling(20).std()
                upper = ma20 + 2 * std20
                lower = ma20 - 2 * std20
                rng = (upper - lower).iloc[-1]
                if rng > 0:
                    pos = (c.iloc[-1] - lower.iloc[-1]) / rng  # 0..1
                    signals.append(_clamp(1 - 2 * pos))  # oversold=+1, overbought=-1

            # Momentum 20d
            if len(c) >= 21:
                m20 = (c.iloc[-1] - c.iloc[-21]) / (c.iloc[-21] + 1e-9)
                signals.append(_clamp(m20 * 10))

            score = float(np.mean(signals)) if signals else 0.0
            return _clamp(score), {"method": "fallback", "n_signals": len(signals)}
        except Exception:
            return 0.0, {"method": "fallback_error"}

    def _score_factor(self, df: pd.DataFrame):
        """25% — qlib Alpha158 factor groups."""
        details: Dict[str, Any] = {}
        try:
            _add_path()
            from atlas.correlation_portfolio.factor_models.factor_engine import FactorEngine
            fe = FactorEngine()
            groups = fe.group_scores(df)
            details = {k: round(v, 3) for k, v in groups.items()}
            # Weight groups: MOMENTUM + TECHNICAL strongest predictors
            weights = {
                "MOMENTUM":   0.25,
                "VOLUME":     0.15,
                "VOLATILITY": 0.10,
                "QUALITY":    0.20,
                "TECHNICAL":  0.20,
                "MICRO":      0.10,
            }
            weighted = sum(groups.get(k, 0) * w for k, w in weights.items())
            return _clamp(weighted), details
        except Exception as e:
            logger.warning("factor scorer error: %s", e)
            return self._score_factor_fallback(df)

    def _score_factor_fallback(self, df: pd.DataFrame):
        """Manual alpha factors when FactorEngine unavailable."""
        try:
            c = df["Close"]
            v = df["Volume"]
            signals = []

            # Momentum 1m, 3m, 6m
            for n in [21, 63, 126]:
                if len(c) > n:
                    signals.append(_clamp((c.iloc[-1]/c.iloc[-n] - 1) * 10))

            # Volume momentum
            if len(v) > 5:
                vm = v.iloc[-5:].mean() / (v.iloc[-20:].mean() + 1e-9) - 1
                signals.append(_clamp(vm))

            # Volatility regime (lower = better trend)
            if len(c) > 20:
                vol = c.pct_change().rolling(20).std().iloc[-1]
                signals.append(_clamp(0.3 - vol * 10))  # <3% vol = positive

            score = float(np.mean(signals)) if signals else 0.0
            return _clamp(score), {"method": "fallback", "n": len(signals)}
        except Exception:
            return 0.0, {}

    def _score_fundamental(self, ticker: str, last_close: float, info: Optional[dict] = None):
        """20% — DCF + quality metrics."""
        details: Dict[str, Any] = {}
        try:
            import yfinance as yf
            if info is None:
                t = yf.Ticker(ticker)
                info = t.info or {}

            # P/E score: lower P/E relative to growth = better (PEG ratio)
            pe = info.get("trailingPE") or info.get("forwardPE")
            eg = info.get("earningsGrowth") or info.get("revenueGrowth")
            peg_score = 0.0
            if pe and eg and eg > 0:
                peg = pe / (eg * 100)       # PEG < 1 = undervalued
                peg_score = _clamp((1 - peg) * 0.5)
                details["PEG"] = round(peg, 2)

            # P/B score
            pb = info.get("priceToBook")
            pb_score = 0.0
            if pb:
                pb_score = _clamp((3 - pb) / 4)   # P/B < 3 = positive
                details["P/B"] = round(pb, 2)

            # Profit margin
            margin = info.get("profitMargins")
            margin_score = 0.0
            if margin:
                margin_score = _clamp(margin * 3)  # 33% margin = max positive
                details["net_margin"] = round(margin, 3)

            # Revenue growth
            rev_growth = info.get("revenueGrowth")
            growth_score = 0.0
            if rev_growth:
                growth_score = _clamp(rev_growth * 4)
                details["rev_growth"] = round(rev_growth, 3)

            # Debt/Equity (lower is better for quality)
            de = info.get("debtToEquity")
            debt_score = 0.0
            if de is not None:
                debt_score = _clamp((1 - de / 200))  # D/E < 200% = neutral, 0% = great
                details["D/E"] = round(de, 1)

            # Return on Equity
            roe = info.get("returnOnEquity")
            roe_score = 0.0
            if roe:
                roe_score = _clamp(roe * 4)   # 25% ROE = max positive
                details["ROE"] = round(roe, 3)

            # DCF rough estimate
            fcf = info.get("freeCashflow")
            shares = info.get("sharesOutstanding")
            dcf_score = 0.0
            if fcf and shares and shares > 0:
                # Gordon Growth Model simplified
                wacc, g = 0.10, 0.025
                fcf_ps = fcf / shares
                if wacc > g:
                    intrinsic = fcf_ps * (1 + g) / (wacc - g)
                    upside = (intrinsic - last_close) / (last_close + 1e-9)
                    dcf_score = _clamp(upside)
                    details["DCF_intrinsic"] = round(intrinsic, 2)
                    details["DCF_upside_pct"] = round(upside * 100, 1)

            # Weighted average
            scored_items = [
                (peg_score,    0.20),
                (pb_score,     0.10),
                (margin_score, 0.20),
                (growth_score, 0.15),
                (debt_score,   0.10),
                (roe_score,    0.15),
                (dcf_score,    0.10),
            ]
            total = sum(s * w for s, w in scored_items)
            n_valid = sum(1 for s, _ in scored_items if s != 0.0)
            if n_valid < 2:
                details["warning"] = "limited fundamentals available"
            return _clamp(total), details

        except Exception as e:
            logger.warning("fundamental scorer error: %s", e)
            return 0.0, {"error": str(e)[:80]}

    def _score_momentum(self, df: pd.DataFrame):
        """10% — Multi-horizon price + volume momentum."""
        details: Dict[str, Any] = {}
        try:
            c = df["Close"]
            v = df["Volume"]
            signals = []

            # Multi-horizon returns (signal = tanh-normalised)
            horizons = [(1, "1d"), (5, "1w"), (21, "1m"), (63, "3m")]
            for n, label in horizons:
                if len(c) > n:
                    r = (c.iloc[-1] - c.iloc[-(n+1)]) / (c.iloc[-(n+1)] + 1e-9)
                    sig = float(math.tanh(r * 15))  # tanh normalises outliers
                    signals.append(sig)
                    details[f"ret_{label}"] = round(r * 100, 2)

            # Volume confirmation (rising price + rising volume = bullish)
            if len(v) > 21 and len(c) > 21:
                vol_trend = v.iloc[-5:].mean() / (v.iloc[-21:].mean() + 1e-9) - 1
                price_trend = (c.iloc[-1] - c.iloc[-21]) / (c.iloc[-21] + 1e-9)
                vol_sig = _clamp(math.copysign(abs(vol_trend), price_trend))
                signals.append(vol_sig * 0.5)
                details["vol_confirm"] = round(vol_sig, 3)

            # Rate of change acceleration
            if len(c) > 42:
                r1 = (c.iloc[-1] - c.iloc[-22]) / (c.iloc[-22] + 1e-9)
                r2 = (c.iloc[-22] - c.iloc[-43]) / (c.iloc[-43] + 1e-9)
                accel = r1 - r2
                signals.append(_clamp(accel * 8))
                details["accel"] = round(accel * 100, 2)

            score = float(np.mean(signals)) if signals else 0.0
            return _clamp(score), details
        except Exception as e:
            logger.warning("momentum scorer error: %s", e)
            return 0.0, {}

    def _score_regime(self, df: pd.DataFrame):
        """10% — Market regime detection (trend/volatility/correlation)."""
        details: Dict[str, Any] = {}
        try:
            c = df["Close"]
            if len(c) < 50:
                return 0.0, {"warning": "not enough data"}

            signals = []

            # Trend strength via ADX proxy
            h = df["High"]; lo = df["Low"]
            tr = pd.concat([
                h - lo,
                (h - c.shift()).abs(),
                (lo - c.shift()).abs()
            ], axis=1).max(axis=1)
            atr14 = tr.rolling(14).mean()

            dm_plus = (h.diff().clip(lower=0))
            dm_minus = (-lo.diff().clip(upper=0))
            di_plus = 100 * (dm_plus.rolling(14).mean() / (atr14 + 1e-9))
            di_minus = 100 * (dm_minus.rolling(14).mean() / (atr14 + 1e-9))
            dx = (100 * (di_plus - di_minus).abs() / (di_plus + di_minus + 1e-9))
            adx = dx.rolling(14).mean().iloc[-1]
            details["ADX"] = round(adx, 1)

            # Strong trend (ADX > 25) → amplify momentum direction
            trend_dir = 1.0 if di_plus.iloc[-1] > di_minus.iloc[-1] else -1.0
            if adx > 25:
                trend_sig = trend_dir * min(adx / 50, 1.0)
            else:
                trend_sig = trend_dir * 0.1  # choppy — near-neutral

            signals.append(trend_sig)

            # Volatility regime: VIX proxy from 30d realised vol
            rv = c.pct_change().rolling(30).std().iloc[-1] * math.sqrt(252)
            details["RV30"] = round(rv * 100, 1)
            if rv < 0.15:
                vol_sig = 0.3     # low vol = benign
            elif rv < 0.30:
                vol_sig = 0.0     # neutral
            elif rv < 0.50:
                vol_sig = -0.3    # elevated
            else:
                vol_sig = -0.7    # crisis
            signals.append(vol_sig)

            # Mean reversion potential (distance from 200d SMA)
            if len(c) >= 200:
                sma200 = c.rolling(200).mean().iloc[-1]
                dev = (c.iloc[-1] - sma200) / (sma200 + 1e-9)
                # Mean-reversion signal: far above = bearish, far below = bullish
                mr_sig = _clamp(-dev * 5)
                details["dist_200d"] = round(dev * 100, 1)
                signals.append(mr_sig * 0.5)

            score = float(np.mean(signals)) if signals else 0.0
            return _clamp(score), details
        except Exception as e:
            logger.warning("regime scorer error: %s", e)
            return 0.0, {}

    # ─────────────────────────────────────────
    # Price Prediction
    # ─────────────────────────────────────────

    def _make_prediction(self, df: pd.DataFrame, composite: float, verdict: str) -> Optional[PricePrediction]:
        """ATR-based entry/stop/target with dynamic multipliers by conviction."""
        try:
            c = df["Close"]
            h = df["High"]
            lo = df["Low"]

            last = float(c.iloc[-1])
            tr = pd.concat([h - lo, (h - c.shift()).abs(), (lo - c.shift()).abs()], axis=1).max(axis=1)
            atr = float(tr.rolling(14).mean().iloc[-1])

            if atr <= 0 or last <= 0:
                return None

            atr_pct = atr / last

            # Multipliers scale with conviction
            abs_score = abs(composite) / 100
            stop_mult   = 1.0 + abs_score * 0.5    # 1.0x – 1.5x ATR
            target1_mult = 2.0 + abs_score * 1.0   # 2.0x – 3.0x ATR
            target2_mult = 3.5 + abs_score * 2.0   # 3.5x – 5.5x ATR

            if composite >= 0:
                # Long trade
                entry    = last
                stop     = round(last - stop_mult * atr, 4)
                target_1 = round(last + target1_mult * atr, 4)
                target_2 = round(last + target2_mult * atr, 4)
                exp_ret  = (target_1 - entry) / entry * 100
            else:
                # Short / avoid trade (targets below)
                entry    = last
                stop     = round(last + stop_mult * atr, 4)
                target_1 = round(last - target1_mult * atr, 4)
                target_2 = round(last - target2_mult * atr, 4)
                exp_ret  = (target_1 - entry) / entry * 100

            risk  = abs(entry - stop)
            rwd   = abs(target_1 - entry)
            rr    = rwd / (risk + 1e-9)

            # Horizon: faster exit on high conviction
            if abs(composite) >= 60:
                horizon = 10
            elif abs(composite) >= 30:
                horizon = 20
            else:
                horizon = 30

            return PricePrediction(
                entry=round(entry, 4),
                stop_loss=stop,
                target_1=target_1,
                target_2=target_2,
                rr_ratio=round(rr, 2),
                horizon_days=horizon,
                expected_return_pct=round(exp_ret, 2),
                atr=round(atr, 4),
            )
        except Exception as e:
            logger.warning("prediction error: %s", e)
            return None

    # ─────────────────────────────────────────
    # Verdict
    # ─────────────────────────────────────────

    def _verdict(self, score: float) -> str:
        for lo, hi, label in self.VERDICTS:
            if lo <= score <= hi:
                return label
        return "HOLD"

    # ─────────────────────────────────────────
    # Insights + Risk Flags
    # ─────────────────────────────────────────

    def _generate_insights(self, components, verdict, pred, tech_d, fund_d, mom_d) -> List[str]:
        ins = []

        # Overall direction
        ins.append(f"Composite verdict: {verdict}")

        # Best and worst components
        sorted_c = sorted(components, key=lambda x: abs(x.raw_score), reverse=True)
        best = sorted_c[0]
        worst = sorted_c[-1]
        ins.append(f"Strongest signal: {best.name.upper()} ({'+' if best.raw_score >= 0 else ''}{best.raw_score*100:.0f}/100)")

        # Technical
        if tech_d.get("action"):
            ins.append(f"Strategy engines: {tech_d['action']} at {tech_d.get('confidence',0)*100:.0f}% confidence")

        # Fundamental
        if "DCF_upside_pct" in fund_d:
            upsign = "+" if fund_d["DCF_upside_pct"] > 0 else ""
            ins.append(f"DCF model shows {upsign}{fund_d['DCF_upside_pct']:.1f}% vs current price")
        if "net_margin" in fund_d:
            ins.append(f"Net margin {fund_d['net_margin']*100:.1f}% | ROE {fund_d.get('ROE',0)*100:.1f}%")

        # Momentum
        ret_1m = mom_d.get("ret_1m")
        ret_3m = mom_d.get("ret_3m")
        if ret_1m is not None and ret_3m is not None:
            ins.append(f"Price momentum: 1M {ret_1m:+.1f}% | 3M {ret_3m:+.1f}%")

        # R:R
        if pred:
            ins.append(f"Trade setup: Entry {pred.entry:.2f} | Stop {pred.stop_loss:.2f} | T1 {pred.target_1:.2f} (R:R {pred.rr_ratio:.1f}x)")

        return ins[:8]

    def _generate_risk_flags(self, df, fund_d, dispersion, components) -> List[str]:
        flags = []

        # Signal disagreement
        if dispersion > 0.5:
            flags.append("⚠ High signal dispersion — components disagree significantly")

        # Debt concern
        if fund_d.get("D/E", 0) > 200:
            flags.append(f"⚠ High leverage: D/E ratio {fund_d['D/E']:.0f}%")

        # Volatility
        c = df["Close"]
        if len(c) > 20:
            rv = c.pct_change().rolling(20).std().iloc[-1]
            if rv * math.sqrt(252) > 0.5:
                flags.append("⚠ Elevated annualised volatility (>50%)")

        # Thin fundamental data
        if fund_d.get("warning"):
            flags.append("⚠ Limited fundamental data available")

        # Negative momentum collision (all going down)
        mom = next((c for c in components if c.name == "momentum"), None)
        tech = next((c for c in components if c.name == "technical"), None)
        if mom and tech and mom.raw_score < -0.5 and tech.raw_score > 0.3:
            flags.append("⚠ Momentum/Technical divergence — wait for confirmation")

        return flags


# ─────────────────────────────────────────────
# Screener
# ─────────────────────────────────────────────

class UniverseScreener:
    """
    Screens a list of tickers and ranks them by composite score.
    Returns sorted list of TraderResult with top BUYs and worst AVOIDs.
    """

    def __init__(self):
        self.scorer = CompositeScorer()

    def screen(self, tickers: List[str], period: str = "1y") -> List[TraderResult]:
        import yfinance as yf
        results = []
        for ticker in tickers:
            try:
                df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
                if df is None or len(df) < 30:
                    continue
                df.columns = [c.capitalize() for c in df.columns]
                # Flatten multi-index if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [c[0] for c in df.columns]
                info = yf.Ticker(ticker).info
                result = self.scorer.score(ticker, df, info=info)
                results.append(result)
            except Exception as e:
                logger.warning("screen error %s: %s", ticker, e)
        results.sort(key=lambda r: r.composite_score, reverse=True)
        return results


# ─────────────────────────────────────────────
# Import path helper
# ─────────────────────────────────────────────

def _add_path():
    """Ensure the atlas package is importable."""
    candidate = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    candidate = os.path.abspath(candidate)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)
