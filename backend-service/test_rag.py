import asyncio

from app.core.config import get_settings

settings = get_settings()

from app.embedding.embedding_client import OpenAIEmbeddingClient
from app.embedding.embedding_service import EmbeddingService

from app.rag.llm_client import LLMClient
from app.rag.rag_service import RAGService

from app.repositories.mock_chunk_repository import MockChunkRepository
from app.retrieval.retrieval_service import RetrievalService


async def main():

    embedding_client = OpenAIEmbeddingClient(
        api_key=settings.openai_api_key,
    )

    embedding_service = EmbeddingService(
        client=embedding_client,
    )

    retrieval_service = RetrievalService(
        chunk_repository=MockChunkRepository(),
    )

    llm_client = LLMClient(
        api_key=settings.openai_api_key,
    )

    rag_service = RAGService(
        embedding_service=embedding_service,
        retrieval_service=retrieval_service,
        llm_client=llm_client,
    )

    response = await rag_service.answer(
        "What PPE should employees wear?"
    )

    print("\nANSWER")
    print("-" * 60)
    print(response.answer)

    print("\nSOURCES")
    print("-" * 60)

    for source in response.sources:
        print(source)


if __name__ == "__main__":
    asyncio.run(main())