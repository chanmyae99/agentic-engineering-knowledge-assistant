from typing import Any

from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """A document chunk returned by retrieval."""

    chunk_id: str
    document_id: str
    content: str
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)



class RetrievedImage(BaseModel):
    """An image returned by semantic image-caption retrieval."""

    image_id: str
    document_id: str
    caption: str
    score: float = 0.0

    image_container: str
    image_blob_name: str
    image_file_name: str

    metadata: dict[str, Any] = Field(default_factory=dict)