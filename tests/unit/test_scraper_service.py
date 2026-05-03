import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
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

MOCK_HTML_NOT_FOUND = """
<html><body><p>No results.</p></body></html>
"""


def _mock_scraper(html: str, status_code: int = 200):
    response = MagicMock()
    response.status_code = status_code
    response.text = html
    response.raise_for_status = MagicMock()
    scraper = MagicMock()
    scraper.get.return_value = response
    return scraper


class TestFetchWordDetails:
    def test_successful_scrape_returns_word_data(self):
        scraper = _mock_scraper(MOCK_HTML_FOUND)
        result = fetch_word_details("hello", scraper)

        assert result.word == "hello"
        assert len(result.results) == 2
        assert result.results[0].meaning == "merhaba"
        assert result.results[0].type == "interj."
        assert result.results[1].meaning == "selam"

    def test_audio_links_extracted_correctly(self):
        scraper = _mock_scraper(MOCK_HTML_FOUND)
        result = fetch_word_details("hello", scraper)

        assert result.audio.us == "https://cdn.tureng.com/us/hello.mp3"
        assert result.audio.uk == "https://cdn.tureng.com/uk/hello.mp3"
        assert result.audio.aus is None

    def test_word_not_found_raises_404(self):
        scraper = _mock_scraper(MOCK_HTML_NOT_FOUND)
        with pytest.raises(HTTPException) as exc_info:
            fetch_word_details("xyzunknownword", scraper)
        assert exc_info.value.status_code == 404

    def test_403_response_raises_503(self):
        scraper = _mock_scraper("", status_code=403)
        with pytest.raises(HTTPException) as exc_info:
            fetch_word_details("hello", scraper)
        assert exc_info.value.status_code == 503

    def test_network_error_raises_500(self):
        scraper = MagicMock()
        scraper.get.side_effect = ConnectionError("Network unreachable")
        with pytest.raises(HTTPException) as exc_info:
            fetch_word_details("hello", scraper)
        assert exc_info.value.status_code == 500

    def test_duplicate_translations_are_filtered(self):
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
        result = fetch_word_details("run", scraper)
        assert len(result.results) == 1
