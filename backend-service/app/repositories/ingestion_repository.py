from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.chunking.models import DocumentChunk
from app.embedding.models import EmbeddingVector
from app.ingestion.models import CaptionedImage


class IngestionRepository(Protocol):
    """
    Define persistence operations required by the ingestion pipeline.

    Implementations are responsible for storing document metadata, text
    chunks, embeddings, extracted images, and processing status updates.

    The ingestion service depends on this protocol instead of a specific
    database implementation, allowing PostgreSQL persistence to be replaced
    or mocked during testing.
    """

    def create_document(
        self,
        *,
        file_name: str,
        file_type: str,
        source_container: str,
        source_blob_name: str,
        mime_type: str | None = None,
        file_size_bytes: int | None = None,
        checksum: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> UUID:
        """
        Create a document record and return its generated identifier.

        The document should initially be stored with a processing status such
        as ``processing`` so failures can be tracked and retried.
        """
        ...

    def save_chunks(
        self,
        *,
        document_id: UUID,
        chunks: list[DocumentChunk],
        embeddings: list[EmbeddingVector],
    ) -> None:
        """
        Persist document chunks together with their embedding vectors.

        The chunk and embedding collections must have matching lengths and
        corresponding item identifiers.
        """
        ...

    def save_images(
        self,
        *,
        document_id: UUID,
        captioned_images: list[CaptionedImage],
        caption_embeddings: list[EmbeddingVector],
        image_container: str,
    ) -> None:
        """
        Persist extracted image metadata, captions, and caption embeddings.

        Image binary content should already be uploaded to blob storage before
        this method is called.
        """
        ...

    def mark_document_completed(
        self,
        *,
        document_id: UUID,
    ) -> None:
        """Mark a successfully ingested document as completed."""
        ...

    def mark_document_failed(
        self,
        *,
        document_id: UUID,
        error_message: str,
    ) -> None:
        """Mark a failed document and store the failure description."""
        ...