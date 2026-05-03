import pytest
from unittest.mock import AsyncMock, patch
from core.exceptions import (
    WordNotFoundException,
    ProxyBlockedException,
    BaseTranslatorException,
    TargetSiteStructureChanged
)
from services.scraper_service import fetch_word_details


MOCK_HTML_FOUND = """
<html>
<body>
  <audio>
    <source src="//cdn.tureng.com/us/hello.mp3" type="audio/mpeg">
    <source src="//cdn.tureng.com/uk/hello.mp3" type="audio/mpeg">
  </audio>
  <table id="englishResultsTable">
    <tr>
      <td></td>
      <td>Common Usage</td>
      <td><a>hello</a> <i>interj.</i></td>
      <td><a>merhaba</a></td>
    </tr>
    <tr>
      <td></td>
      <td>Informal</td>
      <td><a>hello</a> <i>n.</i></td>
      <td><a>selam</a></td>
    </tr>
  </table>
</body>
</html>
"""

MOCK_HTML_NOT_FOUND_H1 = """
<html><body><h1>Term not found</h1></body></html>
"""

MOCK_HTML_NO_TABLE = """
<html><body><h1>Some other error</h1></body></html>
"""


def _mock_scraper(html: str, status_code: int = 200):
    response = AsyncMock()
    response.status_code = status_code
    response.text = html
    scraper = AsyncMock()
    scraper.get.return_value = response
    return scraper


@pytest.mark.asyncio
class TestFetchWordDetails:
    async def test_successful_scrape_returns_word_data(self):
        scraper = _mock_scraper(MOCK_HTML_FOUND)
        result = await fetch_word_details("hello", scraper)

        assert result.word == "hello"
        assert len(result.results) == 2
        assert result.results[0].meaning == "merhaba"
        assert result.results[0].type == "interj."
        assert result.results[1].meaning == "selam"

    async def test_audio_links_extracted_correctly(self):
        scraper = _mock_scraper(MOCK_HTML_FOUND)
        result = await fetch_word_details("hello", scraper)

        assert str(result.audio.us) == "https://cdn.tureng.com/us/hello.mp3"
        assert str(result.audio.uk) == "https://cdn.tureng.com/uk/hello.mp3"
        assert result.audio.aus is None

    async def test_word_not_found_raises_404_status(self):
        scraper = _mock_scraper("", status_code=404)
        with pytest.raises(WordNotFoundException):
            await fetch_word_details("xyzunknownword", scraper)

    async def test_word_not_found_h1_msg(self):
        scraper = _mock_scraper(MOCK_HTML_NOT_FOUND_H1)
        with pytest.raises(WordNotFoundException):
            await fetch_word_details("xyzunknownword", scraper)

    async def test_table_missing_raises_structure_changed(self):
        scraper = _mock_scraper(MOCK_HTML_NO_TABLE)
        with pytest.raises(TargetSiteStructureChanged):
            await fetch_word_details("hello", scraper)

    async def test_403_response_raises_proxy_blocked(self):
        scraper = _mock_scraper("", status_code=403)
        with pytest.raises(ProxyBlockedException):
            await fetch_word_details("hello", scraper)

    async def test_network_error_raises_500(self):
        scraper = AsyncMock()
        scraper.get.side_effect = Exception("Network unreachable")
        with pytest.raises(BaseTranslatorException) as exc_info:
            await fetch_word_details("hello", scraper)
        assert exc_info.value.status_code == 500

    async def test_duplicate_translations_are_filtered(self):
        """Identical term+meaning pairs should only appear once."""
        html_with_dupes = """
        <html><body>
          <table id="englishResultsTable">
            <tr><td></td><td>General</td><td><a>run</a></td><td><a>koşmak</a></td></tr>
            <tr><td></td><td>Sports</td><td><a>run</a></td><td><a>koşmak</a></td></tr>
          </table>
        </body></html>
        """
        scraper = _mock_scraper(html_with_dupes)
        result = await fetch_word_details("run", scraper)
        assert len(result.results) == 1
