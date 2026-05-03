import asyncio
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from models.schemas import WordDetailData, AudioLinks, TranslationItem
from core.config import api_settings, app_logger
from core.exceptions import (
    ProxyBlockedException,
    TargetSiteStructureChanged,
    WordNotFoundException,
    ScrapingTimeoutException,
    BaseTranslatorException
)


def _is_transient_error(exception: BaseException) -> bool:
    """Determine if an exception is transient and should be retried."""
    if isinstance(exception, (WordNotFoundException, TargetSiteStructureChanged)):
        return False
    return True


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception) & retry_if_exception_type(BaseTranslatorException),
    reraise=True
)
async def fetch_word_details(target_word: str, scraper: AsyncSession) -> WordDetailData:
    """
    Scrapes word translation details from the target website asynchronously.
    Uses tenacity for exponential backoff retries on transient errors.
    """
    target_url = f"{api_settings.target_base_url}/{target_word}"

    try:
        response = await scraper.get(target_url, timeout=api_settings.scraper_timeout)

        if response.status_code == 403 or response.status_code == 503:
            app_logger.warning("Scraper blocked by target", extra={"word": target_word, "status": response.status_code})
            raise ProxyBlockedException()

        if response.status_code == 404:
            raise WordNotFoundException(target_word)

        if response.status_code != 200:
            raise BaseTranslatorException(status_code=response.status_code, detail=f"Unexpected status code: {response.status_code}")

        # HTML parsing is fast enough to do synchronously in most cases
        html_soup = BeautifulSoup(response.text, "html.parser")

        # 1. Extract Audio Links
        audio_links_dict = {}
        audio_sources = html_soup.find_all("source", type="audio/mpeg")
        for media_source in audio_sources:
            audio_src = media_source.get("src", "")
            if audio_src:
                full_audio_url = (
                    f"https:{audio_src}" if audio_src.startswith("//") else audio_src
                )
                if "us/" in audio_src:
                    audio_links_dict["us"] = full_audio_url
                elif "uk/" in audio_src:
                    audio_links_dict["uk"] = full_audio_url
                elif "aus/" in audio_src:
                    audio_links_dict["aus"] = full_audio_url

        # 2. Extract Translations
        results_table = html_soup.find("table", {"id": "englishResultsTable"})

        if not results_table:
            # Table might be missing if word not found or layout changed
            not_found_msg = html_soup.find("h1")
            if not_found_msg and "Term not found" in not_found_msg.text:
                raise WordNotFoundException(target_word)
            raise TargetSiteStructureChanged()

        extracted_translations = []
        table_rows = results_table.find_all("tr")

        for current_row in table_rows:
            row_columns = current_row.find_all("td")
            if len(row_columns) < 4:
                continue

            category_col = row_columns[1]
            english_col = row_columns[2]
            turkish_col = row_columns[3]

            if category_col.has_attr("colspan"):
                continue

            usage_category = category_col.text.strip()
            type_element = english_col.find("i")
            word_type = type_element.text.strip() if type_element else ""

            term_element = english_col.find("a")
            english_term = (
                term_element.text.strip()
                if term_element
                else english_col.text.replace(word_type, "").strip()
            )

            meaning_element = turkish_col.find("a")
            turkish_meaning = (
                meaning_element.text.strip()
                if meaning_element
                else turkish_col.text.strip()
            )

            if not turkish_meaning or not english_term or "Category" in usage_category:
                continue

            is_duplicate = any(
                item["meaning"] == turkish_meaning and item["term"] == english_term
                for item in extracted_translations
            )

            if not is_duplicate:
                extracted_translations.append(
                    {
                        "category": usage_category,
                        "term": english_term,
                        "type": word_type,
                        "meaning": turkish_meaning,
                    }
                )

        if not extracted_translations:
             raise WordNotFoundException(target_word)

        return WordDetailData(
            word=target_word,
            audio=AudioLinks(**audio_links_dict),
            results=[TranslationItem(**item) for item in extracted_translations],
        )

    except (WordNotFoundException, TargetSiteStructureChanged):
        # Do not retry for non-transient errors
        raise
    except BaseTranslatorException:
        raise
    except TimeoutError:
        app_logger.warning("Scraping timeout", extra={"word": target_word})
        raise ScrapingTimeoutException()
    except Exception as runtime_error:
        app_logger.error(
            "Scraper error",
            extra={"word": target_word, "error": str(runtime_error)},
            exc_info=True,
        )
        raise BaseTranslatorException(
            status_code=500,
            detail="An internal error occurred while processing the word."
        )
