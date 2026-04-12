import cloudscraper
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from models.schemas import WordDetailData, AudioLinks, TranslationItem
from core.config import app_logger

def fetch_word_details(target_word: str) -> WordDetailData:
    target_url = f"https://tureng.com/en/turkish-english/{target_word}"
    
    scraper = cloudscraper.create_scraper(browser={
        'browser': 'chrome', 
        'platform': 'windows', 
        'mobile': False
    })

    try:
        response = scraper.get(target_url, timeout=10)
        
        if response.status_code == 403:
            app_logger.warning(f"403 Forbidden for word: {target_word}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
                detail="Scraping service is temporarily blocked by the target server."
            )

        response.raise_for_status()
        html_soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Extract Audio Links
        audio_links_dict = {}
        audio_sources = html_soup.find_all("source", type="audio/mpeg")
        for media_source in audio_sources:
            audio_src = media_source.get("src", "")
            if audio_src:
                full_audio_url = f"https:{audio_src}" if audio_src.startswith("//") else audio_src
                if "us/" in audio_src: audio_links_dict["us"] = full_audio_url
                elif "uk/" in audio_src: audio_links_dict["uk"] = full_audio_url
                elif "aus/" in audio_src: audio_links_dict["aus"] = full_audio_url

        # 2. Extract Translations
        results_table = html_soup.find("table", {"id": "englishResultsTable"})
        extracted_translations = []

        if not results_table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Word '{target_word}' not found or invalid."
            )

        table_rows = results_table.find_all("tr")

        for current_row in table_rows:
            row_columns = current_row.find_all("td")
            if len(row_columns) >= 4:
                category_col = row_columns[1]
                english_col = row_columns[2]
                turkish_col = row_columns[3]

                if category_col.has_attr('colspan'):
                    continue

                usage_category = category_col.text.strip()
                type_element = english_col.find("i")
                word_type = type_element.text.strip() if type_element else ""
                
                term_element = english_col.find("a")
                english_term = term_element.text.strip() if term_element else english_col.text.replace(word_type, "").strip()
                
                meaning_element = turkish_col.find("a")
                turkish_meaning = meaning_element.text.strip() if meaning_element else turkish_col.text.strip()

                if turkish_meaning and english_term and "Category" not in usage_category:
                    is_duplicate_entry = any(
                        item["meaning"] == turkish_meaning and item["term"] == english_term 
                        for item in extracted_translations
                    )
                    
                    if not is_duplicate_entry:
                        extracted_translations.append({
                            "category": usage_category,
                            "term": english_term,
                            "type": word_type, 
                            "meaning": turkish_meaning
                        })

        return WordDetailData(
            word=target_word,
            audio=AudioLinks(**audio_links_dict),
            results=[TranslationItem(**item) for item in extracted_translations]
        )

    except HTTPException:
        raise
    except Exception as runtime_error:
        app_logger.error(f"Error scraping '{target_word}': {str(runtime_error)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="An internal error occurred while processing the word."
        )