# Atlas Operations Workspace

## Purpose

Atlas Operations is the common workflow layer used by both the manual web UI
and ARIA. It prevents the manual and AI-assisted experiences from becoming two
independent systems.

## Truth contract

Every visible workflow step returns:

- `status`: `live`, `cached`, `degraded`, `unavailable`, or `skipped`.
- `data`: structured output, or `null` when unavailable.
- `source`: the handler/provider that produced the result.
- `mode`: `LIVE`, `MANUAL`, `PAPER`, `SIMULATION`, or `DEMO`.
- `updated_at`: timestamp for the result.
- `error`: explicit failure detail; never replaced silently with demo data.

## Shared controls

Manual control is exposed in the React dashboard and through
`/api/operations/*`. ARIA uses the `atlas_operations_workflow` tool. Both use
the same SQLite store and `OperationsEngine`.

ARIA proposals are persisted as `draft` and return
`requires_human_review: true`. A proposal does not execute automatically.

## Current vertical slice

`symbol-due-diligence-v1` runs real market data through market-state,
indicator, and risk analysis. The user can change symbol/timeframe, disable
steps, save a new workflow version, execute it, and inspect source/error/output
for each step.

## API

- `GET /api/operations/handlers`
- `GET /api/operations/workflows`
- `POST /api/operations/workflows`
- `PATCH /api/operations/workflows/{workflow_id}`
- `POST /api/operations/workflows/{workflow_id}/runs`
- `GET /api/operations/runs/{run_id}`

## Next increments

1. Add portfolio-risk, scenario, signals, Monte Carlo, and report handlers.
2. Add explicit input mappings between step outputs and later steps.
3. Add approval, retry, cancellation, and waiting states.
4. Add artifacts linked by workflow/run/step IDs.
5. Add ARIA planning through registered handlers with validation before save.
6. Add DAG execution only after sequential workflows are reliable.
