from app.repositories.mock_chunk_repository import MockChunkRepository
from app.retrieval.retrieval_service import RetrievalService


def main() -> None:
    repository = MockChunkRepository()

    retrieval_service = RetrievalService(
        chunk_repository=repository,
        top_k=5,
    )

    results = retrieval_service.retrieve(
        query_text="What PPE should employees wear?",
        query_embedding=[0.1] * 1536,
    )

    print(f"Retrieved {len(results)} chunks")

    for index, chunk in enumerate(results, start=1):
        print("\n" + "=" * 60)
        print(f"RESULT {index}")
        print(f"Chunk ID: {chunk.chunk_id}")
        print(f"Document ID: {chunk.document_id}")
        print(f"Score: {chunk.score}")
        print(f"Metadata: {chunk.metadata}")
        print(f"Content: {chunk.content}")


if __name__ == "__main__":
    main()