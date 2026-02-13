"""OCI Cost Manager - FastAPI Application."""

from contextlib import asynccontextmanager
import logging
import time
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    start = time.time()
    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed_ms = int((time.time() - start) * 1000)
        log_event(
            level="error",
            log_type="backend",
            source="api",
            message="request_failed",
            correlation_id=correlation_id,
            route=request.url.path,
            method=request.method,
            status_code=500,
            details={"elapsed_ms": elapsed_ms, "error": str(exc)},
        )
        raise
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
