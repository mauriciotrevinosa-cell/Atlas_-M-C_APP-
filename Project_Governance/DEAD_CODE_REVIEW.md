# Dead Code Review — `mmo.js`

**Date identified:** 2026-03-10
**File:** `apps/desktop/mmo.js` (~2600 lines)
**Status:** Pending human review before deletion

---

## Background

During the MMO Phase 3A–3B refactor the IIFE in `mmo.js` was significantly
extended. Due to the way JavaScript hoisting works inside a strict-mode IIFE,
duplicate `function` declarations in the same scope are legal — the last
declaration silently wins. Three function groups appear to be dead code
(shadowed by later, more complete definitions).

> **Do NOT delete blindly.** Verify with `git log -p` or a quick search to
> confirm nothing outside the IIFE references the early versions before
> removing them.

---

## Suspected Dead Code Regions

### 1. `_computeLocalQuantumState` — lines ~101–238

**Active version:** lines ~1484–1685 (Phase 3A/3B, full physics)
**Dead version:** lines ~101–238 (original, pre-Phase-3A)

**Differences:** The dead version lacks:
- CIR thermal coupling (`cir_temperature`, `beta_thermal`)
- WKB tunneling nodes (`tunneling_nodes`, `potential_field`)
- Quantum Fisher Information (`F_Q`, `cramer_rao_bound`)
- Probability current J (`j_flows`, `j_directional`)
- Berry phase γ and path integral distribution (Phase 3B)
- Non-Hermitian H_eff (Phase 3C)

**Confidence it is dead:** High — the active version at line 1484 was
added in commit `3c25df9` and is what `_normalizeQuantumState`,
`analyze()`, and `_loadScanner()` all delegate to.

---

### 2. `_buildView` — lines ~243–362

**Active version:** lines ~1835–1969 (current HTML layout with all Phase 3A-3C cards)
**Dead version:** lines ~243–362 (old layout, missing layer-detail card, berry card, etc.)

**Differences:** The dead version has an older HTML structure:
- Missing `mmo-layer-detail-card`
- Missing `mmo-berry-card`
- Missing entanglement card in bottom bar
- Old button labels without Unicode symbols

**Confidence it is dead:** High — `_init()` calls `_buildView()` which
resolves to the last definition in the IIFE.

---

### 3. `_startVacuumChamber` — lines ~582–724

**Active version:** lines ~1971–2225 (live, with `_vkRenderData`, focus modes, node groups, entanglement nodes)
**Dead version:** lines ~582–724 (original, simpler Three.js vacuum chamber)

**Differences:** The dead version lacks:
- `_vkRenderData` integration
- Focus-based camera targets (`structure`, `energy`, `thermal`, `surface`, `nodes`)
- Entanglement nodes (5 orbiting spheres with correlation lines)
- `_startVacuumChamber._syncNodes` hook
- `ResizeObserver` for responsive resizing

**Confidence it is dead:** High — both `_buildView()` versions call
`_startVacuumChamber()` and JS resolves it to the last definition.

---

## Recommended Deletion Procedure

```bash
# 1. Confirm active line ranges haven't shifted (check after any recent merge)
grep -n "function _computeLocalQuantumState\|function _buildView\|function _startVacuumChamber" \
  apps/desktop/mmo.js

# 2. Verify nothing external calls these by name (they are inner IIFE functions,
#    so external references are impossible — but double-check just in case)
grep -rn "_computeLocalQuantumState\|_startVacuumChamber" apps/desktop/ \
  --include="*.js" --include="*.html"

# 3. Delete lines using your editor with a known-good range, then:
node --check apps/desktop/mmo.js   # syntax check
# Open the app, run MMO.analyze('SPY') in the browser console, verify all panels load

# 4. Commit with message:
# chore(mmo): remove dead duplicate function declarations (~350 lines)
```

---

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|-----------|
| Accidentally deleting active code | Low | Line numbers confirmed, active versions are all later in the file |
| Breaking strict-mode behavior | None | Removing earlier duplicate is safe; last wins |
| Unexpected external caller | Very low | Functions are inside a strict IIFE, not exported |
| Regression in vacuum chamber | Low | Run `MMO.analyze('SPY')` smoke test after deletion |

---

## Estimated Line Savings

| Block | Approx. lines |
|-------|--------------|
| Dead `_computeLocalQuantumState` | ~137 |
| Dead `_buildView` | ~119 |
| Dead `_startVacuumChamber` | ~143 |
| **Total** | **~399 lines** |

---

*Identified by Claude Sonnet 4.6 during MMO Phase 3B development session.*
*Resolve before the next major refactor to keep the file manageable.*
