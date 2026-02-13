# OCI Cost Manager

OCI Cost Manager is a FinOps-oriented cloud cost governance product for OCI workloads.

## What This Product Is
- Decision-first cost analytics (Dashboard, Costs, Movers, Top Drivers).
- Governance layer (allocation confidence, ownership dimensions, tag coverage).
- Action engine with approvals, dry-run executors, and full audit history.
- Budget guardrails with forecast narratives and notifications.
- Audit-grade exports (XLSX + manifest + validation).

## What This Product Is Not
- Not an auto-remediation system by default.
- Not a replacement for OCI native billing exports.
- Not a general SIEM/CMDB platform.

## Deployment Modes
- Local dev: Vite + FastAPI.
- Docker Compose: frontend + backend + persistent volumes.
- Demo mode: read-only UX with executor blocking for safe walkthroughs.

## Environment Setup
- Copy `.env.example` to `.env`.
- Fill real values in `.env` only (never commit `.env`).
- Keep OCI credentials outside git (for example mounted in `/home/app/.oci/config`).

## Safety Philosophy
- Additive API evolution only.
- Approval-first actions; destructive flows require explicit confirmation + flags.
- RBAC + row-level scope filters for enterprise tenancy segmentation.
- Feature flags gate risky capabilities.

## Runtime Hardening (Phase 7)
- Non-root containers.
- Read-only root filesystems where possible.
- Dropped Linux capabilities + `no-new-privileges`.
- Internal-only backend network exposure through frontend reverse proxy.
- Health probes: `/api/v1/health/live`, `/api/v1/health/ready`.

## Backup / Restore (SQLite)
- Script: `src/backend/scripts/db_backup_restore.py`
- Backup example:
  - `python src/backend/scripts/db_backup_restore.py backup --db src/backend/oci_cost_manager.db --out ./backups`
- Restore example:
  - `python src/backend/scripts/db_backup_restore.py restore --file ./backups/<file>.db --db src/backend/oci_cost_manager.db`

## Optional Postgres Path (Documented)
- Current default is SQLite for fast deployment.
- Migration path to Postgres is supported architecturally (SQLAlchemy models/routes are DB-agnostic).
- Recommended for HA and larger retention windows.

## Phase 3: Aggregates + Cached Cost Engine

This phase adds cache-first cost APIs that never call OCI in request threads:

- `GET /api/v1/cost/summary?range=prev_month|ytd|prev_year`
- `GET /api/v1/cost/by-service?range=...&limit=...`
- `GET /api/v1/cost/by-compartment?range=...&limit=...`
- `GET /api/v1/cost/by-resource?range=...&limit=...`

Fallback chain for all fast cost endpoints:

1. Redis cache
2. Snapshot table (`cost_snapshots`)
3. Aggregate tables

Degraded mode:

- If current aggregates are missing, API serves last snapshot with `meta.stale=true`
- UI should render stale banner and never blank page

Async refresh jobs:

- `POST /api/v1/jobs/aggregate_refresh`
- `POST /api/v1/jobs/snapshot_refresh`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/result`

Cache policy:

- Summary TTL: 5 minutes
- Breakdowns TTL: 1 hour
- Snapshot cache TTL: 1 hour
- Admin bust: `POST /api/v1/cache/bust`

Operational flow:

1. Bring up stack: `docker compose up -d`
2. Queue aggregate refresh: `POST /api/v1/jobs/aggregate_refresh`
3. Queue snapshot refresh: `POST /api/v1/jobs/snapshot_refresh`
4. Verify fast endpoint: `GET /api/v1/cost/summary?range=prev_month`
5. Confirm second call is cache hit via `meta.source=cache`

## Phase 4: OCI Diagnostics + Degraded Mode

Diagnostics is cache-first and non-blocking. Cost endpoints remain aggregate-only and never invoke OCI during page load.

Endpoints:

- `GET /api/v1/diagnostics`
- `POST /api/v1/jobs/diagnostics_refresh`
- `POST /api/v1/diagnostics/refresh` (compat trigger)
- `GET /api/v1/jobs/summary`

Diagnostics response model includes:

- `status`: `connected | partial | failed | degraded`
- `checks`: config/key/tenancy/identity/usage/cost reachability
- `last_sync_time`
- `checked_at`
- `mode`
- `message`

Degraded mode behavior:

- If OCI checks fail, API returns last known diagnostics and/or stale snapshot metadata.
- Dashboard/Costs continue to load from cache + aggregates (no blank states).
- UI global status bar shows OCI/DB/Worker/Reports status and last sync timestamp.

Examples:

```bash
curl -s http://localhost:8000/api/v1/diagnostics | jq .
```

```bash
curl -s -X POST http://localhost:8000/api/v1/jobs/diagnostics_refresh \
  -H "Content-Type: application/json" \
  -d '{"params":{}}' | jq .
```

## Phase 5: Structured Logging + Logs UI

Phase 5 introduces centralized classified logging with correlation propagation across frontend, backend API, and worker tasks.

Schema:

- `log_events` (types: `oci|backend|frontend|db|security|audit`)
- `audit_events` (governance actions)

API:

- `POST /api/v1/logs/frontend`
- `GET /api/v1/logs`
- `GET /api/v1/logs/{correlation_id}`
- `POST /api/v1/logs/export` (async, returns `202` + `job_id`)
- `GET /api/v1/logs/metrics/db`

Key behavior:

- `X-Correlation-Id` is accepted from client or generated by middleware and returned in response headers.
- API request completion and failures are logged with correlation IDs.
- Worker jobs log state transitions and inherit correlation IDs from queued job params.
- Cache bust and job triggers are tracked in audit logs.
- Frontend error telemetry is throttled and redacted before ingest.

Logs UI:

- New page `/logs` (admin + finops roles).
- Supports log type filter, level filter, text search, correlation lookup, and async export.

PgBouncer hotfix:

- Use `edoburu/pgbouncer:v1.25.1-p0`.
- Container internal listen port is `5432`; compose maps host `6432 -> 5432`.

## Neutral Comparison: Holori / Ternary
- Similar value categories:
  - Cost visibility and movers
  - Allocation/showback/governance
  - Optimization recommendations and budget controls
- OCI Cost Manager focus:
  - OCI-native workflow with explainable contracts and safe action gating
  - Lightweight deployment and explicit audit artifacts

## Core Docs
- Architecture overview: `y/architecture-overview.md`
- Feature matrix: `y/feature-matrix.md`
- Ops runbook: `y/ops-runbook.md`
- Release notes: `y/release-notes-v1.md`
