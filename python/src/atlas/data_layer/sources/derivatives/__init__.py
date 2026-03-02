"""
Derivatives / Crypto Data Sources
==================================
Providers for cryptocurrency exchanges (spot + futures) via CCXT.

Copyright (c) 2026 M&C. All rights reserved.
"""

try:
    from atlas.data_layer.sources.derivatives.ccxt_provider import CCXTProvider
    __all__ = ["CCXTProvider"]
except ImportError:
    __all__ = []
