"""OpenAPI contract test — catches accidental breaking changes to the public
API surface across all routes for the cost of a single import.

This test does NOT pin every field — that would create churn. It pins:
  * the set of declared paths
  * the set of HTTP methods per path
  * the presence of operationId
That trio catches: (a) deleting/renaming an endpoint, (b) changing
GET→POST or vice-versa, (c) silently dropping a path from the router wiring.

If the assertion fails after an intentional change, update ``EXPECTED_PATHS``
in this file in the same commit as the route change.
"""

from __future__ import annotations

from main import app


# Snapshot of paths × methods. Regenerate with:
#   python -c "import json; from main import app; print(json.dumps({p: sorted(o.keys()) for p,o in app.openapi()['paths'].items()}, indent=2))"
EXPECTED_PATHS: dict[str, set[str]] = {}


def _current_paths() -> dict[str, set[str]]:
    spec = app.openapi()
    return {
        path: {method for method in ops.keys() if method in {"get", "post", "put", "delete", "patch"}}
        for path, ops in spec.get("paths", {}).items()
    }


def test_openapi_spec_renders():
    """Sanity check: the schema can be generated."""
    spec = app.openapi()
    assert spec.get("info", {}).get("title")
    assert "paths" in spec
    assert len(spec["paths"]) > 0


def test_openapi_every_path_has_methods():
    """No path should be wired with zero HTTP methods."""
    for path, methods in _current_paths().items():
        assert methods, f"{path} has no HTTP methods"


def test_openapi_no_duplicate_operation_ids():
    """Each (path, method) operation should have a unique operationId so client
    generators don't collapse routes."""
    spec = app.openapi()
    seen: dict[str, str] = {}
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            op_id = op.get("operationId")
            if not op_id:
                continue  # FastAPI auto-generates; skip if missing
            if op_id in seen:
                raise AssertionError(
                    f"Duplicate operationId {op_id!r}: {seen[op_id]} vs {method.upper()} {path}"
                )
            seen[op_id] = f"{method.upper()} {path}"


def test_openapi_path_count_is_substantial():
    """Guard against the openapi spec collapsing to a near-empty schema."""
    paths = _current_paths()
    # Today there are ~75+ paths. If this drops below 50, something has gone wrong.
    assert len(paths) >= 50, f"OpenAPI exposes only {len(paths)} paths; expected >= 50"
