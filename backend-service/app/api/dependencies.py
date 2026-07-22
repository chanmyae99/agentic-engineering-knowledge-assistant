from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.agent.agent_service import AgentService
from app.core.container import ServiceContainer


def get_service_container(
    request: Request,
) -> ServiceContainer:
    """Return the application service container."""

    container = getattr(
        request.app.state,
        "service_container",
        None,
    )

    if container is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application services are not available.",
        )

    return container


def get_agent_service(
    request: Request,
) -> AgentService:
    """Return the shared AgentService instance."""

    container = get_service_container(request)

    return container.agent_service