"""
Data Quality Validator
======================
Checks OHLCV data for common issues before it enters the Atlas pipeline.

Checks performed:
  1. NaN ratio — too many missing values
  2. Price spikes — unrealistic jumps (>50% in one candle)
  3. Volume anomalies — zero volume periods
  4. OHLC consistency — high >= low, high >= open/close, etc.
  5. Time gaps — missing candles in the series
  6. Duplicate timestamps

Copyright (c) 2026 M&C. All rights reserved.
"""

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger("atlas.data_layer")


class DataValidator:
    """
    Validate OHLCV DataFrame quality.

    Returns a report dict:
        {
            "is_valid": True/False,
            "total_rows": int,
            "issues": [...],
            "warnings": [...],
            "checks": {...}
        }

    An issue makes is_valid=False. A warning does not.
    """

    def __init__(
        self,
        max_nan_ratio: float = 0.05,
        max_spike_pct: float = 0.50,
        max_zero_volume_ratio: float = 0.20,
        max_gap_ratio: float = 0.10,
    ):
        """
        Args:
            max_nan_ratio:         Fail if NaN% exceeds this (default 5%)
            max_spike_pct:         Flag if price jumps > this % in one candle
            max_zero_volume_ratio: Warn if zero-volume candles exceed this ratio
            max_gap_ratio:         Warn if time gaps exceed this ratio
        """
        self.max_nan_ratio = max_nan_ratio
        self.max_spike_pct = max_spike_pct
        self.max_zero_volume_ratio = max_zero_volume_ratio
        self.max_gap_ratio = max_gap_ratio

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run all quality checks on a DataFrame.

        Args:
            df: Normalized OHLCV DataFrame

        Returns:
            Validation report dictionary
        """
        issues: List[str] = []
        warnings: List[str] = []
        checks: Dict[str, Any] = {}

        if df is None or df.empty:
            return {
                "is_valid": False,
                "total_rows": 0,
                "issues": ["DataFrame is empty"],
                "warnings": [],
                "checks": {},
            }

        total_rows = len(df)

        # --- Check 1: NaN ratio ---
        nan_counts = df.isna().sum()
        nan_ratio = nan_counts.sum() / (total_rows * len(df.columns))
        checks["nan_ratio"] = round(float(nan_ratio), 4)

        if nan_ratio > self.max_nan_ratio:
            issues.append(
                f"NaN ratio too high: {nan_ratio:.2%} "
                f"(max {self.max_nan_ratio:.2%}). "
                f"Columns: {nan_counts[nan_counts > 0].to_dict()}"
            )

        # --- Check 2: Price spikes ---
        if "close" in df.columns and total_rows > 1:
            returns = df["close"].pct_change().abs()
            spikes = returns[returns > self.max_spike_pct]
            checks["spike_count"] = len(spikes)

            if len(spikes) > 0:
                spike_dates = spikes.index.strftime("%Y-%m-%d").tolist()[:5]
                warnings.append(
                    f"Price spikes detected ({len(spikes)} candles > "
                    f"{self.max_spike_pct:.0%}): {spike_dates}"
                )

        # --- Check 3: OHLC consistency ---
        ohlc_issues = 0
        if all(c in df.columns for c in ["open", "high", "low", "close"]):
            # High should be >= Low
            bad_hl = (df["high"] < df["low"]).sum()
            # High should be >= Open and Close
            bad_ho = (df["high"] < df["open"]).sum()
            bad_hc = (df["high"] < df["close"]).sum()
            # Low should be <= Open and Close
            bad_lo = (df["low"] > df["open"]).sum()
            bad_lc = (df["low"] > df["close"]).sum()

            ohlc_issues = bad_hl + bad_ho + bad_hc + bad_lo + bad_lc
            checks["ohlc_inconsistencies"] = int(ohlc_issues)

            if ohlc_issues > 0:
                issues.append(
                    f"OHLC consistency violations: {ohlc_issues} rows "
                    f"(high<low={bad_hl}, high<open={bad_ho}, "
                    f"high<close={bad_hc}, low>open={bad_lo}, low>close={bad_lc})"
                )

        # --- Check 4: Zero volume ---
        if "volume" in df.columns:
            zero_vol = (df["volume"] == 0).sum()
            zero_vol_ratio = zero_vol / total_rows
            checks["zero_volume_ratio"] = round(float(zero_vol_ratio), 4)

            if zero_vol_ratio > self.max_zero_volume_ratio:
                warnings.append(
                    f"High zero-volume ratio: {zero_vol_ratio:.2%} "
                    f"({zero_vol} of {total_rows} candles)"
                )

        # --- Check 5: Duplicate timestamps ---
        dup_count = df.index.duplicated().sum()
        checks["duplicate_timestamps"] = int(dup_count)

        if dup_count > 0:
            issues.append(f"Duplicate timestamps found: {dup_count}")

        # --- Check 6: Time gaps ---
        if isinstance(df.index, pd.DatetimeIndex) and total_rows > 2:
            diffs = df.index.to_series().diff().dropna()
            if len(diffs) > 0:
                median_diff = diffs.median()
                # A "gap" is when diff > 3x the median interval
                gaps = diffs[diffs > median_diff * 3]
                gap_ratio = len(gaps) / total_rows
                checks["gap_ratio"] = round(float(gap_ratio), 4)
                checks["gap_count"] = len(gaps)

                if gap_ratio > self.max_gap_ratio:
                    warnings.append(
                        f"Time gaps detected: {len(gaps)} gaps "
                        f"({gap_ratio:.2%} of candles)"
                    )

        # --- Summary ---
        is_valid = len(issues) == 0

        report = {
            "is_valid": is_valid,
            "total_rows": total_rows,
            "issues": issues,
            "warnings": warnings,
            "checks": checks,
        }

        if not is_valid:
            logger.warning("Validation FAILED: %s", issues)
        elif warnings:
            logger.info("Validation PASSED with warnings: %s", warnings)
        else:
            logger.debug("Validation PASSED: %d rows clean", total_rows)

        return report
