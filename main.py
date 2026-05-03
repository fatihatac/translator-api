from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn

from core.config import api_settings, app_logger
from core.lifespan import lifespan
from api.routes.health_route import health_router
from api.routes.translation_route import translation_router

# --- Rate Limiter (shared across routes) ---
limiter = Limiter(key_func=get_remote_address)

# --- Application ---
app = FastAPI(
    title=api_settings.project_title,
    version=api_settings.project_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# --- Rate Limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore



# --- Global Exception Handlers ---
from core.exceptions import BaseTranslatorException

@app.exception_handler(BaseTranslatorException)
async def custom_translator_exception_handler(request: Request, exc: BaseTranslatorException):
    app_logger.error(
        "Translator error",
        extra={"path": str(request.url), "error": str(exc.detail), "status_code": exc.status_code},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    app_logger.error(
        "Unhandled exception",
        extra={"path": str(request.url), "error": str(exc)},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error."},
    )

# --- CORS ---
app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=api_settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "x-api-key",
    ],
)

# --- Security Headers Middleware ---
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastly.jsdelivr.net;"
    )
    return response

# --- Routers ---
app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(translation_router, prefix="/api/translate", tags=["Translation"])


if __name__ == "__main__":
    print(f"🚀 {api_settings.project_title} starting on http://127.0.0.1:8000")
    print(f"📜 For docs go to http://127.0.0.1:8000/api/docs")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
