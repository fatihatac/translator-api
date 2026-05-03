import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from main import app
from models.schemas import WordDetailData, AudioLinks, TranslationItem
from services.cache_service import TranslationCache

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
def client():
    """
    Creates a TestClient with:
    - mocked app.state (no real scraper or network calls)
    - API key auth disabled (api_key = "") so route logic is tested in isolation
    """
    mock_cache = TranslationCache(maxsize=10, ttl=60)
    mock_scraper = MagicMock()

    with patch("core.security.api_settings") as mock_settings:
        mock_settings.api_key = ""  # Auth disabled — tested separately in TestApiKeySecurity
        with TestClient(app, raise_server_exceptions=False) as c:
            # IMPORTANT: set state AFTER entering the context so lifespan doesn't overwrite them
            c.app.state.cache = mock_cache
            c.app.state.scraper = mock_scraper
            yield c, mock_cache, mock_scraper


class TestTranslationRoute:
    def test_live_fetch_returns_200(self, client):
        test_client, cache, scraper = client
        word = "apple"

        with patch("api.routes.translation_route.fetch_word_details") as mock_fetch:
            mock_fetch.return_value = _make_mock_result(word)
            response = test_client.get(f"/api/translate/{word}")

        assert response.status_code == 200
        body = response.json()
        assert body["source"] == "live"
        assert body["data"]["word"] == word

    def test_cache_hit_returns_from_cache(self, client):
        test_client, cache, scraper = client
        word = "book"
        cache.set(word, _make_mock_result(word))

        with patch("api.routes.translation_route.fetch_word_details") as mock_fetch:
            response = test_client.get(f"/api/translate/{word}")
            mock_fetch.assert_not_called()

        assert response.status_code == 200
        assert response.json()["source"] == "cache"

    def test_word_is_lowercased_and_stripped(self, client):
        test_client, cache, scraper = client

        with patch("api.routes.translation_route.fetch_word_details") as mock_fetch:
            mock_fetch.return_value = _make_mock_result("hello")
            response = test_client.get("/api/translate/HELLO")

        assert response.status_code == 200
        # First positional arg passed to fetch_word_details must be lowercased
        called_word = mock_fetch.call_args[0][0]
        assert called_word == "hello"

    def test_result_is_cached_after_live_fetch(self, client):
        test_client, cache, scraper = client
        word = "chair"

        with patch("api.routes.translation_route.fetch_word_details") as mock_fetch:
            mock_fetch.return_value = _make_mock_result(word)
            test_client.get(f"/api/translate/{word}")

        assert cache.get(word) is not None

    def test_scraper_404_returns_404(self, client):
        test_client, cache, scraper = client
        from fastapi import HTTPException

        with patch("api.routes.translation_route.fetch_word_details") as mock_fetch:
            mock_fetch.side_effect = HTTPException(status_code=404, detail="Not found")
            response = test_client.get("/api/translate/xyzunknown")

        assert response.status_code == 404

    def test_scraper_503_returns_503(self, client):
        test_client, cache, scraper = client
        from fastapi import HTTPException

        with patch("api.routes.translation_route.fetch_word_details") as mock_fetch:
            mock_fetch.side_effect = HTTPException(status_code=503, detail="Blocked")
            response = test_client.get("/api/translate/anything")

        assert response.status_code == 503


class TestHealthRoute:
    def test_ping_returns_awake(self, client):
        test_client, *_ = client
        response = test_client.get("/api/ping")
        assert response.status_code == 200
        assert response.json()["status"] == "awake"

    def test_health_returns_metrics(self, client):
        test_client, *_ = client
        response = test_client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert "uptime_seconds" in body
        assert "cache" in body
        assert "current_size" in body["cache"]


class TestApiKeySecurity:
    @pytest.fixture
    def auth_client(self):
        """Separate client fixture where API key IS enforced."""
        with TestClient(app, raise_server_exceptions=False) as c:
            c.app.state.cache = TranslationCache(maxsize=10, ttl=60)
            c.app.state.scraper = MagicMock()
            yield c

    def test_request_without_key_is_rejected_when_key_configured(self, auth_client):
        with patch("core.security.api_settings") as mock_settings:
            mock_settings.api_key = "secret-key"
            response = auth_client.get("/api/translate/hello")
        assert response.status_code == 403

    def test_request_with_correct_key_is_accepted(self, auth_client):
        with patch("core.security.api_settings") as mock_settings:
            mock_settings.api_key = "secret-key"
            with patch("api.routes.translation_route.fetch_word_details") as mock_fetch:
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
