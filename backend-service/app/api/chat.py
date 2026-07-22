from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent.agent_service import AgentService
from app.agent.exceptions import AgentError, EmptyQuestionError
from app.agent.models import AgentResponse
from app.api.dependencies import get_agent_service
from app.schemas.chat import ChatRequest


router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the engineering knowledge assistant",
)
async def chat(
    request: ChatRequest,
    agent_service: Annotated[
        AgentService,
        Depends(get_agent_service),
    ],
) -> AgentResponse:
    """Answer using internal RAG or web-search fallback."""

    try:
        return await agent_service.answer(
            question=request.question,
        )

    except EmptyQuestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except AgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc