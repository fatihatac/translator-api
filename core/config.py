import logging
import sys
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
try:
    from pythonjsonlogger import jsonlogger  # legacy (<= 2.x)
except ImportError:  # pragma: no cover
    from pythonjsonlogger import json as jsonlogger  # type: ignore


class AppSettings(BaseSettings):
    # --- Project ---
    project_title: str = "Translator API"
    project_version: str = "1.0.0"

    # --- Security ---
    api_key: str = ""

    # --- Cache ---
    max_cache_size: int = 1000
    cache_ttl_seconds: int = 3600
    redis_url: str | None = None

    # --- Scraper ---
    target_base_url: str = "https://tureng.com/en/turkish-english"
    scraper_timeout: int = 10

    # --- CORS ---
    allowed_cors_origins: List[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


api_settings = AppSettings()


def _setup_logger(name: str) -> logging.Logger:
    """Configure a JSON structured logger for production use."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    return logger


app_logger = _setup_logger("translator_api")
