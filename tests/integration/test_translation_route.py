import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from models.schemas import WordDetailData, AudioLinks, TranslationItem
from core.dependencies import get_cache, get_scraper
from services.cache_service import MemoryCache

TEST_API_KEY = "test-api-key-123"


def _make_mock_result(word: str) -> WordDetailData:
    return WordDetailData(
        word=word,
        audio=AudioLinks(us="https://example.com/us.mp3"),
        results=[
            TranslationItem(category="General", term=word, type="n.", meaning="test_anlam")
        ],
    )


@pytest.fixture
def mock_cache():
    return MemoryCache(maxsize=10, ttl=60)

@pytest.fixture
def mock_scraper():
    return AsyncMock()

@pytest.fixture
def client(mock_cache, mock_scraper):
    """
    Creates a TestClient with overridden dependencies.
    """
    app.dependency_overrides[get_cache] = lambda: mock_cache
    app.dependency_overrides[get_scraper] = lambda: mock_scraper

    with patch("core.security.api_settings") as mock_settings:
        mock_settings.api_key = ""  # Auth disabled
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c, mock_cache, mock_scraper
            
    app.dependency_overrides.clear()


class TestTranslationRoute:
    def test_live_fetch_returns_200(self, client):
        test_client, cache, scraper = client
        word = "apple"

        with patch("api.routes.translation_route.fetch_word_details", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = _make_mock_result(word)
            response = test_client.get(f"/api/translate/{word}")

        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "live"
        assert body["data"]["word"] == word

    @pytest.mark.asyncio
    async def test_cache_hit_returns_from_cache(self, client):
        test_client, cache, scraper = client
        word = "book"
        await cache.set(word, _make_mock_result(word))

        with patch("api.routes.translation_route.fetch_word_details", new_callable=AsyncMock) as mock_fetch:
            response = test_client.get(f"/api/translate/{word}")
            mock_fetch.assert_not_called()

        assert response.status_code == 200
        assert response.json()["source"] == "cache"

    def test_word_is_lowercased_and_stripped(self, client):
        test_client, cache, scraper = client

        with patch("api.routes.translation_route.fetch_word_details", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = _make_mock_result("hello")
            response = test_client.get("/api/translate/HELLO")

        assert response.status_code == 200
        called_word = mock_fetch.call_args[0][0]
        assert called_word == "hello"

    @pytest.mark.asyncio
    async def test_result_is_cached_after_live_fetch(self, client):
        test_client, cache, scraper = client
        word = "chair"

        with patch("api.routes.translation_route.fetch_word_details", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = _make_mock_result(word)
            test_client.get(f"/api/translate/{word}")

        assert await cache.get(word) is not None

    def test_scraper_404_returns_404(self, client):
        test_client, cache, scraper = client
        from core.exceptions import WordNotFoundException

        with patch("api.routes.translation_route.fetch_word_details", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = WordNotFoundException("xyzunknown")
            response = test_client.get("/api/translate/xyzunknown")

        assert response.status_code == 404

    def test_scraper_503_returns_503(self, client):
        test_client, cache, scraper = client
        from core.exceptions import ProxyBlockedException

        with patch("api.routes.translation_route.fetch_word_details", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ProxyBlockedException()
            response = test_client.get("/api/translate/anything")

        assert response.status_code == 503


class TestHealthRoute:
    def test_ping_returns_ok(self, client):
        test_client, *_ = client
        response = test_client.get("/api/ping")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_returns_metrics(self, client):
        test_client, *_ = client
        response = test_client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "uptime_seconds" in body
        assert "cache" in body
        assert "current_size" in body["cache"]


class TestApiKeySecurity:
    @pytest.fixture
    def auth_client(self, mock_cache, mock_scraper):
        app.dependency_overrides[get_cache] = lambda: mock_cache
        app.dependency_overrides[get_scraper] = lambda: mock_scraper
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
        app.dependency_overrides.clear()

    def test_request_without_key_is_rejected_when_key_configured(self, auth_client):
        with patch("core.security.api_settings") as mock_settings:
            mock_settings.api_key = "secret-key"
            response = auth_client.get("/api/translate/hello")
        assert response.status_code == 403

    def test_request_with_correct_key_is_accepted(self, auth_client):
        with patch("core.security.api_settings") as mock_settings:
            mock_settings.api_key = "secret-key"
            with patch("api.routes.translation_route.fetch_word_details", new_callable=AsyncMock) as mock_fetch:
                mock_fetch.return_value = _make_mock_result("hello")
                response = auth_client.get(
                    "/api/translate/hello", headers={"x-api-key": "secret-key"}
                )
        assert response.status_code == 200

    def test_request_with_wrong_key_is_rejected(self, auth_client):
        with patch("core.security.api_settings") as mock_settings:
            mock_settings.api_key = "secret-key"
            response = auth_client.get(
                "/api/translate/hello", headers={"x-api-key": "wrong-key"}
            )
        assert response.status_code == 403
