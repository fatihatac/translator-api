import time
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
    Implements a simple Circuit Breaker pattern.
    """
    def __init__(self, redis_url: str, ttl: int) -> None:
        self.redis = redis.from_url(redis_url, decode_responses=True, socket_timeout=1.0)
        self.ttl = ttl
        
        # Circuit Breaker state
        self._error_count = 0
        self._max_errors = 3
        self._circuit_open_until = 0.0
        self._circuit_open_duration = 30.0  # seconds

    def _is_circuit_open(self) -> bool:
        if time.time() < self._circuit_open_until:
            return True
        # If time passed, half-open (reset errors to give it a chance)
        if self._error_count >= self._max_errors:
            self._error_count = 0
        return False

    def _record_error(self):
        self._error_count += 1
        if self._error_count >= self._max_errors:
            self._circuit_open_until = time.time() + self._circuit_open_duration
            app_logger.error(f"Redis Circuit Breaker OPENED for {self._circuit_open_duration}s")

    def _record_success(self):
        if self._error_count > 0:
            self._error_count = 0

    async def get(self, key: str) -> Optional[WordDetailData]:
        if self._is_circuit_open():
            return None  # Degraded mode: bypass cache

        try:
            data = await self.redis.get(key)
            self._record_success()
            if data:
                return WordDetailData.model_validate_json(data)
        except Exception as e:
            app_logger.error(f"Redis get error: {e}")
            self._record_error()
        return None

    async def set(self, key: str, value: WordDetailData) -> None:
        if self._is_circuit_open():
            return
            
        try:
            await self.redis.set(key, value.model_dump_json(), ex=self.ttl)
            self._record_success()
        except Exception as e:
            app_logger.error(f"Redis set error: {e}")
            self._record_error()

    async def delete(self, key: str) -> None:
        if self._is_circuit_open():
            return

        try:
            await self.redis.delete(key)
            self._record_success()
        except Exception as e:
            app_logger.error(f"Redis delete error: {e}")
            self._record_error()

    async def clear(self) -> None:
        if self._is_circuit_open():
            return

        try:
            await self.redis.flushdb()
            self._record_success()
        except Exception as e:
            app_logger.error(f"Redis clear error: {e}")
            self._record_error()

    async def stats(self) -> dict:
        if self._is_circuit_open():
            return {
                "current_size": 0,
                "max_size": 0,
                "ttl_seconds": self.ttl,
                "type": "redis (DEGRADED)"
            }
            
        try:
            db_size = await self.redis.dbsize()
            self._record_success()
            return {
                "current_size": db_size,
                "max_size": 0,  # Redis configuration dependent
                "ttl_seconds": self.ttl,
                "type": "redis"
            }
        except Exception as e:
            app_logger.error(f"Redis stats error: {e}")
            self._record_error()
            return {
                "current_size": 0,
                "max_size": 0,
                "ttl_seconds": self.ttl,
                "type": "redis (DEGRADED)"
            }
