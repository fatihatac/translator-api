from typing import AsyncGenerator
from fastapi import Request
from curl_cffi.requests import AsyncSession
from services.cache_base import BaseCache

# Global instances managed by lifespan
_cache_instance: BaseCache | None = None
_scraper_instance: AsyncSession | None = None


def set_cache_instance(cache: BaseCache):
    global _cache_instance
    _cache_instance = cache


def set_scraper_instance(scraper: AsyncSession):
    global _scraper_instance
    _scraper_instance = scraper


async def get_cache() -> AsyncGenerator[BaseCache, None]:
    """Provides the shared cache instance."""
    if _cache_instance is None:
        raise RuntimeError("Cache instance is not initialized")
    yield _cache_instance


async def get_scraper() -> AsyncGenerator[AsyncSession, None]:
    """Provides the shared scraper session."""
    if _scraper_instance is None:
        raise RuntimeError("Scraper instance is not initialized")
    yield _scraper_instance
