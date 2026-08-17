import asyncio

from app.agent.agent_service import AgentService
from app.core.config import get_settings
from app.embedding.embedding_client import OpenAIEmbeddingClient
from app.embedding.embedding_service import EmbeddingService
from app.rag.llm_client import LLMClient
from app.rag.rag_service import RAGService
from app.repositories.mock_chunk_repository import MockChunkRepository
from app.retrieval.retrieval_service import RetrievalService
from app.web_search.serper_client import SerperClient


async def main() -> None:
    settings = get_settings()

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is missing from .env.")

    if not settings.serper_api_key:
        raise ValueError("SERPER_API_KEY is missing from .env.")

    embedding_client = OpenAIEmbeddingClient(
        api_key=settings.openai_api_key,
    )

    embedding_service = EmbeddingService(
        client=embedding_client,
    )

    retrieval_service = RetrievalService(
        chunk_repository=MockChunkRepository(),
        top_k=settings.top_k,
    )

    llm_client = LLMClient(
        api_key=settings.openai_api_key,
    )

    rag_service = RAGService(
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
        llm_client=llm_client,
    )

    serper_client = SerperClient(
        api_key=settings.serper_api_key,
    )

    agent_service = AgentService(
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
        rag_service=rag_service,
        serper_client=serper_client,
        llm_client=llm_client,
        retrieval_score_threshold=(
            settings.retrieval_score_threshold
        ),
        web_top_k=settings.web_search_top_k,
    )

    questions = [
        "What PPE should employees wear?",
        "What is the latest stable version of Kubernetes?",
    ]

    try:
        for question in questions:
            response = await agent_service.answer(question)

            print("\n" + "=" * 70)
            print(f"QUESTION: {question}")
            print(f"ROUTE: {response.route}")

            print("\nANSWER")
            print(response.answer)

            print("\nSOURCES")
            if not response.sources:
                print("No sources returned.")
            else:
                for source in response.sources:
                    print(source)

            print("\nMETADATA")
            print(response.metadata)

    finally:
        await serper_client.close()


if __name__ == "__main__":
    asyncio.run(main())