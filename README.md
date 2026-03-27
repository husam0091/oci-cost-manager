## Project Overview

OCI Cost Manager is an enterprise FinOps platform for Oracle Cloud Infrastructure. It provides real-time cost analytics, resource inventory, budget tracking, governance actions, and async report generation.

## Commands

### Docker (primary development approach)
```bash
cp .env.example .env          # First-time setup
docker compose up -d --build  # Start all services
docker compose logs -f backend # Follow backend logs
docker compose restart backend # Restart single service
```

Services run at: Frontend `http://localhost:8080`, Backend API `http://localhost:8000`

### Frontend (`src/frontend/`)
```bash
npm ci              # Install dependencies
npm run dev         # Vite dev server
npm run build       # Production build → dist/
npm run lint        # ESLint
npm run preview     # Preview production build
```

### Backend (`src/backend/`)
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000  # Run backend locally
celery -A worker.celery_app worker -Q default,heavy -l INFO  # Run Celery worker

# Tests
pytest -q                    # Full test suite
pytest tests/test_costs.py   # Single test file
pytest -k "test_dashboard"   # Filter by name

# Code quality
black .                       # Format
ruff check .                  # Lint
```

## Architecture

### Services (Docker Compose)
- **postgres** (PostgreSQL 16) — primary data store
- **pgbouncer** — connection pooling (transaction mode, 50 conn)
- **redis** — caching (DB 0), Celery broker (DB 1), Celery results (DB 2)
- **backend** — FastAPI application
- **worker** — Celery worker consuming `default` and `heavy` queues
- **frontend** — React app served by Nginx, which also reverse-proxies `/api/` to backend

### Backend Structure

```
src/backend/
├── main.py              # FastAPI app, route registration, lifespan
├── worker.py            # Celery app bootstrap
├── api/routes/          # Route handlers (~22 modules, one per domain)
├── api/schemas/         # Pydantic request/response models
├── core/
│   ├── config.py        # Settings from env vars (single source of truth)
│   ├── database.py      # SQLAlchemy engine, session factory
│   ├── models.py        # ORM models for all tables
│   ├── auth.py          # JWT authentication
│   ├── rbac.py          # Role-based access control
│   ├── cache.py         # Cache abstraction interface
│   └── redis_cache.py   # Redis implementation
└── services/
    ├── aggregate_engine.py   # Cost aggregation + snapshot computation
    ├── oci_client.py         # OCI SDK wrapper
    ├── budget_engine.py      # Budget validation logic
    ├── scanner.py            # OCI resource scanning
    ├── actions_engine.py     # Governance action dispatch
    ├── executors/            # Dry-run / local action handlers
    └── executors_oci/        # Real OCI action handlers
```

### Key Data Flows

**Dashboard (fast path):** Route → Redis cache → return snapshot + "updating" badge. Stale data triggers async Celery refresh.

**Resource scan (async):** `POST /api/v1/admin/scan/run` → returns `job_id` immediately → Celery worker calls OCI APIs → stores in PostgreSQL → frontend polls `/api/v1/jobs/{job_id}`.

**Cost aggregation:** Celery task reads raw cost rows → computes breakdowns by day/month/compartment/service → writes to aggregate tables + Redis (TTL ~1hr).

**Report export:** Frontend triggers format selection → queued Celery job → generates JSON/CSV/XLSX file → frontend polls progress → downloads when ready.

### Frontend Structure

```
src/frontend/src/
├── App.jsx              # Root router
├── pages/               # One component per route (Dashboard, Costs, Resources, etc.)
├── services/api.js      # Axios HTTP client + all API call wrappers
├── hooks/useStaleSnapshotQuery.js  # Cache-first data fetching pattern
├── utils/dateRanges.js  # Date range helpers
└── constants/copy.js    # UI text labels
```

The `useStaleSnapshotQuery` hook implements the stale-while-revalidate pattern used by most pages.

## Configuration

All backend settings are in `src/backend/core/config.py` (Pydantic Settings class). They map from environment variables defined in `.env` (template: `.env.example`). Key groups:

- `DATABASE_URL` — PostgreSQL connection string (routed through PgBouncer in Docker)
- `REDIS_URL` — Redis connection
- `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND`
- `OCI_CONFIG_*` — OCI tenancy, user, key fingerprint, region

## API Conventions

- All routes are versioned under `/api/v1/`
- Async jobs return `{ job_id, status_url }` immediately — callers poll `/api/v1/jobs/{job_id}`
- Audit events are written via `event_logger.py` for all governance actions
- Cache keys follow pattern `{domain}:{identifier}:{params_hash}`

