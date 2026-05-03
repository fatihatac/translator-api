import time
import pytest
from models.schemas import WordDetailData, AudioLinks
from services.cache_service import TranslationCache


def _make_word_data(word: str) -> WordDetailData:
    return WordDetailData(word=word, audio=AudioLinks(), results=[])


class TestTranslationCache:
    def setup_method(self):
        self.cache = TranslationCache(maxsize=5, ttl=2)

    def test_set_and_get(self):
        data = _make_word_data("hello")
        self.cache.set("hello", data)
        result = self.cache.get("hello")
        assert result is not None
        assert result.word == "hello"

    def test_get_missing_key_returns_none(self):
        assert self.cache.get("nonexistent") is None

    def test_entry_expires_after_ttl(self):
        data = _make_word_data("expire")
        self.cache.set("expire", data)
        assert self.cache.get("expire") is not None
        time.sleep(2.1)
        assert self.cache.get("expire") is None

    def test_delete(self):
        data = _make_word_data("delete_me")
        self.cache.set("delete_me", data)
        self.cache.delete("delete_me")
        assert self.cache.get("delete_me") is None

    def test_delete_nonexistent_does_not_raise(self):
        self.cache.delete("ghost_key")  # Should not raise

    def test_clear(self):
        self.cache.set("a", _make_word_data("a"))
        self.cache.set("b", _make_word_data("b"))
        self.cache.clear()
        assert self.cache.stats()["current_size"] == 0

    def test_stats(self):
        self.cache.set("x", _make_word_data("x"))
        stats = self.cache.stats()
        assert stats["current_size"] == 1
        assert stats["max_size"] == 5
        assert stats["ttl_seconds"] == 2

    def test_maxsize_eviction(self):
        """When cache is full, adding a new item evicts the oldest (LRU)."""
        for i in range(5):
            self.cache.set(f"word_{i}", _make_word_data(f"word_{i}"))
        assert self.cache.stats()["current_size"] == 5
        self.cache.set("word_new", _make_word_data("word_new"))
        assert self.cache.stats()["current_size"] == 5
