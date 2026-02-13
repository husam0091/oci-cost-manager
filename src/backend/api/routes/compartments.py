"""Compartment API endpoints."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query

from services import get_oci_client

router = APIRouter()


@router.get("")
async def list_compartments(
    parent_id: Optional[str] = Query(None, description="Parent compartment OCID"),
):
    """List all compartments.
    
    Returns compartments in a hierarchical structure.
    """
    try:
        oci_client = get_oci_client()
        compartments = oci_client.list_compartments(parent_id)
        
        # Build response
        result = []
        for comp in compartments:
            result.append({
                "id": comp.id,
                "name": comp.name,
                "description": comp.description,
                "parent_id": comp.compartment_id,
                "lifecycle_state": comp.lifecycle_state,
                "time_created": comp.time_created.isoformat() if comp.time_created else None,
            })
        
        return {
            "success": True,
            "data": result,
            "meta": {"total": len(result)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tree")
async def get_compartment_tree():
    """Get compartments as a hierarchical tree structure."""
    try:
        oci_client = get_oci_client()
        tenancy = oci_client.get_tenancy()
        compartments = oci_client.list_compartments()
        
        # Build tree structure
        comp_map = {tenancy.id: {
            "id": tenancy.id,
            "name": tenancy.name,
            "description": "Root tenancy",
            "parent_id": None,
            "children": [],
        }}
        
        for comp in compartments:
            comp_map[comp.id] = {
                "id": comp.id,
                "name": comp.name,
                "description": comp.description,
                "parent_id": comp.compartment_id,
                "children": [],
            }
        
        # Build hierarchy
        root = comp_map[tenancy.id]
        for comp_id, comp_data in comp_map.items():
            if comp_id == tenancy.id:
                continue
            parent_id = comp_data["parent_id"]
            if parent_id in comp_map:
                comp_map[parent_id]["children"].append(comp_data)
        
        return {
            "success": True,
            "data": root,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{compartment_id}")
async def get_compartment(compartment_id: str):
    """Get details for a specific compartment."""
    try:
        oci_client = get_oci_client()
        identity_client = oci_client.identity_client
        
        compartment = identity_client.get_compartment(compartment_id).data
        
        return {
            "success": True,
            "data": {
                "id": compartment.id,
                "name": compartment.name,
                "description": compartment.description,
                "parent_id": compartment.compartment_id,
                "lifecycle_state": compartment.lifecycle_state,
                "time_created": compartment.time_created.isoformat() if compartment.time_created else None,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_compartments():
    """Refresh compartments from OCI."""
    try:
        oci_client = get_oci_client()
        compartments = oci_client.list_compartments()
        
        return {
            "success": True,
            "message": f"Refreshed {len(compartments)} compartments",
            "meta": {"total": len(compartments)},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
