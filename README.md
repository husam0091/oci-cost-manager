# OCI Cost Manager

Enterprise-style FinOps platform for OCI with:
- React + Vite frontend
- FastAPI backend
- PostgreSQL + PgBouncer
- Redis + Celery workers
- Cached cost APIs, diagnostics, logs, and governance workflows

## Quick Start

1. Clone and enter project:
```bash
git clone https://github.com/husam0091/sam0091.git
cd sam0091/oci-cost-manager
```

2. Create runtime env:
```bash
cp .env.example .env
```

3. Configure OCI credentials on host (not in git):
- OCI config path: `/home/<user>/.oci/config`
- Private key file referenced from config

4. Start services:
```bash
docker compose up -d --build
```

5. Open app:
- `http://localhost:8080`

## Main Services

- `frontend` (UI)
- `backend` (API)
- `worker` (async jobs)
- `postgres` (DB)
- `pgbouncer` (pooling)
- `redis` (cache/queue)

## Project Map

- File-by-file guide: `PROJECT_STRUCTURE.md`

## Core API Endpoints

- Health: `GET /api/v1/health`
- Diagnostics: `GET /api/v1/diagnostics`
- Cost summary: `GET /api/v1/cost/summary?range=prev_month`
- Jobs: `POST /api/v1/jobs/aggregate_refresh`, `POST /api/v1/jobs/snapshot_refresh`
- Logs: `GET /api/v1/logs`

## Notes

- No OCI calls are made from page load cost endpoints.
- UI reads cache/aggregates first, with stale snapshot fallback.
