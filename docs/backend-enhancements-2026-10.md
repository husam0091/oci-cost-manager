# OCI spend explorer and reliability update

## What changed

Cost Analysis now follows one flow: select UTC dates and region, filter by service, then open a resource for billed SKUs, quantities, units and effective billed rates. The new authenticated `GET /api/v1/billing/spend` reads OCI Usage API charges; failed calls never become sample or estimated bills. Totals cover every page; CSV export explicitly downloads the current page.

Charges, negative credits/adjustments and net totals remain separate for each currency. Inventory enriches names, compartment and region; unrestricted users retain unattributed charges. Scoped users see only resources whose assigned scope can be verified. Licensing labels require billed-SKU evidence: BYOL, License Included, metered software charge, or Not determined. PAYG describes a commercial plan, not a license model inferred from a server image.

Removed duplicate summary/mover/database panels from Cost Analysis, four unused resource-filter states, and unused Recharts/manual bundling (35 dependency packages removed). Dashboard cost increases now use a warning color and decreases use a savings color.

## Backend fixes

- Billing explorer: inclusive end dates, UTC boundaries, maximum 366-day range, pagination, provenance, per-principal 10-minute cache and explicit refresh.
- Queries respect OCI's four-group limit, including currency. Overview groups by service/SKU/resource/currency; resource details group by SKU/part number/unit/currency.
- Correct `computed_quantity` extraction; only display quantity when grouped by unit. Preserve zero computed cost; reject missing amounts rather than inventing zero.
- Apply allocation filters before pagination, return accurate filtered totals, deterministic ordering, status filtering and allowlisted sorting. Rule-derived filters stream candidates in batches; broad queries still evaluate all candidate allocations.
- Budget-status caches now include identity, role, scope and UTC day to prevent cross-user response reuse.
- Atomic file-cache replacement preserves previous valid entries if serialization fails and rejects non-finite JSON. Concurrent clears tolerate already-deleted files.
- Calendar-date serialization no longer shifts Riyadh dates backward; shared API wrappers use the corrected helper.
- CI covers main/master, runs calendar regressions and fixes backend working-directory/security-search checks. Search errors now fail the gate.

## Billing interpretation

This is OCI-reported `computedAmount`, not an independently generated final invoice. Recent usage can lag. Taxes, fees, adjustments, Marketplace agreements and subscription discounts need invoice reconciliation. Effective billed rate is cost divided by usage, not a public price or quote. External BYOL licenses/support are outside this view and are not assumed free. A negative amount is preserved as a credit/adjustment without guessing the credit program.

No live tenancy credentials were available in the development session. SDK behavior is tested with contract fakes. After deploying to the configured server, reconcile with OCI Cost Analysis using identical UTC dates, region, service, resource and currency. Inspect a Windows/SQL/database SKU and verify PAYG/entitlement terms in the applicable agreement. Simulate a connection failure: the page must show an error, not a zero bill.

No database migration is required. Existing API routes remain available. No infrastructure-changing actions are executed by this feature.

## Validation

From `src/backend`, use an isolated SQLite database:

```sh
DATABASE_URL=sqlite:///./test.db PYTHONPATH=. pytest -q
python -m compileall -q api core services tests
```

From `src/frontend`:

```sh
npm ci
npm test
npm run lint
npm run build
```

The repository originally had only master. Main is initialized from that history for the requested merge; existing deployments tracking master need to select main to receive this update.

## Oracle references checked 16 October 2026

- [Cost Analysis: grouping, currency and quantity](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/costanalysisoverview.htm)
- [Cost Reports: billed cost and invoice differences](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/costusagereportsoverview.htm)
- [Microsoft licensing on OCI](https://docs.oracle.com/en-us/iaas/Content/Compute/References/microsoftlicensing.htm)
- [BYOL to PaaS FAQ](https://www.oracle.com/cloud/bring-your-own-license/faq/)
