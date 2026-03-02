"""
Desktop-facing module that ties simulation artifacts to a chosen ticker or portfolio.
"""

from __future__ import annotations

from collections import deque
from random import Random
from typing import Any

from atlas.core.analytics.artifacts import Artifact, ArtifactType
from atlas.core.analytics.modules.base import AnalysisModule, ArtifactPublisher, SimulationTickContext


class PortfolioStockSimulationModule(AnalysisModule):
    module_id = "portfolio_stock_simulation"
    title = "Portfolio/Stock Simulation"
    description = "Publishes stock/portfolio simulation artifacts based on selected mode."

    def __init__(self, seed: int = 41, max_points: int = 240) -> None:
        self._rng = Random(seed)
        self._stock_history: deque[tuple[int, float]] = deque(maxlen=max_points)
        self._stock_return_history: deque[float] = deque(maxlen=max_points)
        self._equity_history: deque[tuple[int, float]] = deque(maxlen=max_points)
        self._stock_cursor = 0
        self._stock_ticker = ""
        self._stock_candle_fingerprint = ""

    @staticmethod
    def _coerce_positions(raw: Any) -> list[dict[str, float | str]]:
        if not isinstance(raw, list):
            return []
        positions: list[dict[str, float | str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol", "")).strip().upper()
            if not symbol:
                continue
            qty = float(item.get("qty", 0) or 0)
            avg_price = float(item.get("avg_price", 0) or 0)
            current_price = float(item.get("current_price", avg_price) or avg_price)
            if qty <= 0 or current_price <= 0:
                continue
            positions.append(
                {
                    "symbol": symbol,
                    "qty": qty,
                    "avg_price": avg_price,
                    "current_price": current_price,
                }
            )
        return positions

    @staticmethod
    def _coerce_stock_candles(raw: Any) -> list[dict[str, float | str]]:
        if not isinstance(raw, list):
            return []
        candles: list[dict[str, float | str]] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                open_price = float(item.get("open", 0) or 0)
                high_price = float(item.get("high", 0) or 0)
                low_price = float(item.get("low", 0) or 0)
                close_price = float(item.get("close", 0) or 0)
                volume = float(item.get("volume", 0) or 0)
            except Exception:
                continue
            if open_price <= 0 or high_price <= 0 or low_price <= 0 or close_price <= 0:
                continue
            candles.append(
                {
                    "time": str(item.get("time", "")),
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                }
            )
        return candles

    @staticmethod
    def _build_histogram_from_returns(returns: list[float]) -> tuple[list[str], list[float]]:
        labels = ["<-2%", "-2..-1%", "-1..0%", "0..1%", "1..2%", ">2%"]
        if not returns:
            return labels, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

        buckets = [0, 0, 0, 0, 0, 0]
        for value in returns:
            pct = value * 100.0
            if pct < -2:
                buckets[0] += 1
            elif pct < -1:
                buckets[1] += 1
            elif pct < 0:
                buckets[2] += 1
            elif pct < 1:
                buckets[3] += 1
            elif pct < 2:
                buckets[4] += 1
            else:
                buckets[5] += 1

        return labels, [float(value) for value in buckets]

    def _simulate_stock(self, context: SimulationTickContext, publish: ArtifactPublisher) -> None:
        inputs = context.inputs
        ticker = str(inputs.get("ticker", "SPY")).upper()
        base_price = float(inputs.get("seed_price", 100.0) or 100.0)

        candles = self._coerce_stock_candles(inputs.get("stock_candles", []))
        candles_fingerprint = str(inputs.get("stock_candles_fingerprint", ""))

        ticker_changed = ticker != self._stock_ticker
        candle_set_changed = candles_fingerprint != self._stock_candle_fingerprint
        if ticker_changed or candle_set_changed:
            self._stock_cursor = 0
            self._stock_history.clear()
            self._stock_return_history.clear()
            self._stock_ticker = ticker
            self._stock_candle_fingerprint = candles_fingerprint

        if candles:
            cursor = min(self._stock_cursor, len(candles) - 1)
            candle = candles[cursor]
            new_price = float(candle["close"])
            candle_label = str(candle.get("time", f"idx-{cursor}"))
            source = "real_candle"

            self._stock_cursor += 1
            if self._stock_cursor >= len(candles):
                self._stock_cursor = 0
                publish(
                    Artifact(
                        artifact_type=ArtifactType.EVENT,
                        title="Stock Candle Replay Restarted",
                        module_id=self.module_id,
                        payload={
                            "message": f"{ticker} candle replay reached end and restarted from first candle",
                            "severity": "info",
                        },
                        tags=["stock", "event", "replay"],
                        published_by=self.module_id,
                        tick=context.tick,
                    )
                )
        else:
            if self._stock_history:
                last_price = self._stock_history[-1][1]
            else:
                last_price = base_price

            drift = 0.0006
            noise = self._rng.uniform(-0.02, 0.02)
            new_price = max(1.0, last_price * (1.0 + drift + noise))
            candle_label = f"tick-{context.tick}"
            source = "synthetic_fallback"
            candle = None

        self._stock_history.append((context.tick, round(new_price, 4)))

        returns = 0.0
        if len(self._stock_history) > 1:
            returns = (new_price / self._stock_history[-2][1]) - 1.0
            self._stock_return_history.append(returns)

        recent_returns = list(self._stock_return_history)[-60:]
        bins, counts = self._build_histogram_from_returns(recent_returns)

        publish(
            Artifact(
                artifact_type=ArtifactType.SCALAR,
                title=f"{ticker} Price",
                module_id=self.module_id,
                payload={
                    "value": round(new_price, 2),
                    "unit": "USD",
                    "min": 0.0,
                    "max": max(1.0, round(new_price * 2.5, 2)),
                    "threshold": round(base_price, 2),
                    "status": "up" if returns >= 0 else "down",
                },
                tags=["stock", "scalar", ticker, source],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.TIMESERIES,
                title=f"{ticker} Price Path",
                module_id=self.module_id,
                payload={
                    "points": [
                        {"x": tick, "y": price, "series": ticker}
                        for tick, price in self._stock_history
                    ],
                    "x_label": "tick",
                    "y_label": "price",
                },
                tags=["stock", "timeseries", ticker, source],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.HISTOGRAM,
                title=f"{ticker} Return Distribution",
                module_id=self.module_id,
                payload={
                    "bins": bins,
                    "counts": counts,
                    "unit": "count",
                },
                tags=["stock", "histogram", ticker, source],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        if candle is not None:
            recent_window = candles[max(0, cursor - 7): cursor + 1]
            publish(
                Artifact(
                    artifact_type=ArtifactType.TABLE,
                    title=f"{ticker} Recent Candles",
                    module_id=self.module_id,
                    payload={
                        "columns": ["Date", "Open", "High", "Low", "Close", "Volume"],
                        "rows": [
                            [
                                str(c["time"]),
                                round(float(c["open"]), 2),
                                round(float(c["high"]), 2),
                                round(float(c["low"]), 2),
                                round(float(c["close"]), 2),
                                int(float(c["volume"])),
                            ]
                            for c in recent_window
                        ],
                    },
                    tags=["stock", "table", ticker, source],
                    published_by=self.module_id,
                    tick=context.tick,
                )
            )

        if candle is not None:
            publish(
                Artifact(
                    artifact_type=ArtifactType.LOG,
                    title="Stock Simulation Log",
                    module_id=self.module_id,
                    payload={
                        "message": (
                            f"mode=stock source=real ticker={ticker} date={candle_label} "
                            f"close={new_price:.2f} ret={returns * 100.0:.2f}%"
                        ),
                        "values": {
                            "ticker": ticker,
                            "source": source,
                            "date": candle_label,
                            "close": round(new_price, 4),
                            "return_pct": round(returns * 100.0, 4),
                            "open": round(float(candle["open"]), 4),
                            "high": round(float(candle["high"]), 4),
                            "low": round(float(candle["low"]), 4),
                            "volume": int(float(candle["volume"])),
                        },
                    },
                    tags=["stock", "log", source],
                    published_by=self.module_id,
                    tick=context.tick,
                )
            )
        else:
            publish(
                Artifact(
                    artifact_type=ArtifactType.LOG,
                    title="Stock Simulation Log",
                    module_id=self.module_id,
                    payload={
                        "message": (
                            f"mode=stock source=synthetic ticker={ticker} tick={context.tick} "
                            f"price={new_price:.2f} ret={returns * 100.0:.2f}%"
                        ),
                        "values": {
                            "ticker": ticker,
                            "source": source,
                            "price": round(new_price, 4),
                            "return_pct": round(returns * 100.0, 4),
                        },
                    },
                    tags=["stock", "log", source],
                    published_by=self.module_id,
                    tick=context.tick,
                )
            )

    def _simulate_portfolio(self, context: SimulationTickContext, publish: ArtifactPublisher) -> None:
        inputs = context.inputs
        positions = self._coerce_positions(inputs.get("positions", []))
        if not positions:
            publish(
                Artifact(
                    artifact_type=ArtifactType.LOG,
                    title="Portfolio Simulation Log",
                    module_id=self.module_id,
                    payload={"message": "mode=portfolio skipped: no valid positions provided"},
                    tags=["portfolio", "log"],
                    published_by=self.module_id,
                    tick=context.tick,
                )
            )
            return

        total_equity = sum(float(item["qty"]) * float(item["current_price"]) for item in positions)
        drift = self._rng.uniform(-0.015, 0.02)
        simulated_equity = max(100.0, total_equity * (1.0 + drift))
        self._equity_history.append((context.tick, round(simulated_equity, 2)))

        rows: list[list[float | str]] = []
        top_weight = 0.0
        for item in positions:
            weight = (float(item["qty"]) * float(item["current_price"])) / max(1e-9, total_equity)
            top_weight = max(top_weight, weight)
            rows.append(
                [
                    str(item["symbol"]),
                    round(float(item["qty"]), 4),
                    round(float(item["avg_price"]), 2),
                    round(float(item["current_price"]), 2),
                    round(weight * 100.0, 2),
                ]
            )
        rows.sort(key=lambda row: float(row[4]), reverse=True)

        concentration = top_weight * 100.0
        status = "normal"
        severity = "info"
        if concentration >= 50:
            status = "warning"
            severity = "warning"
        if concentration >= 65:
            status = "critical"
            severity = "error"

        publish(
            Artifact(
                artifact_type=ArtifactType.SCALAR,
                title="Portfolio Concentration",
                module_id=self.module_id,
                payload={
                    "value": round(concentration, 2),
                    "unit": "%",
                    "min": 0.0,
                    "max": 100.0,
                    "threshold": 50.0,
                    "status": status,
                },
                tags=["portfolio", "scalar", "risk"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.TIMESERIES,
                title="Portfolio Equity Path",
                module_id=self.module_id,
                payload={
                    "points": [
                        {"x": tick, "y": equity, "series": "equity"}
                        for tick, equity in self._equity_history
                    ],
                    "x_label": "tick",
                    "y_label": "equity",
                },
                tags=["portfolio", "timeseries"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.TABLE,
                title="Portfolio Weights",
                module_id=self.module_id,
                payload={
                    "columns": ["Symbol", "Qty", "Avg Price", "Current Price", "Weight (%)"],
                    "rows": rows,
                },
                tags=["portfolio", "table"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        publish(
            Artifact(
                artifact_type=ArtifactType.LOG,
                title="Portfolio Simulation Log",
                module_id=self.module_id,
                payload={
                    "message": (
                        f"mode=portfolio tick={context.tick} equity={simulated_equity:.2f} "
                        f"concentration={concentration:.2f}% positions={len(rows)}"
                    ),
                    "values": {
                        "simulated_equity": round(simulated_equity, 2),
                        "concentration_pct": round(concentration, 2),
                        "positions": len(rows),
                    },
                },
                tags=["portfolio", "log"],
                published_by=self.module_id,
                tick=context.tick,
            )
        )

        if severity != "info":
            publish(
                Artifact(
                    artifact_type=ArtifactType.EVENT,
                    title="Portfolio Concentration Alert",
                    module_id=self.module_id,
                    payload={
                        "message": f"Top position concentration reached {concentration:.2f}%",
                        "severity": severity,
                    },
                    tags=["portfolio", "alert"],
                    published_by=self.module_id,
                    tick=context.tick,
                )
            )

    def on_tick(self, context: SimulationTickContext, publish: ArtifactPublisher) -> None:
        mode = str(context.inputs.get("mode", "stock")).strip().lower()
        if mode == "portfolio":
            self._simulate_portfolio(context, publish)
        else:
            self._simulate_stock(context, publish)
