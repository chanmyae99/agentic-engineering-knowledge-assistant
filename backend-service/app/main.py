from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.ingestion import router as ingestion_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(chat_router)
app.include_router(ingestion_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Backend Service Running",
        "environment": settings.environment,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "repository": settings.repository_type,
    }