from __future__ import annotations

from app.agent.agent_service import AgentService
from app.core.config import Settings
from app.embedding.embedding_client import OpenAIEmbeddingClient
from app.embedding.embedding_service import EmbeddingService
from app.rag.llm_client import LLMClient
from app.rag.rag_service import RAGService
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.mock_chunk_repository import MockChunkRepository
from app.repositories.postgres_chunk_repository import (
    PostgresChunkRepository,
)
from app.retrieval.retrieval_service import RetrievalService
from app.web_search.serper_client import SerperClient
from app.repositories.postgres_ingestion_repository import (
    PostgresIngestionRepository,
)
from app.chunking.chunking_service import ChunkingService

class ServiceContainer:
    """Create and manage shared application services."""

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
        # Repositories
        # Configure retrieval and ingestion persistence.
        # --------------------------------------------------------------

        self.chunk_repository = self._create_chunk_repository(
            settings=settings,
        )

        self.ingestion_repository = PostgresIngestionRepository()

        # --------------------------------------------------------------
        # Chunking
        # Convert parsed document units into validated structured chunks.
        # --------------------------------------------------------------

        self.chunking_service = ChunkingService()

        # --------------------------------------------------------------
        # Embedding
        # Generate vector embeddings for queries and document chunks.
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
        # Retrieve the most relevant chunks from the configured store.
        # --------------------------------------------------------------

        self.retrieval_service = RetrievalService(
            chunk_repository=self.chunk_repository,
            top_k=settings.top_k,
        )

        # --------------------------------------------------------------
        # Large Language Model (LLM)
        # Generate responses using retrieved context.
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
        # Web Search
        # Used when retrieval confidence is below the threshold.
        # --------------------------------------------------------------

        self.serper_client = SerperClient(
            api_key=serper_api_key,
        )

        # --------------------------------------------------------------
        # Agent
        # Orchestrates retrieval, RAG generation and web search.
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
        """Release shared asynchronous resources."""

        await self.embedding_client.close()
        await self.serper_client.close()

    @staticmethod
    def _require_setting(
        value: str | None,
        setting_name: str,
    ) -> str:
        """Return a required configuration value."""

        if value is None or not value.strip():
            raise RuntimeError(
                f"{setting_name} must be configured before "
                "starting the application."
            )

        return value.strip()

    @staticmethod
    def _create_chunk_repository(
        settings: Settings,
    ) -> ChunkRepository:
        """
        Create the configured chunk repository.

        Supported repository types:
        - memory: Mock repository for development and testing.
        - postgres: PostgreSQL + pgvector repository.
        """

        repository_type = settings.repository_type.strip().lower()

        if repository_type == "memory":
            return MockChunkRepository()

        if repository_type == "postgres":
            if (
                settings.database_url is None
                or not settings.database_url.strip()
            ):
                raise RuntimeError(
                    "DATABASE_URL must be configured when "
                    "REPOSITORY_TYPE=postgres."
                )

            return PostgresChunkRepository()

        raise RuntimeError(
            "Unsupported REPOSITORY_TYPE: "
            f"{settings.repository_type!r}. "
            "Expected 'memory' or 'postgres'."
        )