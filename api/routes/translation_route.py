from fastapi import APIRouter, Depends, Request
from curl_cffi.requests import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address

from models.schemas import TranslationResponse
from services.scraper_service import fetch_word_details
from services.cache_base import BaseCache
from core.config import app_logger
from core.security import verify_api_key
from core.dependencies import get_cache, get_scraper

limiter = Limiter(key_func=get_remote_address)

translation_router = APIRouter(dependencies=[Depends(verify_api_key)])


@translation_router.get(
    "/{word}",
    response_model=TranslationResponse,
    summary="Translate a word",
    description="Fetches translation details for the given English/Turkish word. Results are cached with TTL.",
)
@limiter.limit("30/minute")
async def get_translation(
    request: Request,
    word: str,
    cache: BaseCache = Depends(get_cache),
    scraper: AsyncSession = Depends(get_scraper),
):
    target_word = word.lower().strip()

    # 1. Cache check
    cached_result = await cache.get(target_word)
    if cached_result:
        app_logger.info("Cache hit", extra={"word": target_word})
        return TranslationResponse(source="cache", data=cached_result)

    # 2. Live fetch (async execution)
    app_logger.info("Live fetch", extra={"word": target_word})
    result = await fetch_word_details(target_word, scraper)

    # 3. Store in cache
    await cache.set(target_word, result)

    return TranslationResponse(source="live", data=result)
