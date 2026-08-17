from typing import Protocol

from app.retrieval.models import RetrievedImage


class ImageRepository(Protocol):
    """Interface for searching stored document images."""

    def semantic_search(
        self,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedImage]:
        ...