from typing import List, Optional
from pydantic import BaseModel, Field


class TranslationItem(BaseModel):
    category: str
    term: str
    type: str
    meaning: str


class AudioLinks(BaseModel):
    us: Optional[str] = None
    uk: Optional[str] = None
    aus: Optional[str] = None


class WordDetailData(BaseModel):
    word: str
    audio: AudioLinks
    results: List[TranslationItem]


class TranslationResponse(BaseModel):
    source: str = Field(..., description="Indicates if the data is from 'cache' or 'live'")
    data: WordDetailData


class PingResponse(BaseModel):
    status: str


class CacheStats(BaseModel):
    current_size: int
    max_size: int
    ttl_seconds: int


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: int
    cache: CacheStats
