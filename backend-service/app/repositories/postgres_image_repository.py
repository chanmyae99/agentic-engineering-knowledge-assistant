from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.repositories.image_repository import ImageRepository
from app.retrieval.models import RetrievedImage


class PostgresImageRepository(ImageRepository):
    """Search document images using caption embeddings."""

    _SEMANTIC_SEARCH_SQL = text(
        """
        SELECT
            images.id,
            images.document_id,
            images.image_file_name,
            images.image_container,
            images.image_blob_name,
            images.caption,
            images.page_number,
            images.metadata,
            documents.file_name,
            (
                1 - (
                    images.caption_embedding
                    <=> CAST(:query_embedding AS vector)
                )
            ) AS score
        FROM document_images AS images
        INNER JOIN documents
            ON documents.id = images.document_id
        WHERE images.caption_embedding IS NOT NULL
        ORDER BY score DESC
        LIMIT :top_k
        """
    )

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
    ) -> None:
        self._session_factory = session_factory

    def semantic_search(
        self,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedImage]:
        if not query_embedding:
            raise ValueError(
                "Query embedding must not be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        embedding_literal = self._to_vector_literal(
            query_embedding
        )

        with self._session_factory() as session:
            rows = session.execute(
                self._SEMANTIC_SEARCH_SQL,
                {
                    "query_embedding": embedding_literal,
                    "top_k": top_k,
                },
            ).mappings().all()

        return [
            self._to_retrieved_image(dict(row))
            for row in rows
        ]

    @staticmethod
    def _to_vector_literal(
        embedding: list[float],
    ) -> str:
        return "[" + ",".join(
            str(float(value))
            for value in embedding
        ) + "]"

    @staticmethod
    def _to_retrieved_image(
        row: dict[str, Any],
    ) -> RetrievedImage:
        stored_metadata = row.get("metadata")

        metadata = (
            dict(stored_metadata)
            if isinstance(stored_metadata, dict)
            else {}
        )

        metadata.update(
            {
                "document_name": row.get("file_name"),
                "page": row.get("page_number"),
            }
        )

        return RetrievedImage(
            image_id=str(row["id"]),
            document_id=str(row["document_id"]),
            caption=row["caption"],
            score=float(row["score"] or 0.0),
            image_container=row["image_container"],
            image_blob_name=row["image_blob_name"],
            image_file_name=row["image_file_name"],
            metadata=metadata,
        )