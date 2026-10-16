# Commitment vs Spend — Interface 2.3.0

The `/commitments` page compares a selected OCI Universal Credits contract (or a clearly marked manual contract) with actual OCI Usage API COST data. It does not substitute list prices, backup counts, SKU quantities or inferred license charges for billed spend.

## Prerequisite: January YTD parsing

`get_usage_summary()` accepts a null computed amount **only when OCI explicitly reports computed quantity zero**. Missing quantity, positive quantity or negative quantity with no amount still fails. The Object Storage Requests January fixture includes blank currency and zero quantity. Blank currency is retained as unspecified, never relabeled USD. Billing errors log their exception with a correlation ID: parse errors return `502 / OCI_BILLING_PARSE_ERROR`; upstream availability errors return `503 / OCI_BILLING_UNAVAILABLE`. Usage pagination now follows every `opc-next-page` with the existing global throttle and transient retries; failures do not silently return a partial total.

## OCI discovery and provenance

Each operation has an independent status, row count, HTTP status/error code and redacted OCI error text in `subscription_sync_runs.sources`. The Commitments page and **Diagnostics** (`/logs`) show these results. Empty, forbidden/not found, unavailable and missing subscription identifier are distinct outcomes. A 404 does not prove a policy is missing: home region, tenancy ownership, subscription entitlement and endpoint availability can also matter.

| Source | Operations | Treatment |
| --- | --- | --- |
| `oci:organizations` | Owned and assigned subscription lists, then their detail operations | Installed SDK uses `list_subscriptions()` without compartment ID; assigned subscriptions require the root tenancy. Preserve SKU metadata and commercial payment model; do not value a contract from SKU quantity. |
| `oci:onesubscription` | Subscription, subscribed services, commitments, billing schedules, aggregated computed usage | Reuse Organizations' subscription number/classic ID, or an optional subscription ID on a manual contract. The subscription API requires an identifier; it cannot enumerate a tenancy with only compartment ID. Use `list_aggregated_computed_usages`, the installed SDK method. Child APIs fail independently. |
| Existing fallback helper | `OCIClientService.get_subscriptions()` | Retained for deployments needing its three fallback APIs. Legacy inferred prices/dates are not accepted as confirmed monetary commitments. |
| `oci:usage` | COST plus independent CREDIT, EXPIREDCREDIT and ALLCREDIT queries | COST is the actual-spend source. Negative COST values remain credits. Additional credit query totals are recorded independently and never added to COST again. |
| `manual` | Confirmed value/currency/start/end/term entered by admin or FinOps | Persisted with actor and source. Optional OCI subscription ID unlocks OneSubscription requests when Organizations is forbidden. Never merged silently with OCI values. |

### Auto-renewing Universal Credits terms (production follow-up)

An auto-renewing parent can have `time_end = null` while its subscribed services carry dated annual financial terms. Discovery now expands **each child service term before validating dates**. It preserves the child's start/end/status/total_value (including zero addenda and expired history), inherits currency, and links the term to its parent classic subscription ID and Organizations record. Detailed `SubscribedServiceClient` identifiers are kept separate from embedded order-line IDs; commitment calls use only the detailed subscribed-service ID. The active, positive-value Universal Credits term is the default; an addendum with zero value is never added to the annual commitment or selected as its substitute.

Explicit `CLOUDCM` / `Universal Credits` evidence identifies infrastructure agreements. Fusion ERP/HCM/EPM/Planning contracts remain visible as SaaS metadata, but infrastructure consumption, utilisation and breakdowns are withheld, including for old persisted periods. Unclassified agreements also fail closed. Existing manual contracts remain explicitly infrastructure references. No data cleanup or production-row rewrite is required for these read-time safeguards.

Automatic sync now fetches COST only for active, positive-value infrastructure terms. Expired history, SaaS agreements, zero addenda and metadata-only records do not trigger historical resource scans. Daily history is grouped by **service, compartment and region**, preserving exact anniversary date slicing without resource/day explosion. Only the current anniversary/calendar windows request **MONTHLY** resource detail for team allocations; identical windows share the request. Resource detail is accepted only when its currency total reconciles with the corresponding aggregate to one cent. Historical expired terms are retained as contract metadata; this sync does not automatically backfill their spend. The Usage API cutoff is the current calendar month plus the previous 12 months (October 2025 onward for October 2026). Older complete saved calendar snapshots can be reused; otherwise those periods are marked outside retention with unknown actuals, so a partial history never becomes a falsely complete term total.

CREDIT / EXPIREDCREDIT / ALLCREDIT requests now send `group_by = None`; the shared Usage wrapper also suppresses its automatic currency grouping for these modes. Returned currencies remain separate; missing currency is not inferred.

The user's production inspection reports an active Universal Credits term of **USD 1,710,000** starting **2026-01-23**, plus a zero addendum and expired terms, under an open-ended parent. These are user-supplied observations, not a live query from this environment. Regression fixtures cover this topology and value. The comparison uses spend starting January 23, **not** January 1 YTD; the reported USD 1.28M YTD must not be assumed to be term consumption. A new deployed sync is still needed to confirm the live result.

A OneSubscription parent may have no monetary total. Explicit `subscribed_services[].total_value` values are additive only when **every** service has the same start/end dates as the parent. Otherwise the amount remains unavailable. Commitment quantities, installment schedules and current remaining balances are evidence, not assumed annual values. Organizations metadata can be successful even when it does not contain enough contract data to build a dated monetary comparison.

Raw source evidence is retained in the contract record, not returned in chart payloads. Monetary contracts retain source and computed timestamp. Renewals use distinct source/identifier/start/end keys, preserving historical periods. Overlapping contracts remain separate: selecting two overlapping agreements is not permission to add their allowances or duplicate tenancy consumption.

## IAM checklist

Replace `<group>` with the correct group (domain-qualified when appropriate). These are read-only statements to be reviewed/applied by the tenancy IAM administrator; this feature changes no IAM policies.

```text
Allow group <group> to read organizations-subscriptions in tenancy
Allow group <group> to read organizations-assigned-subscriptions in tenancy
Allow group <group> to read usage-report in tenancy
```

The first two statements follow Oracle's [subscription access examples](https://docs.oracle.com/en-us/iaas/Content/applications-manager/manage-access.htm). The [Organizations permission reference](https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/organizationsreference.htm) maps List/Get subscriptions and assigned subscriptions to their distinct resource permissions. Usage access is described in [Cost Analysis access](https://docs.oracle.com/en-us/iaas/Content/Billing/Concepts/costanalysisoverview.htm).

**OneSubscription and OSP:** a universally valid least-privilege policy statement could not be confirmed from Oracle's public reference for these account-specific endpoints. The UI deliberately does not present an invented `read onesubscription` or `read osp-subscriptions` policy as a verified fix. Diagnostics retain the exact failed operation, OCI code and service message so the tenancy administrator/Oracle support can confirm the account's required entitlement and policy. Do not broaden access to `manage all-resources` to make discovery pass. Missing subscription identifier is a separate prerequisite, not an IAM failure.

References: [OneSubscription list prerequisites](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/onesubscription/subscription/subscription/list.html), [CommitmentClient](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/onesubscription/client/oci.onesubscription.CommitmentClient.html), [Organizations SDK](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/tenant_manager_control_plane.html). Runtime calls match the SDK pinned by this repository.

## Period accounting

Dates are UTC dates with **exclusive ends**. A 15 March anniversary yields 15 October through 15 November exclusive (14 November inclusive in ordinary reporting language). Month arithmetic is anchored to the original day: 31 January → 28/29 February → 31 March, without drift. Calendar mode splits the same anniversary allowance across calendar boundaries.

Monthly base allowance = total value / term months. Each anniversary month allocates that base across its actual days. Calendar windows sum the daily portions; shortened final months prorate by the nominal anniversary month's length. Consequently a shortened term's distributed allowance can be below total stated commitment; the UI labels prorating as an estimate. Manual term months must match the actual number of full/partial anniversary windows, at most 120.

All facts carry their original currency. APIs select the contract currency, keep negative amounts negative, and never sum EUR into USD. Incomplete periods expose null actual/forecast, not zero. Confirmed empty Usage API results can be zero. Linear forecasts use observed net spend / elapsed UTC days × term days; utilisation is not capped at 100%. Region filtering narrows spend while retaining the **whole contract's allowance**, explicitly labeled. A whole-tenancy allowance is not a regional or team budget.

Charts show the cumulative committed ramp, actuals and dashed forecast; last 12 monthly allowances vs actuals; active-month services; and top compartments or allocated teams as a share of monthly allowance. Credits are separate table columns. A service links into the existing Spend explorer with service and date selection. XLSX and CSV exports use the existing configured export directory/download conventions and mark allowance/forecast columns as estimates.

**Attribution limit:** COST describes tenancy consumption, not a proven subscription allocation. This comparison is labeled accordingly; rated OneSubscription evidence is saved separately. Do not call the comparison a reconciled invoice or the cost funded by a particular agreement.

## Persistence and execution

Alembic `20261017_01` adds `subscription_contracts`, `subscription_periods`, `subscription_sync_runs` and `settings.commitments_enabled` (default true). The existing `init_db()` deployment compatibility path creates the new tables and adds the setting for installations that do not run Alembic separately. The new migration is idempotent against that path. No production data is edited during development.

`jobs.subscription_sync` runs on the existing **heavy** Celery queue, tracks its parent `job_runs` row, checkpoints each contract/mode, and persists a source report. A PostgreSQL transaction advisory lock on a dedicated connection prevents simultaneous subscription syncs across workers, including behind transaction-mode PgBouncer. It does not acquire or modify the inventory scan lock. APScheduler enqueues it daily and inventory completion enqueues it through `_queue_post_scan_refresh_jobs`. The feature flag disables enqueueing and API access; the admin feature-flag UI exposes it.

Initial ingestion loads historical calendar chunks needed for the active infrastructure term-to-date accuracy. Subsequent syncs refresh the current and previous 12 months, reuse complete older saved calendar chunks, and recompute anniversary/calendar views. COST requests reuse `get_usage_summary()` and its throttle. Allocation enrichment uses existing resource inventory and allocation rules; unknown/deleted resources remain unallocated. Charts do not fetch raw SKU lists.

Read endpoints use synchronous FastAPI handlers (worker thread pool). Overview/periods and breakdown use the existing atomic file cache with TTL 600; cache keys include principal, source revision, period mode and region. Small contract/diagnostic metadata reads stay fresh from the database. Gzip remains supplied by existing FastAPI/nginx configuration. Chart data is aggregated server-side, service/group breakdowns are top ten plus an explicit Other bucket, and contracts are paginated at 100. Recharts 3 is lazily loaded with the new page, keeping it out of the initial application bundle.

Tenancy-wide contracts are deliberately unavailable to principals restricted to particular teams/apps/envs/compartments: no allocation of the contract allowance has been authorized for those scopes. They receive 403 and guidance to use the scoped Spend explorer. Read-only tenancy users can read; only admin/FinOps can create contracts or sync. Team cost shares are not assigned team budgets.

## API

All paths are under `/api/v1/subscriptions` and require the existing authenticated cookie.

| Method/path | Purpose |
| --- | --- |
| GET `/contracts?offset=0&limit=100` | Source-labeled contracts and diagnostics |
| POST `/contracts` | Manual contract; name, total_value, ISO currency, start_date, exclusive end_date, term_months; optional oci_subscription_id |
| POST `/sync` | Queue heavy job; poll existing `/api/v1/jobs/{job_id}` |
| GET `/overview?contract_id=...&mode=subscription&region=all` | KPIs, term trajectory, bounded period summaries, freshness and estimates |
| GET `/periods?contract_id=...&months=12&mode=calendar` | Period summaries |
| GET `/breakdown?period=<period-id>&group_by=service` | Top services/compartments/teams plus Other |
| GET `/diagnostics` | Last sync's per-source outcomes and policy checklist |
| GET `/export?contract_id=...&mode=subscription&format=csv` | CSV or XLSX download; accepts region |
| GET root (existing route) | Reuses persisted contracts and currency-separated YTD/MTD. No longer hardcodes committed zero or compares calendar YTD with a subscription term. |

The old Dashboard manual input remains a separately labeled, browser-local USD reference; it is not used for inferred term utilisation. Use dated persisted contracts on Commitments for accounting.

## Validation and deployment

Run the normal backend tests, frontend tests/lint/build and security response leak gate. `scripts/benchmark_commitments.py` runs a local synthetic SQLite/ASGI probe (no OCI or production DB), comparing idle health latency with health latency during a cold chart request, checking JSON below 300 KB, and reporting process RSS before/after. It is not a production memory or SDK-latency benchmark.

Observed local probe (13 periods / 13,000 facts): idle health p95 **0.449 ms**; health during cold read p95 **14.364 ms** including heartbeat scheduling gaps; cold overview **45.969 ms**; JSON **6,277 bytes**; RSS **148.62 → 154.77 MiB**. Hardware, Python allocator and workload affect these results. No claim is made that production memory matches this fixture.

Delivery is one PR to **master**, version **2.3.0**. No production restart or scan interruption is performed by creating the PR. Wait for inventory completion before applying the existing deployment path:

```bash
./deploy/update-app.sh
```

After deploying, check `/release.json` for `2.3.0`, open Commitments, run **Sync subscriptions**, wait for its job, and inspect the source checklist. If metadata lacks a monetary amount or IAM blocks discovery, enter a confirmed manual contract (and optional OCI subscription identifier). Confirm the same date window/currency/region in OCI Cost Analysis, inspect January YTD, verify negative credits, and compare actual production health p95/RSS with the 2.2.0 baseline.

### Tenancy verification status at PR creation

| Source | Live result |
| --- | --- |
| Organizations owned/assigned | Not queried: this coding environment has no provided production connection |
| OneSubscription services/commitments/schedules/rated usage | Not queried; SDK signatures and independent failures tested with fixtures |
| COST / credit variants | Not queried in the tenancy; parsing, pagination and currency accounting tested with fixtures |
| Manual fallback | Local API, validation, persistence and export tests pass |

The first deployed sync supplies actual tenancy-specific results in Diagnostics. This report does not invent source responses or assume IAM is the only possible cause.

## Explicit unavailable capabilities

Future credit-expiry alerts require a source with **dated future balances**; EXPIREDCREDIT aggregate usage dates are not assumed to be future expiry dates. The UI states expiry data is unavailable instead of fabricating the requested 60-day alert. PAYG-rate comparison remains unavailable unless a compatible rate card/quantities are supplied; discounted actual spend is not relabeled a PAYG estimate. Support Rewards, opt-in budget creation, outbound alert notifications and assigned team allowance chargeback are not implemented in this release. Forecast overage, low utilisation and stale-data banners are implemented.

## Prompt 0 merge gate: canonical terms and audited source lines

`subscription_contract_lines` retains every financial line and its original service/order identifiers. Synchronization now produces one canonical term for matching **parent + currency + exact dates**, or an explicit `subscription_term_id` / `contract_term_id` shared by those lines. Different overlapping date windows are **not** merged solely because they intersect; ordinary master agreement/order numbers can span renewals and are insufficient proof. When a source does not supply a verified relationship, distinct dated terms remain separate rather than inventing a larger commitment.

The Tamam-shaped fixture uses explicit term identity for its three different 2025 windows, exact bounds for the two 2024 lines, and a uniquely contained 2026 zero addendum: it produces one active USD 1.71M infrastructure term and three expired infrastructure terms. This tests the requested shape; it does not assert that unprovided production identifiers have been verified. Ambiguous zero addenda remain unassigned audit lines, never selectable commitments.

Organizations rows and old aggregate parents are metadata, not extra monetary contracts. Original rows are retained with canonical aliases; existing reconciled period usage is reused once (never summed across concurrent lines), while allowances are recalculated from the grouped commitment. The next subscription sync performs this idempotent transition after deployment. Read-only APIs follow old term aliases and expose `/subscriptions/contracts/{id}/lines` for audit. The selector groups Infrastructure, SaaS, Expired and Manual; each label includes dates instead of repeating a year-only name. A new migration (`20261017_02`) creates the child-line table; the normal `init_db()` compatibility path also creates it.
