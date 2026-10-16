import asyncio
import threading
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from api.routes import billing, compartments, costs
from core.database import Base, get_db
from core.models import LogEvent, Resource, ScanRun
from core.rbac import Principal
from main import app
from services import scan_lifecycle, scanner
from services import cost_calculator as calculator
from services import oci_diagnostics
from services.log_retention import prune_operational_logs


@pytest.fixture
def local_db(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setenv("SCAN_LOCK_PATH", str(tmp_path / "scan.lock"))
    monkeypatch.setattr(scan_lifecycle, "SessionLocal", factory)
    with factory() as db:
        yield db, factory
    engine.dispose()


def test_orphan_recovery_respects_live_scan_lock_without_age_guess(local_db):
    db, _ = local_db
    db.add(ScanRun(status="running", started_at=datetime.now(UTC) - timedelta(hours=4)))
    db.commit()
    lease = scan_lifecycle.acquire_scan_lock()
    assert scan_lifecycle.recover_orphaned_scans(db) == 0
    assert db.query(ScanRun).one().status == "running"
    lease.close()  # Simulate process death/restart releasing its kernel lease.
    assert scan_lifecycle.recover_orphaned_scans(db) == 1
    assert db.query(ScanRun).one().status == "failed"
    assert scan_lifecycle.recover_orphaned_scans(db) == 0


def test_scan_admission_reserves_run_before_start_and_rejects_duplicates(
    local_db, monkeypatch
):
    db, _ = local_db
    started, finish, ended = threading.Event(), threading.Event(), threading.Event()

    def held_scan(db, **kwargs):
        started.set()
        try:
            finish.wait(2)
        finally:
            ended.set()

    monkeypatch.setattr(scanner, "run_full_scan", held_scan)
    first = scan_lifecycle.start_inventory_scan()
    try:
        assert started.wait(1)
        second = scan_lifecycle.start_inventory_scan()
        assert first["status"] == "started"
        assert second == {"status": "already_running", "run_id": first["run_id"]}
        assert db.query(ScanRun).count() == 1
    finally:
        finish.set()
        assert ended.wait(1)
        # Wait for execute() to release the lease, not just for the fake body.
        for _ in range(100):
            lease = scan_lifecycle.acquire_scan_lock()
            if lease:
                lease.close()
                break
            time.sleep(0.005)


def test_inventory_checkpoint_and_image_cache_survive_later_interruption(local_db):
    db, factory = local_db
    image_reads = []
    instance = lambda n: SimpleNamespace(
        id=f"r{n}",
        display_name=f"vm{n}",
        compartment_id="c1",
        lifecycle_state="RUNNING",
        shape="flex",
        image_id="same-image",
    )

    class Client:
        tenancy_id = "tenancy"
        database_client = SimpleNamespace(
            list_autonomous_databases=lambda **kw: SimpleNamespace(data=[])
        )

        def list_availability_domains(self, _):
            return [SimpleNamespace(name="AD1")]

        def list_instances(self, compartment):
            return [instance(1), instance(2)] if compartment == "c1" else []

        def get_instance_image(self, image_id):
            image_reads.append(image_id)
            return SimpleNamespace(display_name="Oracle Linux")

        def get_instance_private_ip(self, *args):
            return "10.0.0.1"

        def __getattr__(self, name):
            if name.startswith("list_"):
                return lambda *a, **kw: []
            raise AttributeError(name)

    def stop_after_first(region, completed, total, count, phase):
        if completed == 1:
            raise RuntimeError("simulated interruption")

    with pytest.raises(RuntimeError, match="simulated"):
        scanner._scan_region(
            db,
            Client(),
            [SimpleNamespace(id="c1"), SimpleNamespace(id="c2")],
            "me-jeddah-1",
            progress=stop_after_first,
        )
    db.rollback()
    with factory() as reader:
        assert reader.query(Resource).count() == 2
    assert image_reads == ["same-image"]


def test_incomplete_attachment_scan_never_labels_volume_unattached(local_db):
    db, _ = local_db

    class Client:
        tenancy_id = "t"
        database_client = SimpleNamespace(
            list_autonomous_databases=lambda **kw: SimpleNamespace(data=[])
        )

        def list_availability_domains(self, _):
            return [SimpleNamespace(name="AD1")]

        def list_volume_attachments(self, _):
            raise RuntimeError("permission denied")

        def list_volumes(self, *a):
            return [
                SimpleNamespace(
                    id="v1",
                    display_name="disk",
                    compartment_id="c",
                    lifecycle_state="AVAILABLE",
                )
            ]

        def __getattr__(self, name):
            if name.startswith("list_"):
                return lambda *a, **kw: []
            raise AttributeError(name)

    scanner._scan_region(db, Client(), [SimpleNamespace(id="c")], "me-jeddah-1")
    assert db.query(Resource).one().details["attachment_state"] == "UNKNOWN"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["resource_costs", "compartments"])
async def test_slow_oci_does_not_stall_health_or_event_loop(monkeypatch, kind):
    monkeypatch.setattr(costs, "get_cached", lambda key: None)
    monkeypatch.setattr(costs, "set_cached", lambda *a: None)

    def slow(*args, **kwargs):
        time.sleep(0.6)
        return []

    monkeypatch.setattr(
        costs,
        "get_cost_calculator",
        lambda: SimpleNamespace(get_costs_by_resource=slow),
    )
    monkeypatch.setattr(
        compartments, "get_oci_client", lambda: SimpleNamespace(list_compartments=slow)
    )
    path = (
        "/api/v1/costs/by-resource?start_date=2026-01-01&end_date=2026-01-31"
        if kind == "resource_costs"
        else "/api/v1/compartments"
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        gaps = []
        stop = asyncio.Event()

        async def heartbeat():
            last = time.monotonic()
            while not stop.is_set():
                response = await client.get("/api/v1/health/live")
                assert response.status_code == 200
                now = time.monotonic()
                gaps.append(now - last)
                last = now
                await asyncio.sleep(0.02)

        ping = asyncio.create_task(heartbeat())
        await asyncio.sleep(0.04)
        try:
            response = await client.get(path)
            assert response.status_code == 200
            await asyncio.sleep(0.04)
        finally:
            stop.set()
            await ping
        assert max(gaps) < 0.35, f"event loop stalled: {max(gaps):.3f}s"


def test_by_resource_reads_cache_and_summary_omits_sku_payload(monkeypatch):
    calls = []

    def fetch(*args, **kwargs):
        calls.append(True)
        return [
            dict(
                resource_id="r1",
                total_cost=10,
                skus=[dict(sku_name="Windows OS", cost=10, quantity=2)],
            )
        ]

    monkeypatch.setattr(
        costs,
        "get_cost_calculator",
        lambda: SimpleNamespace(get_costs_by_resource=fetch),
    )
    client = TestClient(app)
    url = "/api/v1/costs/by-resource?start_date=2026-01-01&end_date=2026-01-31"
    first = client.get(url)
    assert first.status_code == 200
    second = client.get(url + "&view=summary").json()
    assert second["cached"] is True
    assert len(calls) == 1
    assert "skus" not in second["data"][0]
    assert second["data"][0]["sku_text"] == "Windows OS"
    assert client.get(url + "&refresh=true").status_code == 200
    assert len(calls) == 2


def test_overview_response_is_bounded_but_totals_cover_all_resources(
    local_db, monkeypatch
):
    db, _ = local_db
    service = FastAPI()
    service.include_router(billing.router, prefix="/billing")
    service.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr(
        billing,
        "resolve_principal",
        lambda *a, **kw: Principal("a", "admin", [], [], [], []),
    )
    monkeypatch.setattr(
        billing,
        "get_cost_calculator",
        lambda: SimpleNamespace(
            get_usage_summary=lambda **kw: [
                dict(
                    resource_id=f"r{i}",
                    service="Compute",
                    sku_name="Compute",
                    computed_amount=1,
                    currency="USD",
                )
                for i in range(100)
            ]
        ),
    )
    client = TestClient(service)
    url = "/billing/spend?start_date=2026-01-01&end_date=2026-01-31&limit=1"
    full = client.get(url)
    compact = client.get(url + "&view=overview")
    data = compact.json()["data"]
    assert data["totals"][0]["net"] == 100
    assert len(data["resources"]) == 8
    assert data["resource_counts"]["USD"] == 100
    assert data["items"] == []
    assert len(compact.content) < len(full.content) * 0.35
    listing = client.get(url + "&view=items").json()["data"]
    assert "resources" not in listing and "by_service" not in listing


def test_lru_eviction_and_expiry(monkeypatch):
    monkeypatch.setattr(calculator, "_cache_max_entries", 2)
    monkeypatch.setattr(calculator, "_cache", calculator.OrderedDict())
    calculator.set_cached("a", 1)
    calculator.set_cached("b", 2)
    assert calculator.get_cached("a") == 1
    calculator.set_cached("c", 3)
    assert calculator.get_cached("b") is None
    with calculator._cache_lock:
        calculator._cache["a"] = (1, time.time() - calculator._cache_ttl - 1)
    assert calculator.get_cached("a") is None


def test_missing_snapshots_do_not_overwrite_known_healthy_oci_check(
    local_db, monkeypatch
):
    db, _ = local_db
    monkeypatch.setattr(oci_diagnostics, "_snapshot_last_sync", lambda db: None)
    data = oci_diagnostics.ensure_degraded_if_stale(
        {"status": "connected", "mode": "connected"}, db
    )
    assert data["status"] == "connected"
    assert data["data_freshness"] == "not_synced"
    assert oci_diagnostics._minimal_unknown()["status"] == "unknown"


def test_retention_is_opt_in_and_preserves_audit(local_db, monkeypatch):
    db, _ = local_db
    old = datetime.now(UTC) - timedelta(days=60)
    for kind in ["backend", "audit"]:
        db.add(
            LogEvent(
                id=kind,
                ts=old,
                level="info",
                log_type=kind,
                source="api",
                message="old",
                correlation_id="test",
            )
        )
    db.commit()
    monkeypatch.delenv("LOG_RETENTION_DAYS", raising=False)
    assert prune_operational_logs(db) == 0
    assert prune_operational_logs(db, 30) == 1
    assert db.query(LogEvent).one().log_type == "audit"


def test_direct_api_compression_for_large_cached_response(monkeypatch):
    monkeypatch.setattr(
        costs,
        "get_cached",
        lambda key: {
            "success": True,
            "data": [{"resource_id": "r", "explanation": "x" * 10000}],
            "meta": {},
        },
    )
    response = TestClient(app).get(
        "/api/v1/costs/by-resource", headers={"Accept-Encoding": "gzip"}
    )
    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
    assert int(response.headers["content-length"]) < len(response.content) / 2


def test_request_db_logging_skips_routine_health_and_keeps_errors(monkeypatch):
    import main

    calls = []
    monkeypatch.setattr(main, "log_event", lambda **kwargs: calls.append(kwargs))
    client = TestClient(app)
    for _ in range(3):
        assert client.get("/api/v1/health/live").status_code == 200
    assert calls == []
    assert client.get("/missing-route").status_code == 404
    assert any(
        c["message"] == "request_completed" and c["status_code"] == 404 for c in calls
    )
