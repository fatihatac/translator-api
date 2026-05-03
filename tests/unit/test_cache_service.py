import time
import pytest
import asyncio
from models.schemas import WordDetailData, AudioLinks
from services.cache_service import MemoryCache


def _make_word_data(word: str) -> WordDetailData:
    return WordDetailData(word=word, audio=AudioLinks(), results=[])


@pytest.mark.asyncio
class TestMemoryCache:
    def setup_method(self):
        self.cache = MemoryCache(maxsize=5, ttl=2)

    async def test_set_and_get(self):
        data = _make_word_data("hello")
        await self.cache.set("hello", data)
        result = await self.cache.get("hello")
        assert result is not None
        assert result.word == "hello"

    async def test_get_missing_key_returns_none(self):
        assert await self.cache.get("nonexistent") is None

    async def test_entry_expires_after_ttl(self):
        data = _make_word_data("expire")
        await self.cache.set("expire", data)
        assert await self.cache.get("expire") is not None
        await asyncio.sleep(2.1)
        assert await self.cache.get("expire") is None

    async def test_delete(self):
        data = _make_word_data("delete_me")
        await self.cache.set("delete_me", data)
        await self.cache.delete("delete_me")
        assert await self.cache.get("delete_me") is None

    async def test_delete_nonexistent_does_not_raise(self):
        await self.cache.delete("ghost_key")  # Should not raise

    async def test_clear(self):
        await self.cache.set("a", _make_word_data("a"))
        await self.cache.set("b", _make_word_data("b"))
        await self.cache.clear()
        stats = await self.cache.stats()
        assert stats["current_size"] == 0

    async def test_stats(self):
        await self.cache.set("x", _make_word_data("x"))
        stats = await self.cache.stats()
        assert stats["current_size"] == 1
        assert stats["max_size"] == 5
        assert stats["ttl_seconds"] == 2
        assert stats["type"] == "memory"

    async def test_maxsize_eviction(self):
        """When cache is full, adding a new item evicts the oldest (LRU)."""
        for i in range(5):
            await self.cache.set(f"word_{i}", _make_word_data(f"word_{i}"))
        stats = await self.cache.stats()
        assert stats["current_size"] == 5
        await self.cache.set("word_new", _make_word_data("word_new"))
        stats = await self.cache.stats()
        assert stats["current_size"] == 5
