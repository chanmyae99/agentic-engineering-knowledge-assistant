import asyncio

from app.core.config import get_settings
from app.web_search.serper_client import SerperClient


async def main() -> None:
    settings = get_settings()

    if not settings.serper_api_key:
        raise ValueError(
            "SERPER_API_KEY is missing from the .env file."
        )

    client = SerperClient(
        api_key=settings.serper_api_key,
    )

    try:
        response = await client.search(
            query="latest manufacturing workplace safety guidelines",
            top_k=3,
        )

        print(f"\nQUERY: {response.query}")
        print(f"RESULTS: {len(response.results)}")

        for index, result in enumerate(
            response.results,
            start=1,
        ):
            print("\n" + "=" * 60)
            print(f"RESULT {index}")
            print(f"Title: {result.title}")
            print(f"Link: {result.link}")
            print(f"Snippet: {result.snippet}")
            print(f"Position: {result.position}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())