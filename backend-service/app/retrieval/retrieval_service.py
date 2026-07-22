from app.repositories.chunk_repository import ChunkRepository
from app.retrieval.models import RetrievedChunk


class RetrievalService:
    """Retrieves the most relevant document chunks."""

    def __init__(
        self,
        chunk_repository: ChunkRepository,
        top_k: int = 5,
    ) -> None:
        self._chunk_repository = chunk_repository
        self._top_k = top_k

    def retrieve(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        if not query_text.strip():
            raise ValueError("Query text must not be empty.")

        if not query_embedding:
            raise ValueError("Query embedding must not be empty.")

        result_limit = top_k or self._top_k

        return self._chunk_repository.hybrid_search(
            query_text=query_text,
            query_embedding=query_embedding,
            top_k=result_limit,
        )