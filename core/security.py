from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from core.config import api_settings

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def verify_api_key(key: str = Security(api_key_header)) -> None:
    """
    FastAPI dependency that validates the x-api-key header.
    If API_KEY is not configured in .env, authentication is skipped (dev mode).
    """
    if not api_settings.api_key:
        return  # Dev mode: no key configured, allow all requests

    if not key or key != api_settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key.",
        )
