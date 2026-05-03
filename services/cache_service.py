import threading
from typing import Optional
from cachetools import TTLCache
from models.schemas import WordDetailData


class TranslationCache:
    """
    Thread-safe, TTL-aware in-memory cache for translation results.

    Uses a threading.Lock to prevent race conditions when multiple
    async workers (run_in_threadpool) read/write concurrently.
    TTLCache automatically evicts entries after `ttl` seconds.
    """

    def __init__(self, maxsize: int, ttl: int) -> None:
        self._cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[WordDetailData]:
        with self._lock:
            return self._cache.get(key)

    def set(self, key: str, value: WordDetailData) -> None:
        with self._lock:
            self._cache[key] = value

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def stats(self) -> dict:
        with self._lock:
            return {
                "current_size": len(self._cache),
                "max_size": self._cache.maxsize,
                "ttl_seconds": self._cache.ttl,
            }
