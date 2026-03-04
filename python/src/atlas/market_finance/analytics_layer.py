from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
import json
import logging
from pathlib import Path
from typing import Any, Dict, Mapping

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .data_layer import safe_symbol

logger = logging.getLogger("atlas.market_finance.analytics")


@dataclass(slots=True)
class AnalyticsResult:
    summary: Dict[str, Any]
    files: Dict[str, str]
    enriched_frames: Dict[str, pd.DataFrame]


class AnalyticsEngine:
    """Phase 1 analytics engine for reproducible run artifacts."""

    def analyze(
        self,
        market_data: Mapping[str, pd.DataFrame],
        run_dir: Path,
        vol_window: int = 20,
        corr_window: int = 20,
    ) -> AnalyticsResult:
        analytics_dir = run_dir / "analytics"
        analytics_dir.mkdir(parents=True, exist_ok=True)

        enriched_frames: Dict[str, pd.DataFrame] = {}
        symbol_summary: Dict[str, Any] = {}
        files: Dict[str, str] = {}

        for symbol, raw_df in market_data.items():
            if raw_df.empty:
                continue
            symbol_key = safe_symbol(symbol)
            df = raw_df.copy()

            df["simple_return"] = df["close"].pct_change()
            df["log_return"] = np.log(df["close"] / df["close"].shift(1))
            df["rolling_volatility"] = df["log_return"].rolling(vol_window).std() * np.sqrt(252)

            patterns = self._candlestick_patterns(df)
            df["doji"] = patterns["doji"]
            df["engulfing"] = patterns["engulfing"]

            enriched_frames[symbol_key] = df

            csv_path = analytics_dir / f"{symbol_key}_analytics.csv"
            df.to_csv(csv_path, index=True)
            files[f"{symbol_key}_analytics_csv"] = str(csv_path.resolve())

            symbol_summary[symbol_key] = {
                "rows": int(len(df)),
                "latest_simple_return": self._safe_float(df["simple_return"].iloc[-1]),
                "latest_log_return": self._safe_float(df["log_return"].iloc[-1]),
                "latest_rolling_volatility": self._safe_float(df["rolling_volatility"].iloc[-1]),
                "doji_count": int(df["doji"].sum()),
                "bullish_engulfing_count": int((df["engulfing"] == "bullish").sum()),
                "bearish_engulfing_count": int((df["engulfing"] == "bearish").sum()),
            }

        returns_df = pd.DataFrame(
            {symbol: frame["log_return"] for symbol, frame in enriched_frames.items()}
        ).dropna(how="all")

        corr_matrix = returns_df.corr() if not returns_df.empty else pd.DataFrame()
        corr_matrix_path = analytics_dir / "correlation_matrix.csv"
        corr_matrix.to_csv(corr_matrix_path, index=True)
        files["correlation_matrix_csv"] = str(corr_matrix_path.resolve())

        rolling_corr = self._rolling_correlations(returns_df, corr_window=corr_window)
        rolling_corr_path = analytics_dir / "rolling_correlations.csv"
        rolling_corr.to_csv(rolling_corr_path, index=False)
        files["rolling_correlations_csv"] = str(rolling_corr_path.resolve())

        heatmap_path = analytics_dir / "correlation_heatmap.png"
        self._render_heatmap(corr_matrix, heatmap_path)
        files["correlation_heatmap_png"] = str(heatmap_path.resolve())

        summary = {
            "symbols": sorted(list(enriched_frames.keys())),
            "vol_window": vol_window,
            "corr_window": corr_window,
            "rows_in_returns_panel": int(len(returns_df)),
            "symbol_summary": symbol_summary,
        }

        report_path = analytics_dir / "analytics_report.json"
        report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        files["analytics_report_json"] = str(report_path.resolve())

        return AnalyticsResult(summary=summary, files=files, enriched_frames=enriched_frames)

    def _rolling_correlations(self, returns_df: pd.DataFrame, corr_window: int) -> pd.DataFrame:
        if returns_df.empty or len(returns_df.columns) < 2:
            return pd.DataFrame(columns=["timestamp_utc", "symbol_a", "symbol_b", "rolling_corr"])

        rows = []
        for symbol_a, symbol_b in combinations(returns_df.columns, 2):
            corr_series = returns_df[symbol_a].rolling(corr_window).corr(returns_df[symbol_b])
            corr_series = corr_series.dropna()
            for timestamp, value in corr_series.items():
                rows.append(
                    {
                        "timestamp_utc": str(timestamp),
                        "symbol_a": symbol_a,
                        "symbol_b": symbol_b,
                        "rolling_corr": float(value),
                    }
                )
        return pd.DataFrame(rows)

    def _render_heatmap(self, corr_matrix: pd.DataFrame, output_path: Path) -> None:
        fig, ax = plt.subplots(figsize=(6, 5))

        if corr_matrix.empty:
            ax.text(0.5, 0.5, "No correlation data", ha="center", va="center")
            ax.set_axis_off()
        else:
            values = corr_matrix.values
            im = ax.imshow(values, cmap="coolwarm", vmin=-1.0, vmax=1.0)
            ax.set_xticks(np.arange(len(corr_matrix.columns)))
            ax.set_yticks(np.arange(len(corr_matrix.index)))
            ax.set_xticklabels(corr_matrix.columns, rotation=45, ha="right")
            ax.set_yticklabels(corr_matrix.index)
            for i in range(values.shape[0]):
                for j in range(values.shape[1]):
                    ax.text(j, i, f"{values[i, j]:.2f}", ha="center", va="center", fontsize=8)
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            ax.set_title("Correlation Heatmap")

        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)

    def _candlestick_patterns(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        body = (df["close"] - df["open"]).abs()
        candle_range = (df["high"] - df["low"]).replace(0, np.nan)

        doji = (body <= candle_range * 0.1).fillna(False)

        prev_open = df["open"].shift(1)
        prev_close = df["close"].shift(1)

        bullish = (
            (df["close"] > df["open"])
            & (prev_close < prev_open)
            & (df["close"] >= prev_open)
            & (df["open"] <= prev_close)
        )
        bearish = (
            (df["close"] < df["open"])
            & (prev_close > prev_open)
            & (df["open"] >= prev_close)
            & (df["close"] <= prev_open)
        )

        engulfing = pd.Series("none", index=df.index)
        engulfing.loc[bullish] = "bullish"
        engulfing.loc[bearish] = "bearish"

        return {"doji": doji.astype(bool), "engulfing": engulfing}

    def _safe_float(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
            return float(value)
        except Exception:
            return None
