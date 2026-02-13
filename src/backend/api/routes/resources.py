"""Resource API endpoints."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from core.cache import get_cached, set_cached
from services import get_oci_client

router = APIRouter()

# Cache TTL: 1 hour for resource data
RESOURCE_CACHE_TTL = 3600


@router.get("")
async def list_resources(
    compartment_id: Optional[str] = Query(None, description="Filter by compartment"),
    resource_type: Optional[str] = Query(None, description="Filter by type: oracle_db, mysql, sql_server"),
    limit: int = Query(50, description="Max number of resources to return"),
    refresh: bool = Query(False, description="Force refresh from OCI API"),
    quick: bool = Query(False, description="Quick mode: sample a few compartments and skip SQL Server"),
):
    """List database resources. Uses cache and returns quickly with partial results if needed."""

    cache_scope = compartment_id or "tenancy"
    cache_key = f"resources_list_{resource_type or 'all'}_{cache_scope}_{'quick' if quick else 'full'}"
    alt_quick_key = f"resources_list_{resource_type or 'all'}_{cache_scope}_quick"
    alt_full_key = f"resources_list_{resource_type or 'all'}_{cache_scope}_full"

    # Return cached (limited) list unless refresh requested
    if not refresh:
        cached = get_cached(cache_key)
        if cached:
            return {
                "success": True,
                "data": cached[:limit],
                "cached": True,
                "meta": {"total": len(cached), "returned": min(limit, len(cached)), "mode": 'quick' if 'quick' in cache_key else 'full'},
            }

    def fetch_all():
        oci_client = get_oci_client()
        tenancy_id = oci_client.tenancy_id
        # Get compartments to search
        if compartment_id:
            compartments = [type('obj', (object,), {'id': compartment_id})]
        else:
            compartments = oci_client.list_compartments()
            compartments.append(type('obj', (object,), {'id': tenancy_id}))
            if quick:
                # Sample first few compartments for speed
                compartments = compartments[:3] + [type('obj', (object,), {'id': tenancy_id})]

        results = []
        for comp in compartments:
            comp_id = comp.id

            # Oracle DB Systems
            if not resource_type or resource_type == "oracle_db":
                try:
                    db_systems = oci_client.list_db_systems(comp_id)
                    for db in db_systems:
                        results.append({
                            "id": db.id,
                            "name": db.display_name,
                            "type": "oracle_db",
                            "compartment_id": db.compartment_id,
                            "status": db.lifecycle_state,
                            "shape": db.shape,
                            "details": {
                                "edition": getattr(db, "database_edition", None),
                                "version": getattr(db, "version", None),
                                "cpu_core_count": getattr(db, "cpu_core_count", None),
                                "data_storage_size_in_gbs": getattr(db, "data_storage_size_in_gbs", None),
                                "node_count": getattr(db, "node_count", None),
                            },
                        })
                        if len(results) >= limit and not refresh:
                            return results
                except Exception:
                    pass

            # MySQL DB Systems
            if not resource_type or resource_type == "mysql":
                try:
                    mysql_systems = oci_client.list_mysql_db_systems(comp_id)
                    for db in mysql_systems:
                        results.append({
                            "id": db.id,
                            "name": db.display_name,
                            "type": "mysql",
                            "compartment_id": db.compartment_id,
                            "status": db.lifecycle_state,
                            "shape": getattr(db, "shape_name", None),
                            "details": {
                                "mysql_version": getattr(db, "mysql_version", None),
                                "is_heat_wave_cluster_attached": getattr(db, "is_heat_wave_cluster_attached", False),
                            },
                        })
                        if len(results) >= limit and not refresh:
                            return results
                except Exception:
                    pass

            # Autonomous Databases (ATP/ADW)
            if not resource_type or resource_type in ("autonomous_db", "oracle_db"):
                try:
                    adb_list = oci_client.database_client.list_autonomous_databases(compartment_id=comp_id).data
                    for adb in adb_list:
                        results.append({
                            "id": getattr(adb, "id", None),
                            "name": getattr(adb, "display_name", getattr(adb, "db_name", "Autonomous DB")),
                            "type": "autonomous_db",
                            "compartment_id": getattr(adb, "compartment_id", comp_id),
                            "status": getattr(adb, "lifecycle_state", None),
                            "shape": None,
                            "details": {
                                "db_workload": getattr(adb, "db_workload", None),
                                "cpu_core_count": getattr(adb, "cpu_core_count", None),
                                "data_storage_size_in_tbs": getattr(adb, "data_storage_size_in_tbs", None),
                            },
                        })
                        if len(results) >= limit and not refresh:
                            return results
                except Exception:
                    pass

            # SQL Server instances (compute with SQL Server images)
            if (not quick) and (not resource_type or resource_type == "sql_server"):
                try:
                    instances = oci_client.list_instances(comp_id)
                    for instance in instances:
                        image = None
                        try:
                            if hasattr(instance, 'source_details') and getattr(instance.source_details, 'image_id', None):
                                image = oci_client.get_instance_image(instance.source_details.image_id)
                        except Exception:
                            image = None
                        if image and hasattr(image, 'display_name') and image.display_name:
                            name_l = image.display_name.lower()
                            if ("sql server" in name_l) or ("sql-server" in name_l):
                                results.append({
                                    "id": instance.id,
                                    "name": instance.display_name,
                                    "type": "sql_server",
                                    "compartment_id": instance.compartment_id,
                                    "status": instance.lifecycle_state,
                                    "shape": instance.shape,
                                    "details": {
                                        "image_name": image.display_name,
                                        "ocpus": getattr(getattr(instance, 'shape_config', None), 'ocpus', None),
                                        "memory_in_gbs": getattr(getattr(instance, 'shape_config', None), 'memory_in_gbs', None),
                                    },
                                })
                                if len(results) >= limit and not refresh:
                                    return results
                except Exception:
                    pass
        return results

    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            try:
                # If a specific compartment is selected, allow longer even without refresh
                timeout_sec = 120.0 if refresh else (30.0 if compartment_id else 10.0)
                items = await asyncio.wait_for(
                    loop.run_in_executor(executor, fetch_all),
                    timeout=timeout_sec,
                )
            except asyncio.TimeoutError:
                # Prefer a full cache if available, otherwise quick
                cached_full = get_cached(alt_full_key)
                if cached_full:
                    return {
                        "success": True,
                        "data": cached_full[:limit],
                        "cached": True,
                        "meta": {"total": len(cached_full), "returned": min(limit, len(cached_full)), "warning": "Timeout - showing cached full", "mode": "full"},
                    }
                cached_quick = get_cached(alt_quick_key)
                if cached_quick:
                    return {
                        "success": True,
                        "data": cached_quick[:limit],
                        "cached": True,
                        "meta": {"total": len(cached_quick), "returned": min(limit, len(cached_quick)), "warning": "Timeout - showing cached quick", "mode": "quick"},
                    }
                # Timed out and no cache – return empty quickly
                return {"success": True, "data": [], "cached": False, "meta": {"total": 0, "returned": 0, "warning": "Timeout", "mode": "full" if not quick else "quick"}}

        # Cache full/partial results
        if items:
            set_cached(cache_key, items, RESOURCE_CACHE_TTL)

        return {
            "success": True,
            "data": items[:limit],
            "cached": False,
            "meta": {"total": len(items), "returned": min(limit, len(items))},
        }
    except Exception as e:
        # Return cached on error
        cached = get_cached(cache_key)
        if cached:
            return {
                "success": True,
                "data": cached[:limit],
                "cached": True,
                "meta": {"total": len(cached), "returned": min(limit, len(cached)), "warning": str(e)},
            }
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_resources_summary(
    refresh: bool = Query(False, description="Force refresh from OCI API"),
):
    """Get summary count of resources by type. Uses cache by default."""
    cache_key = "resources_summary"
    
    # Check cache first
    if not refresh:
        cached = get_cached(cache_key)
        if cached is not None:
            return {
                "success": True,
                "data": cached,
                "cached": True,
            }
    
    def fetch_summary():
        try:
            oci_client = get_oci_client()
            compartments = oci_client.list_compartments()
            compartments.append(type('obj', (object,), {'id': oci_client.tenancy_id}))
            
            summary = {
                "oracle_db": 0,
                "mysql": 0,
                "sql_server": 0,
                "total": 0,
            }
            
            for comp in compartments:
                try:
                    summary["oracle_db"] += len(oci_client.list_db_systems(comp.id))
                except Exception:
                    pass
                
                try:
                    summary["mysql"] += len(oci_client.list_mysql_db_systems(comp.id))
                except Exception:
                    pass
            
            summary["total"] = summary["oracle_db"] + summary["mysql"] + summary["sql_server"]
            return summary
        except Exception as e:
            return {"oracle_db": 0, "mysql": 0, "sql_server": 0, "total": 0, "error": str(e)}
    
    try:
        # Run in thread pool with timeout
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            try:
                timeout_sec = 120.0 if refresh else 10.0
                summary = await asyncio.wait_for(
                    loop.run_in_executor(executor, fetch_summary),
                    timeout=timeout_sec
                )
            except asyncio.TimeoutError:
                # Return cached even if expired
                cached = get_cached(cache_key)
                if cached:
                    return {
                        "success": True,
                        "data": cached,
                        "cached": True,
                        "warning": "API timeout - showing cached data",
                    }
                summary = {"oracle_db": 0, "mysql": 0, "sql_server": 0, "total": 0, "error": "Request timed out"}
        
        # Cache the result
        set_cached(cache_key, summary, RESOURCE_CACHE_TTL)
        
        return {
            "success": True,
            "data": summary,
            "cached": False,
        }
    except Exception as e:
        cached = get_cached(cache_key)
        if cached:
            return {
                "success": True,
                "data": cached,
                "cached": True,
                "warning": f"API error - showing cached data: {str(e)}",
            }
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{resource_id}")
async def get_resource(resource_id: str):
    """Get details for a specific resource."""
    try:
        oci_client = get_oci_client()
        
        # Try to find as Oracle DB
        try:
            db = oci_client.database_client.get_db_system(resource_id).data
            return {
                "success": True,
                "data": {
                    "id": db.id,
                    "name": db.display_name,
                    "type": "oracle_db",
                    "compartment_id": db.compartment_id,
                    "status": db.lifecycle_state,
                    "shape": db.shape,
                    "details": {
                        "edition": getattr(db, "database_edition", None),
                        "version": getattr(db, "version", None),
                        "cpu_core_count": getattr(db, "cpu_core_count", None),
                        "data_storage_size_in_gbs": getattr(db, "data_storage_size_in_gbs", None),
                    },
                },
            }
        except Exception:
            pass
        
        # Try as MySQL
        try:
            db = oci_client.mysql_client.get_db_system(resource_id).data
            return {
                "success": True,
                "data": {
                    "id": db.id,
                    "name": db.display_name,
                    "type": "mysql",
                    "compartment_id": db.compartment_id,
                    "status": db.lifecycle_state,
                    "shape": getattr(db, "shape_name", None),
                },
            }
        except Exception:
            pass
        
        # Try as compute instance
        try:
            instance = oci_client.compute_client.get_instance(resource_id).data
            return {
                "success": True,
                "data": {
                    "id": instance.id,
                    "name": instance.display_name,
                    "type": "compute",
                    "compartment_id": instance.compartment_id,
                    "status": instance.lifecycle_state,
                    "shape": instance.shape,
                },
            }
        except Exception:
            pass
        
        raise HTTPException(status_code=404, detail="Resource not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
