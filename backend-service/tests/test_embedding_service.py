import asyncio
import os

from dotenv import load_dotenv

from app.embedding.embedding_client import OpenAIEmbeddingClient
from app.embedding.embedding_service import EmbeddingService
from app.embedding.models import EmbeddingInput


load_dotenv()


async def main() -> None:
    client = OpenAIEmbeddingClient(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        ),
        expected_dimensions=int(
            os.getenv("EMBEDDING_DIMENSION", "1536")
        ),
    )

    service = EmbeddingService(
        client=client,
        batch_size=int(
            os.getenv("EMBEDDING_BATCH_SIZE", "32")
        ),
    )

    inputs = [
        EmbeddingInput(
            item_id=f"chunk-{index}",
            text=f"Safety procedure number {index}.",
        )
        for index in range(3)
    ]

    try:
        result = await service.embed_inputs(inputs)

        print("MODEL:", result.model)
        print("INPUT COUNT:", result.input_count)
        print("DIMENSIONS:", result.dimensions)
        print("TOTAL TOKENS:", result.total_tokens)

        query = await service.embed_query(
            "What are the safety procedures?"
        )

        print("QUERY DIMENSIONS:", query.dimensions)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())