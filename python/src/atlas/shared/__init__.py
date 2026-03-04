"""
Atlas Shared Utilities
======================
Cross-cutting concerns: asset classification, registry, helpers.
"""

from atlas.shared.asset_registry import AssetRegistry, AssetInfo, get_registry

__all__ = ["AssetRegistry", "AssetInfo", "get_registry"]
