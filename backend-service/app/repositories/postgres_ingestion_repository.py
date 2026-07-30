from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.chunking.models import DocumentChunk
from app.database.session import SessionLocal
from app.embedding.models import EmbeddingVector
from app.ingestion.models import CaptionedImage
from app.repositories.ingestion_repository import (
    IngestionRepository,
)


class PostgresIngestionRepository(IngestionRepository):
    """
    Persist ingestion results in PostgreSQL.

    This repository handles document records, text chunks, embedding
    vectors, extracted-image metadata, and processing-status updates.
    """

    _CREATE_DOCUMENT_SQL = text(
        """
        INSERT INTO documents (
            file_name,
            file_type,
            source_container,
            source_blob_name,
            mime_type,
            file_size_bytes,
            checksum,
            processing_status,
            processing_error,
            metadata
        )
        VALUES (
            :file_name,
            :file_type,
            :source_container,
            :source_blob_name,
            :mime_type,
            :file_size_bytes,
            :checksum,
            'processing',
            NULL,
            CAST(:metadata AS jsonb)
        )
        ON CONFLICT (
            source_container,
            source_blob_name
        )
        DO UPDATE SET
            file_name = EXCLUDED.file_name,
            file_type = EXCLUDED.file_type,
            mime_type = EXCLUDED.mime_type,
            file_size_bytes = EXCLUDED.file_size_bytes,
            checksum = EXCLUDED.checksum,
            processing_status = 'processing',
            processing_error = NULL,
            metadata = EXCLUDED.metadata,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
    )

    _DELETE_EXISTING_CHUNKS_SQL = text(
        """
        DELETE FROM document_chunks
        WHERE document_id = :document_id
        """
    )

    _INSERT_CHUNK_SQL = text(
        """
        INSERT INTO document_chunks (
            document_id,
            chunk_index,
            content,
            embedding,
            content_type,
            token_count,
            section_path,
            metadata
        )
        VALUES (
            :document_id,
            :chunk_index,
            :content,
            CAST(:embedding AS vector),
            :content_type,
            :token_count,
            CAST(:section_path AS jsonb),
            CAST(:metadata AS jsonb)
        )
        """
    )

    _DELETE_EXISTING_IMAGES_SQL = text(
        """
        DELETE FROM document_images
        WHERE document_id = :document_id
        """
    )

    _INSERT_IMAGE_SQL = text(
        """
        INSERT INTO document_images (
            document_id,
            image_index,
            page_number,
            image_file_name,
            image_container,
            image_blob_name,
            caption,
            caption_embedding,
            mime_type,
            width,
            height,
            metadata
        )
        VALUES (
            :document_id,
            :image_index,
            :page_number,
            :image_file_name,
            :image_container,
            :image_blob_name,
            :caption,
            CAST(:caption_embedding AS vector),
            :mime_type,
            :width,
            :height,
            CAST(:metadata AS jsonb)
        )
        """
    )

    _MARK_COMPLETED_SQL = text(
        """
        UPDATE documents
        SET
            processing_status = 'completed',
            processing_error = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :document_id
        """
    )

    _MARK_FAILED_SQL = text(
        """
        UPDATE documents
        SET
            processing_status = 'failed',
            processing_error = :error_message,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = :document_id
        """
    )

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
    ) -> None:
        self._session_factory = session_factory

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
        Create or reset a document record for ingestion.

        Re-ingesting an existing blob reuses the existing document ID and
        resets its status to ``processing``.
        """
        normalized_file_name = self._require_text(
            file_name,
            "file_name",
        )
        normalized_file_type = self._require_text(
            file_type,
            "file_type",
        ).lower()
        normalized_container = self._require_text(
            source_container,
            "source_container",
        )
        normalized_blob_name = self._require_text(
            source_blob_name,
            "source_blob_name",
        )

        if file_size_bytes is not None and file_size_bytes < 0:
            raise ValueError(
                "file_size_bytes must not be negative."
            )

        with self._session_factory.begin() as session:
            document_id = session.execute(
                self._CREATE_DOCUMENT_SQL,
                {
                    "file_name": normalized_file_name,
                    "file_type": normalized_file_type,
                    "source_container": normalized_container,
                    "source_blob_name": normalized_blob_name,
                    "mime_type": (
                        mime_type.strip()
                        if mime_type
                        else None
                    ),
                    "file_size_bytes": file_size_bytes,
                    "checksum": (
                        checksum.strip()
                        if checksum
                        else None
                    ),
                    "metadata": self._to_json_value(
                        metadata or {}
                    ),
                },
            ).scalar_one()

        return UUID(str(document_id))

    def save_chunks(
        self,
        *,
        document_id: UUID,
        chunks: list[DocumentChunk],
        embeddings: list[EmbeddingVector],
    ) -> None:
        """
        Replace the stored chunks for one document.

        Chunk order and embedding identifiers are validated before any
        database changes are committed.
        """
        if not chunks:
            raise ValueError(
                "At least one document chunk is required."
            )

        if len(chunks) != len(embeddings):
            raise ValueError(
                "Chunk and embedding counts must match."
            )

        rows: list[dict[str, Any]] = []

        for chunk, embedding in zip(
            chunks,
            embeddings,
            strict=True,
        ):
            expected_item_id = (
                f"{document_id}:{chunk.chunk_index}"
            )

            embedding_item_id = getattr(
                embedding,
                "item_id",
                None,
            )

            if embedding_item_id != expected_item_id:
                raise ValueError(
                    "Embedding item ID does not match its chunk. "
                    f"Expected {expected_item_id!r}, "
                    f"received {embedding_item_id!r}."
                )

            if str(chunk.document_id) != str(document_id):
                raise ValueError(
                    "Chunk document_id does not match the "
                    "target document."
                )

            metadata = self._build_chunk_metadata(chunk)

            rows.append(
                {
                    "document_id": str(document_id),
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "embedding": self._to_vector_literal(
                        self._extract_embedding_values(
                            embedding
                        )
                    ),
                    "content_type": self._enum_value(
                        chunk.content_type
                    ),
                    "token_count": chunk.token_count,
                    "section_path": self._to_json_value(
                        chunk.section_path
                    ),
                    "metadata": self._to_json_value(
                        metadata
                    ),
                }
            )

        with self._session_factory.begin() as session:
            session.execute(
                self._DELETE_EXISTING_CHUNKS_SQL,
                {
                    "document_id": str(document_id),
                },
            )

            session.execute(
                self._INSERT_CHUNK_SQL,
                rows,
            )

    def save_images(
        self,
        *,
        document_id: UUID,
        captioned_images: list[CaptionedImage],
        caption_embeddings: list[EmbeddingVector],
        image_container: str,
    ) -> None:
        """
        Replace stored image records for one document.

        The uploaded image blob name can be supplied through
        ``CaptionedImage.metadata["image_blob_name"]``. When it is absent,
        the extracted image file name is used.
        """
        normalized_container = self._require_text(
            image_container,
            "image_container",
        )

        if len(captioned_images) != len(caption_embeddings):
            raise ValueError(
                "Captioned-image and embedding counts must match."
            )

        rows: list[dict[str, Any]] = []

        for captioned_image, embedding in zip(
            captioned_images,
            caption_embeddings,
            strict=True,
        ):
            image = captioned_image.image

            image_blob_name = str(
                captioned_image.metadata.get(
                    "image_blob_name",
                    image.file_name,
                )
            ).strip()

            if not image_blob_name:
                raise ValueError(
                    "An image blob name is required."
                )

            rows.append(
                {
                    "document_id": str(document_id),
                    "image_index": image.image_index,
                    "page_number": image.page_number,
                    "image_file_name": image.file_name,
                    "image_container": normalized_container,
                    "image_blob_name": image_blob_name,
                    "caption": captioned_image.caption,
                    "caption_embedding": (
                        self._to_vector_literal(
                            self._extract_embedding_values(
                                embedding
                            )
                        )
                    ),
                    "mime_type": image.mime_type,
                    "width": image.width,
                    "height": image.height,
                    "metadata": self._to_json_value(
                        self._build_image_metadata(
                            captioned_image
                        )
                    ),
                }
            )

        with self._session_factory.begin() as session:
            session.execute(
                self._DELETE_EXISTING_IMAGES_SQL,
                {
                    "document_id": str(document_id),
                },
            )

            if rows:
                session.execute(
                    self._INSERT_IMAGE_SQL,
                    rows,
                )

    def mark_document_completed(
        self,
        *,
        document_id: UUID,
    ) -> None:
        """Mark a successfully ingested document as completed."""
        with self._session_factory.begin() as session:
            result = session.execute(
                self._MARK_COMPLETED_SQL,
                {
                    "document_id": str(document_id),
                },
            )

            self._ensure_document_updated(
                row_count=result.rowcount,
                document_id=document_id,
            )

    def mark_document_failed(
        self,
        *,
        document_id: UUID,
        error_message: str,
    ) -> None:
        """Record an ingestion failure for a document."""
        normalized_error = self._require_text(
            error_message,
            "error_message",
        )

        with self._session_factory.begin() as session:
            result = session.execute(
                self._MARK_FAILED_SQL,
                {
                    "document_id": str(document_id),
                    "error_message": normalized_error[:4000],
                },
            )

            self._ensure_document_updated(
                row_count=result.rowcount,
                document_id=document_id,
            )

    @staticmethod
    def _build_chunk_metadata(
        chunk: DocumentChunk,
    ) -> dict[str, Any]:
        """Build retrieval metadata for one document chunk."""
        metadata = chunk.metadata.model_dump(mode="json")

        metadata.update(
            {
                "page_start": chunk.page_start,
                "page_end": chunk.page_end,
                "section": chunk.section,
                "paragraph_start": chunk.paragraph_start,
                "paragraph_end": chunk.paragraph_end,
            }
        )

        return metadata

    @staticmethod
    def _build_image_metadata(
        captioned_image: CaptionedImage,
    ) -> dict[str, Any]:
        """Combine extraction and caption metadata."""
        metadata = dict(captioned_image.image.metadata)

        metadata.update(captioned_image.metadata)
        metadata["caption_model"] = (
            captioned_image.caption_model
        )
        metadata["paragraph_number"] = (
            captioned_image.image.paragraph_number
        )

        return metadata

    @staticmethod
    def _extract_embedding_values(
        embedding: EmbeddingVector,
    ) -> list[float]:
        """Extract numerical values from an embedding model."""
        for field_name in (
            "values",
            "embedding",
            "vector",
        ):
            values = getattr(
                embedding,
                field_name,
                None,
            )

            if values is not None:
                vector = [
                    float(value)
                    for value in values
                ]

                if not vector:
                    break

                return vector

        raise ValueError(
            "EmbeddingVector does not contain usable vector values."
        )

    @staticmethod
    def _to_vector_literal(
        values: Sequence[float],
    ) -> str:
        """Convert embedding values to pgvector text input."""
        return "[" + ",".join(
            str(float(value))
            for value in values
        ) + "]"

    @staticmethod
    def _enum_value(value: object) -> str:
        """Return a serializable enum or string value."""
        raw_value = getattr(value, "value", value)
        return str(raw_value)

    @staticmethod
    def _to_json_value(value: object) -> str:
        """
        Serialize a Python value for PostgreSQL JSONB input.

        SQLAlchemy passes the resulting JSON string to PostgreSQL, where
        the SQL statement explicitly casts it to ``jsonb``.
        """
        import json

        return json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    @staticmethod
    def _require_text(
        value: str,
        field_name: str,
    ) -> str:
        """Validate and normalize a required text value."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"{field_name} must be a non-empty string."
            )

        return value.strip()

    @staticmethod
    def _ensure_document_updated(
        *,
        row_count: int | None,
        document_id: UUID,
    ) -> None:
        """Raise an error when the document record does not exist."""
        if row_count == 0:
            raise LookupError(
                f"Document {document_id} was not found."
            )