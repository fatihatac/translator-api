import logging
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    project_title: str = "Translator API"
    project_version: str = "1.0.0"
    max_cache_size: int = 1000
    
    # Pydantic will automatically parse the JSON array from .env
    allowed_cors_origins: List[str] = []

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

api_settings = AppSettings()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
app_logger = logging.getLogger("translator_api")