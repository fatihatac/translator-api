from typing import Dict
from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from models.schemas import TranslationResponse, WordDetailData
from services.scraper_service import fetch_word_details

# 1. Eski MAX_CACHE_SIZE yerine yeni api_settings objesini dahil ediyoruz
from core.config import app_logger, api_settings

translation_router = APIRouter()

# In-memory dictionary cache
translation_cache: Dict[str, WordDetailData] = {}

@translation_router.get("/{word}", response_model=TranslationResponse)
async def get_translation(word: str):
    target_word = word.lower().strip()

    # Check cache first
    if target_word in translation_cache:
        app_logger.info(f"Cache hit for word: {target_word}")
        return TranslationResponse(source="cache", data=translation_cache[target_word])

    app_logger.info(f"Live fetching word: {target_word}")
    
    # Run synchronous scraper in a threadpool to avoid blocking
    scraped_result = await run_in_threadpool(fetch_word_details, target_word)

    # 2. Burada api_settings.max_cache_size kullanarak kontrolü sağlıyoruz
    if len(translation_cache) >= api_settings.max_cache_size:
        oldest_cache_key = next(iter(translation_cache))
        del translation_cache[oldest_cache_key]
        
    translation_cache[target_word] = scraped_result

    return TranslationResponse(source="live", data=scraped_result)