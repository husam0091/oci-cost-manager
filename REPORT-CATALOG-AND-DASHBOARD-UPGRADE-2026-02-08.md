# OCI Cost Manager Upgrade: Report Catalog + Decision Dashboard

Date: 2026-02-08

## Delivered in this implementation pass

1. New backend dashboard contract:
- `GET /api/v1/dashboard/summary`
- Includes:
  - totals + previous period delta
  - top 5 services (+ filtering threshold)
  - normalized category counts with monthly/daily cost impact
  - storage/backup breakdown
  - unattached volume waste and top waste compartments
  - top resources with metadata + delta + top SKU
  - important compartments spotlight
  - governance quality metrics

2. Important compartments settings APIs:
- `GET /api/v1/admin/settings/important-compartments`
- `POST /api/v1/admin/settings/important-compartments`
- Stored in settings model:
  - `important_compartment_ids`
  - `important_include_children`

3. New report engine endpoint:
- `POST /api/v1/admin/exports/generate`
- Supports catalog report types:
  - `executive_summary_monthly`
  - `cost_by_compartment`
  - `showback_team_app_env`
  - `inventory_summary_compartment`
  - `storage_backup_governance`
  - `license_spend`
  - `anomaly_movers`
- Output artifacts:
  - `.xlsx`
  - `.manifest.json`
  - `.validation.json`
- Existing download behavior preserved:
  - `GET /api/v1/admin/exports/download/{name}`

4. Export history enrichment:
- `/api/v1/admin/exports/list` now surfaces report metadata where manifest exists.

5. Frontend refactors:
- `Dashboard.jsx` switched to `/dashboard/summary` and now shows decision-driving sections.
- `ExportReports.jsx` replaced dropdown with report catalog + filter panel + history badges + sidecar downloads.
- `Settings.jsx` now supports important compartments selection and save.

6. API client additions:
- `getDashboardSummary`
- `adminGenerateExport`
- `adminGetImportantCompartments`
- `adminSetImportantCompartments`

7. Tests added:
- `test_dashboard_summary_end_date_is_inclusive`
- `test_export_generate_creates_manifest_and_validation`

## Files changed

- `src/backend/core/models.py`
- `src/backend/core/database.py`
- `src/backend/api/routes/dashboard.py` (new)
- `src/backend/api/routes/admin.py`
- `src/backend/main.py`
- `src/backend/tests/test_dashboard_and_exports.py` (new)
- `src/frontend/src/services/api.js`
- `src/frontend/src/pages/Dashboard.jsx`
- `src/frontend/src/pages/ExportReports.jsx`
- `src/frontend/src/pages/Settings.jsx`
- `src/frontend/src/utils/dateRanges.js`

## Important notes

1. Backend/frontend restart required to activate new endpoints/UI wiring.
2. Existing export snapshot endpoints remain available and were not removed.
3. Docker workflow not changed.

## Remaining enhancements (next iteration)

1. Deep rule engine (virtual tags + priority + shared allocations) with dedicated tables.
2. Report sheet refinements for full Tier 1/2/3 parity and richer per-report formatting.
3. More complete anomaly baseline math and trend visual components.
4. Additional contract tests for "Other" bucket behavior and stable column headers across all report types.

