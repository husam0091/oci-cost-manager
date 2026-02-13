# Cost Analysis Date-Range Debug Report

Date: 2026-02-08  
Project: `D:\my-lab\oci-cost-manager`

## Problem

On the Cost Analysis page, custom date ranges (example `2025-07-01` to `2026-02-08`) showed:
- `$0` across cost categories
- Empty top resources/SKU/image sections
- "No data available" despite known OCI costs

## Root Cause

1. Frontend date format was already correct.
- `input type="date"` sends ISO date values (`YYYY-MM-DD`).
- Requests were built correctly in `src/frontend/src/pages/Costs.jsx`.

2. Backend date handling had end-date boundary risk.
- Date-only `end_date` was parsed at midnight, which can exclude expected end-day data.

3. Primary runtime failure was request behavior on wide ranges.
- Cost page used `Promise.all(...)` and depended on live `/api/v1/costs/by-resource`.
- Axios global timeout is 15s; this call can exceed that for large windows, causing failure and empty UI fallback.

4. SKU category mapping lived in frontend.
- Classification logic duplicated in UI and depended on raw SKU payload quality.
- This should be deterministic and centralized in backend.

## Code Fixes Applied

### A) Backend date parsing + inclusive end-date logic

File: `src/backend/api/routes/costs.py`

- Added `_parse_cost_date(...)`:
  - Supports `YYYY-MM-DD` and full ISO datetime.
  - Treats date-only `end_date` as inclusive full day by converting to next-day exclusive boundary.
  - Normalizes all parsed values to UTC.
- Added range validation (`end_date > start_date`).

### B) Backend workload category normalization

File: `src/backend/api/routes/costs.py`

- Added `_normalize_workload_category(...)`.
- `/costs/by-resource` now enriches each row with:
  - `resource_type`
  - `normalized_workload_category`

This removes frontend dependence on ad-hoc SKU parsing.

### C) Reduce by-resource payload for Cost page

Files:
- `src/backend/services/cost_calculator.py`
- `src/backend/api/routes/costs.py`

- Added `include_skus` support.
- Backend can group only by `resourceId` when `include_skus=false`, reducing payload and latency for dashboard-style views.
- Default remains backward-compatible (`include_skus=true`).

### D) Frontend request robustness for custom ranges

Files:
- `src/frontend/src/services/api.js`
- `src/frontend/src/pages/Costs.jsx`

- `getCostsByResource(...)` now supports custom timeout (used as 60s on Cost page).
- Cost page requests:
  - `/costs/by-resource?...&include_skus=false`
- Cost page uses backend-provided `normalized_workload_category`.

## Verification Findings

Live endpoint checks (on current environment) showed non-zero data for:
- `/api/v1/costs/by-resource?start_date=2025-07-01&end_date=2026-02-08`
- `/api/v1/costs/databases?start_date=2025-07-01&end_date=2026-02-08`

This confirms data exists and issue was request/filter/runtime handling, not missing OCI cost data.

## Required Runtime Step

Restart backend service/container so patched code is loaded.

Suggested verification after restart:
1. Open Cost Analysis page and set custom range.
2. Confirm network request includes:
   - `start_date=YYYY-MM-DD`
   - `end_date=YYYY-MM-DD`
   - `include_skus=false`
3. Confirm response `data` is non-empty when costs exist.
4. Confirm `$0` and "No data" only appear when backend actually returns empty data.

## Files Changed

- `src/backend/api/routes/costs.py`
- `src/backend/services/cost_calculator.py`
- `src/frontend/src/services/api.js`
- `src/frontend/src/pages/Costs.jsx`
