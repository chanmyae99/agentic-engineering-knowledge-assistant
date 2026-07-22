from typing import Protocol

from app.retrieval.models import RetrievedChunk


class ChunkRepository(Protocol):
    """Interface for searching stored document chunks."""

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        ...