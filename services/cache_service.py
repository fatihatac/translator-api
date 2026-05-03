import json
import threading
from typing import Optional
from cachetools import TTLCache
import redis.asyncio as redis

from models.schemas import WordDetailData
from services.cache_base import BaseCache
from core.config import app_logger


class MemoryCache(BaseCache):
    """
    Thread-safe, TTL-aware in-memory cache for translation results.
    """
    def __init__(self, maxsize: int, ttl: int) -> None:
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()

    async def get(self, key: str) -> Optional[WordDetailData]:
        with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: WordDetailData) -> None:
        with self._lock:
            self._cache[key] = value

    async def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    async def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    async def stats(self) -> dict:
        with self._lock:
            return {
                "current_size": len(self._cache),
                "max_size": self._cache.maxsize,
                "ttl_seconds": self._cache.ttl,
                "type": "memory"
            }


class RedisCache(BaseCache):
    """
    Redis-based cache for horizontal scaling.
    """
    def __init__(self, redis_url: str, ttl: int) -> None:
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.ttl = ttl

    async def get(self, key: str) -> Optional[WordDetailData]:
        try:
            data = await self.redis.get(key)
            if data:
                return WordDetailData.model_validate_json(data)
        except Exception as e:
            app_logger.error(f"Redis get error: {e}")
        return None

    async def set(self, key: str, value: WordDetailData) -> None:
        try:
            await self.redis.set(key, value.model_dump_json(), ex=self.ttl)
        except Exception as e:
            app_logger.error(f"Redis set error: {e}")

    async def delete(self, key: str) -> None:
        try:
            await self.redis.delete(key)
        except Exception as e:
            app_logger.error(f"Redis delete error: {e}")

    async def clear(self) -> None:
        try:
            await self.redis.flushdb()
        except Exception as e:
            app_logger.error(f"Redis clear error: {e}")

    async def stats(self) -> dict:
        try:
            db_size = await self.redis.dbsize()
            return {
                "current_size": db_size,
                "max_size": 0,  # Redis configuration dependent
                "ttl_seconds": self.ttl,
                "type": "redis"
            }
        except Exception as e:
            app_logger.error(f"Redis stats error: {e}")
            return {
                "current_size": 0,
                "max_size": 0,
                "ttl_seconds": self.ttl,
                "type": "redis"
            }
