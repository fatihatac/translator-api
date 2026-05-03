from contextlib import asynccontextmanager
from fastapi import FastAPI
import cloudscraper

from core.config import api_settings, app_logger
from services.cache_service import TranslationCache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown.
    - Creates a single shared cloudscraper instance (avoids per-request overhead).
    - Creates a single shared TTLCache instance with thread-safety.
    """
    app_logger.info(
        "Application starting up",
        extra={
            "title": api_settings.project_title,
            "version": api_settings.project_version,
            "cache_size": api_settings.max_cache_size,
            "cache_ttl": api_settings.cache_ttl_seconds,
        },
    )

    # Initialize shared scraper instance
    app.state.scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )

    # Initialize shared cache instance
    app.state.cache = TranslationCache(
        maxsize=api_settings.max_cache_size,
        ttl=api_settings.cache_ttl_seconds,
    )

    yield

    app_logger.info("Application shutting down")
