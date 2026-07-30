from __future__ import annotations

import asyncio
from pathlib import Path

from app.chunking.chunking_service import ChunkingService
from app.core.config import get_settings
from app.embedding.embedding_client import OpenAIEmbeddingClient
from app.embedding.embedding_service import EmbeddingService
from app.ingestion.caption_client import OpenAIImageCaptionClient
from app.ingestion.caption_service import CaptionService
from app.ingestion.document_parser import DocumentParser
from app.ingestion.ingestion_service import IngestionService
from app.repositories.postgres_ingestion_repository import (
    PostgresIngestionRepository,
)
from app.storage.azure_blob_storage import AzureBlobStorage


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


async def main() -> None:
    settings = get_settings()

    if not settings.azure_storage_connection_string:
        raise RuntimeError(
            "AZURE_STORAGE_CONNECTION_STRING is not configured."
        )

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    # ----------------------------------------------------------
    # Infrastructure
    # ----------------------------------------------------------

    blob_storage = AzureBlobStorage(
        settings.azure_storage_connection_string,
    )

    document_parser = DocumentParser()

    chunking_service = ChunkingService()

    embedding_client = OpenAIEmbeddingClient(
        api_key=settings.openai_api_key,
        model="text-embedding-3-small",
        expected_dimensions=1536,
    )

    embedding_service = EmbeddingService(
        client=embedding_client,
    )

    caption_client = OpenAIImageCaptionClient(
        api_key=settings.openai_api_key,
    )

    caption_service = CaptionService(
        caption_client=caption_client,
    )

    repository = PostgresIngestionRepository()

    ingestion_service = IngestionService(
        blob_storage=blob_storage,
        document_parser=document_parser,
        source_container=(
            settings.azure_original_documents_container
        ),
        image_container=(
            settings.azure_extracted_images_container
        ),
        ingestion_repository=repository,
        chunking_service=chunking_service,
        embedding_service=embedding_service,
        caption_service=caption_service,
    )

    # ----------------------------------------------------------
    # Discover documents
    # ----------------------------------------------------------

    blob_names = blob_storage.list_blobs(
        settings.azure_original_documents_container,
    )

    documents = [
        blob_name
        for blob_name in blob_names
        if Path(blob_name).suffix.lower()
        in SUPPORTED_EXTENSIONS
    ]

    print(f"\nFound {len(documents)} document(s).\n")

    success = 0
    failed = 0

    # ----------------------------------------------------------
    # Ingest documents
    # ----------------------------------------------------------

    for blob_name in documents:
        print(f"Ingesting: {blob_name}")

        try:
            document_id = (
                await ingestion_service.ingest_document(
                    blob_name
                )
            )

            success += 1

            print(
                f"✓ Success "
                f"(document_id={document_id})\n"
            )

        except Exception as exc:
            failed += 1

            print(
                f"✗ Failed\n"
                f"  {exc}\n"
            )

    # ----------------------------------------------------------
    # Cleanup
    # ----------------------------------------------------------

    await embedding_client.close()
    await caption_client.close()

    print("=" * 50)
    print("Ingestion Summary")
    print("=" * 50)
    print(f"Successful : {success}")
    print(f"Failed     : {failed}")
    print(f"Total      : {len(documents)}")


if __name__ == "__main__":
    asyncio.run(main())