from fastapi import APIRouter, Depends

from app.agent.agent_service import AgentService
from app.api.dependencies import get_agent_service
from app.schemas.evaluation import (
    EvaluationQueryRequest,
    EvaluationQueryResponse,
)


router = APIRouter(
    prefix="/evaluation",
    tags=["Evaluation"],
)


@router.post(
    "/query",
    response_model=EvaluationQueryResponse,
)
async def evaluate_query(
    request: EvaluationQueryRequest,
    agent_service: AgentService = Depends(
        get_agent_service
    ),
) -> EvaluationQueryResponse:
    """
    Run one question through the real agent pipeline and expose the
    retrieved chunk text required for offline RAG evaluation.

    This endpoint is intended for evaluation and debugging only.
    """

    response, chunks = (
        await agent_service.evaluate_query(
            request.question
        )
    )

    return EvaluationQueryResponse(
        question=request.question,
        answer=response.answer,
        route=response.route,
        retrieved_contexts=[
            chunk.content
            for chunk in chunks
        ],
        sources=response.sources,
        metadata=response.metadata,
    )