from __future__ import annotations
from urllib import response

from app.agent.exceptions import EmptyQuestionError
from app.agent.models import (
    AgentImage,
    AgentResponse,
    AgentSource,
)
from app.agent.prompt_builder import AgentPromptBuilder
from app.embedding.embedding_service import EmbeddingService
from app.rag.llm_client import LLMClient
from app.rag.rag_service import RAGService
from app.retrieval.models import RetrievedChunk, RetrievedImage
from app.retrieval.retrieval_service import RetrievalService
from app.web_search.serper_client import SerperClient
from app.storage.azure_blob_storage import AzureBlobStorage


class AgentService:
    """
    Orchestrate question answering across internal RAG and web search.

    The agent first embeds the user question and performs internal retrieval.
    If the retrieved text chunks meet the configured relevance threshold,
    the request is answered using the internal RAG pipeline.

    Relevant document images are also retrieved using image-caption
    embeddings and returned together with the internal answer.

    If internal retrieval confidence is insufficient, the agent falls back
    to web search using Serper.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        retrieval_service: RetrievalService,
        rag_service: RAGService,
        serper_client: SerperClient,
        llm_client: LLMClient,
        blob_storage: AzureBlobStorage,
        retrieval_score_threshold: float,
        web_top_k: int = 5,
        image_top_k: int = 3,
    ) -> None:
        """
        Initialize the agent and its dependencies.

        Parameters
        ----------
        embedding_service:
            Generates embeddings for user queries.

        retrieval_service:
            Retrieves relevant internal text chunks and images.

        rag_service:
            Produces answers grounded in retrieved internal text.

        serper_client:
            Performs external web search when internal retrieval is weak.

        llm_client:
            Generates responses from web-search context.

        retrieval_score_threshold:
            Minimum text-retrieval score required to use the internal route.

        web_top_k:
            Maximum number of web results used for fallback generation.

        image_top_k:
            Maximum number of internal images returned with a RAG response.
        """
        if not 0.0 <= retrieval_score_threshold <= 1.0:
            raise ValueError("retrieval_score_threshold must be between 0 and 1.")

        if web_top_k < 1:
            raise ValueError("web_top_k must be at least 1.")

        if image_top_k < 1:
            raise ValueError("image_top_k must be at least 1.")

        self._embedding_service = embedding_service
        self._retrieval_service = retrieval_service
        self._rag_service = rag_service
        self._serper_client = serper_client
        self._llm_client = llm_client
        self._blob_storage = blob_storage

        self._retrieval_score_threshold = retrieval_score_threshold
        self._web_top_k = web_top_k
        self._image_top_k = image_top_k

    async def answer(
        self,
        question: str,
    ) -> AgentResponse:
        """
        Answer a user question using internal RAG or web fallback.

        Processing flow
        ---------------
        1. Validate the user question.
        2. Generate a query embedding.
        3. Retrieve relevant internal text chunks.
        4. Evaluate the highest retrieval score.
        5. Use internal RAG when confidence is sufficient.
        6. Otherwise, fall back to web search.
        """
        cleaned_question = self._validate_question(question)

        # ----------------------------------------------------------
        # Generate one query embedding that can be reused for both
        # text retrieval and image-caption retrieval.
        # ----------------------------------------------------------

        query_embedding = await self._embedding_service.embed_query(cleaned_question)

        embedding_values = self._extract_embedding_values(query_embedding)

        # ----------------------------------------------------------
        # Retrieve relevant internal text chunks.
        # ----------------------------------------------------------

        chunks = self._retrieval_service.retrieve(
            query_text=cleaned_question,
            query_embedding=embedding_values,
        )

        highest_score = self._get_highest_score(chunks)

        # ----------------------------------------------------------
        # Internal route
        #
        # Image retrieval is only performed after the text route has
        # been accepted. This prevents unrelated image results from
        # being returned when the request should fall back to web.
        # ----------------------------------------------------------

        if self._should_use_internal_route(
            chunks=chunks,
            highest_score=highest_score,
        ):
            images = self._retrieval_service.retrieve_images(
                query_embedding=embedding_values,
                top_k=self._image_top_k,
            )

            return await self._answer_from_internal_documents(
                question=cleaned_question,
                chunks=chunks,
                images=images,
                highest_score=highest_score,
            )

        # ----------------------------------------------------------
        # Web fallback route
        # ----------------------------------------------------------

        route_reason = self._get_web_route_reason(chunks)

        return await self._answer_from_web(
            question=cleaned_question,
            highest_score=highest_score,
            retrieved_chunk_count=len(chunks),
            route_reason=route_reason,
        )
        
    async def evaluate_query(
        self,
        question: str,
    ) -> tuple[AgentResponse, list[RetrievedChunk]]:
        """
        Run the normal RAG retrieval pipeline for evaluation.

        In addition to the generated response, this method returns
        the retrieved text chunks so evaluation frameworks such as
        RAGAS can assess retrieval quality and answer faithfulness.

        Image retrieval is intentionally excluded because the current
        evaluation focuses on text-based RAG performance.
        """

        cleaned_question = self._validate_question(
        question
        )

        # Generate an embedding for the evaluation question.
        query_embedding = (
            await self._embedding_service.embed_query(
            cleaned_question
            )
        )

        embedding_values = self._extract_embedding_values(
            query_embedding
        )

        # Retrieve the same document chunks used by the RAG pipeline.
        chunks = self._retrieval_service.retrieve(
            query_text=cleaned_question,
            query_embedding=embedding_values,
        )

        highest_score = self._get_highest_score(
            chunks
        )

        # Use internal RAG when the retrieved chunks satisfy
        # the configured retrieval threshold.
        if self._should_use_internal_route(
            chunks=chunks,
            highest_score=highest_score,
        ):
            response = (
                await self._answer_from_internal_documents(
                    question=cleaned_question,
                    chunks=chunks,
                    highest_score=highest_score,
                )
            )
        

            return response, chunks

        # Otherwise use the existing web-search fallback.
        route_reason = self._get_web_route_reason(
            chunks
        )

        response = await self._answer_from_web(
            question=cleaned_question,
            highest_score=highest_score,
            retrieved_chunk_count=len(chunks),
            route_reason=route_reason,
        )

        return response, chunks


    async def _answer_from_internal_documents(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        images: list[RetrievedImage],
        highest_score: float,
    ) -> AgentResponse:
        """
        Generate an answer grounded in internal document chunks.

        Text chunks are passed to the RAG service for answer generation.
        Retrieved images are returned as supporting visual context for the
        frontend.
        """
        rag_response = await self._rag_service.answer_from_chunks(
            question=question,
            chunks=chunks,
        )

        sources = [
            AgentSource(
                source_type="internal",
                title=source.document_name,
                location=source.location,
                score=source.score,
            )
            for source in rag_response.sources
        ]

        agent_images = [
            AgentImage(
                image_id=image.image_id,
                document_name=str(
                    image.metadata.get(
                        "document_name",
                        image.document_id,
                    )
                ),
                page=image.metadata.get("page"),
                caption=image.caption,
                score=image.score,
                image_container=image.image_container,
                image_blob_name=image.image_blob_name,
                image_file_name=image.image_file_name,
                image_url=self._blob_storage.generate_read_url(
                    container_name=image.image_container,
                    blob_name=image.image_blob_name,
                    expiry_minutes=30,
                ),
            )
            for image in images
        ]

        return AgentResponse(
            answer=rag_response.answer,
            route="internal",
            sources=sources,
            images=agent_images,
            metadata={
                "route_reason": ("retrieval_score_met_threshold"),
                "highest_retrieval_score": highest_score,
                "retrieved_chunk_count": len(chunks),
                "retrieved_image_count": len(images),
                "retrieval_threshold": (self._retrieval_score_threshold),
            },
        )

    async def _answer_from_web(
        self,
        question: str,
        highest_score: float,
        retrieved_chunk_count: int,
        route_reason: str,
    ) -> AgentResponse:
        """
        Generate an answer from Serper web-search results.

        This route is used when internal retrieval does not meet the
        configured relevance threshold.
        """
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
                images=[],
                metadata={
                    "route_reason": route_reason,
                    "highest_retrieval_score": (highest_score),
                    "retrieved_chunk_count": (retrieved_chunk_count),
                    "retrieval_threshold": (self._retrieval_score_threshold),
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
            images=[],
            metadata={
                "route_reason": route_reason,
                "highest_retrieval_score": (highest_score),
                "retrieved_chunk_count": (retrieved_chunk_count),
                "retrieval_threshold": (self._retrieval_score_threshold),
                "web_result_count": len(web_response.results),
            },
        )

    def _should_use_internal_route(
        self,
        chunks: list[RetrievedChunk],
        highest_score: float,
    ) -> bool:
        """
        Determine whether internal retrieval is sufficiently relevant.
        """
        if not chunks:
            return False

        return highest_score >= self._retrieval_score_threshold

    @staticmethod
    def _get_highest_score(
        chunks: list[RetrievedChunk],
    ) -> float:
        """
        Return the highest retrieved chunk score.

        Empty retrieval results return zero.
        """
        if not chunks:
            return 0.0

        return max(chunk.score for chunk in chunks)

    @staticmethod
    def _get_web_route_reason(
        chunks: list[RetrievedChunk],
    ) -> str:
        """
        Describe why the question was routed to web search.
        """
        if not chunks:
            return "no_chunks_retrieved"

        return "retrieval_score_below_threshold"

    @staticmethod
    def _validate_question(
        question: str,
    ) -> str:
        """
        Validate and normalize a user question.
        """
        if not isinstance(question, str) or not question.strip():
            raise EmptyQuestionError("Question must not be empty.")

        return question.strip()

    @staticmethod
    def _extract_embedding_values(
        embedding: object,
    ) -> list[float]:
        """
        Extract vector values from the embedding response model.

        Several field names are supported to remain compatible with
        different embedding model representations.
        """
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

        raise ValueError("Unable to extract values from the embedding result.")

    @staticmethod
    def _build_internal_location(
        *,
        page: int | None,
        metadata: dict,
    ) -> str | None:
        """
        Build a human-readable internal source location.

        PDF sources use page numbers.

        DOCX sources use their section and paragraph range because Word
        document page numbers are not stable across different renderers.
        """
        if page is not None:
            return f"Page {page}"

        section = metadata.get("section")
        paragraph_start = metadata.get("paragraph_start")
        paragraph_end = metadata.get("paragraph_end")

        if section and paragraph_start is not None:
            if paragraph_end is not None and paragraph_end != paragraph_start:
                return (
                    f"Section: {section}, "
                    f"Paragraphs "
                    f"{paragraph_start}–{paragraph_end}"
                )

            return f"Section: {section}, " f"Paragraph {paragraph_start}"

        if section:
            return f"Section: {section}"

        if paragraph_start is not None:
            if paragraph_end is not None and paragraph_end != paragraph_start:
                return f"Paragraphs " f"{paragraph_start}–{paragraph_end}"

            return f"Paragraph {paragraph_start}"

        return None
