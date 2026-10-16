"""Local synthetic probe; no OCI credentials, production DB, scheduler or Celery required.
Run: PYTHONPATH=src/backend python scripts/benchmark_commitments.py
"""

import asyncio
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
import httpx
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from core import cache
from core.database import Base, get_db
from core.models import SubscriptionContract, SubscriptionPeriod
from core.rbac import Principal
from services.commitments import month_at
from api.routes import commitments


def rss_mb():
    return int(Path("/proc/self/statm").read_text().split()[1]) * 4096 / 1024**2


def p95(samples):
    return round(sorted(samples)[int(len(samples) * 0.95)] * 1000, 3)


async def main():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    anchor = month_at(now.date().replace(day=1), -12)
    with Session(engine) as db:
        db.add(
            SubscriptionContract(
                id="fixture",
                source="manual",
                name="Synthetic probe",
                status="active",
                start_date=anchor,
                end_date=month_at(anchor, 24),
                total_value=24000,
                currency="USD",
                term_months=24,
                details={},
                computed_at=now,
            )
        )
        for i in range(13):
            start, end = month_at(anchor, i), month_at(anchor, i + 1)
            facts = [
                dict(
                    currency="USD",
                    region="fixture",
                    service=f"service-{n%10}",
                    compartment=f"compartment-{n%100}",
                    team="fixture-team",
                    kind="charge",
                    amount="1",
                    date=start.isoformat(),
                )
                for n in range(1000)
            ]
            db.add(
                SubscriptionPeriod(
                    id=f"p{i}",
                    contract_id="fixture",
                    mode="subscription",
                    start_date=start,
                    end_date=end,
                    allowance=1000,
                    actual=1000,
                    forecast=1000,
                    details={"facts": facts, "complete": True, "elapsed_days": 20},
                    computed_at=now,
                )
            )
        db.commit()
    app = FastAPI()
    app.include_router(commitments.router, prefix="/subscriptions")

    @app.get("/health")
    async def health():
        return {"ok": True}

    def dependency():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = dependency
    commitments.resolve_principal = lambda *a, **k: Principal(
        "fixture", "admin", [], [], [], []
    )
    with tempfile.TemporaryDirectory() as folder:
        cache.CACHE_DIR = Path(folder)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://fixture"
        ) as client:
            idle = []
            for _ in range(30):
                start = time.perf_counter()
                await client.get("/health")
                idle.append(time.perf_counter() - start)
            before = rss_mb()
            gaps = []
            stop = asyncio.Event()

            async def heartbeat():
                last = time.perf_counter()
                while not stop.is_set():
                    await client.get("/health")
                    now_tick = time.perf_counter()
                    gaps.append(now_tick - last)
                    last = now_tick
                    await asyncio.sleep(0.005)

            ping = asyncio.create_task(heartbeat())
            await asyncio.sleep(0.01)
            start = time.perf_counter()
            response = await client.get("/subscriptions/overview?contract_id=fixture")
            elapsed = (time.perf_counter() - start) * 1000
            await asyncio.sleep(0.03)
            stop.set()
            await ping
            result = dict(
                environment="local synthetic SQLite/ASGI; not production or OCI latency",
                fixture_periods=13,
                fixture_facts=13000,
                health_idle_p95_ms=p95(idle),
                health_during_cold_p95_ms=p95(gaps),
                cold_overview_ms=round(elapsed, 3),
                payload_bytes=len(response.content),
                rss_before_mb=round(before, 2),
                rss_after_mb=round(rss_mb(), 2),
                status=response.status_code,
            )
            print(json.dumps(result, indent=2))
            assert (
                response.status_code == 200
                and result["payload_bytes"] < 300000
                and result["health_during_cold_p95_ms"] < 200
            )
    engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
