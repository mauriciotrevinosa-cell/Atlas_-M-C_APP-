from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence

import numpy as np
import pandas as pd

from atlas.data_layer.cache_store import CacheStore
from atlas.data_layer.manager import DataManager
from atlas.data_layer.normalize import normalize_ohlcv
from atlas.data_layer.quality.validator import DataValidator

logger = logging.getLogger("atlas.market_finance.data")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_symbol(symbol: str) -> str:
    return (
        symbol.strip()
        .upper()
        .replace("/", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )


@dataclass(slots=True)
class DataPayload:
    symbol: str
    frame: pd.DataFrame
    metadata: Dict[str, Any]
    cache_key: str
    cache_hit: bool
    source: str
    files: Dict[str, str]


class DataRouter:
    """
    Phase 1 data router with provider priority, cache, PIT metadata and offline fallback.
    """

    def __init__(
        self,
        provider_priority: Optional[Sequence[str]] = None,
        cache_dir: str = "data/cache/market_finance",
        cache_ttl_hours: int = 24,
    ) -> None:
        self.provider_priority = list(provider_priority or ("yahoo", "polygon", "ccxt"))
        self.cache = CacheStore(cache_dir=cache_dir, ttl_hours=cache_ttl_hours)
        self.manager = DataManager(enable_cache=False, enable_validation=False)
        self.validator = DataValidator()

    def get_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1d",
        as_of: Optional[str] = None,
        provider_priority: Optional[Sequence[str]] = None,
        run_dir: Optional[Path] = None,
        use_cache: bool = True,
        allow_stale_cache: bool = True,
    ) -> DataPayload:
        symbol = safe_symbol(symbol)
        provider_order = list(provider_priority or self.provider_priority)
        as_of_utc = as_of or utc_now_iso()
        cache_key = f"phase1_{symbol}_{start_date}_{end_date}_{interval}"

        if use_cache:
            cached = self.cache.get_with_meta(cache_key, allow_stale=False)
            if cached is not None:
                frame, cache_meta = cached
                prepared = self._prepare_frame(frame)
                metadata = self._build_metadata(
                    symbol=symbol,
                    frame=prepared,
                    provider="cache",
                    cache_key=cache_key,
                    as_of_utc=as_of_utc,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    cache_hit=True,
                    offline_fallback=False,
                    provider_errors={},
                    cache_meta=cache_meta,
                )
                files = self._write_run_files(run_dir, symbol, prepared, metadata)
                return DataPayload(
                    symbol=symbol,
                    frame=prepared,
                    metadata=metadata,
                    cache_key=cache_key,
                    cache_hit=True,
                    source="cache",
                    files=files,
                )

        stale_cache: Optional[tuple[pd.DataFrame, Dict[str, Any]]] = None
        if use_cache and allow_stale_cache:
            stale_cache = self.cache.get_with_meta(cache_key, allow_stale=True)

        provider_errors: Dict[str, str] = {}
        for provider in provider_order:
            try:
                raw_df = self.manager.get_historical(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    provider=provider,
                    use_cache=False,
                )
                if raw_df is None or raw_df.empty:
                    provider_errors[provider] = "empty_dataset"
                    continue

                frame = self._prepare_frame(raw_df)
                metadata = self._build_metadata(
                    symbol=symbol,
                    frame=frame,
                    provider=provider,
                    cache_key=cache_key,
                    as_of_utc=as_of_utc,
                    start_date=start_date,
                    end_date=end_date,
                    interval=interval,
                    cache_hit=False,
                    offline_fallback=False,
                    provider_errors=provider_errors,
                    cache_meta=None,
                )

                if use_cache:
                    self.cache.set(
                        cache_key,
                        frame,
                        metadata={
                            "symbol": symbol,
                            "provider": provider,
                            "as_of_utc": as_of_utc,
                            "pit_version": metadata["pit"]["version"],
                            "dataset_hash": metadata["pit"]["dataset_hash"],
                        },
                    )

                files = self._write_run_files(run_dir, symbol, frame, metadata)
                return DataPayload(
                    symbol=symbol,
                    frame=frame,
                    metadata=metadata,
                    cache_key=cache_key,
                    cache_hit=False,
                    source=provider,
                    files=files,
                )
            except Exception as exc:  # pragma: no cover - network/provider dependent
                provider_errors[provider] = str(exc)

        if stale_cache is not None:
            frame, cache_meta = stale_cache
            prepared = self._prepare_frame(frame)
            metadata = self._build_metadata(
                symbol=symbol,
                frame=prepared,
                provider="cache",
                cache_key=cache_key,
                as_of_utc=as_of_utc,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                cache_hit=True,
                offline_fallback=True,
                provider_errors=provider_errors,
                cache_meta=cache_meta,
            )
            files = self._write_run_files(run_dir, symbol, prepared, metadata)
            return DataPayload(
                symbol=symbol,
                frame=prepared,
                metadata=metadata,
                cache_key=cache_key,
                cache_hit=True,
                source="cache_stale",
                files=files,
            )

        raise RuntimeError(
            "Data fetch failed for symbol "
            f"{symbol}. Providers attempted: {provider_order}. Errors: {provider_errors}"
        )

    def get_many(
        self,
        symbols: Iterable[str],
        start_date: str,
        end_date: str,
        interval: str = "1d",
        as_of: Optional[str] = None,
        provider_priority: Optional[Sequence[str]] = None,
        run_dir: Optional[Path] = None,
        use_cache: bool = True,
        allow_stale_cache: bool = True,
    ) -> Dict[str, DataPayload]:
        outputs: Dict[str, DataPayload] = {}
        for symbol in symbols:
            payload = self.get_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                interval=interval,
                as_of=as_of,
                provider_priority=provider_priority,
                run_dir=run_dir,
                use_cache=use_cache,
                allow_stale_cache=allow_stale_cache,
            )
            outputs[payload.symbol] = payload
        return outputs

    def _prepare_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        normalized = normalize_ohlcv(frame)
        if normalized.empty:
            return normalized

        idx = pd.to_datetime(normalized.index, utc=True)
        normalized.index = idx
        normalized.index.name = "timestamp_utc"
        normalized = normalized.sort_index()
        normalized = normalized[~normalized.index.duplicated(keep="first")]

        numeric_columns = ["open", "high", "low", "close", "volume"]
        for col in numeric_columns:
            normalized[col] = pd.to_numeric(normalized[col], errors="coerce")

        normalized[["open", "high", "low", "close"]] = normalized[
            ["open", "high", "low", "close"]
        ].ffill(limit=2)
        normalized["volume"] = normalized["volume"].fillna(0.0)

        return normalized.dropna(subset=["open", "high", "low", "close"])

    def _build_metadata(
        self,
        symbol: str,
        frame: pd.DataFrame,
        provider: str,
        cache_key: str,
        as_of_utc: str,
        start_date: str,
        end_date: str,
        interval: str,
        cache_hit: bool,
        offline_fallback: bool,
        provider_errors: Dict[str, str],
        cache_meta: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        validation = self.validator.validate(frame)
        integrity = self._integrity_report(frame, start_date=start_date, end_date=end_date, interval=interval)
        dataset_hash = self._dataset_hash(frame)

        return {
            "symbol": symbol,
            "provider": provider,
            "interval": interval,
            "as_of_utc": as_of_utc,
            "fetched_at_utc": utc_now_iso(),
            "date_range": {
                "start": str(frame.index.min()) if len(frame) else None,
                "end": str(frame.index.max()) if len(frame) else None,
            },
            "rows": int(len(frame)),
            "timezone": "UTC",
            "pit": {
                "version": "v1",
                "dataset_hash": dataset_hash,
                "as_of_utc": as_of_utc,
            },
            "cache": {
                "enabled": True,
                "key": cache_key,
                "hit": cache_hit,
                "stale": bool((cache_meta or {}).get("stale", False)),
                "metadata": cache_meta or {},
            },
            "offline_fallback": offline_fallback,
            "provider_attempt_errors": provider_errors,
            "validation": validation,
            "integrity": integrity,
        }

    def _integrity_report(
        self,
        frame: pd.DataFrame,
        start_date: str,
        end_date: str,
        interval: str,
        split_threshold: float = 0.35,
    ) -> Dict[str, Any]:
        if frame.empty:
            return {
                "nan_ratio": 1.0,
                "nan_by_column": {},
                "gap_count": 0,
                "gap_ratio": 0.0,
                "split_candidates": [],
                "trading_calendar": "none",
                "expected_bars": 0,
                "observed_bars": 0,
            }

        nan_by_col = {k: int(v) for k, v in frame.isna().sum().to_dict().items()}
        nan_ratio = float(frame.isna().sum().sum() / (len(frame) * len(frame.columns)))

        split_candidates = (
            frame["close"].pct_change().abs().loc[lambda s: s > split_threshold].index
        )
        split_dates = [ts.isoformat() for ts in split_candidates[:25]]

        expected_bars = len(frame)
        gap_count = 0
        trading_calendar = "inferred"

        if interval == "1d":
            expected_idx = pd.bdate_range(start=start_date, end=end_date, tz="UTC")
            observed_idx = pd.DatetimeIndex(frame.index).normalize().unique()
            missing = expected_idx.difference(observed_idx)
            expected_bars = int(len(expected_idx))
            gap_count = int(len(missing))
            trading_calendar = "weekday_business_day"
        else:
            expected_delta = self._interval_delta(interval)
            if expected_delta is not None and len(frame) > 1:
                diffs = frame.index.to_series().diff().dropna()
                gap_count = int((diffs > (expected_delta * 1.5)).sum())

        gap_ratio = float(gap_count / max(expected_bars, 1))

        return {
            "nan_ratio": round(nan_ratio, 6),
            "nan_by_column": nan_by_col,
            "gap_count": gap_count,
            "gap_ratio": round(gap_ratio, 6),
            "split_candidates": split_dates,
            "trading_calendar": trading_calendar,
            "expected_bars": expected_bars,
            "observed_bars": int(len(frame)),
        }

    def _dataset_hash(self, frame: pd.DataFrame) -> str:
        payload = {
            "index": [ts.isoformat() for ts in frame.index],
            "close": [round(float(v), 10) for v in frame["close"].tolist()],
            "volume": [round(float(v), 10) for v in frame["volume"].tolist()],
        }
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:16]

    def _interval_delta(self, interval: str) -> Optional[pd.Timedelta]:
        mapping = {
            "1m": pd.Timedelta(minutes=1),
            "5m": pd.Timedelta(minutes=5),
            "15m": pd.Timedelta(minutes=15),
            "30m": pd.Timedelta(minutes=30),
            "1h": pd.Timedelta(hours=1),
            "1d": pd.Timedelta(days=1),
            "1wk": pd.Timedelta(days=7),
        }
        return mapping.get(interval)

    def _write_run_files(
        self,
        run_dir: Optional[Path],
        symbol: str,
        frame: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> Dict[str, str]:
        if run_dir is None:
            return {}

        symbol_dir = run_dir / "data" / safe_symbol(symbol)
        symbol_dir.mkdir(parents=True, exist_ok=True)

        data_path = symbol_dir / "dataset.csv"
        metadata_path = symbol_dir / "metadata.json"

        frame.to_csv(data_path, index=True)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return {
            "dataset_csv": str(data_path.resolve()),
            "metadata_json": str(metadata_path.resolve()),
        }
