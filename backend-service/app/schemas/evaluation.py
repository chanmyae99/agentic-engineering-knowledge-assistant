from typing import Any

from pydantic import BaseModel, Field

from app.agent.models import AgentSource


class EvaluationQueryRequest(BaseModel):
    """Request model for evaluating a single RAG query."""

    question: str


class EvaluationQueryResponse(BaseModel):
    """
    Evaluation response containing the generated answer and
    retrieved document contexts required by RAGAS.
    """

    question: str
    answer: str
    route: str

    retrieved_contexts: list[str] = Field(
        default_factory=list
    )

    sources: list[AgentSource] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )