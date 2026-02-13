# OCI Cost Manager Governance Redesign

Date: 2026-02-08  
Scope: Decision-first dashboard + FinOps governance value + audit-ready reporting foundation

## What Has Been Implemented In This Change Set

### 1) Decision-driving backend APIs

Added to `src/backend/api/routes/costs.py`:

- `GET /api/v1/costs/summary`
  - total, previous_total, delta_abs, delta_pct
  - top_driver
  - biggest_mover
  - unallocated pct/count
  - freshness (scan + snapshot times/status)

- `GET /api/v1/costs/breakdown`
  - group_by `service|compartment|env|team|app|resource`
  - current/previous/delta/share
  - top-N + Other bucket support

- `GET /api/v1/costs/movers`
  - group_by `service|compartment|resource`
  - sorted by absolute delta
  - include/exclude negative movers

- `GET /api/v1/costs/insights`
  - actionable insights list from summary/breakdown/freshness

Added alias endpoint:
- `GET /api/v1/insights`
  - file: `src/backend/api/routes/insights.py`
  - wired in `src/backend/main.py`

### 2) Date correctness hardening

- ISO parsing helper with UTC normalization.
- End-date inclusive behavior for date-only inputs.
- Range validation (`end > start`).

### 3) Backend normalization centralization

- Workload category normalization moved server-side:
  - `sql_server`, `windows_server`, `security_appliance`, `storage_and_backup`, `other`
- Resource rows now include normalized category metadata for frontend use.

### 4) Performance-oriented cost endpoint behavior

In `src/backend/services/cost_calculator.py`:
- Added `include_skus` option for `get_costs_by_resource(...)`.
- Enables lightweight aggregation for dashboard/cost summaries without large SKU payloads.

### 5) Frontend dashboard redesign (value architecture)

Rebuilt `src/frontend/src/pages/Dashboard.jsx` to include:
- 4 KPI executive cards
- 6-month trend panel
- Breakdown panel with group_by toggle
- Top movers table (service/compartment/resource)
- Actionable insights panel
- Governance quick view (environment segmentation + freshness)

### 6) Cost analysis page upgrade

Updated `src/frontend/src/pages/Costs.jsx`:
- Summary row (total/delta/top driver/biggest mover/unallocated)
- Breakdown table with group toggle
- Movers section
- Keeps existing range presets + custom range behavior

### 7) API client updates

Updated `src/frontend/src/services/api.js`:
- Added:
  - `getCostSummary`
  - `getCostBreakdown`
  - `getCostMovers`
  - `getInsights`

---

## Incremental Safe Commit Plan (Requested)

Use this sequence for clean rollout:

1. Commit A: Date correctness + analytics endpoint scaffolding
- Files:
  - `src/backend/api/routes/costs.py`
  - `src/backend/services/cost_calculator.py`
- Verify:
  - custom ranges return inclusive end-day data
  - summary/breakdown/movers return deterministic schema

2. Commit B: Insights route and app wiring
- Files:
  - `src/backend/api/routes/insights.py`
  - `src/backend/main.py`
- Verify:
  - `/api/v1/insights` returns same payload as `/api/v1/costs/insights`

3. Commit C: Dashboard decision-first frontend
- Files:
  - `src/frontend/src/pages/Dashboard.jsx`
  - `src/frontend/src/services/api.js`
- Verify:
  - KPI cards populate
  - movers + insights + env tiles load

4. Commit D: Cost analysis upgrades
- Files:
  - `src/frontend/src/pages/Costs.jsx`
  - `src/frontend/src/services/api.js` (if changed further)
- Verify:
  - custom range + breakdown + movers + summary all work

5. Commit E (next): Inventory cost-aware virtualization + drawer
- Add:
  - server-side paging/sorting/filters in `/api/v1/data/resources`
  - frontend virtualized table + drilldown drawer

6. Commit F (next): Normalization + allocation rules engine
- Add new tables/models:
  - allocation rules
  - normalized mapping metadata
- Add admin CRUD endpoints for rules.

7. Commit G (next): Report catalog + tiered templates
- Implement Tier-1 reports first:
  - Executive summary
  - service/compartment deltas
  - top resources
  - unallocated mapping
- Generate `manifest.json` + `validation.json` per run.

---

## Remaining Work To Reach Full Requested Scope

Not fully completed yet in this pass:

1. Full virtual tags/rules engine CRUD + priority resolver.
2. Shared-cost allocation percentage engine at report time.
3. Full inventory virtualization + 6/12-month drawer trends + related resources.
4. Tiered report catalog execution (Tier 1/2/3 all templates).
5. React Query caching layer adoption across pages.
6. Automated tests required by scope:
- date inclusivity tests
- Other-bucket tests
- rule-priority/match-confidence tests
- export schema stability tests
- frontend smoke tests

---

## Runtime Notes

1. Restart backend/frontend containers to pick up code changes.
2. Verify Docker workflow remains unchanged (`docker compose up -d --build`).
3. Validate with:
- `/api/v1/costs/summary`
- `/api/v1/costs/breakdown?group_by=service`
- `/api/v1/costs/movers?group_by=resource`
- `/api/v1/insights`

