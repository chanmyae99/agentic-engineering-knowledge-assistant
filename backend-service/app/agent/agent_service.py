from __future__ import annotations

from app.agent.exceptions import EmptyQuestionError
from app.agent.models import AgentResponse, AgentSource
from app.agent.prompt_builder import AgentPromptBuilder
from app.embedding.embedding_service import EmbeddingService
from app.rag.llm_client import LLMClient
from app.rag.rag_service import RAGService
from app.retrieval.models import RetrievedChunk
from app.retrieval.retrieval_service import RetrievalService
from app.web_search.serper_client import SerperClient


class AgentService:
    """Route questions between internal RAG and web search."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        retrieval_service: RetrievalService,
        rag_service: RAGService,
        serper_client: SerperClient,
        llm_client: LLMClient,
        retrieval_score_threshold: float,
        web_top_k: int = 5,
    ) -> None:
        if not 0.0 <= retrieval_score_threshold <= 1.0:
            raise ValueError(
                "retrieval_score_threshold must be between 0 and 1."
            )

        if web_top_k < 1:
            raise ValueError("web_top_k must be at least 1.")

        self._embedding_service = embedding_service
        self._retrieval_service = retrieval_service
        self._rag_service = rag_service
        self._serper_client = serper_client
        self._llm_client = llm_client
        self._retrieval_score_threshold = retrieval_score_threshold
        self._web_top_k = web_top_k

    async def answer(
        self,
        question: str,
    ) -> AgentResponse:
        """Answer using internal documents or web-search fallback."""

        cleaned_question = self._validate_question(question)

        query_embedding = await self._embedding_service.embed_query(
            cleaned_question
        )

        embedding_values = self._extract_embedding_values(
            query_embedding
        )

        chunks = self._retrieval_service.retrieve(
            query_text=cleaned_question,
            query_embedding=embedding_values,
        )

        highest_score = self._get_highest_score(chunks)

        if self._should_use_internal_route(
            chunks=chunks,
            highest_score=highest_score,
        ):
            return await self._answer_from_internal_documents(
                question=cleaned_question,
                chunks=chunks,
                highest_score=highest_score,
            )

        route_reason = self._get_web_route_reason(chunks)

        return await self._answer_from_web(
            question=cleaned_question,
            highest_score=highest_score,
            retrieved_chunk_count=len(chunks),
            route_reason=route_reason,
        )

    async def _answer_from_internal_documents(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        highest_score: float,
    ) -> AgentResponse:
        """Generate an answer using retrieved internal chunks."""

        rag_response = await self._rag_service.answer_from_chunks(
            question=question,
            chunks=chunks,
        )

        sources = [
            AgentSource(
                source_type="internal",
                title=source.document_name,
                location=(
                    f"Page {source.page}"
                    if source.page is not None
                    else None
                ),
                score=source.score,
            )
            for source in rag_response.sources
        ]

        return AgentResponse(
            answer=rag_response.answer,
            route="internal",
            sources=sources,
            metadata={
                "route_reason": "retrieval_score_met_threshold",
                "highest_retrieval_score": highest_score,
                "retrieved_chunk_count": len(chunks),
                "retrieval_threshold": (
                    self._retrieval_score_threshold
                ),
            },
        )

    async def _answer_from_web(
        self,
        question: str,
        highest_score: float,
        retrieved_chunk_count: int,
        route_reason: str,
    ) -> AgentResponse:
        """Generate an answer using Serper web-search results."""

        web_response = await self._serper_client.search(
            query=question,
            top_k=self._web_top_k,
        )

        if not web_response.results:
            return AgentResponse(
                answer=(
                    "The internal documents did not contain enough "
                    "relevant information, and no useful web results "
                    "were found."
                ),
                route="unavailable",
                sources=[],
                metadata={
                    "route_reason": route_reason,
                    "highest_retrieval_score": highest_score,
                    "retrieved_chunk_count": retrieved_chunk_count,
                    "retrieval_threshold": (
                        self._retrieval_score_threshold
                    ),
                    "web_result_count": 0,
                },
            )

        prompt = AgentPromptBuilder.build(
            question=question,
            results=web_response.results,
        )

        answer = await self._llm_client.generate(prompt)

        sources = [
            AgentSource(
                source_type="web",
                title=result.title,
                url=result.link,
            )
            for result in web_response.results
        ]

        return AgentResponse(
            answer=answer,
            route="web",
            sources=sources,
            metadata={
                "route_reason": route_reason,
                "highest_retrieval_score": highest_score,
                "retrieved_chunk_count": retrieved_chunk_count,
                "retrieval_threshold": (
                    self._retrieval_score_threshold
                ),
                "web_result_count": len(web_response.results),
            },
        )

    def _should_use_internal_route(
        self,
        chunks: list[RetrievedChunk],
        highest_score: float,
    ) -> bool:
        """Return True when internal retrieval is sufficiently relevant."""

        if not chunks:
            return False

        return highest_score >= self._retrieval_score_threshold

    @staticmethod
    def _get_highest_score(
        chunks: list[RetrievedChunk],
    ) -> float:
        """Return the highest retrieval score, or zero when empty."""

        if not chunks:
            return 0.0

        return max(chunk.score for chunk in chunks)

    @staticmethod
    def _get_web_route_reason(
        chunks: list[RetrievedChunk],
    ) -> str:
        """Explain why the request was routed to web search."""

        if not chunks:
            return "no_chunks_retrieved"

        return "retrieval_score_below_threshold"

    @staticmethod
    def _validate_question(
        question: str,
    ) -> str:
        """Validate and normalize a user question."""

        if not isinstance(question, str) or not question.strip():
            raise EmptyQuestionError("Question must not be empty.")

        return question.strip()

    @staticmethod
    def _extract_embedding_values(
        embedding: object,
    ) -> list[float]:
        """Extract vector values from the embedding response model."""

        for attribute_name in (
            "values",
            "embedding",
            "vector",
        ):
            values = getattr(
                embedding,
                attribute_name,
                None,
            )

            if values is not None:
                return list(values)

        raise ValueError(
            "Unable to extract values from the embedding result."
        )