# Agent Gateway Design

Last updated: 2026-05-11

Source of truth: `docs/ATLAS_MASTER_ROADMAP_2026_CONSOLIDATED.md`, Phase 2.

## Purpose

Atlas needs a controlled way for ARIA, Codex, Claude, desktop tools, and future
MCP clients to request work without receiving unrestricted backend access. The
Agent Gateway exposes a small, audited, paper-first API surface for data reads,
workspace writes, backtests, notifications, and tightly gated execution flows.

The gateway is not a trading engine and must not own deterministic risk,
portfolio, execution, or business rules. It routes requests to Atlas services,
enforces capability checks, records audit events, and returns job status or
artifacts.

## API Namespace: `/api/agent/v1`

All external-agent routes live under `/api/agent/v1`.

Planned route groups:

| Route | Method | Capability | Purpose |
| --- | --- | --- | --- |
| `/api/agent/v1/session` | `GET` | `R` | Inspect token scope, expiry, paper flag, and allowed capabilities. |
| `/api/agent/v1/data/query` | `POST` | `R` | Read market, macro, news, filings, or derived feature data through approved providers. |
| `/api/agent/v1/workspace/artifacts` | `POST` | `W` | Save reports, notes, charts, decision records, or run metadata. |
| `/api/agent/v1/backtests` | `POST` | `B` | Submit a backtest or simulation job. |
| `/api/agent/v1/jobs/{job_id}` | `GET` | `R` | Poll job status and summarized progress. |
| `/api/agent/v1/jobs/{job_id}/events` | `GET` | `R` | Stream job progress through SSE or WebSocket bridge. |
| `/api/agent/v1/jobs/{job_id}/artifacts` | `GET` | `R` | Fetch artifacts produced by an approved job. |
| `/api/agent/v1/notify` | `POST` | `N` | Send user-visible report, alert, or workflow notification. |
| `/api/agent/v1/trading/proposals` | `POST` | `T` | Create paper-only trade proposals for risk review. |
| `/api/agent/v1/admin/tokens` | `POST` | `C` | Issue or rotate scoped tokens; admin only. |

Live execution endpoints are intentionally excluded from v1. If added later,
they must require explicit live-trading enablement, human approval gates, broker
risk limits, and a separate production incident playbook.

## Scoped Tokens

Agent access uses scoped bearer tokens. Tokens must be revocable and short
lived by default.

Required token fields:

| Field | Meaning |
| --- | --- |
| `token_id` | Stable identifier used in audit logs; never log raw token secrets. |
| `subject` | Agent, user, service, or MCP client identity. |
| `capabilities` | Set of allowed capability letters. |
| `expires_at` | Hard expiration timestamp. |
| `paper_only` | Defaults to `true`; required for any `T` capability in v1. |
| `market_whitelist` | Allowed markets, venues, or data domains. |
| `asset_whitelist` | Allowed symbols, assets, or asset classes. |
| `rate_limit` | Requests and job submissions per minute/hour/day. |
| `job_limit` | Max concurrent async jobs and max runtime. |
| `artifact_scope` | Workspace paths or artifact collections the token can write. |
| `issued_by` | User or admin process that issued the token. |
| `revoked_at` | Optional revocation timestamp. |

Default token posture:

- `paper_only: true`
- no `C` capability
- no live broker credentials
- no unrestricted filesystem access
- explicit market and asset allowlists
- rate limits enforced before service dispatch

## Capability Model

Capability letters are intentionally compact so they can be carried in tokens,
audit logs, MCP metadata, and UI review screens.

| Capability | Name | Allowed actions |
| --- | --- | --- |
| `R` | Read | Query approved data, health, job status, and artifacts. |
| `W` | Workspace write | Save notes, reports, charts, run metadata, and decision logs. |
| `B` | Backtest/simulation | Submit and inspect simulations, backtests, scenario runs, and paper evaluations. |
| `N` | Notify/report | Emit user-visible notifications, reports, and alerts. |
| `C` | Credentials/admin | Create tokens, rotate secrets, inspect credential health, or change gateway policy. |
| `T` | Trading | Create trade proposals or paper orders only by default. Live trading is out of scope for v1. |

Capability checks are deny-by-default. A request must pass all relevant checks:
token validity, capability, paper flag, market whitelist, asset whitelist, rate
limit, job limit, and route-specific policy.

## Paper-Only Defaults

The gateway must assume advisory and paper behavior unless a future governance
process explicitly enables live execution.

Required defaults:

- `T` capability cannot place live orders in v1.
- Paper proposals must go through existing risk and portfolio guardrails.
- Backtests and simulations cannot mutate live portfolio state.
- MCP tools expose read/backtest functions first, not live execution.
- UI labels and audit events must distinguish paper proposals from live actions.
- Any live-trading expansion requires a new design review and verification plan.

## Audit Log

Every agent call creates an immutable audit event before dispatch and updates
that event after completion.

Minimum audit fields:

| Field | Meaning |
| --- | --- |
| `audit_id` | Unique event id. |
| `timestamp` | Request receive time. |
| `token_id` | Scoped token identifier. |
| `subject` | Agent or user identity. |
| `route` | API route and method. |
| `capability_requested` | Capability required by the route. |
| `capability_result` | Allowed or denied, with reason. |
| `paper_only` | Effective paper flag. |
| `market_scope` | Markets touched by the request. |
| `asset_scope` | Assets touched by the request. |
| `request_hash` | Hash of normalized request body. |
| `job_id` | Async job id, when applicable. |
| `artifact_ids` | Produced artifacts or reports. |
| `status_code` | Final response code. |
| `duration_ms` | Request duration. |
| `error_code` | Stable error code for failures. |

Audit records should be queryable by token, subject, job, artifact, market,
asset, capability, and time range. Raw credentials, token secrets, and broker
secrets must never be written to audit logs.

## Async Jobs

Backtests, simulations, research runs, report generation, and long data pulls
use an async job model.

Job lifecycle:

1. Client submits a job request.
2. Gateway validates token, capabilities, paper flag, scope, and rate limits.
3. Gateway writes an audit event and creates a queued job.
4. Worker executes through Atlas services, not agent-provided code.
5. Client polls `/jobs/{job_id}` or streams `/jobs/{job_id}/events`.
6. Worker writes artifacts to the artifact registry.
7. Gateway exposes completed artifacts according to token scope.

Job states:

- `queued`
- `running`
- `waiting_for_approval`
- `completed`
- `failed`
- `cancelled`
- `expired`

Each job must have a max runtime, cancellation path, progress events, structured
error code, and artifact manifest. Jobs created with paper-only tokens cannot
write live portfolio or broker state.

## MCP Read/Backtest Boundary

The MCP server should be a client of `/api/agent/v1`, not a privileged bypass.
Initial MCP exposure is limited to read and backtest tools.

Allowed MCP tools in the first milestone:

| MCP tool | Gateway route | Capability |
| --- | --- | --- |
| `atlas.session.inspect` | `/session` | `R` |
| `atlas.data.query` | `/data/query` | `R` |
| `atlas.backtest.submit` | `/backtests` | `B` |
| `atlas.job.status` | `/jobs/{job_id}` | `R` |
| `atlas.job.events` | `/jobs/{job_id}/events` | `R` |
| `atlas.artifact.get` | `/jobs/{job_id}/artifacts` | `R` |

Explicit MCP exclusions:

- no live order placement
- no credential creation or rotation
- no unrestricted workspace writes
- no direct database writes
- no filesystem mutation outside approved artifact scopes
- no bypass of risk, portfolio, or execution services

MCP backtests must return persisted job ids and artifact references, not only
chat text. This keeps ARIA, Codex, Claude, and other clients aligned around
deterministic Atlas artifacts.

## Verification

Implementation should not start until these verification paths are accepted:

- Token tests for allowed, denied, expired, revoked, over-rate, out-of-market,
  and out-of-asset requests.
- Capability matrix tests covering `R`, `W`, `B`, `N`, `C`, and `T`.
- Paper-only tests proving `T` cannot place live orders in v1.
- Audit tests proving every allowed and denied request records an event without
  secrets.
- Async job tests for submit, poll, stream, complete, fail, cancel, expire, and
  artifact access.
- MCP boundary tests proving MCP can read and submit backtests but cannot access
  credentials, live trading, direct DB writes, or unrestricted filesystem paths.
- Backtest artifact tests proving results are persisted and retrievable through
  scoped access.
- Governance review confirming any future live-trading expansion has a separate
  design, human approval, broker risk limits, and rollback plan.

Milestone acceptance: Codex, Claude, or ARIA can request a backtest through a
scoped token, receive job status, stream progress, and fetch artifacts without
touching live execution.
