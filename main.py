from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import api_settings
from api.routes.health_route import health_router
from api.routes.translation_route import translation_router

app = FastAPI(
    title=api_settings.project_title,
    version=api_settings.project_version,
)

app.add_middleware(
    CORSMiddleware, # type: ignore
    allow_origins=api_settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST" ,"OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "x-api-key"
    ],
)

app.include_router(health_router, prefix="/api", tags=["Health"])
app.include_router(translation_router, prefix="/api/translate", tags=["Translation"])

if __name__ == "__main__":
    print(f"🚀 {api_settings.project_title} is starting on http://127.0.0.1:8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)