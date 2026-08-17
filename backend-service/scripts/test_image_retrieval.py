import asyncio

from app.core.config import get_settings
from app.core.container import ServiceContainer


async def main() -> None:
    settings = get_settings()
    container = ServiceContainer(settings)

    try:
        # Create an embedding for an image-related query.
        query_embedding = (
            await container.embedding_service.embed_query(
                "combustible dust explosion diagram"
            )
        )

        # EmbeddingVector may expose the vector using one of these names.
        embedding_values = None

        for field_name in ("values", "embedding", "vector"):
            value = getattr(query_embedding, field_name, None)

            if value is not None:
                embedding_values = list(value)
                break

        if embedding_values is None:
            raise RuntimeError(
                "Could not find embedding values."
            )

        # Search image caption embeddings.
        images = container.retrieval_service.retrieve_images(
            query_embedding=embedding_values,
            top_k=3,
        )

        print("\nImage retrieval results")
        print("=" * 60)

        for index, image in enumerate(images, start=1):
            print(f"\nResult {index}")
            print(f"File: {image.image_file_name}")
            print(
                "Document:",
                image.metadata.get("document_name"),
            )
            print(
                "Page:",
                image.metadata.get("page"),
            )
            print(f"Score: {image.score:.3f}")
            print(f"Caption: {image.caption}")
            print(
                "Blob:",
                f"{image.image_container}/"
                f"{image.image_blob_name}",
            )

    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())