> [!NOTE]
> OCI Cost Manager is an active project. Features, APIs, and configuration options may change between releases.

<div align="center">

# OCI Cost Manager

**Enterprise FinOps platform for Oracle Cloud Infrastructure**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi)](src/backend)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](src/frontend)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql)](docker-compose.yml)

[Getting Started](#quick-start) · [Features](#features) · [Architecture](#architecture) · [Configuration](#configuration) · [Contributing](#contributing)

</div>

---

## What is OCI Cost Manager?

OCI Cost Manager is a self-hosted cost intelligence console for Oracle Cloud Infrastructure. It connects directly to your OCI tenancy, scans resources across multiple regions, and surfaces real-time cost analytics, budget tracking, governance actions, and compliance reporting — all from a single dashboard.

Built for FinOps teams, cloud architects, and platform engineers who need more than the native OCI console provides: per-resource license cost detection, async report generation, role-based access control, and a clean multi-persona UI that surfaces the right data to the right person.

---

## OCI Cost Manager in Action

| Dashboard | Resources | Costs |
|-----------|-----------|-------|
| Live spend snapshot, trend charts, persona-ordered navigation | Per-resource inventory with marketplace license detection | Daily/monthly cost breakdowns by compartment and service |

| Budget | Governance | Recommendations |
|--------|------------|-----------------|
| Budget utilisation with threshold alerts | Tag compliance, security posture, and policy checks | Right-sizing suggestions with estimated savings |

---

## Features

- **Multi-region scanning** — scan all enabled OCI regions in a single run; switch regions instantly from the top navigation bar
- **Real-time cost analytics** — rolling 30-day spend per resource, cost by compartment, service, and day
- **Marketplace license detection** — automatically estimates monthly license costs for F5 BIG-IP, Palo Alto VM-Series/Panorama, Fortinet FortiGate/FortiProxy/FortiManager/FortiAnalyzer, Microsoft SQL Server, and Windows Server images
- **MySQL HeatWave cost estimation** — derives OCPU count from shape name and adds HeatWave cluster premium when applicable
- **Volume backup cost estimation** — estimates backup storage spend at $0.026/GB/month
- **Budget tracking** — set budgets per compartment or globally; visual utilisation bars with configurable alert thresholds
- **Governance & compliance** — tag policy checks, security posture scanning, and automated remediation actions
- **Export reports** — generate JSON, CSV, and XLSX reports asynchronously; download from the UI when ready
- **Role-based access control** — `admin`, `editor`, and `viewer` roles; persona-aware navigation ordering (Executive / FinOps / Engineer)
- **Portal SSL** — upload PEM or PFX certificates from the Settings page; nginx auto-configures HTTPS/443
- **Async job queue** — Celery workers handle long-running scans and exports; frontend polls progress in real time
- **Audit logging** — all governance actions and configuration changes are written to the event log

---

## Product Editions

| Feature | Community | Enterprise |
|---------|-----------|------------|
| Multi-region scanning | ✅ | ✅ |
| License cost detection | ✅ | ✅ |
| Dashboard & cost analytics | ✅ | ✅ |
| Budget tracking | ✅ | ✅ |
| Governance actions | ✅ | ✅ |
| Export reports | ✅ | ✅ |
| RBAC (admin/editor/viewer) | ✅ | ✅ |
| Portal SSL (HTTPS/443) | ✅ | ✅ |
| SSO / SAML | ❌ | ✅ |
| Multi-tenancy | ❌ | ✅ |
| Priority support | ❌ | ✅ |

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Clone & Build](#clone--build)
4. [Common Commands](#common-commands)
5. [Configuration](#configuration)
6. [OCI Credentials](#oci-credentials)
7. [Multi-Region Setup](#multi-region-setup)
8. [Portal SSL](#portal-ssl)
9. [Architecture](#architecture)
10. [API Conventions](#api-conventions)
11. [Roadmap](#roadmap)
12. [License](#license)
13. [Contributing](#contributing)
14. [Get in Touch](#get-in-touch)

---

## Prerequisites

- **Docker Desktop** 4.x or later (with Compose v2)
- **OCI account** with at least one tenancy and a user API key
- 2 GB RAM minimum; 4 GB recommended for multi-region deployments
- Ports `8080` (HTTP) and `8443` (HTTPS, optional) available on the host

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/husam0091/oci-cost-manager.git
cd oci-cost-manager

# 2. Start  (no pre-configuration needed — OCI credentials are configured via the UI)
docker compose up -d --build

# 3. Open
open http://localhost:8080
# Default credentials: admin / admin  (update immediately in Settings)
```

The app starts with no OCI credentials pre-loaded. On first login, go to **Settings → OCI Connection** to enter your tenancy OCID, user OCID, fingerprint, region, and upload your PEM private key. Once saved, trigger an initial scan from **Settings → Scan Now**.

---

## Clone & Build

```bash
git clone https://github.com/husam0091/oci-cost-manager.git
cd oci-cost-manager
```

Start the stack:

```bash
docker compose up -d --build
docker compose logs -f backend   # watch startup
```

### Frontend (standalone dev)

```bash
cd src/frontend
npm ci
npm run dev          # Vite dev server → http://localhost:5173
npm run build        # Production build → dist/
npm run preview      # Preview production build
npm run lint         # ESLint
```

### Backend (standalone dev)

```bash
cd src/backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Celery worker (separate terminal)
celery -A worker.celery_app worker -Q default,heavy -l INFO
```

---

## Common Commands

```bash
# Restart a single service
docker compose restart backend

# View logs
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# Run backend tests
docker compose exec backend pytest -q
docker compose exec backend pytest tests/test_costs.py
docker compose exec backend pytest -k "test_dashboard"

# Code quality
docker compose exec backend black .
docker compose exec backend ruff check .

# Stop everything
docker compose down

# Full reset (removes volumes — deletes all data)
docker compose down -v
```

---

## Configuration

All backend settings are resolved from environment variables defined in `.env` (template: `.env.example`). They map to the Pydantic Settings class in `src/backend/core/config.py`.

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` |
| `REDIS_URL` | Redis URL for caching | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Celery broker | `redis://redis:6379/1` |
| `CELERY_RESULT_BACKEND` | Celery results | `redis://redis:6379/2` |
| `SECRET_KEY` | JWT signing key — **change this** | — |
| `OCI_CONFIG_REGION` | Primary OCI region identifier | `us-ashburn-1` |
| `OCI_CONFIG_TENANCY` | OCI tenancy OCID | — |
| `OCI_CONFIG_USER` | OCI user OCID | — |
| `OCI_CONFIG_FINGERPRINT` | API key fingerprint | — |
| `OCI_CONFIG_KEY_CONTENT` | PEM private key (inline) | — |
| `PORTAL_SSL_DIR` | Directory where SSL certs are stored | `/app/portal-ssl` |
| `ENABLE_DEMO_MODE` | Makes all mutating actions read-only | `false` |

---

## OCI Credentials

OCI Cost Manager uses the standard OCI API key authentication. You need:

1. An OCI user with `inspect` (minimum) or `read` permissions on the tenancy
2. An RSA API key pair — [generate one in the OCI Console](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm)
3. The key fingerprint from the Console after uploading the public key

Paste the **private key PEM content** (the full `-----BEGIN RSA PRIVATE KEY-----` block) into `OCI_CONFIG_KEY_CONTENT` in `.env`, or set `OCI_CONFIG_KEY_FILE` to the path of the key file on disk.

For least-privilege access the following IAM policy is sufficient for read-only scanning:

```hcl
Allow group FinOpsReaders to inspect all-resources in tenancy
Allow group FinOpsReaders to read usage-reports in tenancy
Allow group FinOpsReaders to read usage-budgets in tenancy
```

---

## Multi-Region Setup

OCI Cost Manager can scan multiple OCI regions in a single sweep and lets you filter data per region from the top navigation bar.

1. Log in as `admin` and navigate to **Settings → Scan Regions**
2. Your primary region (from `.env`) is shown as read-only
3. Add additional regions (e.g. `me-riyadh-1`, `eu-frankfurt-1`) using the input field
4. Click **Save**, then trigger a new scan — each region is scanned in sequence and resources are tagged by region
5. Use the **Region** dropdown in the top bar to filter all pages to a single region, or select **All Regions**

> [!TIP]
> If a newly added region shows no resources, trigger a manual scan from **Settings → Scan Now**. Resources only appear after the first successful scan of that region.

---

## Portal SSL

OCI Cost Manager supports HTTPS/443 via uploadable certificates managed through the Settings page.

1. Navigate to **Settings → Portal SSL (HTTPS/443)**
2. Upload a **PFX** bundle (certificate + private key in one file, optional passphrase) **or** separate PEM cert + key files
3. Optionally upload an intermediate CA chain or root CA certificate
4. The backend stores the certificate files and updates nginx configuration automatically
5. After upload, reload nginx on the host: `sudo nginx -t && sudo systemctl reload nginx` (or restart the frontend container)

Supported formats: PEM, DER, PFX/PKCS#12.

> [!NOTE]
> Certificate files are stored in the `portal_ssl` Docker named volume and shared between the backend and frontend containers. The private key is stored with `0600` permissions.

---

## Architecture

### Services

```
┌─────────────────────────────────────────────────────────┐
│                     Docker Compose                      │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌───────────────────┐  │
│  │ frontend │    │ backend  │    │      worker       │  │
│  │  React   │───▶│ FastAPI  │───▶│  Celery (async)   │  │
│  │  + nginx │    │  :8000   │    │  default + heavy  │  │
│  │  :8080   │    └────┬─────┘    └─────────┬─────────┘  │
│  │  :8443   │         │                    │            │
│  └──────────┘    ┌────▼──────────────────▼─┐           │
│                  │        Redis :6379        │           │
│                  │  DB0 cache · DB1 broker   │           │
│                  │  DB2 results              │           │
│                  └──────────────────────────┘           │
│                         │                               │
│                  ┌──────▼──────┐                        │
│                  │  pgbouncer  │                        │
│                  │  :5432      │                        │
│                  └──────┬──────┘                        │
│                         │                               │
│                  ┌──────▼──────┐                        │
│                  │ PostgreSQL  │                        │
│                  │    :5432    │                        │
│                  └─────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

### Key Data Flows

**Dashboard (fast path)**
Route → Redis cache → return snapshot + "updating" badge. Stale data triggers async Celery refresh in the background.

**Resource scan (async)**
`POST /api/v1/admin/scan/run` → returns `job_id` immediately → Celery worker iterates enabled regions → calls OCI APIs → stores tagged resources in PostgreSQL → frontend polls `/api/v1/jobs/{job_id}`.

**Cost aggregation**
Celery task reads raw cost rows → computes breakdowns by day/month/compartment/service → writes to aggregate tables + Redis (TTL ~1 hr).

**Report export**
Frontend triggers format selection → queued Celery job → generates JSON/CSV/XLSX → frontend polls progress → download link when ready.

### Backend Structure

```
src/backend/
├── main.py                   # FastAPI app, route registration, lifespan
├── worker.py                 # Celery app bootstrap
├── api/
│   ├── routes/               # ~22 route modules (one per domain)
│   └── schemas/              # Pydantic request/response models
├── core/
│   ├── config.py             # Pydantic Settings — all env vars
│   ├── database.py           # SQLAlchemy engine, session, migrations
│   ├── models.py             # ORM models for all tables
│   ├── auth.py               # JWT authentication
│   ├── rbac.py               # Role-based access control
│   ├── cache.py              # Cache abstraction interface
│   └── redis_cache.py        # Redis implementation
└── services/
    ├── aggregate_engine.py   # Cost aggregation + snapshot computation
    ├── oci_client.py         # OCI SDK wrapper (multi-region factory)
    ├── budget_engine.py      # Budget validation logic
    ├── scanner.py            # OCI resource scanner (multi-region)
    ├── actions_engine.py     # Governance action dispatch
    ├── executors/            # Dry-run / local action handlers
    └── executors_oci/        # Real OCI action handlers
```

### Frontend Structure

```
src/frontend/src/
├── App.jsx                         # Root router, auth, region state
├── pages/                          # One component per route
│   ├── Dashboard.jsx
│   ├── Resources.jsx               # License & cost detection
│   ├── Costs.jsx
│   ├── Budget.jsx
│   ├── Governance.jsx
│   ├── Recommendations.jsx
│   ├── Actions.jsx
│   ├── Logs.jsx
│   ├── ExportReports.jsx
│   └── Settings.jsx                # SSL upload, regions, profile
├── services/api.js                 # Axios client + all API wrappers
├── components/GlobalStatusBar.jsx  # Integration health indicator
├── hooks/useStaleSnapshotQuery.js  # Stale-while-revalidate pattern
├── utils/dateRanges.js             # Date range helpers
└── constants/copy.js               # UI text labels
```

---

## API Conventions

- All routes versioned under `/api/v1/`
- Async jobs return `{ job_id, status_url }` immediately — callers poll `/api/v1/jobs/{job_id}`
- All responses follow `{ success: bool, data: ... }` envelope
- Audit events written via `event_logger.py` for all governance and admin actions
- Cache keys follow pattern `{domain}:{identifier}:{params_hash}`

---

## Roadmap

- [ ] Anomaly detection — flag unexpected cost spikes automatically
- [ ] Cost allocation tags — custom tag-based cost attribution rules
- [ ] Scheduled reports — send PDF/XLSX summaries via email on a cron schedule
- [ ] OCI Budgets API integration — sync OCI native budgets bidirectionally
- [ ] Slack / Teams alerts — push budget threshold alerts to messaging platforms
- [ ] SSO / SAML — enterprise identity provider integration
- [ ] Multi-tenancy — manage multiple OCI tenancies from a single instance

---

> [!WARNING]
> OCI Cost Manager stores your OCI private key in the database (encrypted at rest if `SECRET_KEY` is set) and writes it to disk inside the container. Treat the `SECRET_KEY` environment variable and your OCI API key with the same care as production credentials.

> [!CAUTION]
> Governance actions (stop instance, delete resource, resize shape) are **irreversible** in live mode. Use `ENABLE_DEMO_MODE=true` in non-production environments to make all mutating actions read-only.

---

## License

[MIT License](LICENSE) — free to use, modify, and distribute.

---

## Contributing

Pull requests are welcome. For significant changes, please open an issue first to discuss the proposed change.

```bash
# Fork & clone
git clone https://github.com/YOUR_USERNAME/oci-cost-manager.git

# Create a feature branch
git checkout -b feat/your-feature

# Make changes, run tests
docker compose exec backend pytest -q

# Push and open a PR
git push origin feat/your-feature
```

Please follow the existing code style — `black` + `ruff` for Python, ESLint for JavaScript.

---

## Get in Touch

- **Issues & bugs** — [GitHub Issues](https://github.com/husam0091/oci-cost-manager/issues)
- **Feature requests** — open a GitHub Discussion or Issue with the `enhancement` label
- **Security vulnerabilities** — please report privately via GitHub's security advisory feature

---

<div align="center">

Built for OCI FinOps teams who need cost visibility beyond the native console.

</div>

### Runtime reliability and architecture

See [Interface 2.2 runtime guide](docs/runtime-reliability-2.2.md) for scan recovery,
compartment checkpoints, cache/payload fixes, deployment checks, and the recommended
migration to durable inventory jobs and database-backed billing ingestion.
