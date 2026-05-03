from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class TranslationItem(BaseModel):
    category: str = Field(..., min_length=1, description="Usage category")
    term: str = Field(..., min_length=1, description="English term")
    type: str = Field(..., description="Word type (e.g., n., v.)")
    meaning: str = Field(..., min_length=1, description="Turkish meaning")


class AudioLinks(BaseModel):
    us: Optional[HttpUrl] = Field(None, description="US English audio URL")
    uk: Optional[HttpUrl] = Field(None, description="UK English audio URL")
    aus: Optional[HttpUrl] = Field(None, description="Australian English audio URL")


class WordDetailData(BaseModel):
    word: str = Field(..., min_length=1, description="The queried word")
    audio: AudioLinks
    results: List[TranslationItem] = Field(default_factory=list)


class TranslationResponse(BaseModel):
    source: str = Field(..., pattern="^(cache|live)$", description="Indicates if the data is from 'cache' or 'live'")
    data: WordDetailData


class PingResponse(BaseModel):
    status: str = Field(..., pattern="^ok$")


class CacheStats(BaseModel):
    current_size: int = Field(..., ge=0)
    max_size: int = Field(..., gt=0)
    ttl_seconds: int = Field(..., gt=0)
    type: str = Field(..., description="Type of cache (memory, redis)")


class HealthResponse(BaseModel):
    status: str = Field(..., pattern="^ok$")
    version: str
    uptime_seconds: int = Field(..., ge=0)
    cache: CacheStats
