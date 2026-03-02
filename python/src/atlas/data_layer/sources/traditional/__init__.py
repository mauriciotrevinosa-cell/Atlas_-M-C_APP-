"""
Traditional Market Data Sources
================================
Providers for equities, ETFs, indices, forex via standard APIs.

Copyright (c) 2026 M&C. All rights reserved.
"""

from atlas.data_layer.sources.traditional.yahoo_provider import YahooFinanceProvider

__all__ = ["YahooFinanceProvider"]

# Polygon is optional (requires API key)
try:
    from atlas.data_layer.sources.traditional.polygon_provider import PolygonProvider
    __all__.append("PolygonProvider")
except ImportError:
    pass
