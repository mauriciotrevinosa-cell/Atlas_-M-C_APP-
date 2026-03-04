"""
Atlas Providers
===============
Top-level provider wrappers for data access.

  YFinanceProvider  — Yahoo Finance (yfinance), live network
  CacheProvider     — Disk cache (Parquet), fully offline

Use DataRouter (atlas.data_router) as the unified entry point rather than
instantiating providers directly.
"""

from atlas.providers.yfinance_provider import YFinanceProvider, NetworkUnavailableError
from atlas.providers.cache_provider import CacheProvider

__all__ = ["YFinanceProvider", "CacheProvider", "NetworkUnavailableError"]
