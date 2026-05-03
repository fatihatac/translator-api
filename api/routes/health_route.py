import time
from fastapi import APIRouter, Request
from models.schemas import PingResponse, HealthResponse
from core.config import api_settings

health_router = APIRouter()

_start_time = time.time()


@health_router.get("/ping", response_model=PingResponse, summary="Liveness check")
async def keep_alive_ping():
    """Lightweight liveness probe — confirms the server is running."""
    return PingResponse(status="awake")


@health_router.get("/health", response_model=HealthResponse, summary="Readiness check")
async def health_check(request: Request):
    """
    Readiness probe — returns server version, uptime, and cache statistics.
    Useful for load balancers and monitoring dashboards.
    """
    cache_stats = request.app.state.cache.stats()
    return HealthResponse(
        status="healthy",
        version=api_settings.project_version,
        uptime_seconds=int(time.time() - _start_time),
        cache=cache_stats,
    )
