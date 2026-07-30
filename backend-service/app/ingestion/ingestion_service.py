"""
Application service for orchestrating document ingestion.

The ingestion service coordinates the complete workflow:

1. Download the source document from blob storage.
2. Parse text units and extract images.
3. Create or reset the document record in PostgreSQL.
4. Build structure-aware text chunks.
5. Generate embeddings for text chunks.
6. Persist chunks and embeddings.
7. Caption extracted images.
8. Upload extracted images to blob storage.
9. Generate embeddings for image captions.
10. Persist image metadata and caption embeddings.
11. Mark the document as completed or failed.

The actual parsing, chunking, embedding, captioning, storage and database
operations remain delegated to their respective services.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import replace
from pathlib import PurePosixPath
from uuid import UUID

from app.chunking.chunking_service import ChunkingService
from app.embedding.embedding_service import EmbeddingService
from app.embedding.models import EmbeddingInput
from app.ingestion.caption_service import CaptionService
from app.ingestion.document_parser import DocumentParser
from app.ingestion.models import (
    CaptionedImage,
    IngestionResult,
    ParsedDocument,
    TextUnit,
)
from app.repositories.ingestion_repository import IngestionRepository
from app.storage.blob_storage import BlobStorage


logger = logging.getLogger(__name__)


class IngestionService:
    """
    Coordinate the complete document-ingestion pipeline.

    This service acts only as an orchestrator. Detailed operations are
    delegated to:

    - BlobStorage for downloading and uploading files
    - DocumentParser for extracting text and images
    - ChunkingService for producing validated text chunks
    - EmbeddingService for generating vectors
    - CaptionService for describing extracted images
    - IngestionRepository for PostgreSQL persistence

    Parameters
    ----------
    blob_storage:
        Storage implementation used to download source documents and upload
        extracted images.

    document_parser:
        Parser capable of handling the supported PDF and DOCX documents.

    source_container:
        Blob container containing the original source documents.

    ingestion_repository:
        Repository responsible for storing documents, chunks and images.

    chunking_service:
        Service responsible for creating validated, structure-aware chunks.

    embedding_service:
        Service responsible for generating chunk and caption embeddings.

    caption_service:
        Optional service for generating descriptions of extracted images.
        It is required when a document contains images.

    image_container:
        Blob container where extracted images will be uploaded. When omitted,
        the source document container is reused.
    """

    def __init__(
        self,
        blob_storage: BlobStorage,
        document_parser: DocumentParser,
        source_container: str,
        ingestion_repository: IngestionRepository,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        caption_service: CaptionService | None = None,
        image_container: str | None = None,
    ) -> None:
        if blob_storage is None:
            raise ValueError("blob_storage is required.")

        if document_parser is None:
            raise ValueError("document_parser is required.")

        if ingestion_repository is None:
            raise ValueError("ingestion_repository is required.")

        if chunking_service is None:
            raise ValueError("chunking_service is required.")

        if embedding_service is None:
            raise ValueError("embedding_service is required.")

        self._blob_storage = blob_storage
        self._document_parser = document_parser

        self._source_container = self._require_text(
            source_container,
            "source_container",
        )

        self._image_container = self._require_text(
            image_container or source_container,
            "image_container",
        )

        self._ingestion_repository = ingestion_repository
        self._chunking_service = chunking_service
        self._embedding_service = embedding_service
        self._caption_service = caption_service

    def extract_document(
        self,
        blob_name: str,
    ) -> ParsedDocument:
        """
        Download and parse one source document.

        This method extracts text units and embedded images but does not
        caption images, create embeddings or write anything to PostgreSQL.

        Parameters
        ----------
        blob_name:
            Full blob path of the source PDF or DOCX document.

        Returns
        -------
        ParsedDocument
            Parsed text units, extracted images and document metadata.
        """
        normalized_blob_name = self._require_blob_name(blob_name)

        document_bytes = self._blob_storage.download_blob(
            container_name=self._source_container,
            blob_name=normalized_blob_name,
        )

        return self._document_parser.parse(
            document_bytes=document_bytes,
            file_name=normalized_blob_name,
        )

    async def extract_and_caption_document(
        self,
        blob_name: str,
    ) -> IngestionResult:
        """
        Download, parse and caption one document.

        This method is useful for testing the parser and captioning pipeline
        without writing any records to PostgreSQL.
        """
        parsed_document = self.extract_document(blob_name)

        if self._caption_service is None:
            raise RuntimeError(
                "CaptionService has not been configured."
            )

        captioned_images = (
            await self._caption_service.caption_images(
                parsed_document.images
            )
        )

        return IngestionResult(
            parsed_document=parsed_document,
            captioned_images=captioned_images,
        )

    async def ingest_document(
        self,
        blob_name: str,
    ) -> UUID:
        """
        Run the complete ingestion workflow for one source document.

        The document record is created with a ``processing`` status. After
        successful parsing, chunking, embedding and persistence, its status
        becomes ``completed``.

        When an error occurs after the document record has been created, its
        status is changed to ``failed`` and the original exception is raised.

        Parameters
        ----------
        blob_name:
            Full Azure Blob Storage path of the source document.

        Returns
        -------
        UUID
            Database identifier of the successfully ingested document.
        """
        normalized_blob_name = self._require_blob_name(blob_name)
        document_id: UUID | None = None

        logger.info(
            "Starting ingestion for container=%s blob=%s",
            self._source_container,
            normalized_blob_name,
        )

        try:
            # ----------------------------------------------------------
            # 1. Download the original source document.
            # ----------------------------------------------------------

            document_bytes = self._blob_storage.download_blob(
                container_name=self._source_container,
                blob_name=normalized_blob_name,
            )

            if not document_bytes:
                raise ValueError(
                    f"Downloaded document is empty: "
                    f"{normalized_blob_name}"
                )

            # ----------------------------------------------------------
            # 2. Parse text units and extract embedded images.
            # ----------------------------------------------------------

            parsed_document = self._document_parser.parse(
                document_bytes=document_bytes,
                file_name=normalized_blob_name,
            )

            # ----------------------------------------------------------
            # 3. Create or reset the document database record.
            #
            # Re-ingesting the same container/blob combination should
            # reuse its existing document ID and reset its processing
            # status to "processing".
            # ----------------------------------------------------------

            document_id = (
                self._ingestion_repository.create_document(
                    file_name=self._source_file_name(
                        parsed_document.file_name
                    ),
                    file_type=parsed_document.file_type,
                    source_container=self._source_container,
                    source_blob_name=normalized_blob_name,
                    mime_type=self._mime_type_for(
                        parsed_document.file_type
                    ),
                    file_size_bytes=len(document_bytes),
                    checksum=self._sha256(document_bytes),
                    metadata=parsed_document.metadata,
                )
            )

            logger.info(
                "Document record prepared document_id=%s blob=%s",
                document_id,
                normalized_blob_name,
            )

            # ----------------------------------------------------------
            # 4-6. Chunk text, generate embeddings and save the chunks.
            # ----------------------------------------------------------

            await self._ingest_text_chunks(
                document_id=document_id,
                parsed_document=parsed_document,
                blob_name=normalized_blob_name,
            )

            # ----------------------------------------------------------
            # 7-10. Caption, upload, embed and save extracted images.
            #
            # This method is also called for documents without images so
            # that image rows from an earlier ingestion can be removed.
            # ----------------------------------------------------------

            await self._ingest_images(
                document_id=document_id,
                parsed_document=parsed_document,
                source_blob_name=normalized_blob_name,
            )

            # ----------------------------------------------------------
            # 11. Mark the document as successfully completed.
            # ----------------------------------------------------------

            self._ingestion_repository.mark_document_completed(
                document_id=document_id,
            )

            logger.info(
                "Ingestion completed document_id=%s blob=%s",
                document_id,
                normalized_blob_name,
            )

            return document_id

        except Exception as exc:
            logger.exception(
                "Ingestion failed document_id=%s blob=%s",
                document_id,
                normalized_blob_name,
            )

            # The document record may not exist when downloading or parsing
            # fails before create_document() has been called.
            if document_id is not None:
                try:
                    self._ingestion_repository.mark_document_failed(
                        document_id=document_id,
                        error_message=self._error_message(exc),
                    )
                except Exception:
                    # Do not replace the original ingestion exception with a
                    # secondary error from the status-update operation.
                    logger.exception(
                        "Failed to update document status to failed "
                        "for document_id=%s",
                        document_id,
                    )

            raise

    async def _ingest_text_chunks(
        self,
        *,
        document_id: UUID,
        parsed_document: ParsedDocument,
        blob_name: str,
    ) -> None:
        """
        Create, embed and persist text chunks for one document.

        Chunk construction and validation remain the responsibility of
        ChunkingService. This method only converts parser models and
        coordinates the downstream operations.
        """
        parsed_units = self._to_chunking_units(
            parsed_document.text_units
        )

        chunking_result = self._chunking_service.process(
            parsed_units=parsed_units,
            document_id=str(document_id),
            file_name=self._source_file_name(
                parsed_document.file_name
            ),
            blob_name=blob_name,
            file_type=parsed_document.file_type,
        )

        embedding_result = (
            await self._embedding_service.embed_chunks(
                chunking_result.chunks
            )
        )

        self._ingestion_repository.save_chunks(
            document_id=document_id,
            chunks=chunking_result.chunks,
            embeddings=list(embedding_result.embeddings),
        )

        logger.info(
            "Stored text chunks document_id=%s chunks=%d warnings=%d",
            document_id,
            chunking_result.chunk_count,
            chunking_result.warning_count,
        )

    async def _ingest_images(
        self,
        *,
        document_id: UUID,
        parsed_document: ParsedDocument,
        source_blob_name: str,
    ) -> None:
        """
        Caption, upload, embed and persist extracted document images.

        Images are uploaded before their database records are created so that
        every stored image row refers to an existing blob.
        """
        if not parsed_document.images:
            # Delete image records that may exist from an older ingestion of
            # the same document.
            self._ingestion_repository.save_images(
                document_id=document_id,
                captioned_images=[],
                caption_embeddings=[],
                image_container=self._image_container,
            )

            logger.info(
                "No extracted images found document_id=%s",
                document_id,
            )
            return

        if self._caption_service is None:
            raise RuntimeError(
                "CaptionService must be configured when a document "
                "contains extracted images."
            )

        captioned_images = (
            await self._caption_service.caption_images(
                parsed_document.images
            )
        )

        if not captioned_images:
            return

        uploaded_images: list[CaptionedImage] = []

        for captioned_image in captioned_images:
            image = captioned_image.image

            image_blob_name = self._build_image_blob_name(
                document_id=document_id,
                source_blob_name=source_blob_name,
                image_index=image.image_index,
                image_file_name=image.file_name,
            )

            # BlobStorage.upload_blob returns the actual stored blob name.
            stored_blob_name = self._blob_storage.upload_blob(
                container_name=self._image_container,
                blob_name=image_blob_name,
                data=image.image_bytes,
                content_type=image.mime_type,
            )

            normalized_stored_name = self._require_text(
                stored_blob_name,
                "stored image blob name",
            )

            # CaptionedImage is a dataclass. Create a new instance rather
            # than changing the original object returned by CaptionService.
            updated_metadata = dict(captioned_image.metadata)
            updated_metadata["image_blob_name"] = (
                normalized_stored_name
            )
            updated_metadata["source_blob_name"] = source_blob_name

            uploaded_images.append(
                replace(
                    captioned_image,
                    metadata=updated_metadata,
                )
            )

        # Convert image captions into generic embedding inputs.
        caption_inputs = [
            EmbeddingInput(
                item_id=(
                    f"{document_id}:image:"
                    f"{captioned_image.image.image_index}"
                ),
                text=captioned_image.caption,
                metadata={
                    "source_type": "image_caption",
                    "document_id": str(document_id),
                    "image_index": (
                        captioned_image.image.image_index
                    ),
                    "page_number": (
                        captioned_image.image.page_number
                    ),
                    "image_blob_name": (
                        captioned_image.metadata[
                            "image_blob_name"
                        ]
                    ),
                },
            )
            for captioned_image in uploaded_images
        ]

        caption_embedding_result = (
            await self._embedding_service.embed_inputs(
                caption_inputs
            )
        )

        self._ingestion_repository.save_images(
            document_id=document_id,
            captioned_images=uploaded_images,
            caption_embeddings=list(
                caption_embedding_result.embeddings
            ),
            image_container=self._image_container,
        )

        logger.info(
            "Stored extracted images document_id=%s images=%d",
            document_id,
            len(uploaded_images),
        )

    @staticmethod
    def _to_chunking_units(
        text_units: list[TextUnit],
    ) -> list[dict[str, object]]:
        """
        Convert parser TextUnit objects into chunking dictionaries.

        Parser metadata is preserved so the structure analyzer can use
        page, paragraph, section and parser-specific information.
        """
        units: list[dict[str, object]] = []

        for text_unit in text_units:
            if not isinstance(text_unit, TextUnit):
                raise TypeError(
                    "Every parsed text unit must be a TextUnit."
                )

            unit: dict[str, object] = dict(text_unit.metadata)

            # Standard fields take precedence over duplicate keys from
            # parser-specific metadata.
            unit.update(
                {
                    "text": text_unit.text,
                    "page_number": text_unit.page_number,
                    "section": text_unit.section,
                    "paragraph_number": (
                        text_unit.paragraph_number
                    ),
                }
            )

            units.append(unit)

        return units

    @staticmethod
    def _build_image_blob_name(
        *,
        document_id: UUID,
        source_blob_name: str,
        image_index: int,
        image_file_name: str,
    ) -> str:
        """
        Build a deterministic blob path for an extracted image.

        Example
        -------
        extracted-images/<document-id>/0001_diagram.png
        """
        source_stem = PurePosixPath(
            source_blob_name
        ).stem.strip()

        safe_source_stem = (
            source_stem.replace(" ", "-") or "document"
        )

        original_name = (
            PurePosixPath(image_file_name).name.strip()
        )

        if not original_name:
            original_name = f"image-{image_index}"

        indexed_name = (
            f"{image_index:04d}_{original_name}"
        )

        return (
            f"extracted-images/"
            f"{safe_source_stem}/"
            f"{document_id}/"
            f"{indexed_name}"
        )

    @staticmethod
    def _source_file_name(file_name: str) -> str:
        """Return only the file-name portion of a blob path."""
        normalized_name = IngestionService._require_text(
            file_name,
            "file_name",
        )

        result = PurePosixPath(normalized_name).name

        if not result:
            raise ValueError(
                "file_name must identify a source file."
            )

        return result

    @staticmethod
    def _sha256(document_bytes: bytes) -> str:
        """Generate a SHA-256 checksum for the source document."""
        if not isinstance(document_bytes, bytes):
            raise TypeError(
                "document_bytes must be bytes."
            )

        if not document_bytes:
            raise ValueError(
                "document_bytes must not be empty."
            )

        return hashlib.sha256(document_bytes).hexdigest()

    @staticmethod
    def _mime_type_for(file_type: str) -> str:
        """Resolve the MIME type for a supported source file type."""
        normalized_type = IngestionService._require_text(
            file_type,
            "file_type",
        ).lower().lstrip(".")

        mime_types = {
            "pdf": "application/pdf",
            "docx": (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        }

        return mime_types.get(
            normalized_type,
            "application/octet-stream",
        )

    @staticmethod
    def _require_blob_name(blob_name: str) -> str:
        """Validate and normalize a source-document blob name."""
        normalized_name = IngestionService._require_text(
            blob_name,
            "blob_name",
        )

        path = PurePosixPath(normalized_name)

        if path.name in {"", ".", ".."}:
            raise ValueError(
                "blob_name must identify a source document."
            )

        return normalized_name

    @staticmethod
    def _require_text(
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize a required string value."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field_name} must be a non-empty string."
            )

        return value.strip()

    @staticmethod
    def _error_message(
        exception: Exception,
    ) -> str:
        """Create a useful database error message from an exception."""
        message = str(exception).strip()

        if not message:
            message = exception.__class__.__name__

        # Keep the error comfortably within typical database text limits.
        return message[:4000]