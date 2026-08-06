from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.repositories.chunk_repository import ChunkRepository
from app.retrieval.models import RetrievedChunk


class PostgresChunkRepository(ChunkRepository):
    """Search document chunks stored in PostgreSQL with pgvector."""

    _HYBRID_SEARCH_SQL = text(
        """
        SELECT
            chunks.id,
            chunks.document_id,
            chunks.content,
            chunks.content_type,
            chunks.chunk_index,
            chunks.token_count,
            chunks.section_path,
            chunks.metadata,
            documents.file_name,
            (
                0.80 * (
                    1 - (
                        chunks.embedding
                        <=> CAST(:query_embedding AS vector)
                    )
                )
                +
                0.20 * LEAST(
                    ts_rank_cd(
                        chunks.search_vector,
                        websearch_to_tsquery(
                            'english',
                            :query_text
                        )
                    ),
                    1.0
                )
            ) AS combined_score
        FROM document_chunks AS chunks
        INNER JOIN documents
            ON documents.id = chunks.document_id
        ORDER BY combined_score DESC
        LIMIT :top_k
        """
    )

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
    ) -> None:
        self._session_factory = session_factory

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[RetrievedChunk]:
        normalized_query = query_text.strip()

        if not normalized_query:
            raise ValueError("Query text must not be empty.")

        if not query_embedding:
            raise ValueError("Query embedding must not be empty.")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero.")

        # PostgreSQL accepts pgvector text input such as:
        # [0.123,0.456,...]
        embedding_literal = self._to_vector_literal(
            query_embedding
        )

        with self._session_factory() as session:
            rows = session.execute(
                self._HYBRID_SEARCH_SQL,
                {
                    "query_text": normalized_query,
                    "query_embedding": embedding_literal,
                    "top_k": top_k,
                },
            ).mappings().all()

        return [
            self._to_retrieved_chunk(dict(row))
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
    def _to_retrieved_chunk(
        row: dict[str, Any],
    ) -> RetrievedChunk:
        stored_metadata = row.get("metadata")

        metadata = (
            dict(stored_metadata)
            if isinstance(stored_metadata, dict)
            else {}
        )

        page_start = metadata.get("page_start")
        page_end = metadata.get("page_end")

        metadata.update(
            {
                "document_name": row.get("file_name"),
                "chunk_index": row.get("chunk_index"),
                "content_type": row.get("content_type"),
                "token_count": row.get("token_count"),
                "section_path": row.get("section_path") or [],

                # Keep the detailed page range.
                "page_start": page_start,
                "page_end": page_end,

                # Compatibility field used by the current RAG source model.
                "page": page_start,
            }
        )

        return RetrievedChunk(
            chunk_id=str(row["id"]),
            document_id=str(row["document_id"]),
            content=row["content"],
            score=float(row["combined_score"] or 0.0),
            metadata=metadata,
        )