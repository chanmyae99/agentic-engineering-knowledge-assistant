from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(chat_router)


@app.get("/")
def root():
    return {
        "message": "Backend Service Running",
        "environment": settings.environment,
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "repository": settings.repository_type,
    }