from app.repositories.chunk_repository import ChunkRepository
from app.repositories.image_repository import ImageRepository
from app.retrieval.models import (
    RetrievedChunk,
    RetrievedImage,
)


class RetrievalService:
    """Retrieve relevant text chunks and document images."""

    def __init__(
        self,
        chunk_repository: ChunkRepository,
        image_repository: ImageRepository,
        top_k: int = 5,
        image_top_k: int = 3,
    ) -> None:
        self._chunk_repository = chunk_repository
        self._image_repository = image_repository
        self._top_k = top_k
        self._image_top_k = image_top_k

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

    def retrieve_images(
        self,
        query_embedding: list[float],
        top_k: int | None = None,
    ) -> list[RetrievedImage]:
        if not query_embedding:
            raise ValueError("Query embedding must not be empty.")

        result_limit = top_k or self._image_top_k

        return self._image_repository.semantic_search(
            query_embedding=query_embedding,
            top_k=result_limit,
        )