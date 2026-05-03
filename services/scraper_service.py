import cloudscraper
from bs4 import BeautifulSoup
from fastapi import HTTPException, status

from models.schemas import WordDetailData, AudioLinks, TranslationItem
from core.config import api_settings, app_logger


def fetch_word_details(target_word: str, scraper=None) -> WordDetailData:
    """
    Scrapes word translation details from the target website.

    Args:
        target_word: The word to look up.
        scraper: A shared cloudscraper instance injected via app.state.
                 Falls back to creating a new one if not provided (e.g. in tests).
    """
    if scraper is None:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )

    target_url = f"{api_settings.target_base_url}/{target_word}"

    try:
        response = scraper.get(target_url, timeout=api_settings.scraper_timeout)

        if response.status_code == 403:
            app_logger.warning("Scraper blocked by target", extra={"word": target_word})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scraping service is temporarily blocked by the target server.",
            )

        response.raise_for_status()
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Word '{target_word}' not found or invalid.",
            )

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

        return WordDetailData(
            word=target_word,
            audio=AudioLinks(**audio_links_dict),
            results=[TranslationItem(**item) for item in extracted_translations],
        )

    except HTTPException:
        raise
    except Exception as runtime_error:
        app_logger.error(
            "Scraper error",
            extra={"word": target_word, "error": str(runtime_error)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the word.",
        )
