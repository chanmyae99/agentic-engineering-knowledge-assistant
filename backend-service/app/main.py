from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.ingestion import router as ingestion_router
from app.core.config import get_settings
from app.core.container import ServiceContainer


settings = get_settings()


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """Create shared services at startup and close them at shutdown."""

    container = ServiceContainer(
        settings=settings,
    )

    app.state.service_container = container

    try:
        yield
    finally:
        await container.close()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
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