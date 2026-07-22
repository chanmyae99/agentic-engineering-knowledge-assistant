from typing import Any

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    """Reference to a retrieved source."""

    document_name: str
    page: int | None = None
    score: float


class RAGResponse(BaseModel):
    """Final response returned by the RAG pipeline."""

    answer: str

    sources: list[SourceReference] = Field(
        default_factory=list,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )