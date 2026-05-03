from fastapi import Request
from services.cache_service import TranslationCache


def get_cache(request: Request) -> TranslationCache:
    """Provides the shared TranslationCache instance from app state."""
    return request.app.state.cache


def get_scraper(request: Request):
    """Provides the shared cloudscraper instance from app state."""
    return request.app.state.scraper
