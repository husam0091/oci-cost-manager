"""OCI Cost Manager - FastAPI Application."""

from contextlib import asynccontextmanager
import logging
import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from core.config import get_settings
from core.database import init_db
from api.routes import (
    actions,
    compartments,
    cost,
    diagnostics,
    resources,
    costs,
    dashboard,
    governance,
    me,
    ops,
    recommendations,
    settings_oci,
    insights,
    budgets,
    logs,
    prices,
    health,
    jobs,
)
from api.routes import data, admin
from api.routes import cache
from core.scheduler import start_scheduler
from core.models import Setting  # ensure models are imported
from services.event_logger import log_event

settings = get_settings()
logger = logging.getLogger("oci-cost-manager")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()
    start_scheduler()
    yield
    # Shutdown
    pass


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="OCI Cost Management & Budget Validation Tool",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(
    actions.router,
    prefix=settings.api_prefix,
    tags=["Actions"],
)


@app.exception_handler(HTTPException)
async def http_exception_with_correlation(request: Request, exc: HTTPException):
    correlation_id = getattr(request.state, "correlation_id", None) or request.headers.get("x-correlation-id") or str(uuid.uuid4())
    payload = exc.detail if isinstance(exc.detail, dict) else {"success": False, "error": {"code": "HTTP_ERROR", "reason": str(exc.detail)}}
    if isinstance(payload, dict):
        err = payload.get("error")
        if isinstance(err, dict) and not err.get("correlation_id"):
            err["correlation_id"] = correlation_id
        elif "correlation_id" not in payload:
            payload["correlation_id"] = correlation_id
    response = JSONResponse(status_code=exc.status_code, content=payload)
    response.headers["x-correlation-id"] = correlation_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_with_correlation(request: Request, exc: Exception):
    correlation_id = getattr(request.state, "correlation_id", None) or request.headers.get("x-correlation-id") or str(uuid.uuid4())
    log_event(
        level="error",
        log_type="backend",
        source="api",
        message="unhandled_exception",
        correlation_id=correlation_id,
        route=request.url.path,
        method=request.method,
        status_code=500,
        details={"error": str(exc)},
    )
    response = JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_SERVER_ERROR", "reason": "Internal server error", "correlation_id": correlation_id}},
    )
    response.headers["x-correlation-id"] = correlation_id
    return response


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    start = time.time()
    response = await call_next(request)
    elapsed_ms = int((time.time() - start) * 1000)
    response.headers["x-correlation-id"] = correlation_id
    status_level = "info"
    if response.status_code >= 500:
        status_level = "error"
    elif response.status_code >= 400:
        status_level = "warn"
    log_event(
        level=status_level,
        log_type="backend",
        source="api",
        message="request_completed",
        correlation_id=correlation_id,
        route=request.url.path,
        method=request.method,
        status_code=response.status_code,
        details={"elapsed_ms": elapsed_ms},
    )
    return response
app.include_router(
    me.router,
    prefix=settings.api_prefix,
    tags=["Me"],
)
app.include_router(
    ops.router,
    prefix=settings.api_prefix,
    tags=["Ops"],
)
app.include_router(
    health.router,
    prefix=settings.api_prefix,
    tags=["Health"],
)
app.include_router(
    compartments.router,
    prefix=f"{settings.api_prefix}/compartments",
    tags=["Compartments"],
)
app.include_router(
    resources.router,
    prefix=f"{settings.api_prefix}/resources",
    tags=["Resources"],
)
app.include_router(
    costs.router,
    prefix=f"{settings.api_prefix}/costs",
    tags=["Costs"],
)
app.include_router(
    cost.router,
    prefix=f"{settings.api_prefix}/cost",
    tags=["CostFast"],
)
app.include_router(
    diagnostics.router,
    prefix=f"{settings.api_prefix}/diagnostics",
    tags=["Diagnostics"],
)
app.include_router(
    dashboard.router,
    prefix=f"{settings.api_prefix}/dashboard",
    tags=["Dashboard"],
)
app.include_router(
    governance.router,
    prefix=settings.api_prefix,
    tags=["Governance"],
)
app.include_router(
    recommendations.router,
    prefix=settings.api_prefix,
    tags=["Recommendations"],
)
app.include_router(
    insights.router,
    prefix=f"{settings.api_prefix}/insights",
    tags=["Insights"],
)
app.include_router(
    logs.router,
    prefix=f"{settings.api_prefix}/logs",
    tags=["Logs"],
)
app.include_router(
    budgets.router,
    prefix=f"{settings.api_prefix}/budgets",
    tags=["Budgets"],
)
app.include_router(
    prices.router,
    prefix=f"{settings.api_prefix}/prices",
    tags=["Prices"],
)
app.include_router(
    cache.router,
    prefix=f"{settings.api_prefix}/cache",
    tags=["Cache"],
)
app.include_router(
    data.router,
    prefix=f"{settings.api_prefix}/data",
    tags=["Data"],
)
app.include_router(
    admin.router,
    prefix=f"{settings.api_prefix}/admin",
    tags=["Admin"],
)
app.include_router(
    jobs.router,
    prefix=f"{settings.api_prefix}/jobs",
    tags=["Jobs"],
)
app.include_router(
    settings_oci.router,
    prefix=settings.api_prefix,
    tags=["SettingsOCI"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
