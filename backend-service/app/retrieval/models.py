from typing import Any

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """A document chunk returned by retrieval."""

    chunk_id: str
    document_id: str
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)