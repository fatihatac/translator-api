import time
from fastapi import APIRouter, Depends, Request
from models.schemas import PingResponse, HealthResponse
from core.config import api_settings
from services.cache_base import BaseCache
from core.dependencies import get_cache

health_router = APIRouter()

_start_time = time.time()


@health_router.get("/ping", response_model=PingResponse, summary="Liveness check")
async def keep_alive_ping():
    """Lightweight liveness probe — confirms the server is running."""
    return PingResponse(status="ok")


@health_router.get("/health", response_model=HealthResponse, summary="Readiness check")
async def health_check(request: Request, cache: BaseCache = Depends(get_cache)):
    """
    Readiness probe — returns server version, uptime, and cache statistics.
    Useful for load balancers and monitoring dashboards.
    """
    cache_stats = await cache.stats()
    return HealthResponse(
        status="ok",
        version=api_settings.project_version,
        uptime_seconds=int(time.time() - _start_time),
        cache=cache_stats,
    )
