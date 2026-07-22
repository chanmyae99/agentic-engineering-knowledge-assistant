from __future__ import annotations

from app.embedding.embedding_service import EmbeddingService
from app.embedding.models import EmbeddingVector
from app.rag.llm_client import LLMClient
from app.rag.models import RAGResponse, SourceReference
from app.retrieval.models import RetrievedChunk
from app.rag.prompt_builder import PromptBuilder
from app.retrieval.retrieval_service import RetrievalService


class RAGService:
    """Coordinate embedding, retrieval and grounded answer generation."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        retrieval_service: RetrievalService,
        llm_client: LLMClient,
    ) -> None:
        self._embedding_service = embedding_service
        self._retrieval_service = retrieval_service
        self._llm_client = llm_client

    async def answer(
        self,
        question: str,
        top_k: int | None = None,
    ) -> RAGResponse:
        """Generate an answer grounded in retrieved document chunks."""

        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must not be empty.")

        cleaned_question = question.strip()

        query_embedding = await self._embedding_service.embed_query(
            cleaned_question
        )

        embedding_values = self._extract_embedding_values(
            query_embedding
        )

        chunks = self._retrieval_service.retrieve(
            query_text=cleaned_question,
            query_embedding=embedding_values,
            top_k=top_k,
        )

        if not chunks:
            return RAGResponse(
                answer=(
                    "The available documents do not contain enough "
                    "information to answer this question."
                ),
                sources=[],
                metadata={
                    "retrieved_chunk_count": 0,
                    "requires_web_search": True,
                },
            )

        prompt = PromptBuilder.build(
            question=cleaned_question,
            chunks=chunks,
        )

        answer = await self._llm_client.generate(prompt)

        sources = [
            SourceReference(
                document_name=str(
                    chunk.metadata.get(
                        "document_name",
                        chunk.document_id,
                    )
                ),
                page=chunk.metadata.get("page"),
                score=chunk.score,
            )
            for chunk in chunks
        ]

        return RAGResponse(
            answer=answer,
            sources=sources,
            metadata={
                "retrieved_chunk_count": len(chunks),
                "requires_web_search": False,
            },
        )

    @staticmethod
    def _extract_embedding_values(
        embedding: EmbeddingVector,
    ) -> list[float]:
        """
        Extract the numerical vector from an EmbeddingVector.

        Supports common field names so the service remains compatible
        with the existing embedding model.
        """

        for field_name in ("values", "embedding", "vector"):
            values = getattr(embedding, field_name, None)

            if values is not None:
                return list(values)

        raise ValueError(
            "EmbeddingVector does not contain values, embedding, "
            "or vector data."
        )

    async def answer_from_chunks(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> RAGResponse:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Question must not be empty.")

        if not chunks:
            raise ValueError(
                "At least one retrieved chunk is required."
            )

        prompt = PromptBuilder.build(
            question=question.strip(),
            chunks=chunks,
        )

        answer = await self._llm_client.generate(prompt)

        sources = [
            SourceReference(
                document_name=str(
                    chunk.metadata.get(
                        "document_name",
                        chunk.document_id,
                    )
                ),
                page=chunk.metadata.get("page"),
                score=chunk.score,
            )
            for chunk in chunks
        ]

        return RAGResponse(
            answer=answer,
            sources=sources,
            metadata={
                "retrieved_chunk_count": len(chunks),
            },
        )