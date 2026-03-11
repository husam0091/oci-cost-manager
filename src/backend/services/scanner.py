"""Background scanner that pulls OCI inventory data and stores it in DB."""
from __future__ import annotations
from datetime import UTC, datetime
from typing import Dict, Any
import re

from sqlalchemy.orm import Session

from core.models import AllocationRule, Compartment, Resource, CostSnapshot, TrendPoint, ScanRun, JobRun
from services.oci_client import get_oci_client
from services.cost_calculator import get_cost_calculator
from services.allocation import evaluate_allocation, load_enabled_rules
from services.budget_engine import evaluate_budget_statuses
from core.cache import clear_cache


def upsert_compartments(db: Session):
    oci_client = get_oci_client()
    tenancy = oci_client.get_tenancy()
    comps = oci_client.list_compartments()
    all_nodes = [(tenancy.id, tenancy.name, None)] + [(c.id, c.name, c.compartment_id) for c in comps]
    id_to_parent = {cid: parent for cid, _, parent in all_nodes}
    id_to_name = {cid: name for cid, name, _ in all_nodes}

    def build_path(cid: str) -> str:
        parts = []
        while cid:
            parts.append(id_to_name.get(cid, cid))
            cid = id_to_parent.get(cid)
        return "/".join(reversed(parts))

    for cid, name, parent in all_nodes:
        path = build_path(cid)
        obj = db.get(Compartment, cid)
        if not obj:
            obj = Compartment(id=cid, name=name, parent_id=parent, path=path)
            db.add(obj)
        else:
            obj.name = name
            obj.parent_id = parent
            obj.path = path
    db.commit()


def _upsert_resource_row(db: Session, *, ocid: str, name: str, type_: str, compartment_id: str,
                          status: str, shape: str | None, details: Dict[str, Any]) -> None:
    details = dict(details or {})
    details.setdefault("match_confidence", "medium")
    details.setdefault("match_reason", "scanner_default")
    row = db.query(Resource).filter(Resource.ocid == ocid).one_or_none()
    if not row:
        row = Resource(ocid=ocid, name=name, type=type_, compartment_id=compartment_id,
                       status=status, shape=shape, details=details)
        db.add(row)
    else:
        row.name = name
        row.type = type_
        row.compartment_id = compartment_id
        row.status = status
        row.shape = shape
        row.details = details


def _detect_image_profile(image_name: str | None) -> dict:
    """Classify VM image family for richer resource/cost reporting."""
    if not image_name:
        return {"resource_type": "compute", "image_family": "generic", "image_vendor": None}
    lower = image_name.lower()
    if "sql server" in lower or "sql-server" in lower or "sqlserver" in lower or "mssql" in lower:
        return {"resource_type": "sql_server", "image_family": "sql_server", "image_vendor": "microsoft"}
    if "windows" in lower:
        return {"resource_type": "windows_server", "image_family": "windows_server", "image_vendor": "microsoft"}
    if "fortigate" in lower or "palo alto" in lower or "paloalto" in lower or "f5" in lower:
        vendor = "fortinet" if "fortigate" in lower else "palo_alto" if "palo" in lower else "f5"
        return {"resource_type": "security_appliance", "image_family": "security_appliance", "image_vendor": vendor}
    return {"resource_type": "compute", "image_family": "generic", "image_vendor": None}


def _looks_like_sql_workload(inst_name: str | None, image_name: str | None) -> bool:
    text = f"{inst_name or ''} {image_name or ''}".lower()
    # Avoid false positives from words like "mysql".
    return bool(re.search(r"(microsoft[\s-]*sql|sql[\s-]*server|\bmssql\b)", text))


def _format_bytes(size_bytes: int | None) -> str | None:
    """Format bytes to human readable string."""
    if not size_bytes:
        return None
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def upsert_resources(db: Session) -> int:
    oci_client = get_oci_client()
    comps = db.query(Compartment).all()
    count = 0
    
    # Cache availability domains (needed for file storage)
    tenancy_id = oci_client.tenancy_id
    availability_domains = oci_client.list_availability_domains(tenancy_id)
    ad_names = [ad.name for ad in availability_domains]

    # Build tenancy-wide attachment maps first to avoid cross-compartment false UNATTACHED labels.
    attached_vol_ids_global: set[str] = set()
    attached_boot_ids_global: set[str] = set()
    attached_states = {"ATTACHED", "ATTACHING", "DETACHING"}
    for comp in comps:
        comp_id = comp.id
        try:
            for att in oci_client.list_volume_attachments(comp_id):
                state = str(getattr(att, "lifecycle_state", "") or "").upper()
                vol_id = getattr(att, "volume_id", None)
                if vol_id and state in attached_states:
                    attached_vol_ids_global.add(vol_id)
        except Exception:
            pass
        try:
            for att in oci_client.list_boot_volume_attachments(comp_id):
                state = str(getattr(att, "lifecycle_state", "") or "").upper()
                bvol_id = getattr(att, "boot_volume_id", None)
                if bvol_id and state in attached_states:
                    attached_boot_ids_global.add(bvol_id)
        except Exception:
            pass

    for comp in comps:
        comp_id = comp.id
        
        # === Oracle DB Systems ===
        try:
            for dbs in oci_client.list_db_systems(comp_id):
                _upsert_resource_row(db, ocid=dbs.id, name=dbs.display_name, type_="oracle_db",
                                     compartment_id=dbs.compartment_id, status=dbs.lifecycle_state,
                                     shape=dbs.shape,
                                     details={
                                         "edition": getattr(dbs, "database_edition", None),
                                         "version": getattr(dbs, "version", None),
                                         "cpu_core_count": getattr(dbs, "cpu_core_count", None),
                                         "data_storage_size_in_gbs": getattr(dbs, "data_storage_size_in_gbs", None),
                                         "node_count": getattr(dbs, "node_count", None),
                                     })
                count += 1
        except Exception:
            pass
        
        # === MySQL DB Systems ===
        try:
            for m in oci_client.list_mysql_db_systems(comp_id):
                _upsert_resource_row(db, ocid=m.id, name=m.display_name, type_="mysql",
                                     compartment_id=m.compartment_id, status=m.lifecycle_state,
                                     shape=getattr(m, "shape_name", None),
                                     details={
                                         "mysql_version": getattr(m, "mysql_version", None),
                                         "is_heat_wave_cluster_attached": getattr(m, "is_heat_wave_cluster_attached", False),
                                     })
                count += 1
        except Exception:
            pass
        
        # === Autonomous Databases ===
        try:
            adb_list = oci_client.database_client.list_autonomous_databases(compartment_id=comp_id).data
            for adb in adb_list:
                _upsert_resource_row(db, ocid=getattr(adb, "id", None),
                                     name=getattr(adb, "display_name", getattr(adb, "db_name", "Autonomous DB")),
                                     type_="autonomous_db",
                                     compartment_id=getattr(adb, "compartment_id", comp_id),
                                     status=getattr(adb, "lifecycle_state", None),
                                     shape=None,
                                     details={
                                         "db_workload": getattr(adb, "db_workload", None),
                                         "cpu_core_count": getattr(adb, "cpu_core_count", None),
                                         "data_storage_size_in_tbs": getattr(adb, "data_storage_size_in_tbs", None),
                                     })
                count += 1
        except Exception:
            pass
        
        # === Compute Instances (VMs) - includes SQL/Windows/security image detection ===
        try:
            instances = oci_client.list_instances(comp_id)
            for inst in instances:
                lifecycle = getattr(inst, "lifecycle_state", "UNKNOWN")
                if lifecycle in ("TERMINATED", "TERMINATING"):
                    continue
                # Get image info to detect SQL Server
                image_name = None
                image_id = getattr(inst, "image_id", None)
                if not image_id and getattr(inst, "source_details", None):
                    image_id = getattr(inst.source_details, "image_id", None)
                if image_id:
                    image = oci_client.get_instance_image(image_id)
                    if image:
                        image_name = image.display_name
                
                # Get private IP
                private_ip = oci_client.get_instance_private_ip(inst.id, comp_id)
                
                profile = _detect_image_profile(image_name)
                resource_type = profile["resource_type"]
                if resource_type == "compute" and _looks_like_sql_workload(getattr(inst, "display_name", None), image_name):
                    resource_type = "sql_server"
                    profile["image_family"] = "sql_server"
                    profile["image_vendor"] = "microsoft"
                
                # Parse shape config for OCPUs/memory
                shape_config = getattr(inst, "shape_config", None)
                ocpus = getattr(shape_config, "ocpus", None) if shape_config else None
                memory_gb = getattr(shape_config, "memory_in_gbs", None) if shape_config else None
                
                _upsert_resource_row(db, ocid=inst.id, name=inst.display_name, type_=resource_type,
                                     compartment_id=inst.compartment_id, status=inst.lifecycle_state,
                                     shape=inst.shape,
                                     details={
                                         "ocpus": ocpus,
                                         "memory_in_gbs": memory_gb,
                                         "availability_domain": getattr(inst, "availability_domain", None),
                                         "private_ip": private_ip,
                                         "image_name": image_name,
                                         "image_family": profile["image_family"],
                                         "image_vendor": profile["image_vendor"],
                                         "time_created": str(getattr(inst, "time_created", None)),
                                     })
                count += 1
        except Exception:
            pass
        
        # === File Storage (NFS File Systems) ===
        for ad_name in ad_names:
            try:
                file_systems = oci_client.list_file_systems(comp_id, ad_name)
                mount_targets = oci_client.list_mount_targets(comp_id, ad_name)
                
                # Map export set IDs to mount target IPs and export paths.
                export_map = {}
                for mt in mount_targets:
                    if getattr(mt, "export_set_id", None):
                        exports = oci_client.list_exports(comp_id, mt.export_set_id)
                        for exp in exports:
                            fs_id = getattr(exp, "file_system_id", None)
                            if not fs_id:
                                continue
                            export_map.setdefault(fs_id, []).append({
                                "path": getattr(exp, "path", None),
                                "mount_target_id": getattr(mt, "id", None),
                                "mount_target_name": getattr(mt, "display_name", None),
                                "export_set_id": getattr(mt, "export_set_id", None),
                            })
                
                for fs in file_systems:
                    metered_bytes = getattr(fs, "metered_bytes", 0)
                    _upsert_resource_row(db, ocid=fs.id, name=fs.display_name, type_="nfs_file_system",
                                         compartment_id=fs.compartment_id, status=fs.lifecycle_state,
                                         shape=None,
                                         details={
                                             "availability_domain": ad_name,
                                             "metered_bytes": metered_bytes,
                                             "size_display": _format_bytes(metered_bytes),
                                             "protocol": "NFS",
                                             "exports": export_map.get(getattr(fs, "id", None), []),
                                             "time_created": str(getattr(fs, "time_created", None)),
                                         })
                    count += 1
            except Exception:
                pass

        # === Block and Boot Volumes (including unattached) ===
        try:
            attached_vol_ids = attached_vol_ids_global
            attached_boot_ids = attached_boot_ids_global

            for ad_name in ad_names:
                for vol in oci_client.list_volumes(comp_id, ad_name):
                    vol_id = getattr(vol, "id", None)
                    attached = vol_id in attached_vol_ids
                    _upsert_resource_row(
                        db,
                        ocid=vol_id,
                        name=getattr(vol, "display_name", "Block Volume"),
                        type_="block_volume",
                        compartment_id=getattr(vol, "compartment_id", comp_id),
                        status=getattr(vol, "lifecycle_state", "UNKNOWN"),
                        shape=None,
                        details={
                            "availability_domain": ad_name,
                            "size_in_gbs": getattr(vol, "size_in_gbs", None),
                            "vpus_per_gb": getattr(vol, "vpus_per_gb", None),
                            "is_attached": attached,
                            "attachment_state": "ATTACHED" if attached else "UNATTACHED",
                            "time_created": str(getattr(vol, "time_created", None)),
                        },
                    )
                    count += 1

                for bvol in oci_client.list_boot_volumes(comp_id, ad_name):
                    bvol_id = getattr(bvol, "id", None)
                    attached = bvol_id in attached_boot_ids
                    _upsert_resource_row(
                        db,
                        ocid=bvol_id,
                        name=getattr(bvol, "display_name", "Boot Volume"),
                        type_="boot_volume",
                        compartment_id=getattr(bvol, "compartment_id", comp_id),
                        status=getattr(bvol, "lifecycle_state", "UNKNOWN"),
                        shape=None,
                        details={
                            "availability_domain": ad_name,
                            "size_in_gbs": getattr(bvol, "size_in_gbs", None),
                            "vpus_per_gb": getattr(bvol, "vpus_per_gb", None),
                            "is_attached": attached,
                            "attachment_state": "ATTACHED" if attached else "UNATTACHED",
                            "time_created": str(getattr(bvol, "time_created", None)),
                        },
                    )
                    count += 1
        except Exception:
            pass

        # === Block Volume Backups ===
        try:
            for vb in oci_client.list_volume_backups(comp_id):
                size_gbs = getattr(vb, "size_in_gbs", None)
                _upsert_resource_row(
                    db,
                    ocid=getattr(vb, "id", None),
                    name=getattr(vb, "display_name", "Volume Backup"),
                    type_="volume_backup",
                    compartment_id=getattr(vb, "compartment_id", comp_id),
                    status=getattr(vb, "lifecycle_state", "UNKNOWN"),
                    shape=None,
                    details={
                        "source_volume_id": getattr(vb, "volume_id", None),
                        "size_in_gbs": size_gbs,
                        "size_display": _format_bytes(size_gbs * (1024 ** 3) if size_gbs else None),
                        "backup_type": getattr(vb, "type", None),
                        "time_created": str(getattr(vb, "time_created", None)),
                    },
                )
                count += 1
        except Exception:
            pass

        # === Boot Volume Backups ===
        try:
            for bvb in oci_client.list_boot_volume_backups(comp_id):
                size_gbs = getattr(bvb, "size_in_gbs", None)
                _upsert_resource_row(
                    db,
                    ocid=getattr(bvb, "id", None),
                    name=getattr(bvb, "display_name", "Boot Volume Backup"),
                    type_="boot_volume_backup",
                    compartment_id=getattr(bvb, "compartment_id", comp_id),
                    status=getattr(bvb, "lifecycle_state", "UNKNOWN"),
                    shape=None,
                    details={
                        "source_boot_volume_id": getattr(bvb, "boot_volume_id", None),
                        "size_in_gbs": size_gbs,
                        "size_display": _format_bytes(size_gbs * (1024 ** 3) if size_gbs else None),
                        "backup_type": getattr(bvb, "type", None),
                        "time_created": str(getattr(bvb, "time_created", None)),
                    },
                )
                count += 1
        except Exception:
            pass
        
        # === Object Storage (Buckets) ===
        try:
            buckets = oci_client.list_buckets(comp_id)
            for bucket in buckets:
                bucket_name = bucket.name
                details = oci_client.get_bucket_details(bucket_name) or {}
                approx_size = details.get("approximate_size", 0)
                
                _upsert_resource_row(db, ocid=f"bucket:{bucket.namespace}:{bucket_name}",
                                     name=bucket_name, type_="bucket",
                                     compartment_id=comp_id, status="ACTIVE",
                                     shape=None,
                                     details={
                                         "namespace": bucket.namespace,
                                         "storage_tier": details.get("storage_tier"),
                                         "approximate_count": details.get("approximate_count"),
                                         "approximate_size": approx_size,
                                         "size_display": _format_bytes(approx_size),
                                         "time_created": str(getattr(bucket, "time_created", None)),
                                     })
                count += 1
        except Exception:
            pass
    
    db.commit()
    return count


def snapshot_costs_and_trends(db: Session):
    calc = get_cost_calculator()
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    costs = calc.get_costs_by_service(month_start, today)
    snap = db.query(CostSnapshot).filter(CostSnapshot.period == "monthly", CostSnapshot.start_date == month_start).one_or_none()
    if snap:
        snap.end_date = today
        snap.total = sum(costs.values())
        snap.by_service = costs
    else:
        snap = CostSnapshot(period="monthly", start_date=month_start, end_date=today,
                            total=sum(costs.values()), by_service=costs)
        db.add(snap)
    # Trends
    trend = calc.get_cost_trends(6)
    from datetime import datetime as dt
    for point in trend:
        month = point.get("month")
        tp = db.query(TrendPoint).filter(TrendPoint.month == month).one_or_none()
        if not tp:
            tp = TrendPoint(month=month, month_start=dt.strptime(month + "-01", "%Y-%m-%d"))
            db.add(tp)
        tp.total_cost = point.get("total_cost", 0)
        tp.by_service = point.get("by_service", {})
    db.commit()


def enrich_resource_types_from_cost_signatures(db: Session):
    """Fallback classification when OCI image metadata is incomplete."""
    calc = get_cost_calculator()
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today.replace(day=1)
    try:
        rows = calc.get_costs_by_resource(month_start, today)
    except Exception:
        return

    for item in rows:
        rid = item.get("resource_id")
        if not rid:
            continue
        skus = item.get("skus") or []
        sku_text = " ".join((s.get("sku_name") or "").lower() for s in skus)

        detected_type = None
        if "sql server" in sku_text or "microsoft sql" in sku_text:
            detected_type = "sql_server"
        elif "windows os" in sku_text:
            detected_type = "windows_server"
        elif "fortigate" in sku_text or "palo alto" in sku_text or "f5" in sku_text:
            detected_type = "security_appliance"
        elif "file storage" in sku_text:
            detected_type = "nfs_file_system"
        elif "backup" in sku_text:
            detected_type = "volume_backup"

        if not detected_type:
            continue

        row = db.query(Resource).filter(Resource.ocid == rid).one_or_none()
        if row:
            if row.type == "compute":
                row.type = detected_type
                details = dict(row.details or {})
                details["classified_by"] = "cost_signature"
                row.details = details
        else:
            db.add(Resource(
                ocid=rid,
                name=rid.split(".")[-1] if "." in rid else rid,
                type=detected_type,
                compartment_id="unknown",
                status="UNKNOWN",
                shape=None,
                details={"classified_by": "cost_signature"},
            ))
    db.commit()


def backfill_resource_allocation(db: Session):
    rules = load_enabled_rules(db)
    rows = db.query(Resource).all()
    for row in rows:
        alloc = evaluate_allocation(row, rules, compartment_name=None, sku_text="")
        details = dict(row.details or {})
        details["env"] = alloc.env
        details["team"] = alloc.team
        details["app"] = alloc.app
        details["allocation_confidence"] = alloc.allocation_confidence
        details["allocation_reason"] = alloc.allocation_reason
        row.details = details
    db.commit()


def run_full_scan(db: Session) -> dict:
    run = ScanRun()
    db.add(run); db.commit(); db.refresh(run)
    try:
        upsert_compartments(db)
        upsert_resources(db)
        backfill_resource_allocation(db)
        evaluate_budget_statuses(db, persist_alerts=True)
        _queue_post_scan_refresh_jobs(db, run.id)
        run.status = "success"
        run.finished_at = datetime.now(UTC)
        db.commit()
        # Invalidate short-lived API caches after a successful scan refresh.
        clear_cache()
        return {"run_id": run.id, "status": run.status}
    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        run.finished_at = datetime.now(UTC)
        db.commit()
        clear_cache()
        raise


def _queue_post_scan_refresh_jobs(db: Session, run_id: int) -> None:
    """Queue aggregate/snapshot refresh so UI data is rebuilt asynchronously."""
    try:
        import uuid
        from worker import celery_app

        corr = f"scan:{run_id}"
        agg_job = JobRun(
            id=str(uuid.uuid4()),
            job_type="aggregate_refresh",
            status="queued",
            progress=0,
            params={"trigger": "post_scan", "scan_run_id": run_id, "correlation_id": corr},
            created_at=datetime.now(UTC),
        )
        snap_job = JobRun(
            id=str(uuid.uuid4()),
            job_type="snapshot_refresh",
            status="queued",
            progress=0,
            params={"trigger": "post_scan", "scan_run_id": run_id, "correlation_id": corr, "range": "prev_month"},
            created_at=datetime.now(UTC),
        )
        db.add(agg_job)
        db.add(snap_job)
        db.commit()

        celery_app.send_task("jobs.aggregate_refresh", args=[agg_job.id, agg_job.params], queue="heavy")
        celery_app.send_task(
            "jobs.snapshot_refresh",
            args=[snap_job.id, snap_job.params],
            queue="heavy",
            countdown=20,
        )
    except Exception:
        # Never fail the scan because post-scan jobs could not be enqueued.
        db.rollback()
