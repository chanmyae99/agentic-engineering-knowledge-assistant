from __future__ import annotations

from app.agent.agent_service import AgentService
from app.core.config import Settings
from app.embedding.embedding_client import OpenAIEmbeddingClient
from app.embedding.embedding_service import EmbeddingService
from app.rag.llm_client import LLMClient
from app.rag.rag_service import RAGService
from app.repositories.mock_chunk_repository import MockChunkRepository
from app.retrieval.retrieval_service import RetrievalService
from app.web_search.serper_client import SerperClient


class ServiceContainer:
    """Create and hold shared application services."""

    def __init__(
        self,
        settings: Settings,
    ) -> None:
        self.settings = settings

        openai_api_key = self._require_setting(
            value=settings.openai_api_key,
            setting_name="OPENAI_API_KEY",
        )

        serper_api_key = self._require_setting(
            value=settings.serper_api_key,
            setting_name="SERPER_API_KEY",
        )

        # --------------------------------------------------------------
        # Repository
        # --------------------------------------------------------------

        self.chunk_repository = MockChunkRepository()

        # --------------------------------------------------------------
        # Embedding
        # --------------------------------------------------------------

        self.embedding_client = OpenAIEmbeddingClient(
            api_key=openai_api_key,
            model="text-embedding-3-small",
            expected_dimensions=1536,
        )

        self.embedding_service = EmbeddingService(
            client=self.embedding_client,
        )

        # --------------------------------------------------------------
        # Retrieval
        # --------------------------------------------------------------

        self.retrieval_service = RetrievalService(
            chunk_repository=self.chunk_repository,
            top_k=settings.top_k,
        )

        # --------------------------------------------------------------
        # LLM and RAG
        # --------------------------------------------------------------

        self.llm_client = LLMClient(
            api_key=openai_api_key,
            model="gpt-4.1-mini",
        )

        self.rag_service = RAGService(
            embedding_service=self.embedding_service,
            retrieval_service=self.retrieval_service,
            llm_client=self.llm_client,
        )

        # --------------------------------------------------------------
        # Web search
        # --------------------------------------------------------------

        self.serper_client = SerperClient(
            api_key=serper_api_key,
        )

        # --------------------------------------------------------------
        # Agent
        # --------------------------------------------------------------

        self.agent_service = AgentService(
            embedding_service=self.embedding_service,
            retrieval_service=self.retrieval_service,
            rag_service=self.rag_service,
            serper_client=self.serper_client,
            llm_client=self.llm_client,
            retrieval_score_threshold=(
                settings.retrieval_score_threshold
            ),
            web_top_k=settings.web_search_top_k,
        )

    async def close(self) -> None:
        """Close shared asynchronous clients."""

        await self.embedding_client.close()
        await self.serper_client.close()

    @staticmethod
    def _require_setting(
        value: str | None,
        setting_name: str,
    ) -> str:
        """Return a required setting or raise a clear startup error."""

        if value is None or not value.strip():
            raise RuntimeError(
                f"{setting_name} must be configured before "
                "starting the application."
            )

        return value.strip()