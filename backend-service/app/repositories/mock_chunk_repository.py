from app.repositories.chunk_repository import ChunkRepository
from app.retrieval.models import RetrievedChunk


class MockChunkRepository(ChunkRepository):
    """Temporary repository used until PostgreSQL is available."""

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        normalized_query = query_text.strip().lower()

        ppe_keywords = {
            "ppe",
            "helmet",
            "helmets",
            "glove",
            "gloves",
            "safety shoe",
            "safety shoes",
            "protective equipment",
            "personal protective equipment",
        }

        is_ppe_question = any(
            keyword in normalized_query
            for keyword in ppe_keywords
        )

        if not is_ppe_question:
            return []

        chunks = [
            RetrievedChunk(
                chunk_id="chunk-001",
                document_id="document-001",
                content=(
                    "Employees must wear safety helmets, "
                    "protective gloves and safety shoes "
                    "before entering the workshop."
                ),
                score=0.95,
                metadata={
                    "document_name": "Safety SOP.pdf",
                    "page": 12,
                },
            ),
            RetrievedChunk(
                chunk_id="chunk-002",
                document_id="document-001",
                content=(
                    "Visitors must register at the security "
                    "counter before entering production areas."
                ),
                score=0.88,
                metadata={
                    "document_name": "Safety SOP.pdf",
                    "page": 5,
                },
            ),
        ]

        return chunks[:top_k]