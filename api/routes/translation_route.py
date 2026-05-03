from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from slowapi import Limiter
from slowapi.util import get_remote_address

from models.schemas import TranslationResponse
from services.scraper_service import fetch_word_details
from services.cache_service import TranslationCache
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
    cache: TranslationCache = Depends(get_cache),
    scraper=Depends(get_scraper),
):
    target_word = word.lower().strip()

    # 1. Cache check
    cached_result = cache.get(target_word)
    if cached_result:
        app_logger.info("Cache hit", extra={"word": target_word})
        return TranslationResponse(source="cache", data=cached_result)

    # 2. Live fetch (runs sync scraper in a thread to avoid blocking the event loop)
    app_logger.info("Live fetch", extra={"word": target_word})
    result = await run_in_threadpool(fetch_word_details, target_word, scraper)

    # 3. Store in cache
    cache.set(target_word, result)

    return TranslationResponse(source="live", data=result)
