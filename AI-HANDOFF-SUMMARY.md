# OCI Cost Manager - Handoff Summary

## App Summary

- **Project**: `D:\my-lab\oci-cost-manager`
- **Goal**: OCI cost governance dashboard with live inventory, cost analytics, scans, settings-driven OCI integration, and export reporting.
- **Stack**:
  - Frontend: React + Vite + Tailwind (served by Nginx in Docker)
  - Backend: FastAPI + SQLAlchemy + SQLite
  - Deployment: Docker Compose (`backend` + `frontend`)
- **Primary features**:
  - Dashboard (cost KPIs, service breakdown, top resources, workload-focused cards)
  - Resources inventory (compartment/type filters, period-based cost context, refresh/scan)
  - Settings/Profile (admin auth, OCI config, connection test, scan control)
  - Export Reports tab (`/exports`) with report types and file downloads (`json/csv/xlsx`)

## Important Recent Fixes

1. **Export download fixed**
   - Correct MIME types for `.xlsx/.csv/.json` in backend download endpoint.
   - Frontend download uses blob + `Content-Disposition` filename handling.
   - Exports are saved/mounted to: `D:\my-lab\y\reports`.

2. **Scan blocking issue fixed**
   - `POST /api/v1/admin/scan/run` now runs scan in background thread.
   - Prevents UI/API freeze caused by long synchronous scan.
   - Added stale running-scan cleanup logic (marks old `running` scans as failed).

3. **Resource classification improved**
   - SQL detection no longer false-matches `mysql`.
   - SQL patterns supported: `sql-server`, `sql server`, `mssql`, `microsoft sql`.
   - Verified production SQL host `10.110.0.90` is correctly in `sql_server`.
   - Misclassified Oracle/MySQL image (`oracle9-cis-mysql-8.0.31-base-img`) removed from SQL classification.

4. **UX updates**
   - Export Reports moved to dedicated route (`/exports`), not inside Settings.
   - Sidebar/theme/layout improved.
   - Resources/Dashboard include fallback logic from cost SKUs when OCI metadata is incomplete.

## Frontend Architecture (Fast Mental Model)

### Routes and layout

- Routes are wired in: `src/frontend/src/App.jsx`
- Main pages:
  - `/` -> `Dashboard.jsx`
  - `/resources` -> `Resources.jsx`
  - `/costs` -> `Costs.jsx`
  - `/budget` -> `Budget.jsx`
  - `/exports` -> `ExportReports.jsx`
  - `/settings` -> `Settings.jsx`
- Auth gating is done in `AppLayout` by calling `adminGetSettings()`; if unauthenticated it renders the login flow from `Settings`.

### State pattern

- Current pattern is **page-local React state + `useEffect`**.
- No global store and no React Query/SWR cache layer yet.
- Repeated requests are expected today (especially Dashboard/Resources count calls).

### Shared API contract location

- Frontend API wrapper: `src/frontend/src/services/api.js`
- Backend route sources:
  - `src/backend/api/routes/data.py`
  - `src/backend/api/routes/costs.py`
  - `src/backend/api/routes/admin.py`

## Frontend Data Contract (Page -> Endpoint Mapping)

### Dashboard (`src/frontend/src/pages/Dashboard.jsx`)

- `GET /api/v1/health/oci`
- `GET /api/v1/data/costs?period=monthly`
- `GET /api/v1/data/trends?months=6`
- `GET /api/v1/data/resources?limit=1000`
- `GET /api/v1/data/resources?limit=1&type=<type>` for several types
- `GET /api/v1/costs/by-resource`
- `POST /api/v1/admin/scan/run` (Refresh Data)

### Resources (`src/frontend/src/pages/Resources.jsx`)

- `GET /api/v1/data/compartments/tree`
- `GET /api/v1/data/resources?type=<optional>&compartment_id=<optional>&limit=1000`
- `GET /api/v1/data/resources?limit=1&type=<type>` (tab counts)
- `GET /api/v1/costs/by-resource?start_date=<...>&end_date=<...>` (filter cost + fallback counts)
- `POST /api/v1/admin/scan/run` (Refresh)

### Export Reports (`src/frontend/src/pages/ExportReports.jsx`)

- `POST /api/v1/admin/exports/snapshot`
- `GET /api/v1/admin/exports/list`
- `GET /api/v1/admin/exports/download/{name}`
- File naming pattern: `export-report-<optional-name>-<YYYYMMDD-HHMMSS>.<ext>`

## Response Schema Samples

### Dashboard KPI source (`GET /api/v1/data/costs?period=monthly`)

```json
{
  "success": true,
  "data": {
    "period": "monthly",
    "start_date": "2026-02-01T00:00:00",
    "end_date": "2026-02-07T00:00:00",
    "total": 19660.64,
    "by_service": {
      "Compute": 9823.40,
      "Database": 3249.66
    }
  }
}
```

### Resources list item (`GET /api/v1/data/resources?...`)

```json
{
  "success": true,
  "data": [
    {
      "id": "ocid1.instance...",
      "name": "opi-mql-db-ha1",
      "type": "sql_server",
      "compartment_id": "ocid1.compartment...",
      "status": "RUNNING",
      "shape": "VM.Standard.E5.Flex",
      "details": {
        "private_ip": "10.110.0.90",
        "image_name": "...Sql-Server-2022-ent-windows-2022-with-lic"
      }
    }
  ],
  "meta": {
    "total": 4,
    "returned": 1,
    "offset": 0
  }
}
```

### Cost breakdown item (`GET /api/v1/costs/by-resource`)

```json
{
  "success": true,
  "data": [
    {
      "resource_id": "ocid1.instance...",
      "compartment_id": null,
      "compartment_name": null,
      "total_cost": 805.01,
      "skus": [
        { "sku_name": "Windows OS", "cost": 52.99 },
        { "sku_name": "Microsoft SQL Enterprise", "cost": 719.71 }
      ]
    }
  ]
}
```

### Export list item (`GET /api/v1/admin/exports/list`)

```json
{
  "success": true,
  "data": [
    {
      "name": "export-report-manual-20260207-180732.xlsx",
      "path": "/exports/export-report-manual-20260207-180732.xlsx",
      "download_url": "/api/v1/admin/exports/download/export-report-manual-20260207-180732.xlsx",
      "size_bytes": 18947,
      "updated_at": "2026-02-07T18:07:32.000000+00:00"
    }
  ]
}
```

## Filters, Date Range, and Ownership

- **Dashboard**: period is mostly fixed to monthly totals + last 6 months trends.
- **Resources**: period selector is local state in `Resources.jsx` (`daily/monthly/yearly/past_year`).
- **Compartment filter**: local state in `Resources.jsx`.
- **No global shared filter state yet** across Dashboard/Resources/Costs.

## Performance Guardrails (Current Reality)

- Resource table size can exceed **5,000 rows** in DB.
- `GET /costs/by-resource` can return very large payloads (observed ~1.8MB+ through nginx).
- Typical full scan observed in this environment: **~2-4 minutes**.
- First bottlenecks seen:
  - OCI API latency/rate limits (429)
  - Large payload transfer + client-side aggregation
  - Repeated page-local fetching (no shared cache)

## Prioritized Improvement Roadmap

1. **Make dashboard decision-driving**
   - Add period-over-period deltas and top cost-change contributors.
   - Add drill-down from KPI cards to pre-filtered Resources/Costs views.

2. **Centralize resource-to-cost mapping**
   - Build backend-normalized mapping fields (`normalized_service`, `match_confidence`, `match_reason`, etc.).
   - Keep fallback classification in one backend location, not duplicated in pages.

3. **Upgrade export quality for audit**
   - Add export manifest (filters, run id, generated by/time, app version).
   - Add validation coverage stats and stable schema columns across CSV/XLSX.

4. **Frontend performance and clarity**
   - Add server-side pagination/filtering for resource-heavy views.
   - Add request caching layer (React Query recommended).
   - Virtualize large tables and memoize heavy chart transforms.

## Concrete First 60 Minutes Checklist

1. Run Docker Compose and open: Dashboard -> Resources -> Exports -> Settings.
2. In browser network tab, capture slow endpoints + payload sizes.
3. Read in order:
   - `src/frontend/src/services/api.js`
   - `src/frontend/src/pages/Dashboard.jsx`
   - `src/frontend/src/pages/Resources.jsx`
   - `src/frontend/src/pages/ExportReports.jsx`
4. Then backend:
   - `src/backend/api/routes/costs.py`
   - `src/backend/api/routes/data.py`
   - `src/backend/services/scanner.py`
5. Confirm classification and scan status behavior before UI refactors.

## Key Files to Review First

### Backend

- `src/backend/api/routes/admin.py`
- `src/backend/services/scanner.py`
- `src/backend/api/routes/data.py`
- `src/backend/api/routes/costs.py`

### Frontend

- `src/frontend/src/pages/ExportReports.jsx`
- `src/frontend/src/pages/Settings.jsx`
- `src/frontend/src/pages/Resources.jsx`
- `src/frontend/src/pages/Dashboard.jsx`
- `src/frontend/src/services/api.js`

### Infra

- `docker-compose.yml`
- `src/frontend/nginx.conf`

## Prompt for Another AI

Continue development of the OCI Cost Manager app in `D:\my-lab\oci-cost-manager`.
Current state: export downloads and scan background execution are fixed; SQL classification was corrected so MySQL images are not tagged as SQL and production SQL host `10.110.0.90` is correctly classified.
Please review backend scanner + admin routes and frontend dashboard/resources/exports pages. Focus next on:
1) improving dashboard usefulness and visual clarity,
2) resource-to-cost mapping quality (names + SKUs + categories),
3) export report quality/validation completeness,
4) performance optimization for large resource/cost responses.
Keep Docker workflow intact and verify changes with lint/build/tests.

## Auth & Admin

- **Auth mechanism**: HTTP-only cookie named `access_token` (JWT), issued by backend on login.
- **Cookie settings**: `httponly=true`, `samesite=lax`, `max_age=3600` (1 hour session).
- **Login endpoint**: `POST /api/v1/admin/login` with `{ username, password }` returns `{ "success": true }` on success.
- **Logout endpoint**: `POST /api/v1/admin/logout` clears cookie.
- **Protected endpoint behavior**: protected admin endpoints return `401` when cookie missing/invalid.
- **Frontend auth gating**:
  - `AppLayout` calls `adminGetSettings()`.
  - If request fails (typically `401`), app renders login UI (`Settings` force-login flow).
- **Protected routes/features**:
  - UI route gating: app requires auth before rendering Dashboard/Resources/Costs/Budget/Exports/Settings.
  - Backend protected endpoints: `/api/v1/admin/settings*`, `/api/v1/admin/scan/*`, `/api/v1/admin/exports/*`.
- **Local dev credential reset**:
  - Default created only when `settings` row `id=1` does not exist: `admin/admin`.
  - Source: `src/backend/core/scheduler.py` (`ensure_default_settings`).
  - If creds are lost, either:
    1) update `settings.password_hash`/`username` in DB, or
    2) remove row `id=1` and restart backend to re-seed `admin/admin`.

## Scan Lifecycle

- **Trigger endpoint**: `POST /api/v1/admin/scan/run`.
- **Response model**:
  - Start: `{ "success": true, "data": { "status": "started" } }`
  - Busy: `{ "success": true, "data": { "status": "already_running", "run_id": <id> } }`
- **Status endpoint**: `GET /api/v1/admin/scan/runs` (latest 20 runs).
- **Scan statuses**: `running | success | failed`.
- **Persistence**: DB table `scan_runs` with fields: `id`, `started_at`, `finished_at`, `status`, `error_message`.
- **Stale cleanup rule**:
  - When `/scan/run` is called, scans older than 30 minutes and still `running` are marked `failed`.
  - Prevents dead `running` state after worker interruption/restart.

## DB Model Index (Core)

- `settings`
  - PK: `id` (uses `1`)
  - Stores admin credentials + scan interval + OCI integration fields.
- `scan_runs`
  - PK: `id`
  - Lifecycle tracking: `started_at`, `finished_at`, `status`, `error_message`.
- `compartments`
  - PK: `id` (OCID)
  - Hierarchy fields: `parent_id`, `path`.
- `resources`
  - PK: `id` (int), unique key: `ocid`
  - Core mapping fields: `type`, `compartment_id`, `status`, `shape`, `details` (JSON).
- `cost_snapshots`
  - PK: `id`
  - Unique key: `(period, start_date)`
  - Summary fields: `total`, `by_service` (JSON).
- `trend_points`
  - PK: `id`
  - Unique key: `month` (`YYYY-MM`)
  - Trend fields: `total_cost`, `by_service` (JSON).

## Known Data Limitations

- `/api/v1/costs/by-resource` can return `compartment_id = null` for OCI usage lines.
- Some resources do not have human-friendly names; fallback labels are used in UI.
- OCI metadata can be incomplete; fallback classification uses SKU text matching.
- Not all costs map 1:1 to a single resource (shared/network/platform costs exist).
- OCI Usage API can rate limit (`429`); scanner and cost endpoints may degrade to cached/partial behavior.

## Clarifications: Count Pattern, Dates, Period Semantics

- **`/api/v1/data/resources?limit=1&type=<type>` pattern**:
  - Backend performs `q.count()` first, then fetches limited rows.
  - Count is DB-side, but frontend currently issues this call repeatedly per type.
  - Recommended future endpoint: `GET /api/v1/data/resources/counts?group_by=type&compartment_id=...`.

- **Date format and timezone (current)**:
  - DB model defaults mostly use `datetime.utcnow` (naive UTC timestamps).
  - Some newer paths use timezone-aware `datetime.now(UTC)`.
  - API currently returns mixed ISO strings (some with offset, some without).
  - Recommendation: normalize all outward timestamps to explicit UTC offset.

- **Period meaning (current)**:
  - `GET /api/v1/data/costs?period=monthly` -> latest monthly snapshot (month-to-date based on scanner snapshot window).
  - `GET /api/v1/costs/by-resource` default window -> start of current month to now.
  - `GET /api/v1/data/trends?months=6` -> latest 6 stored monthly trend points.

## Danger List (Easy to Break)

- Do not change export download headers/filename behavior (keeps browser download stable).
- Do not reintroduce synchronous full-scan execution inside request thread.
- Do not duplicate SKU fallback logic across pages; centralize it.
- Do not keep per-type `limit=1` count fan-out long-term for dashboards.

## Next-Phase FinOps Roadmap (Holori/Ternary Value Parity)

### Target Outcome

Transform OCI Cost Manager into a FinOps-grade platform focused on decision quality, allocation accuracy, and audit-ready outputs.

### 1) Backend Architecture Changes

#### New logical layers

- `services/cost_analytics.py`
  - Period-over-period calculations
  - Top movers (increase/decrease)
  - Time-series groupings (service, compartment, allocation dimensions)
- `services/allocation_engine.py`
  - Virtual tagging rule evaluation
  - Shared cost percentage allocations
  - Match confidence/reason scoring
- `services/report_engine.py`
  - Template-based report generation
  - Manifest + validation output generation

#### New API groups

- `GET /api/v1/analytics/kpis`
  - total, delta absolute, delta %, forecast, unallocated
- `GET /api/v1/analytics/timeseries`
  - group_by: `service|compartment|team|application|environment`
  - granularity: `daily|monthly`
- `GET /api/v1/analytics/top-movers`
- `GET /api/v1/analytics/top-drivers`
- `GET /api/v1/inventory/resources`
  - server-side pagination/filtering/sorting
  - include cost summary + allocation fields
- `GET /api/v1/inventory/resources/{id}/detail`
  - 6/12 month trend, sku breakdown, tags, allocation confidence
- `POST /api/v1/allocation/rules`
- `GET /api/v1/allocation/rules`
- `POST /api/v1/allocation/recompute`
- `POST /api/v1/reports/generate`
- `GET /api/v1/reports/catalog`
- `GET /api/v1/reports/history`

### 2) Data Model Additions (SQLAlchemy)

#### Add to `resources` (or derived resource-cost view)

- `normalized_service` (string)
- `owner_team` (string)
- `application` (string)
- `environment` (string)
- `cost_center` (string)
- `match_confidence` (`high|medium|low`)
- `match_reason` (`ocid|tag|sku|name|fallback`)

#### New tables

- `allocation_rules`
  - `id`, `name`, `priority`, `enabled`
  - conditions JSON: compartment/tag/name regex/sku regex
  - assignments JSON: team/app/env/cost_center
  - shared allocation JSON (optional percentages)
  - timestamps
- `resource_cost_daily` (aggregated)
  - `date`, `resource_id`, `service`, `compartment_id`, `cost`
- `resource_cost_monthly` (aggregated)
  - `month`, `resource_id`, `service`, `compartment_id`, `cost`
- `report_runs`
  - `id`, `template`, `filters_json`, `scan_id`, `status`, `generated_at_utc`
  - `manifest_path`, `validation_path`, `artifact_path`

### 3) Allocation Rule Model

#### Rule execution

1. Load enabled rules by ascending priority.
2. Evaluate IF conditions:
   - compartment match
   - exact tag match
   - regex on resource name
   - regex on SKU names
3. Apply THEN assignments.
4. First match wins by default; optional merge mode for additive fields.
5. If no match, fallback heuristics and mark low confidence.

#### Shared costs

- Support percentage split across allocation targets.
- Validate sum = 100%.
- Track allocation provenance in report validation output.

### 4) Report Definitions and Schemas

#### Tier 1 Core

- Executive Summary
- Cost by Service
- Cost by Compartment
- Top Resources by Cost
- Unallocated / Low-Confidence Mapping

#### Tier 2 FinOps

- Showback (team/app/env)
- Chargeback (allocation rules applied)
- Shared Cost Allocation

#### Tier 3 Governance

- Anomaly Report
- Waste/Hygiene Report
- Tag Coverage & Policy Compliance
- Budget vs Actual (YTD + monthly)

#### Every report artifact includes

- Main data file: CSV/XLSX/JSON (stable columns)
- `manifest.json`:
  - report template, filters, period mode, start/end, scan_id, generated_at_utc, app version
- `validation.json`:
  - input/output row counts
  - totals checksum
  - missing mapping percentages
  - low-confidence counts
  - unallocated totals

### 5) Frontend Strategy

#### Cost Analysis page

- KPI strip: Total, Delta %, Delta absolute, Forecast, Unallocated
- Time-series chart with group switcher
- Top movers table
- Top resources table
- Drill-down to inventory with synced filters

#### Inventory page

- Left filter rail: compartments + team/app/env + confidence
- Main virtualized table with server-side paging
- Row click -> right detail drawer (trend + SKU + tags + confidence)

#### Exports page

- Report catalog by tier
- Per-template filters
- Generate action
- Run history + download links + manifest/validation links

### 6) Performance Plan

- Prefer pre-aggregated daily/monthly cost tables for dashboard queries.
- Add pagination/filtering at API level for inventory endpoints.
- Avoid sending full `/costs/by-resource` to build dashboard cards.
- Introduce query-level indexes for date/resource/compartment dimensions.
- Frontend compatibility for React Query caching and stale-while-revalidate.
- Virtualize inventory table when row count > 500.

### 7) Incremental Safe Implementation Plan

#### Phase 0 (stabilize contracts)

- Freeze current endpoint contracts.
- Add explicit analytics/inventory/report endpoint specs.
- Add baseline API tests.

#### Phase 1 (analytics backend + minimal UI)

- Build `/analytics/kpis`, `/analytics/timeseries`, `/analytics/top-movers`.
- Wire Cost Analysis page to new endpoints.
- Keep existing endpoints intact as fallback.

#### Phase 2 (allocation engine)

- Implement `allocation_rules` model and evaluator.
- Add recompute job.
- Expose normalized fields in inventory endpoints.

#### Phase 3 (inventory rework)

- Server-side paginated inventory API.
- Virtualized table + detail drawer UI.
- Add allocation confidence filtering.

#### Phase 4 (report engine)

- Implement report catalog + templated generator.
- Add manifest + validation artifacts.
- Integrate exports UI with history and artifact downloads.

#### Phase 5 (governance + optimization)

- Add anomaly, waste, compliance templates.
- Tune indexes and payload sizes.
- Add regression/performance test suite for large datasets.

### 8) Non-Negotiable Guardrails

- Do not reintroduce month-to-date behavior where full periods are required.
- Do not duplicate date or mapping logic in multiple frontend pages.
- Do not rely on implicit backend period defaults when explicit dates are available.
- Keep Docker workflow unchanged.
- Keep exports deterministic and audit-grade.
