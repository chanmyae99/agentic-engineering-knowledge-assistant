import asyncio
import os

from dotenv import load_dotenv

from app.embedding.embedding_client import OpenAIEmbeddingClient
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

    inputs = [
        EmbeddingInput(
            item_id="chunk-0",
            text="Workers must wear appropriate protective equipment.",
            metadata={
                "source_type": "chunk",
                "chunk_index": 0,
            },
        ),
        EmbeddingInput(
            item_id="chunk-1",
            text="Emergency exits must remain unobstructed.",
            metadata={
                "source_type": "chunk",
                "chunk_index": 1,
            },
        ),
    ]

    try:
        result = await client.embed(inputs)

        print("MODEL:", result.model)
        print("INPUT COUNT:", result.input_count)
        print("DIMENSIONS:", result.dimensions)
        print("TOTAL TOKENS:", result.total_tokens)

        for embedding in result.embeddings:
            print(
                embedding.item_id,
                len(embedding.vector),
                embedding.metadata,
            )
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())