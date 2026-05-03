from contextlib import asynccontextmanager
from fastapi import FastAPI
from curl_cffi.requests import AsyncSession

from core.config import api_settings, app_logger
from services.cache_service import MemoryCache, RedisCache
from core.dependencies import set_cache_instance, set_scraper_instance


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown.
    - Creates a shared curl_cffi AsyncSession for async scraping.
    - Creates Cache (Redis or Memory depending on config).
    """
    app_logger.info(
        "Application starting up",
        extra={
            "title": api_settings.project_title,
            "version": api_settings.project_version,
            "cache_size": api_settings.max_cache_size,
            "cache_ttl": api_settings.cache_ttl_seconds,
            "redis_enabled": bool(api_settings.redis_url)
        },
    )

    # Initialize shared scraper session
    scraper_session = AsyncSession(impersonate="chrome110")
    set_scraper_instance(scraper_session)

    # Initialize shared cache instance
    if api_settings.redis_url:
        cache_instance = RedisCache(redis_url=api_settings.redis_url, ttl=api_settings.cache_ttl_seconds)
    else:
        cache_instance = MemoryCache(maxsize=api_settings.max_cache_size, ttl=api_settings.cache_ttl_seconds)
    
    set_cache_instance(cache_instance)

    yield

    app_logger.info("Application shutting down")
    
    # Clean up resources
    await scraper_session.close()
    if isinstance(cache_instance, RedisCache):
        await cache_instance.redis.aclose()
