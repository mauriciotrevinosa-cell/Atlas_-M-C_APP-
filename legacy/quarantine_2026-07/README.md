# Quarantine — 2026-07 cleanup audit

Files moved here during the July 2026 cleanup because they are **dead code
confirmed by evidence**, kept (not deleted) per project policy. Nothing at
runtime imports or loads them.

| File | Came from | Why it's here |
|---|---|---|
| `data_layer/data_handler.py` | `python/src/atlas/data_layer/` | Imports `normalize_data`, which no longer exists in `normalize.py` (renamed to `normalize_ohlcv`). Module cannot be imported. Zero references in atlas/apps/tests. Superseded by the provider registry (`atlas.data_layer`). |
| `data_layer/yahoo.py` | `python/src/atlas/data_layer/sources/traditional/` | Same broken `normalize_data` import. Superseded by `yahoo_provider.py` in the same folder. Zero references. |
| `data_layer/normalize.py.bak` | `python/src/atlas/data_layer/` | Stale backup of the old normalize module (the only place `normalize_data` still existed). |
| `desktop_ui/real_estate.js` | `apps/desktop/` | 811-line older Real Estate view. `index.html` loads `realestate.js` (the newer 1,427-line version); nothing references `real_estate.js`. |

If any of these is ever needed again, restore it from here or from git
history (tag `pre-cleanup-2026-07-03`).
