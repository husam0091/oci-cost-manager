---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - oci-cost-manager/AI-HANDOFF-SUMMARY.md
  - oci-cost-manager/product-brief-oci-cost-manager-2026-02-06T14-49-01.md
  - docs/prd.md
  - docs/ux-design-specification.md
  - docs/project-context.md
workflowType: 'architecture'
lastStep: 5
project_name: 'oci-cost-manager'
user_name: 'Hosam'
date: '2026-02-08T20:48:42.2214378+03:00'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
The loaded inputs contain two requirement tracks:
1. Marketing UX track (docs/prd.md, docs/ux-design-specification.md) with 30 FRs focused on navigation, hero, gallery/lightbox, CTA flows, SEO metadata, accessibility, and motion behavior.
2. FinOps platform track (oci-cost-manager/AI-HANDOFF-SUMMARY.md) focused on OCI cost governance workflows: analytics endpoints, inventory/cost mapping, allocation rules, scan lifecycle, and export/report artifacts.

Architecturally, this implies we must anchor decisions to the active delivery priority: Phase 1 analytics backend + Cost page wiring, while preserving current UI stability and avoiding regression in existing routes.

**Non-Functional Requirements:**
Primary architecture-driving NFRs identified:
1. Deterministic numeric policy and reconciliation tolerance requirements.
2. Standardized API envelope and stable lifecycle status contracts.
3. Strong server-side auth/RBAC on admin and export/scan operations.
4. Performance constraints for high-volume resource and cost payloads.
5. Auditability requirements for exports (manifest + validation artifacts).
6. Docker-based reproducible deployment workflow with minimal operational drift.
7. UTC/ISO-8601 consistency for API time semantics.

**Scale & Complexity:**
The project is a full-stack OCI analytics/reporting platform with meaningful data volume and integration constraints.

- Primary domain: Full-stack web + analytics backend
- Complexity level: High
- Estimated architectural components: 10-14 core components (API routing, auth, scan orchestration, OCI integration, cost analytics, allocation engine, reporting/export engine, persistence layer, frontend data access/caching layer, dashboard/cost UI composition, observability, validation policies)

### Technical Constraints & Dependencies

1. Existing stack constraints:
- Frontend: React/Vite/Tailwind (JS modules)
- Backend: FastAPI/SQLAlchemy/SQLite with OCI integrations
- Deployment: Docker Compose workflow must remain intact

2. Contract constraints:
- API must keep /api/v1 versioning and standard response envelope
- Protected endpoints must enforce server-side auth/RBAC
- Status vocabulary must remain canonical and consistent

3. Data and integration constraints:
- OCI APIs may rate-limit or return incomplete metadata
- Cost/resource mapping is imperfect and must expose confidence/reasoning
- Timestamp normalization to explicit UTC is required for consistent consumers

4. Quality/process constraints:
- Business logic must stay in services layer
- No heavy framework migrations in MVP path
- Contract and lifecycle tests are required for export/reporting changes

### Cross-Cutting Concerns Identified

1. Deterministic finance logic:
Centralized rounding/tolerance/parity policy applied uniformly across analytics and exports.

2. Data quality and mapping confidence:
Normalized service/resource mapping with explicit confidence and fallback provenance.

3. Performance and scalability:
Pre-aggregations, server-side pagination/filtering, and reduced payload fan-out for dashboards.

4. Security and governance:
Cookie/JWT auth behavior, admin route protection, and auditable export/scan operations.

5. Observability and operational trust:
Persisted scan/export lifecycle states, structured diagnostics, and debuggable failure visibility.

6. Frontend consistency:
Single source for API data mapping and async state semantics across dashboard/resources/cost views.


## Core Architectural Decisions (Locked)

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. Move from SQLite-in-container to dedicated PostgreSQL 16.12 plus PgBouncer topology.
2. Introduce async worker plane (Celery plus Redis) for scan/ingest/report/optimization jobs.
3. Enforce zero OCI calls on page load; UI reads cached and pre-aggregated tables only.
4. Introduce centralized structured logging and audit trail schema with correlation IDs.
5. Add OCI diagnostics health model with graceful degraded mode and stale-data fallback.
6. Keep all current routes; refactor behind existing API contract surface.

**Important Decisions (Shape Architecture):**
1. Pre-aggregated cost marts (daily, monthly, compartment, resource, license and storage waste).
2. RBAC model (admin, finops, engineer, viewer) with server-side enforcement only.
3. Redis cache policy (5 minutes dashboard, 1 hour cost aggregates, manual bust endpoint).
4. Observability stack design (API logs, DB logs, frontend telemetry, audit events).
5. Async report engine with progress polling and persisted report artifacts.

**Deferred Decisions (Post-MVP hardening):**
1. Multi-tenant shard strategy.
2. Event streaming for very large ingestion scale.
3. ML anomaly detection and forecast ensembles.

### Locked Technical Choices

1. **Data plane:** PostgreSQL 16.12 + PgBouncer transaction pooling + Redis.
2. **Compute plane:** backend API plus dedicated worker container.
3. **Cache/read policy:** all pages read cache and aggregates only.
4. **Aggregate tables:**
- daily_cost_by_service
- monthly_cost_by_service
- cost_by_compartment
- cost_by_resource
- license_cost_table
- storage_waste_table
5. **Index baseline:**
- (date, service)
- (date, compartment_id)
- (resource_id)
- (month, service)
6. **Job contract:** trigger returns job_id immediately; status and result endpoints are polled.
7. **OCI hardening:** diagnostics checks with Connected / Partial / Failed and last sync.
8. **UX speed model:** stale snapshot + skeleton + background refresh + widget hydration.
9. **Logging model:** structured log classes oci/backend/frontend/database/security/audit.
10. **Reporting model:** async generation only, with cache, retries, and progress.
11. **Governance model:** strict RBAC and auditable actor timeline.
12. **Global status bar:** OCI, DB, Worker, Reports, Last sync.
13. **Implementation order:** fixed sequence in Step 5 plan.

## Step 5: Implementation Patterns & Sprint-Ready Execution Plan

### Implementation Patterns & Consistency Rules

**Critical conflict points identified:** 14

#### Naming patterns

**Database naming conventions:**
1. snake_case for all tables and columns.
2. PK format: `id` (uuid or bigint), FK format: `<entity>_id`.
3. Index format: `idx_<table>__<col1>_<col2>`.
4. Materialized view format: `mv_<domain>_<grain>`.

**API naming conventions:**
1. REST paths are plural nouns under `/api/v1`.
2. Query params are snake_case (`start_date`, `cost_center`).
3. Job paths: `/jobs/<job_type>` and `/jobs/<job_id>/status`.
4. Headers: `X-Correlation-Id` only as custom transport identifier.

**Code naming conventions:**
1. Backend Python modules and functions: snake_case.
2. Frontend components: PascalCase file names.
3. Frontend hooks/utilities: camelCase exports.
4. Shared status constants live in dedicated constants modules only.

#### Structure patterns

1. Keep split architecture (`src/frontend`, `src/backend`).
2. Backend layering is strict: routes -> services -> repositories -> models.
3. Worker job modules under `src/backend/worker/jobs/`.
4. Caching helpers under `src/backend/services/cache/`.
5. Observability and logging adapters under `src/backend/observability/`.

#### Format patterns

1. API envelope remains `{ success, data, meta }` and `{ success, error }`.
2. Date and time fields are ISO-8601 UTC only.
3. JSON keys from backend remain snake_case.
4. Error code taxonomy is stable and centrally mapped.

#### Communication patterns

1. Job state vocabulary is canonical: `queued`, `running`, `succeeded`, `failed`.
2. Log schema is canonical across services.
3. Correlation ID propagates frontend -> backend -> worker -> logs.
4. Event payloads include `actor`, `timestamp`, `job_id` when applicable.

#### Process patterns

1. No OCI calls in request path for dashboard, costs, reports open, settings open.
2. Reads are cache-first then aggregate DB fallback.
3. Slow refreshes run async; UI reflects stale snapshot with refresh badge.
4. All long operations are queued jobs with progress API.

### Sprint-ready phased plan (1 to 10)

#### Phase 1 - Split database to PostgreSQL + PgBouncer

**Task 1.1: Introduce postgres and pgbouncer services with persistent volume**
- Acceptance criteria:
  - API and worker connect through PgBouncer DSN.
  - Data persists across container restarts.
  - Health checks pass for postgres and pgbouncer.
- Rollback notes:
  - Switch DSN back to previous SQLite path.
  - Disable postgres and pgbouncer services in compose override.

**Task 1.2: Add Alembic baseline for PostgreSQL schema**
- Acceptance criteria:
  - `alembic upgrade head` creates all core tables on empty PostgreSQL.
  - Existing app starts without route changes.
- Rollback notes:
  - Revert migration revision and point app to previous DB.

**Task 1.3: Migrate settings/auth critical path query tuning**
- Acceptance criteria:
  - Login p95 < 500ms under normal local load.
  - No blocking joins in login/settings read path.
- Rollback notes:
  - Re-enable legacy query path via feature flag.

#### Phase 2 - Add Redis cache

**Task 2.1: Add redis service and cache abstraction module**
- Acceptance criteria:
  - Cache service boots and ping check passes.
  - Backend cache adapter supports get/set/delete with TTL.
- Rollback notes:
  - Fallback to in-memory cache adapter with same interface.

**Task 2.2: Implement cache policy for dashboard and aggregates**
- Acceptance criteria:
  - Dashboard TTL = 300 seconds.
  - Aggregate TTL = 3600 seconds.
  - Manual refresh endpoint invalidates relevant keys.
- Rollback notes:
  - Disable cache middleware and use DB aggregate reads only.

#### Phase 3 - Add worker system

**Task 3.1: Integrate Celery worker and Redis broker**
- Acceptance criteria:
  - Worker starts and consumes queued jobs.
  - API returns job_id immediately for long tasks.
- Rollback notes:
  - Route long tasks to existing scheduler fallback.

**Task 3.2: Implement job status/result persistence**
- Acceptance criteria:
  - Job state transitions persisted and queryable.
  - Status endpoint returns progress and errors.
- Rollback notes:
  - Use in-process status table writes from API fallback task runner.

#### Phase 4 - Implement aggregate cost tables

**Task 4.1: Create aggregate tables and refresh procedures**
- Acceptance criteria:
  - All six aggregate tables exist and populate from raw data.
  - Hourly refresh job updates aggregates without downtime.
- Rollback notes:
  - Disable refresh schedule and keep previous snapshot tables.

**Task 4.2: Add required indexes and query plans**
- Acceptance criteria:
  - Indexes created per baseline.
  - Dashboard and costs query plans use indexes.
- Rollback notes:
  - Drop new indexes and restore prior index set.

#### Phase 5 - Add OCI diagnostics

**Task 5.1: Build diagnostics service checks**
- Acceptance criteria:
  - Checks include config_detected, key_readable, tenancy_reachable, usage_api_reachable, cost_api_reachable.
  - Service emits consolidated health status.
- Rollback notes:
  - Keep existing health endpoint and disable diagnostics card.

**Task 5.2: Header status indicator integration**
- Acceptance criteria:
  - Header shows OCI Connected/Partial/Failed + last sync time.
  - UI still renders with cached data when OCI is down.
- Rollback notes:
  - Hide new header widget via feature flag.

#### Phase 6 - Implement logging system

**Task 6.1: Structured log schema and sinks**
- Acceptance criteria:
  - All logs include timestamp, log_type, severity, component, message, user, correlation_id, oci_request_id.
  - Backend and worker emit to unified log sink.
- Rollback notes:
  - Revert to existing logger config and keep raw logs.

**Task 6.2: Logs dashboard API and page**
- Acceptance criteria:
  - Filters by type, severity, date, service, search.
  - CSV and JSON export endpoints available.
  - Live tail endpoint streams recent records.
- Rollback notes:
  - Hide log page route and retain backend-only logs.

#### Phase 7 - Fix reports async generation

**Task 7.1: Convert report generation to async-only**
- Acceptance criteria:
  - Report trigger returns job_id.
  - Progress/status endpoints report stage and percent.
- Rollback notes:
  - Fall back to prior report route with explicit queued mode toggle.

**Task 7.2: Saved reports and cache results**
- Acceptance criteria:
  - Completed reports listed with metadata and download links.
  - Retry on failure supported.
- Rollback notes:
  - Disable retry and serve only latest successful artifact.

#### Phase 8 - Optimize dashboard loading

**Task 8.1: Cache-first widget APIs and stale snapshots**
- Acceptance criteria:
  - Dashboard first paint from cache/snapshot under 1 second.
  - No OCI requests triggered from dashboard load.
- Rollback notes:
  - Use DB aggregate-only path without cache first.

**Task 8.2: Incremental widget hydration**
- Acceptance criteria:
  - Initial shell and critical widgets render before secondary widgets.
  - No blank screen during refresh.
- Rollback notes:
  - Render all widgets after single aggregate response.

#### Phase 9 - Add classification engine

**Task 9.1: Implement rule-based mapping service**
- Acceptance criteria:
  - Maps team, app, environment, owner, cost_center with confidence score.
  - Supports filters for unallocated/waste/idle/stopped/unattached.
- Rollback notes:
  - Disable rule application and keep previous classification values.

**Task 9.2: Recompute job integration**
- Acceptance criteria:
  - Mapping recompute runs in worker and updates aggregates.
  - UI reflects latest mapping timestamp.
- Rollback notes:
  - Revert to static mapping fallback.

#### Phase 10 - Add audit and governance

**Task 10.1: Audit event model and action hooks**
- Acceptance criteria:
  - Tracks settings changes, report generation, scan triggers, governance actions.
  - Stores actor, action, timestamp, result, correlation_id.
- Rollback notes:
  - Disable hooks and keep passive security logs only.

**Task 10.2: Audit viewer API/page**
- Acceptance criteria:
  - Timeline view by user/action/date/result.
  - RBAC enforced for audit access.
- Rollback notes:
  - Restrict audit endpoints to admin internal use only.

### Minimal docker-compose.yml baseline

```yaml
version: '3.9'

services:
  nginx:
    image: nginx:1.27-alpine
    depends_on:
      - frontend
      - backend
    ports:
      - "80:80"
    volumes:
      - ./src/frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro

  frontend:
    build:
      context: ./src/frontend
    depends_on:
      - backend

  backend:
    build:
      context: ./src/backend
    environment:
      DATABASE_URL: postgresql://app:app@pgbouncer:6432/oci_cost_manager
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      - pgbouncer
      - redis

  worker:
    build:
      context: ./src/backend
    command: celery -A worker.celery_app worker -l info
    environment:
      DATABASE_URL: postgresql://app:app@pgbouncer:6432/oci_cost_manager
      REDIS_URL: redis://redis:6379/0
      CELERY_BROKER_URL: redis://redis:6379/1
      CELERY_RESULT_BACKEND: redis://redis:6379/2
    depends_on:
      - pgbouncer
      - redis

  postgres:
    image: postgres:16.12
    environment:
      POSTGRES_DB: oci_cost_manager
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    volumes:
      - postgres_data:/var/lib/postgresql/data

  pgbouncer:
    image: bitnami/pgbouncer:1.25.0
    environment:
      POSTGRESQL_HOST: postgres
      POSTGRESQL_PORT: 5432
      POSTGRESQL_DATABASE: oci_cost_manager
      POSTGRESQL_USERNAME: app
      POSTGRESQL_PASSWORD: app
      PGBOUNCER_POOL_MODE: transaction
      PGBOUNCER_DEFAULT_POOL_SIZE: 40
      PGBOUNCER_MAX_CLIENT_CONN: 500
    depends_on:
      - postgres

  redis:
    image: redis:8.2.3-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Alembic migration plan (schema-first)

1. `rev_001_postgres_foundation`
- create core auth/settings/scan tables for PostgreSQL compatibility.

2. `rev_002_job_tables`
- create `job_runs`, `job_events`.

3. `rev_003_aggregate_cost_tables`
- create six aggregate tables and index baseline.

4. `rev_004_logging_tables`
- create `system_logs`, `frontend_logs_ingest` (optional), partitions by date.

5. `rev_005_audit_tables`
- create `audit_events` and approval workflow tables.

6. `rev_006_reporting_tables`
- create `report_runs`, `report_artifacts`, `report_cache_index`.

7. `rev_007_classification_tables`
- create mapping rules tables and confidence metadata.

### DB schema baseline (aggregates, logs, jobs, audit)

#### Aggregate tables

1. `daily_cost_by_service`
- columns: `id`, `date`, `service`, `total_cost`, `currency`, `updated_at`
- indexes: `idx_daily_cost_by_service__date_service`

2. `monthly_cost_by_service`
- columns: `id`, `month`, `service`, `total_cost`, `currency`, `updated_at`
- indexes: `idx_monthly_cost_by_service__month_service`

3. `cost_by_compartment`
- columns: `id`, `date`, `compartment_id`, `compartment_name`, `service`, `total_cost`, `updated_at`
- indexes: `idx_cost_by_compartment__date_compartment`

4. `cost_by_resource`
- columns: `id`, `date`, `resource_id`, `resource_name`, `service`, `total_cost`, `updated_at`
- indexes: `idx_cost_by_resource__resource_id`, `idx_cost_by_resource__date_service`

5. `license_cost_table`
- columns: `id`, `date`, `resource_id`, `license_type`, `license_cost`, `updated_at`
- indexes: `idx_license_cost_table__date_service`

6. `storage_waste_table`
- columns: `id`, `date`, `resource_id`, `waste_type`, `waste_cost`, `updated_at`
- indexes: `idx_storage_waste_table__date_service`

#### Job tables

1. `job_runs`
- columns: `id`, `job_type`, `status`, `progress_pct`, `requested_by`, `payload_json`, `result_json`, `error_message`, `created_at`, `started_at`, `finished_at`, `correlation_id`
- indexes: `idx_job_runs__status_created_at`, `idx_job_runs__job_type_created_at`

2. `job_events`
- columns: `id`, `job_id`, `event_type`, `message`, `metadata_json`, `created_at`
- indexes: `idx_job_events__job_id_created_at`

#### Logging tables

1. `system_logs`
- columns: `id`, `timestamp`, `log_type`, `severity`, `component`, `message`, `user_name`, `correlation_id`, `oci_request_id`, `metadata_json`
- indexes: `idx_system_logs__timestamp_type`, `idx_system_logs__severity_timestamp`, `idx_system_logs__correlation_id`

#### Audit tables

1. `audit_events`
- columns: `id`, `timestamp`, `actor_user`, `actor_role`, `action`, `target_type`, `target_id`, `result`, `details_json`, `correlation_id`, `approved_by`
- indexes: `idx_audit_events__timestamp_actor`, `idx_audit_events__action_timestamp`

### API endpoint contract list

#### Health and diagnostics
1. `GET /api/v1/health`
2. `GET /api/v1/health/db`
3. `GET /api/v1/health/cache`
4. `GET /api/v1/health/worker`
5. `GET /api/v1/diagnostics/oci`

#### Jobs
1. `POST /api/v1/jobs/scan`
2. `POST /api/v1/jobs/ingest`
3. `POST /api/v1/jobs/aggregate-refresh`
4. `POST /api/v1/jobs/report-generate`
5. `POST /api/v1/jobs/classification-recompute`
6. `GET /api/v1/jobs/{job_id}/status`
7. `GET /api/v1/jobs/{job_id}/result`

#### Logs
1. `GET /api/v1/logs`
2. `GET /api/v1/logs/tail`
3. `GET /api/v1/logs/export/csv`
4. `GET /api/v1/logs/export/json`

#### Reports
1. `POST /api/v1/reports/generate`
2. `GET /api/v1/reports/runs`
3. `GET /api/v1/reports/runs/{run_id}`
4. `GET /api/v1/reports/runs/{run_id}/artifact/{format}`
5. `POST /api/v1/reports/runs/{run_id}/retry`

#### Cost aggregates
1. `GET /api/v1/aggregates/dashboard`
2. `GET /api/v1/aggregates/costs/by-service`
3. `GET /api/v1/aggregates/costs/by-compartment`
4. `GET /api/v1/aggregates/costs/by-resource`
5. `GET /api/v1/aggregates/costs/license`
6. `GET /api/v1/aggregates/costs/storage-waste`
7. `POST /api/v1/aggregates/refresh`

### UI performance plan

1. Stale snapshot first render:
- read snapshot payload from cache-backed API.
- render immediately, mark as `stale=true` when refresh is in progress.

2. Skeleton strategy:
- page shell skeleton for first ever load only.
- widget skeletons for secondary panels while hydration completes.

3. Background refresh strategy:
- soft refresh in background after initial paint.
- do not clear existing data while refreshing.
- show subtle "updating" badge.

4. Widget hydration:
- hydrate critical widgets first (total cost, top services, status bar).
- hydrate secondary widgets after critical data resolves.

5. No blank states:
- if snapshot exists, show snapshot.
- if no snapshot and backend partial available, show partial widgets with warnings.
- if full failure, show diagnostics panel plus retry controls.

### Fast pages rules checklist

1. Zero OCI calls on page load.
2. All pages load from cache and aggregate endpoints.
3. Background refresh is async and non-blocking.
4. Reports generation is async only.
5. No page clears old data during refresh.
6. No blank states, ever.
7. Header status bar always visible with OCI, DB, Worker, Reports, Last sync.
8. Login and settings use optimized read/write paths only.

